"""Account folder layout: user media vs technical/developer data."""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from smd.branding import INTERNAL_APP_DIRNAME  # noqa: E402 — re-export for callers

TECHNICAL_DIRNAME = "technical"
DOWNLOADS_DIRNAME = "downloads"  # legacy name, kept for migration only
MEMORIES_DIRNAME = "Memories"
MEMORIES_SUFFIX = "-memories"
README_NAME = "README.txt"
ACCOUNT_IDENTITY_NAME = "account_identity.json"
RUN_INFO_DIRNAME = "SMK-run-info"
# Legacy locations (pre-restructure)
LEGACY_STAGING = ".staging"
LEGACY_CHECKPOINT = ".local_checkpoint.json"


def ensure_memories_suffix(name: str) -> str:
    """Append '-memories' to an account name unless it already ends with it
    (case-insensitive), so folder names are self-explanatory on the Desktop
    (e.g. "Las" -> "Las-memories")."""
    name = (name or "").strip()
    if not name:
        return name
    if name.lower().endswith(MEMORIES_SUFFIX):
        return name
    return f"{name}{MEMORIES_SUFFIX}"


@dataclass(frozen=True)
class AccountPaths:
    account_dir: Path
    downloads_dir: Path
    merged_dir: Path
    raw_dir: Path
    technical_dir: Path
    staging_dir: Path
    json_dir: Path
    json_path: Path
    reports_dir: Path
    checkpoint_path: Path
    quarantine_dir: Path
    logs_dir: Path
    debug_dir: Path

    @property
    def library_root(self) -> Path:
        """User-facing library folder (Desktop/<account> or parent of merged/)."""
        if self.merged_dir.name == "merged":
            return self.merged_dir.parent
        return self.merged_dir

    @classmethod
    def internal_accounts_root(cls) -> Path:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local / INTERNAL_APP_DIRNAME / "accounts"

    @classmethod
    def user_desktop_dir(cls, account_name: str) -> Path:
        return Path.home() / "Desktop" / account_name

    @classmethod
    def for_user(cls, account_name: str, *, keep_raw: bool = False) -> AccountPaths:
        """
        Simple layout: photos/videos on Desktop/<account>/.
        Checkpoints, staging, JSON live under %LOCALAPPDATA% only.
        """
        internal = cls.internal_accounts_root() / account_name
        desktop = cls.user_desktop_dir(account_name)
        technical = internal / TECHNICAL_DIRNAME
        if keep_raw:
            merged = desktop / "merged"
            raw = desktop / "raw"
        else:
            merged = desktop
            raw = technical / "raw_unused"
        return cls(
            account_dir=internal,
            downloads_dir=desktop,
            merged_dir=merged,
            raw_dir=raw,
            technical_dir=technical,
            staging_dir=technical / "staging",
            json_dir=technical / "json",
            json_path=technical / "json" / "memories_history.json",
            reports_dir=technical / "reports",
            checkpoint_path=technical / "checkpoint" / "local_checkpoint.json",
            quarantine_dir=technical / "quarantine",
            logs_dir=technical / "logs",
            debug_dir=technical / "debug",
        )

    def ensure_user_dirs(self, *, keep_raw: bool = False) -> None:
        """Create folders for simple user layout."""
        self.merged_dir.mkdir(parents=True, exist_ok=True)
        if keep_raw:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
        for d in (
            self.technical_dir,
            self.staging_dir,
            self.json_dir,
            self.reports_dir,
            self.checkpoint_path.parent,
            self.quarantine_dir,
            self.logs_dir,
            self.debug_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_account(cls, account_dir: Path, *, keep_raw: bool = False) -> AccountPaths:
        """
        Technical layout: photos/videos directly in <account_dir>/ plus
        technical/ working data beside them (same idea as simple mode's
        Desktop/<account>/, just under the user's chosen base dir).

        Nested merged/ (+ raw/) only when keep_raw is on; otherwise media
        sits flat in the account folder - no extra Memories/ wrapper.
        """
        account_dir = Path(account_dir)
        technical = account_dir / TECHNICAL_DIRNAME
        if keep_raw:
            merged = account_dir / "merged"
            raw = account_dir / "raw"
        else:
            merged = account_dir
            raw = technical / "raw_unused"
        return cls(
            account_dir=account_dir,
            downloads_dir=account_dir,
            merged_dir=merged,
            raw_dir=raw,
            technical_dir=technical,
            staging_dir=technical / "staging",
            json_dir=technical / "json",
            json_path=technical / "json" / "memories_history.json",
            reports_dir=technical / "reports",
            checkpoint_path=technical / "checkpoint" / "local_checkpoint.json",
            quarantine_dir=technical / "quarantine",
            logs_dir=technical / "logs",
            debug_dir=technical / "debug",
        )

    def ensure_dirs(self, *, keep_raw: bool = False) -> None:
        self.merged_dir.mkdir(parents=True, exist_ok=True)
        if keep_raw:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
        for d in (
            self.downloads_dir,
            self.technical_dir,
            self.staging_dir,
            self.json_dir,
            self.reports_dir,
            self.checkpoint_path.parent,
            self.quarantine_dir,
            self.logs_dir,
            self.debug_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
        readme = self.technical_dir / README_NAME
        if not readme.exists():
            readme.write_text(_technical_readme_text(), encoding="utf-8")


def normalize_account_dir(path: Path) -> Path:
    """Accept account dir, legacy downloads/ path, or Memories/ path."""
    path = Path(path)
    if path.name in (DOWNLOADS_DIRNAME, MEMORIES_DIRNAME):
        return path.parent
    return path


def resolve_account_paths(
    account_dir: Path,
    *,
    migrate: bool = True,
    create: bool = True,
    keep_raw: bool = False,
) -> AccountPaths:
    """Resolve layout paths. Only creates on-disk folders when create=True."""
    account_dir = normalize_account_dir(account_dir)
    paths = AccountPaths.for_account(account_dir, keep_raw=keep_raw)
    if create:
        paths.ensure_dirs(keep_raw=keep_raw)
        if migrate:
            migrate_account_layout(paths)
    elif migrate and account_dir.exists():
        migrate_account_layout(paths)
    return paths


def migrate_flat_accounts_root(base_dir: Path) -> list[str]:
    """
    Flatten a legacy `<base_dir>/accounts/<name>/` layout (Technical view with a
    custom base dir) into `<base_dir>/<name>/`, matching the simple mode's layout
    (`Desktop/<name>/` - no "accounts" wrapper). Existing folders are moved, not
    recreated, so nothing already downloaded is lost. Returns actions taken.
    """
    base_dir = Path(base_dir)
    legacy_root = base_dir / "accounts"
    actions: list[str] = []
    if not legacy_root.is_dir():
        return actions

    for child in list(legacy_root.iterdir()):
        if not child.is_dir():
            continue
        target = base_dir / child.name
        if target.exists():
            continue
        shutil.move(str(child), str(target))
        actions.append(f"Moved accounts/{child.name} -> {child.name}")

    try:
        if not any(legacy_root.iterdir()):
            legacy_root.rmdir()
            actions.append("Removed empty accounts/ folder")
    except OSError:
        pass

    return actions


def migrate_flat_library_to_subfolders(desktop_account: Path) -> bool:
    """
    Move loose files in Desktop/<account>/ into merged/ when user later enables raw copies.
    Returns True if files were moved.
    """
    desktop_account = Path(desktop_account)
    merged_dir = desktop_account / "merged"
    if merged_dir.is_dir() and any(merged_dir.iterdir()):
        return False
    loose = [p for p in desktop_account.iterdir() if p.is_file()]
    if not loose:
        return False
    merged_dir.mkdir(parents=True, exist_ok=True)
    for path in loose:
        target = merged_dir / path.name
        if target.exists():
            continue
        shutil.move(str(path), str(target))
    return True


def collapse_merged_to_flat(media_root: Path) -> bool:
    """
    Flatten a legacy always-nested `<media_root>/merged/` into `<media_root>/`
    directly, when there's no `raw/` content to justify keeping the nested
    layout. Before keep_raw existed, both simple (Desktop/<name>/) and
    technical (Memories/) layouts always created merged/+raw/ subfolders even
    when the user never enabled "Also save without filters" - leaving a
    pointless single-child merged/ folder for the common case. Never touches
    accounts that genuinely have raw copies (nesting stays, since flat can't
    hold two variants). Returns True if anything was moved.
    """
    media_root = Path(media_root)
    merged = media_root / "merged"
    raw = media_root / "raw"
    if not merged.is_dir():
        return False
    if raw.is_dir() and any(raw.iterdir()):
        return False  # genuinely has both variants - keep the nesting

    moved = False
    for child in list(merged.iterdir()):
        target = media_root / child.name
        if target.exists():
            continue
        shutil.move(str(child), str(target))
        moved = True
    try:
        if not any(merged.iterdir()):
            merged.rmdir()
    except OSError:
        pass
    if raw.is_dir():
        try:
            if not any(raw.iterdir()):
                raw.rmdir()
        except OSError:
            pass
    return moved


def _deep_merge_dir(src: Path, dest: Path, label: str, actions: list[str]) -> None:
    """Move everything under src into dest, recursing into subfolders that
    already exist at dest instead of skipping them outright.

    Needed because ensure_dirs() can pre-create empty stub folders (e.g.
    Memories/merged/, Memories/raw/ for a keep_raw=True account) *before*
    migrate_account_layout() runs. A shallow one-level merge would see
    "Memories/merged already exists" and skip moving legacy
    downloads/merged/ entirely - silently orphaning every file nested inside
    it. Recursing one extra level (however deep the pre-created stubs go)
    fixes that without risking any overwrite: a name collision on an actual
    file just leaves both copies in place, same as the shallow merge did.
    """
    for child in list(src.iterdir()):
        target = dest / child.name
        if child.is_dir():
            if target.is_dir():
                _deep_merge_dir(child, target, f"{label}/{child.name}", actions)
            elif not target.exists():
                shutil.move(str(child), str(target))
                actions.append(f"Moved {label}/{child.name}")
            # else: target exists as a non-directory - leave both alone.
        else:
            if not target.exists():
                shutil.move(str(child), str(target))
                actions.append(f"Moved {label}/{child.name}")
    try:
        if not any(src.iterdir()):
            src.rmdir()
    except OSError:
        pass


def migrate_account_layout(paths: AccountPaths) -> list[str]:
    """Move legacy hidden/ scattered files into technical/. Returns actions taken."""
    actions: list[str] = []
    downloads = paths.downloads_dir
    account = paths.account_dir

    moves: list[tuple[Path, Path, str]] = [
        # 2026-07-19 rename: "downloads" was a confusing name (nothing is
        # downloaded - SMK extracts/processes an export already on disk).
        # Must run first so the legacy-file moves below (which read through
        # paths.downloads_dir, now Memories/) see anything that used to live
        # under downloads/.
        (account / DOWNLOADS_DIRNAME, downloads, "downloads"),
        (downloads / LEGACY_STAGING, paths.staging_dir, "staging"),
        (downloads / LEGACY_CHECKPOINT, paths.checkpoint_path, "checkpoint"),
        (downloads / "reports", paths.reports_dir, "reports"),
        (downloads / "quarantine", paths.quarantine_dir, "quarantine"),
        (downloads / "processing_error.log", paths.logs_dir / "processing_error.log", "log"),
        (account / "json", paths.json_dir, "json"),
        (account / "debug", paths.debug_dir, "debug"),
    ]

    for src, dest, label in moves:
        if not src.exists():
            continue
        if src.is_dir():
            if dest.exists() and any(dest.iterdir()):
                _deep_merge_dir(src, dest, label, actions)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.move(str(src), str(dest))
                actions.append(f"Moved {label}/")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.move(str(src), str(dest))
                actions.append(f"Moved {label}")

    # Lift legacy <account>/Memories/ media up into the account root (2026-08-01).
    legacy_memories = account / MEMORIES_DIRNAME
    if (
        legacy_memories.is_dir()
        and paths.downloads_dir == account
        and legacy_memories.resolve() != account.resolve()
    ):
        _deep_merge_dir(legacy_memories, account, "Memories", actions)
        try:
            if legacy_memories.is_dir() and not any(legacy_memories.iterdir()):
                legacy_memories.rmdir()
                actions.append("Removed empty Memories/ wrapper")
        except OSError:
            pass

    # Only when this account's current layout wants flat (keep_raw=False,
    # so merged_dir IS downloads_dir) - a keep_raw=True account keeps its
    # nested merged/+raw/ untouched, see collapse_merged_to_flat() above.
    if paths.merged_dir == downloads and collapse_merged_to_flat(downloads):
        actions.append("Flattened merged/ into place (no raw copies present)")

    return actions


def is_legacy_desktop_accounts_wrapper(path: Path) -> bool:
    """True for the old Desktop/Memories or Desktop/SMD Media parent folders."""
    path = Path(path)
    desktop = Path.home() / "Desktop"
    try:
        resolved = path.resolve()
        return resolved in {
            (desktop / "Memories").resolve(),
            (desktop / "SMD Media").resolve(),
        }
    except OSError:
        return path.name in ("Memories", "SMD Media") and path.parent.name == "Desktop"


def migrate_accounts_out_of_desktop_wrapper(wrapper: Path) -> tuple[Path, list[str]]:
    """Move account folders out of Desktop/Memories or Desktop/SMD Media onto Desktop.

    Always returns Desktop as the new base when *wrapper* is a legacy parent,
    even if it is empty — callers must persist that so SMK never recreates
    ``Desktop/Memories`` via mkdir(parents=True) for a new account.
    """
    wrapper = Path(wrapper)
    desktop = Path.home() / "Desktop"
    actions: list[str] = []
    if not is_legacy_desktop_accounts_wrapper(wrapper):
        return wrapper, actions
    if not wrapper.is_dir():
        actions.append(f"Retired legacy base {wrapper.name} → Desktop")
        return desktop, actions

    for child in list(wrapper.iterdir()):
        if not child.is_dir():
            continue
        # Skip non-account clutter; account folders are *-memories or have technical/.
        name = child.name
        looks_account = name.lower().endswith(MEMORIES_SUFFIX) or (child / TECHNICAL_DIRNAME).is_dir()
        if not looks_account:
            continue
        dest = desktop / name
        if dest.exists():
            continue
        try:
            shutil.move(str(child), str(dest))
            actions.append(f"Moved {name} to Desktop")
            # Point stored base_dir at Desktop when identity exists.
            try:
                info_path = dest / TECHNICAL_DIRNAME / ACCOUNT_IDENTITY_NAME
                if info_path.is_file():
                    data = json.loads(info_path.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("layout") == "technical":
                        data["base_dir"] = str(desktop)
                        info_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except (OSError, json.JSONDecodeError):
                pass
        except OSError:
            continue
    try:
        if wrapper.is_dir() and not any(wrapper.iterdir()):
            wrapper.rmdir()
            actions.append(f"Removed empty {wrapper.name}/")
    except OSError:
        pass
    if not actions:
        actions.append(f"Retired legacy base {wrapper.name} → Desktop")
    return desktop, actions


def account_identity_path(account_dir: Path) -> Path:
    return Path(account_dir) / TECHNICAL_DIRNAME / ACCOUNT_IDENTITY_NAME


def _read_identity_json(account_dir: Path) -> dict:
    path = account_identity_path(account_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_account_identity(
    account_dir: Path,
    *,
    account_name: str | None = None,
    mydata_ids: list[str] | None = None,
    username: str | None = None,  # deprecated; ignored
    display_name: str | None = None,  # deprecated; ignored
) -> None:
    """Persist folder name + mydata export IDs for later matching.

    Merges into the existing file (layout info from save_account_layout_info
    lives here too). Does not store Snapchat username/display name — those
    are unused and were always null for our flows.
    """
    del username, display_name  # explicit: never persist
    account_dir = Path(account_dir)
    existing = _read_identity_json(account_dir)
    existing.pop("username", None)
    existing.pop("display_name", None)
    name = (account_name or "").strip() or account_dir.name
    if name:
        existing["account_name"] = ensure_memories_suffix(name)
    if mydata_ids is not None:
        existing["mydata_ids"] = sorted(
            {str(item).strip() for item in mydata_ids if str(item).strip()}
        )
    path = account_identity_path(account_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def save_account_layout_info(
    account_dir: Path,
    *,
    layout: str,
    base_dir: str | None = None,
    keep_raw: bool = False,
) -> None:
    """
    Persist which physical layout an account actually uses ('simple' - Desktop/<name>/
    or 'technical' - <base_dir>/<name>/) plus keep_raw, so later lookups
    (After processing, re-runs) always resolve to the real folder instead of
    guessing from whatever the Technical view toggle happens to be set to right
    now. This is purely internal bookkeeping - never shown outside Technical view.
    """
    account_dir = Path(account_dir)
    existing = _read_identity_json(account_dir)
    existing["layout"] = layout
    existing["base_dir"] = str(base_dir) if base_dir else existing.get("base_dir")
    existing["keep_raw"] = bool(keep_raw)
    path = account_identity_path(account_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def load_account_layout_info(account_dir: Path) -> dict | None:
    """Return {'layout', 'base_dir', 'keep_raw'} if previously saved, else None."""
    account_dir = Path(account_dir)
    candidates = [account_dir]
    internal = AccountPaths.internal_accounts_root() / account_dir.name
    if internal not in candidates:
        candidates.append(internal)
    for root in candidates:
        data = _read_identity_json(root)
        if data.get("layout"):
            return {
                "layout": data.get("layout"),
                "base_dir": data.get("base_dir"),
                "keep_raw": bool(data.get("keep_raw", False)),
            }
    return None


def resolve_existing_account_layout(
    account_name: str, current_base_dir: Path
) -> tuple[str, Path | None, bool] | None:
    """
    Figure out how *account_name* actually lives on disk today, independent of
    the live Technical view toggle. Checks both possible physical locations
    (Desktop/<name>/ for simple mode, <base_dir>/<name>/ for technical mode)
    and prefers stored layout info over guessing. Returns
    (layout, base_dir_or_None, keep_raw), or None if the account has never
    been created yet (brand new - caller should fall back to the live toggle).
    """
    account_name = (account_name or "").strip()
    if not account_name:
        return None

    desktop_dir = AccountPaths.user_desktop_dir(account_name)
    simple_internal = AccountPaths.internal_accounts_root() / account_name
    simple_info = load_account_layout_info(simple_internal)
    if simple_info and simple_info.get("layout") == "simple":
        return ("simple", None, bool(simple_info.get("keep_raw")))

    tech_dir = normalize_account_dir(Path(current_base_dir) / account_name)
    tech_info = load_account_layout_info(tech_dir)
    if tech_info and tech_info.get("layout") == "technical":
        stored_base = Path(tech_info.get("base_dir") or current_base_dir)
        return ("technical", stored_base, bool(tech_info.get("keep_raw")))

    # No stored layout info (account created before this bookkeeping existed) -
    # fall back to whichever location actually exists on disk.
    if desktop_dir.is_dir():
        return ("simple", None, False)
    if tech_dir.is_dir():
        return ("technical", Path(current_base_dir), False)
    return None


def load_account_identity(account_dir: Path):
    """Return AccountIdentity if stored, else None."""
    from smd.export_detect import AccountIdentity

    account_dir = Path(account_dir)
    candidates = [account_dir]
    internal = AccountPaths.internal_accounts_root() / account_dir.name
    if internal not in candidates:
        candidates.append(internal)

    for root in candidates:
        path = account_identity_path(root)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        raw_ids = data.get("mydata_ids") or []
        return AccountIdentity(
            username=(data.get("username") or None),
            display_name=(data.get("display_name") or None),
            mydata_ids=frozenset(str(i).strip() for i in raw_ids if str(i).strip()),
        )
    return None


def rename_simple_mode_account(old_name: str, new_name: str) -> list[str]:
    """
    Rename both the Desktop library folder and the matching internal
    %LOCALAPPDATA% account root. Returns actions taken; no-op when unsafe.
    """
    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    actions: list[str] = []
    if not old_name or not new_name or old_name == new_name:
        return actions

    moves = [
        (AccountPaths.user_desktop_dir(old_name), AccountPaths.user_desktop_dir(new_name), "desktop"),
        (AccountPaths.internal_accounts_root() / old_name, AccountPaths.internal_accounts_root() / new_name, "internal"),
    ]
    for src, dest, label in moves:
        if not src.exists() or dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        actions.append(f"Renamed {label} account folder {old_name} -> {new_name}")
    return actions


def rename_technical_mode_account(base_dir: Path, old_name: str, new_name: str) -> list[str]:
    """Rename ``<base_dir>/<old_name>/`` when the target name is free."""
    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    actions: list[str] = []
    if not old_name or not new_name or old_name == new_name:
        return actions
    src = Path(base_dir) / old_name
    dest = Path(base_dir) / new_name
    if not src.is_dir() or dest.exists():
        return actions
    shutil.move(str(src), str(dest))
    actions.append(f"Renamed account folder {old_name} -> {new_name}")
    return actions


def folder_size_bytes(path: Path) -> int:
  total = 0
  if not path.exists():
      return 0
  if path.is_file():
      try:
          return path.stat().st_size
      except OSError:
          return 0
  for child in path.rglob("*"):
      if child.is_file():
          try:
              total += child.stat().st_size
          except OSError:
              pass
  return total


from smd.media_types import format_bytes  # single shared implementation  # noqa: E402


def copy_run_info_into_library(paths: AccountPaths) -> tuple[Path, list[str]]:
    """Copy small technical logistics into ``library_root/SMK-run-info/``.

    Includes json, reports, logs, debug, quarantine (when present), README,
    and account_identity.json. Skips staging (large temporary extract) and
    checkpoint (resume internals). Returns (dest_dir, list of copied labels).
    """
    dest = Path(paths.library_root) / RUN_INFO_DIRNAME
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    def _copy_dir(src: Path, name: str) -> None:
        if not src.is_dir():
            return
        try:
            if not any(src.iterdir()):
                return
        except OSError:
            return
        shutil.copytree(src, dest / name, dirs_exist_ok=True)
        copied.append(name)

    def _copy_file(src: Path, name: str) -> None:
        if not src.is_file():
            return
        shutil.copy2(src, dest / name)
        copied.append(name)

    _copy_dir(paths.json_dir, "json")
    _copy_dir(paths.reports_dir, "reports")
    _copy_dir(paths.logs_dir, "logs")
    _copy_dir(paths.debug_dir, "debug")
    _copy_dir(paths.quarantine_dir, "quarantine")
    _copy_file(paths.technical_dir / README_NAME, README_NAME)
    _copy_file(account_identity_path(paths.account_dir), ACCOUNT_IDENTITY_NAME)

    (dest / "ABOUT.txt").write_text(
        "SMK run info\n"
        "============\n\n"
        "A snapshot of the technical logistics for this account's last processing "
        "work (JSON, reports, logs, etc.). Not your photos/videos.\n\n"
        "Staging (the large temporary unzip) is intentionally not copied here.\n"
        f"Copied: {', '.join(copied) if copied else '(nothing found yet)'}\n",
        encoding="utf-8",
    )
    if "ABOUT.txt" not in copied:
        copied.append("ABOUT.txt")
    return dest, copied


def technical_storage_summary(paths: AccountPaths) -> list[tuple[str, int]]:
    """Named technical subfolders with byte sizes (for UI)."""
    rows: list[tuple[str, int]] = []
    for label, folder in (
        ("staging", paths.staging_dir),
        ("json", paths.json_dir),
        ("reports", paths.reports_dir),
        ("checkpoint", paths.checkpoint_path.parent),
        ("quarantine", paths.quarantine_dir),
        ("logs", paths.logs_dir),
        ("debug", paths.debug_dir),
    ):
        rows.append((label, folder_size_bytes(folder)))
    return rows


def _technical_readme_text() -> str:
    return """Snapchat Memories Keeper - technical folder
==========================================

This folder holds working data used by the program. It is NOT hidden on purpose:
staging especially can use a lot of disk space (often similar to your ZIP export).

Subfolders
----------
staging/     Extracted media from ZIP parts (main + overlay pairs). Removed
             automatically after a clean finish. Deleting early means
             re-extracting from ZIPs on the next run.

json/        memories_history.json - dates, GPS, media types from Snapchat.

reports/     processing_report.json, filename_collisions.json,
             staging_readiness.json - run statistics and verification.

checkpoint/  Resume state (local_checkpoint.json) - lets interrupted runs continue.

quarantine/  Broken or unusable files isolated during processing.

logs/        Error logs from failed runs, plus a full run_activity log per run.

debug/       Processing diagnostics and logs

Your photos and videos
----------------------
Open: ../                  (account folder - with overlays when filters are baked in)
      ../merged/           (with overlays - if "Also save without filters" is on)
      ../raw/              (without overlays, only if "Also save without filters" was on)

Duplicates are handled in the app (Review duplicates in Technical view). Deletions
are recorded in reports/duplicates_deleted_report_*.json.
"""
