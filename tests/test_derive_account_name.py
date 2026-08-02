"""Tests for auto account name derivation from export selection."""
import json
import zipfile
from pathlib import Path

from smd.account_layout import (
    AccountPaths,
    load_account_identity,
    rename_simple_mode_account,
    save_account_identity,
)
from smd.export_detect import (
    AccountIdentity,
    derive_account_name_from_export,
    extract_account_identity_from_zip,
    extract_account_username_from_zip,
    find_existing_account_folder_name,
    format_account_folder_name,
    is_usable_account_folder_name,
    next_unknown_account_name,
)


def _write_zip(path: Path, *, account_json_body: dict | None = None, account_member: str = "json/account.json"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        if account_json_body is not None:
            zf.writestr(account_member, json.dumps(account_json_body))
        zf.writestr("memories/2018-01-01_00-00-00-main.jpg", b"fake")


def test_format_account_folder_name_display_and_username():
    identity = AccountIdentity(username="las_snap", display_name="Las")
    assert format_account_folder_name(identity) == "Las (las_snap)"


def test_format_account_folder_name_username_only():
    identity = AccountIdentity(username="real_username", display_name=None)
    assert format_account_folder_name(identity) == "real_username"


def test_format_account_folder_name_display_only():
    identity = AccountIdentity(username=None, display_name="Mary")
    assert format_account_folder_name(identity) == "Mary"


def test_format_account_folder_name_same_display_and_username():
    identity = AccountIdentity(username="las", display_name="Las")
    assert format_account_folder_name(identity) == "Las"


def test_extract_identity_flat_keys(tmp_path):
    zpath = tmp_path / "mydata~1.zip"
    _write_zip(zpath, account_json_body={"username": "las_snap", "display_name": "Las"})
    identity = extract_account_identity_from_zip([zpath])
    assert identity == AccountIdentity(username="las_snap", display_name="Las")


def test_extract_username_flat_key(tmp_path):
    zpath = tmp_path / "mydata~1.zip"
    _write_zip(zpath, account_json_body={"username": "las_snap", "display_name": "Las"})
    assert extract_account_username_from_zip([zpath]) == "las_snap"


def test_extract_username_nested_capitalized_key(tmp_path):
    zpath = tmp_path / "mydata~2.zip"
    _write_zip(
        zpath,
        account_json_body={"Basic Information": {"Username": "nested_user", "Display Name": "Nested"}},
        account_member="json/account_history.json",
    )
    identity = extract_account_identity_from_zip([zpath])
    assert identity.username == "nested_user"
    assert identity.display_name == "Nested"


def test_extract_username_missing_account_file(tmp_path):
    zpath = tmp_path / "mydata~3.zip"
    _write_zip(zpath, account_json_body=None)
    assert extract_account_identity_from_zip([zpath]) is None


def test_extract_username_missing_zip_file_does_not_raise(tmp_path):
    assert extract_account_identity_from_zip([tmp_path / "does-not-exist.zip"]) is None


def test_derive_account_name_uses_display_and_username(tmp_path):
    export_dir = tmp_path / "Downloads"
    zpath = export_dir / "mydata~1783373820861.zip"
    _write_zip(zpath, account_json_body={"username": "real_username", "display_name": "Las"})
    assert derive_account_name_from_export(export_dir, [zpath]) == "Las (real_username)"


def test_derive_account_name_prefers_zip_identity_over_generic_folder(tmp_path):
    export_dir = tmp_path / "Downloads"
    zpath = export_dir / "mydata~1783373820861.zip"
    _write_zip(zpath, account_json_body={"username": "real_username"})
    assert derive_account_name_from_export(export_dir, [zpath]) == "real_username"


def test_derive_account_name_prefers_zip_identity_over_named_folder(tmp_path):
    export_dir = tmp_path / "SomeFolder"
    zpath = export_dir / "mydata~1.zip"
    _write_zip(zpath, account_json_body={"username": "real_username", "display_name": "Las"})
    assert derive_account_name_from_export(export_dir, [zpath]) == "Las (real_username)"


def test_folder_selection_uses_folder_name(tmp_path):
    export_dir = tmp_path / "Las"
    export_dir.mkdir()
    zips = [export_dir / "mydata~1783373820861.zip"]
    assert derive_account_name_from_export(export_dir, zips) == "Las"


def test_zip_file_uses_parent_folder_name(tmp_path):
    export_dir = tmp_path / "Mary"
    export_dir.mkdir()
    zips = [export_dir / "mydata~999.zip"]
    assert derive_account_name_from_export(zips[0], zips) == "Mary"


def test_generic_downloads_folder_with_no_identity_falls_back_to_unknown_account(tmp_path):
    export_dir = tmp_path / "Downloads"
    export_dir.mkdir()
    zips = [export_dir / "mydata~1783373820861.zip"]
    assert derive_account_name_from_export(export_dir, zips) == "Unknown account 1"


def test_next_unknown_account_name_starts_at_one(tmp_path):
    assert next_unknown_account_name([tmp_path]) == "Unknown account 1"


def test_next_unknown_account_name_skips_used_numbers(tmp_path):
    (tmp_path / "Unknown account 1").mkdir()
    (tmp_path / "Unknown account 2").mkdir()
    assert next_unknown_account_name([tmp_path]) == "Unknown account 3"


def test_next_unknown_account_name_fills_gap_left_by_rename(tmp_path):
    # "Unknown account 1" was renamed away to something else, "Unknown
    # account 2" still exists untouched - the freed-up number 1 is reused
    # rather than always incrementing forever.
    (tmp_path / "Random Friend").mkdir()
    (tmp_path / "Unknown account 2").mkdir()
    assert next_unknown_account_name([tmp_path]) == "Unknown account 1"


def test_unknown_account_folder_survives_rename_to_unrelated_name(tmp_path, monkeypatch):
    """The core "what if the user renames the folder?" scenario: an export
    with no identity info gets "Unknown account 1", the user renames that
    folder to "Random Friend", and re-selecting the *same* export later must
    resolve back to "Random Friend" - not mint a new "Unknown account 2"."""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    export_dir = tmp_path / "Downloads"
    zpath = export_dir / "mydata~1783373820861.zip"
    _write_zip(zpath, account_json_body=None)

    # First run: no identity anywhere -> "Unknown account 1".
    first_name = derive_account_name_from_export(export_dir, [zpath], search_dirs=[desktop])
    assert first_name == "Unknown account 1"

    # Simulate the run completing: folder created + identity (mydata id only,
    # no username/display name) persisted, exactly like start_download() does.
    (desktop / first_name).mkdir()
    save_account_identity(desktop / first_name, mydata_ids=["mydata~1783373820861"])

    # User renames the folder in Explorer to something with zero identifying text.
    renamed = desktop / "Random Friend"
    (desktop / first_name).rename(renamed)

    # Re-selecting the exact same export ZIP later must find "Random Friend",
    # not create "Unknown account 2".
    second_name = derive_account_name_from_export(export_dir, [zpath], search_dirs=[desktop])
    assert second_name == "Random Friend"


def test_existing_output_folder_match(tmp_path):
    out_root = tmp_path / "Desktop"
    out_root.mkdir()
    (out_root / "export-1783373820861").mkdir()
    zips = [tmp_path / "Downloads" / "mydata~1783373820861.zip"]
    zips[0].parent.mkdir()
    zips[0].write_bytes(b"x")
    name = derive_account_name_from_export(zips[0], zips, search_dirs=[out_root])
    assert name == "export-1783373820861"


def test_find_existing_account_folder_by_saved_identity(tmp_path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    old_folder = desktop / "Las"
    old_folder.mkdir()

    internal_root = tmp_path / "internal"
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))
    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))

    internal = internal_root / "Las"
    internal.mkdir(parents=True)
    save_account_identity(internal, account_name="Las", mydata_ids=["mydata~1"])

    identity = AccountIdentity(mydata_ids=frozenset(["mydata~1"]))
    assert find_existing_account_folder_name([desktop], identity=identity) == "Las"


def test_rename_simple_mode_account_moves_desktop_and_internal(tmp_path, monkeypatch):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "Las").mkdir()
    internal_root = tmp_path / "internal"
    (internal_root / "Las").mkdir(parents=True)

    monkeypatch.setattr(AccountPaths, "user_desktop_dir", classmethod(lambda cls, name: desktop / name))
    monkeypatch.setattr(AccountPaths, "internal_accounts_root", classmethod(lambda cls: internal_root))

    actions = rename_simple_mode_account("Las", "Las (las_snap)")
    assert actions
    assert (desktop / "Las (las_snap)").is_dir()
    assert (internal_root / "Las (las_snap)").is_dir()
    assert load_account_identity(desktop / "Las (las_snap)") is None


def test_is_usable_account_folder_name():
    assert is_usable_account_folder_name("Las")
    assert is_usable_account_folder_name("Las (las_snap)")
    assert not is_usable_account_folder_name("Downloads")
    assert not is_usable_account_folder_name("mydata~123")
