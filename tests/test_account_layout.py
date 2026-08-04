"""Tests for account folder layout and migration."""
import json
import tempfile
from pathlib import Path

from smd.account_layout import (
    AccountPaths,
    collapse_merged_to_flat,
    ensure_memories_suffix,
    load_account_layout_info,
    migrate_account_layout,
    migrate_accounts_out_of_desktop_wrapper,
    migrate_flat_accounts_root,
    resolve_account_paths,
    resolve_existing_account_layout,
    save_account_layout_info,
    technical_storage_summary,
)


def test_migrate_legacy_layout():
    with tempfile.TemporaryDirectory() as tmp:
        account = Path(tmp) / "Las"
        downloads = account / "downloads"
        staging = downloads / ".staging"
        staging.mkdir(parents=True)
        (staging / "2020-01-01_uid-main.mp4").write_bytes(b"x")

        json_legacy = account / "json"
        json_legacy.mkdir(parents=True)
        (json_legacy / "memories_history.json").write_text("{}", encoding="utf-8")

        (downloads / ".local_checkpoint.json").write_text(
            json.dumps({"version": 3, "completed_stems": [], "skipped_stems": []}),
            encoding="utf-8",
        )
        (downloads / "reports").mkdir()
        (downloads / "reports" / "processing_report.json").write_text("{}", encoding="utf-8")

        paths = AccountPaths.for_account(account)
        paths.ensure_dirs()
        actions = migrate_account_layout(paths)

        assert paths.staging_dir.is_dir()
        assert any(paths.staging_dir.iterdir())
        assert paths.json_path.exists()
        assert paths.checkpoint_path.exists()
        assert (paths.reports_dir / "processing_report.json").exists()
        assert not (downloads / ".staging").exists()
        assert not (account / "json").exists()
        assert actions


def test_resolve_creates_technical_readme():
    with tempfile.TemporaryDirectory() as tmp:
        account = Path(tmp) / "Test"
        paths = resolve_account_paths(account, migrate=True)
        readme = paths.technical_dir / "README.txt"
        assert readme.exists()
        assert "staging" in readme.read_text(encoding="utf-8").lower()


def test_migrate_flat_accounts_root():
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        legacy_account = base_dir / "accounts" / "Las"
        (legacy_account / "downloads").mkdir(parents=True)
        (legacy_account / "downloads" / "photo.jpg").write_bytes(b"x")

        actions = migrate_flat_accounts_root(base_dir)

        assert (base_dir / "Las" / "downloads" / "photo.jpg").exists()
        assert not (base_dir / "accounts").exists()
        assert actions


def test_migrate_flat_accounts_root_skips_existing_target():
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        (base_dir / "accounts" / "Las").mkdir(parents=True)
        (base_dir / "Las").mkdir()
        (base_dir / "Las" / "keep.txt").write_text("keep", encoding="utf-8")

        migrate_flat_accounts_root(base_dir)

        # Pre-existing flat folder is never overwritten.
        assert (base_dir / "Las" / "keep.txt").exists()


def test_migrate_flat_accounts_root_noop_without_legacy_folder():
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        assert migrate_flat_accounts_root(base_dir) == []


def test_technical_storage_summary():
    with tempfile.TemporaryDirectory() as tmp:
        account = Path(tmp) / "Las"
        paths = resolve_account_paths(account, migrate=True)
        (paths.staging_dir / "big.bin").write_bytes(b"x" * 2048)
        rows = technical_storage_summary(paths)
        staging_size = next(size for label, size in rows if label == "staging")
        assert staging_size >= 2048


def test_copy_run_info_into_library_skips_staging():
    from smd.account_layout import RUN_INFO_DIRNAME, copy_run_info_into_library

    with tempfile.TemporaryDirectory() as tmp:
        account = Path(tmp) / "Las-memories"
        paths = resolve_account_paths(account, migrate=True)
        (paths.staging_dir / "huge.bin").write_bytes(b"x" * 4096)
        (paths.json_dir / "memories_history.json").write_text("{}", encoding="utf-8")
        (paths.reports_dir / "note.txt").write_text("ok", encoding="utf-8")
        dest, copied = copy_run_info_into_library(paths)
        assert dest == paths.library_root / RUN_INFO_DIRNAME
        assert dest.is_dir()
        assert "json" in copied
        assert "reports" in copied
        assert "ABOUT.txt" in copied
        assert not (dest / "staging").exists()


# --- ensure_memories_suffix -------------------------------------------------

def test_ensure_memories_suffix_appends_when_missing():
    assert ensure_memories_suffix("Las") == "Las-memories"


def test_ensure_memories_suffix_is_case_insensitive_and_idempotent():
    assert ensure_memories_suffix("Las-Memories") == "Las-Memories"
    assert ensure_memories_suffix("Las-memories") == "Las-memories"


def test_ensure_memories_suffix_handles_blank_input():
    assert ensure_memories_suffix("") == ""
    assert ensure_memories_suffix("   ") == ""


# --- AccountPaths.for_account / for_user keep_raw ---------------------------

def test_for_account_flat_when_keep_raw_false():
    account = Path("C:/fake/Las-memories")
    paths = AccountPaths.for_account(account, keep_raw=False)
    assert paths.merged_dir == paths.downloads_dir == account
    assert paths.raw_dir == account / "technical" / "raw_unused"
    assert paths.library_root == account


def test_for_account_nested_when_keep_raw_true():
    account = Path("C:/fake/Las-memories")
    paths = AccountPaths.for_account(account, keep_raw=True)
    assert paths.merged_dir == account / "merged"
    assert paths.raw_dir == account / "raw"
    assert paths.library_root == account


def test_for_user_flat_when_keep_raw_false(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    paths = AccountPaths.for_user("Las-memories", keep_raw=False)
    assert paths.merged_dir == paths.downloads_dir == desktop / "Las-memories"


def test_for_user_nested_when_keep_raw_true(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    paths = AccountPaths.for_user("Las-memories", keep_raw=True)
    assert paths.merged_dir == desktop / "Las-memories" / "merged"
    assert paths.raw_dir == desktop / "Las-memories" / "raw"


# --- layout persistence -----------------------------------------------------

def test_save_and_load_account_layout_info_roundtrip(tmp_path):
    account = tmp_path / "Las-memories"
    save_account_layout_info(account, layout="technical", base_dir=str(tmp_path), keep_raw=True)
    info = load_account_layout_info(account)
    assert info == {"layout": "technical", "base_dir": str(tmp_path), "keep_raw": True}


def test_save_account_layout_info_merges_with_existing_identity(tmp_path):
    from smd.account_layout import save_account_identity

    account = tmp_path / "Las-memories"
    save_account_identity(account, account_name="Las-memories", mydata_ids=["mydata~1"])
    save_account_layout_info(account, layout="simple", keep_raw=False)

    data = json.loads((account / "technical" / "account_identity.json").read_text(encoding="utf-8"))
    assert data["account_name"] == "Las-memories"
    assert "username" not in data
    assert "display_name" not in data
    assert data["layout"] == "simple"
    assert data["keep_raw"] is False


def test_load_account_layout_info_missing_returns_none(tmp_path):
    assert load_account_layout_info(tmp_path / "NoSuchAccount") is None


# --- resolve_existing_account_layout ----------------------------------------

def test_resolve_existing_account_layout_prefers_stored_simple_info(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    save_account_layout_info(internal_root / "Las-memories", layout="simple", keep_raw=True)

    result = resolve_existing_account_layout("Las-memories", tmp_path / "base")
    assert result == ("simple", None, True)


def test_resolve_existing_account_layout_prefers_stored_technical_info(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    base_dir = tmp_path / "base"
    save_account_layout_info(base_dir / "Las-memories", layout="technical", base_dir=str(base_dir), keep_raw=False)

    result = resolve_existing_account_layout("Las-memories", base_dir)
    assert result == ("technical", base_dir, False)


def test_resolve_existing_account_layout_falls_back_to_disk_when_no_stored_info(monkeypatch, tmp_path):
    from smd.account_layout import RUN_INFO_DIRNAME

    desktop = tmp_path / "Desktop"
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    lib = desktop / "Las-memories"
    lib.mkdir(parents=True)
    # Legacy account without identity JSON still counts if SMK-run-info exists.
    (lib / RUN_INFO_DIRNAME).mkdir()
    (lib / RUN_INFO_DIRNAME / "ABOUT.txt").write_text("SMK run info\n", encoding="utf-8")

    result = resolve_existing_account_layout("Las-memories", tmp_path / "base")
    assert result == ("simple", None, False)


def test_resolve_existing_account_layout_ignores_non_smk_desktop_folder(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    (desktop / "USB2").mkdir(parents=True)
    (desktop / "USB2" / "photo.jpg").write_bytes(b"x")
    assert resolve_existing_account_layout("USB2", tmp_path / "base") is None


def test_resolve_existing_account_layout_returns_none_for_unknown_account(monkeypatch, tmp_path):
    desktop = tmp_path / "Desktop"
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    assert resolve_existing_account_layout("Never Created", tmp_path / "base") is None


def test_resolve_existing_account_layout_blank_name_returns_none(tmp_path):
    assert resolve_existing_account_layout("", tmp_path) is None


# --- collapse_merged_to_flat -------------------------------------------------

def test_collapse_merged_to_flat_moves_files_when_no_raw(tmp_path):
    media_root = tmp_path / "Memories"
    merged = media_root / "merged"
    merged.mkdir(parents=True)
    (merged / "a.jpg").write_bytes(b"x")
    (merged / "b.mp4").write_bytes(b"y")

    moved = collapse_merged_to_flat(media_root)

    assert moved is True
    assert (media_root / "a.jpg").exists()
    assert (media_root / "b.mp4").exists()
    assert not merged.exists()


def test_collapse_merged_to_flat_keeps_nesting_when_raw_has_content(tmp_path):
    media_root = tmp_path / "Memories"
    merged = media_root / "merged"
    raw = media_root / "raw"
    merged.mkdir(parents=True)
    raw.mkdir(parents=True)
    (merged / "a.jpg").write_bytes(b"x")
    (raw / "a.jpg").write_bytes(b"x-raw")

    moved = collapse_merged_to_flat(media_root)

    assert moved is False
    assert (merged / "a.jpg").exists()
    assert (raw / "a.jpg").exists()


def test_collapse_merged_to_flat_removes_empty_raw_folder(tmp_path):
    media_root = tmp_path / "Memories"
    merged = media_root / "merged"
    raw = media_root / "raw"
    merged.mkdir(parents=True)
    raw.mkdir(parents=True)
    (merged / "a.jpg").write_bytes(b"x")

    moved = collapse_merged_to_flat(media_root)

    assert moved is True
    assert (media_root / "a.jpg").exists()
    assert not raw.exists()


def test_collapse_merged_to_flat_noop_without_merged_folder(tmp_path):
    media_root = tmp_path / "Memories"
    media_root.mkdir(parents=True)
    assert collapse_merged_to_flat(media_root) is False


def test_collapse_merged_to_flat_never_overwrites_existing_flat_file(tmp_path):
    media_root = tmp_path / "Memories"
    merged = media_root / "merged"
    merged.mkdir(parents=True)
    (merged / "a.jpg").write_bytes(b"from-merged")
    (media_root / "a.jpg").write_bytes(b"already-flat")

    collapse_merged_to_flat(media_root)

    assert (media_root / "a.jpg").read_bytes() == b"already-flat"


# --- migrate_account_layout: legacy always-nested merged/ collapses --------

def test_migrate_account_layout_flattens_legacy_nested_merged_when_flat(tmp_path):
    """Accounts created before keep_raw existed always nested merged/(+raw/).
    A flat-mode account (keep_raw=False, the common case) should end up with
    photos directly in the account folder, not stuck one level down."""
    account = tmp_path / "Las-memories"
    legacy_downloads = account / "downloads"
    legacy_merged = legacy_downloads / "merged"
    legacy_merged.mkdir(parents=True)
    (legacy_merged / "2020-01-01_photo.jpg").write_bytes(b"x")

    paths = AccountPaths.for_account(account, keep_raw=False)
    paths.ensure_dirs(keep_raw=False)
    migrate_account_layout(paths)

    assert (paths.downloads_dir / "2020-01-01_photo.jpg").exists()
    assert not (paths.downloads_dir / "merged").exists()


def test_migrate_account_layout_keeps_nesting_when_keep_raw_true(tmp_path):
    """A keep_raw=True account wants merged/+raw/ nested - migration must
    not flatten it even though the legacy layout also happened to nest."""
    account = tmp_path / "Las-memories"
    legacy_downloads = account / "downloads"
    legacy_merged = legacy_downloads / "merged"
    legacy_raw = legacy_downloads / "raw"
    legacy_merged.mkdir(parents=True)
    legacy_raw.mkdir(parents=True)
    (legacy_merged / "2020-01-01_photo.jpg").write_bytes(b"x")
    (legacy_raw / "2020-01-01_photo.jpg").write_bytes(b"raw-x")

    paths = AccountPaths.for_account(account, keep_raw=True)
    paths.ensure_dirs(keep_raw=True)
    migrate_account_layout(paths)

    assert (paths.merged_dir / "2020-01-01_photo.jpg").exists()
    assert (paths.raw_dir / "2020-01-01_photo.jpg").exists()


def test_migrate_account_layout_lifts_legacy_downloads_to_account_root(tmp_path):
    account = tmp_path / "Las-memories"
    legacy_downloads = account / "downloads"
    legacy_downloads.mkdir(parents=True)
    (legacy_downloads / "loose.jpg").write_bytes(b"x")

    paths = AccountPaths.for_account(account, keep_raw=False)
    paths.ensure_dirs(keep_raw=False)
    migrate_account_layout(paths)

    assert not legacy_downloads.exists()
    assert (account / "loose.jpg").exists()


def test_migrate_account_layout_lifts_nested_memories_wrapper(tmp_path):
    account = tmp_path / "Mary-memories"
    nested = account / "Memories"
    nested.mkdir(parents=True)
    (nested / "photo.jpg").write_bytes(b"x")

    paths = AccountPaths.for_account(account, keep_raw=False)
    paths.ensure_dirs(keep_raw=False)
    migrate_account_layout(paths)

    assert (account / "photo.jpg").exists()
    assert not nested.exists()


def test_migrate_accounts_out_of_desktop_wrapper(tmp_path, monkeypatch):
    import smd.account_layout as layout

    desktop = tmp_path / "Desktop"
    wrapper = desktop / "Memories"
    account = wrapper / "Mary-memories"
    (account / "technical").mkdir(parents=True)
    (account / "photo.jpg").write_bytes(b"x")
    monkeypatch.setattr(layout.Path, "home", staticmethod(lambda: tmp_path))

    new_base, actions = migrate_accounts_out_of_desktop_wrapper(wrapper)

    assert new_base == desktop
    assert (desktop / "Mary-memories" / "photo.jpg").exists()
    assert actions
    assert not wrapper.exists() or not any(wrapper.iterdir())


def test_migrate_empty_legacy_wrapper_still_returns_desktop(tmp_path, monkeypatch):
    import smd.account_layout as layout
    from smd.account_layout import is_legacy_desktop_accounts_wrapper

    desktop = tmp_path / "Desktop"
    wrapper = desktop / "Memories"
    wrapper.mkdir(parents=True)
    monkeypatch.setattr(layout.Path, "home", staticmethod(lambda: tmp_path))

    assert is_legacy_desktop_accounts_wrapper(wrapper)
    new_base, actions = migrate_accounts_out_of_desktop_wrapper(wrapper)
    assert new_base == desktop
    assert actions
    assert not wrapper.exists()
