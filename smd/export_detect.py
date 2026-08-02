"""Detect Snapchat export format (bundled local media vs unsupported link-only)."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ExportFormat(str, Enum):
    BUNDLED_LOCAL = "bundled_local"
    LINKS_ONLY = "links_only"
    JSON_ONLY = "json_only"
    EMPTY = "empty"


@dataclass
class ExportAnalysis:
    format: ExportFormat
    json_rows: int = 0
    rows_with_link: int = 0
    https_count: int = 0
    embedded_media_count: int = 0
    main_file_count: int = 0
    overlay_file_count: int = 0
    zip_paths: list[Path] | None = None
    json_path: Path | None = None
    message: str = ""
    year_min: int | None = None
    year_max: int | None = None
    zip_bytes: int = 0

    @property
    def is_bundled(self) -> bool:
        return self.format == ExportFormat.BUNDLED_LOCAL

    @property
    def is_supported(self) -> bool:
        return self.is_bundled

    @property
    def has_links(self) -> bool:
        return self.rows_with_link > 0


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _parse_json_export_stats(raw: str) -> tuple[int, int, int, int | None, int | None]:
    """Return (row_count, rows_with_link, https_count, year_min, year_max)."""
    https = len(re.findall(r"https://", raw))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0, 0, https, None, None
    rows = data.get("Saved Media", data if isinstance(data, list) else [])
    if not isinstance(rows, list):
        rows = []
    with_link = 0
    year_min: int | None = None
    year_max: int | None = None
    for r in rows:
        if not isinstance(r, dict):
            continue
        if (r.get("Download Link") or r.get("Media Download Url") or "").strip():
            with_link += 1
        date_raw = r.get("Date")
        if not isinstance(date_raw, str):
            continue
        m = _YEAR_RE.search(date_raw)
        if not m:
            continue
        year = int(m.group(0))
        year_min = year if year_min is None else min(year_min, year)
        year_max = year if year_max is None else max(year_max, year)
    return len(rows), with_link, https, year_min, year_max


# Back-compat alias for any external callers / older tests.
def _count_links_in_json_text(raw: str) -> tuple[int, int]:
    rows, with_link, _https, _ymin, _ymax = _parse_json_export_stats(raw)
    return rows, with_link


def discover_export_zip_parts(seed: Path) -> list[Path]:
    """Find all parts of a split Snapchat export (mydata~ID.zip, mydata~ID-2.zip, ...)."""
    seed = seed.resolve()
    if seed.is_dir():
        zips = sorted(seed.glob("mydata*.zip"), key=_zip_sort_key)
        return zips if zips else sorted(seed.glob("*.zip"), key=_zip_sort_key)

    if not seed.suffix.lower() == ".zip":
        return []

    parent = seed.parent
    stem = seed.stem  # e.g. mydata~1783373820861 or mydata~1783373820861-2
    base_match = re.match(r"(mydata~\d+)", stem, re.I)
    if not base_match:
        return [seed]

    base = base_match.group(1)
    parts = sorted(parent.glob(f"{base}*.zip"), key=_zip_sort_key)
    return parts if parts else [seed]


def resolve_export_zip_paths(seed: Path | list[Path]) -> list[Path]:
    """
    Resolve ZIP parts from a folder, one file (auto-find siblings), or explicit multi-select.
    """
    if isinstance(seed, list):
        paths = [Path(p).resolve() for p in seed if Path(p).suffix.lower() == ".zip"]
        if not paths:
            return []
        if len(paths) == 1:
            return discover_export_zip_parts(paths[0])
        return sorted(paths, key=_zip_sort_key)
    return discover_export_zip_parts(Path(seed))


def export_base_ids(zip_paths: list[Path]) -> set[str]:
    """Return mydata~ID bases for validation when user picks multiple files."""
    bases: set[str] = set()
    for p in zip_paths:
        m = re.match(r"(mydata~\d+)", p.stem, re.I)
        bases.add(m.group(1) if m else p.stem)
    return bases


_GENERIC_EXPORT_FOLDER_NAMES = frozenset({
    "download", "downloads", "desktop", "documents", "pictures", "videos", "music",
    "zip", "zips", "export", "exports", "snapchat", "memories", "mydata", "temp", "tmp",
    "new folder", "smd media", "memories",
})


def is_usable_account_folder_name(name: str) -> bool:
    """True when a directory name is a reasonable auto account label."""
    name = (name or "").strip()
    if not name or name in (".", ".."):
        return False
    if any(ch in name for ch in '<>:"/\\|?*'):
        return False
    lowered = name.lower()
    if lowered in _GENERIC_EXPORT_FOLDER_NAMES:
        return False
    if re.match(r"mydata~\d+", name, re.I):
        return False
    return True


_ACCOUNT_INFO_FILENAMES = ("account.json", "account_history.json")
_ACCOUNT_FOLDER_NAME_MAX_LEN = 120


@dataclass(frozen=True)
class AccountIdentity:
    """Snapchat account fields read from the export's own account info file,
    plus the mydata~ID(s) of the export(s) that populated this folder."""

    username: str | None = None
    display_name: str | None = None
    mydata_ids: frozenset[str] = frozenset()

    @property
    def folder_name(self) -> str | None:
        return format_account_folder_name(self)

    def matches(self, other: AccountIdentity) -> bool:
        """True if this and *other* are almost certainly the same account -
        by username/display name, or by sharing a mydata export ID. The ID
        check is what keeps folder matching working after a user renames an
        account folder to something with no identifying text at all (e.g. an
        auto-assigned "Unknown account N" renamed to a real name): the ID is
        stored inside the folder, not derived from its current name."""
        if self.mydata_ids and other.mydata_ids and (self.mydata_ids & other.mydata_ids):
            return True
        if self.username and other.username:
            return self.username.lower() == other.username.lower()
        if self.display_name and other.display_name:
            return self.display_name.lower() == other.display_name.lower()
        return False


def _normalize_json_key(key: str) -> str:
    return re.sub(r"[\s_]+", "", key.strip().lower())


def _find_json_string_value(data, key: str, *, _depth: int = 0) -> str | None:
    """Recursively search for a string value under *key* (case/spacing insensitive)."""
    if _depth > 4:
        return None
    want = _normalize_json_key(key)
    if isinstance(data, dict):
        for raw_key, value in data.items():
            if (
                isinstance(raw_key, str)
                and _normalize_json_key(raw_key) == want
                and isinstance(value, str)
                and value.strip()
            ):
                return value.strip()
        for value in data.values():
            found = _find_json_string_value(value, key, _depth=_depth + 1)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_json_string_value(item, key, _depth=_depth + 1)
            if found:
                return found
    return None


def _sanitize_folder_label(text: str) -> str:
    cleaned = (text or "").strip()
    for ch in '<>:"/\\|?*':
        cleaned = cleaned.replace(ch, " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.rstrip(".")


def format_account_folder_name(identity: AccountIdentity) -> str | None:
    """
    Build a Windows-safe folder label that helps tell accounts apart.

    Uses display name + username when both exist (e.g. ``Las (las_snap)``),
    otherwise whichever field is available.
    """
    username = _sanitize_folder_label(identity.username or "")
    display = _sanitize_folder_label(identity.display_name or "")
    if display and username and display.lower() != username.lower():
        name = f"{display} ({username})"
    elif display:
        name = display
    elif username:
        name = username
    else:
        return None

    if len(name) > _ACCOUNT_FOLDER_NAME_MAX_LEN:
        if display and username and display.lower() != username.lower():
            budget = _ACCOUNT_FOLDER_NAME_MAX_LEN - len(username) - 3
            if budget >= 4:
                name = f"{display[:budget].rstrip()} ({username})"
            else:
                name = username[:_ACCOUNT_FOLDER_NAME_MAX_LEN]
        else:
            name = name[:_ACCOUNT_FOLDER_NAME_MAX_LEN].rstrip()

    if is_usable_account_folder_name(name):
        return name
    if username and is_usable_account_folder_name(username):
        return username
    return None


def _read_account_info_json(zip_paths: list[Path]) -> dict | None:
    for zpath in zip_paths:
        try:
            with zipfile.ZipFile(zpath, "r") as zf:
                member = next(
                    (n for n in zf.namelist() if Path(n).name.lower() in _ACCOUNT_INFO_FILENAMES),
                    None,
                )
                if not member:
                    continue
                raw = zf.read(member).decode("utf-8", errors="replace")
                data = json.loads(raw)
        except (zipfile.BadZipFile, OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def extract_account_identity_from_zip(zip_paths: list[Path]) -> AccountIdentity | None:
    """
    Read username and display name from the export's own account info file.

    Returns None when no account file is present or neither field is readable.
    """
    data = _read_account_info_json(zip_paths)
    if not data:
        return None
    username = _find_json_string_value(data, "username")
    display_name = _find_json_string_value(data, "display_name")
    if not username and not display_name:
        return None
    return AccountIdentity(username=username, display_name=display_name)


def extract_account_username_from_zip(zip_paths: list[Path]) -> str | None:
    """Backward-compatible helper - returns username only."""
    identity = extract_account_identity_from_zip(zip_paths)
    return identity.username if identity else None


def find_existing_account_folder_name(
    search_dirs: list[Path],
    *,
    identity: AccountIdentity | None = None,
    mydata_ids: set[str] | None = None,
) -> str | None:
    """
    Return an existing on-disk account folder name that matches this export.

    Matches (in order): a stored mydata export ID shared with this export
    (survives the user renaming the folder to anything, including something
    with no identifying text) → stored username/display name → a folder name
    that happens to contain the export's mydata ID tail (legacy
    ``export-{id}`` folders that predate identity persistence).
    """
    from smd.account_layout import load_account_identity

    merged_ids = set(mydata_ids or [])
    if identity and identity.mydata_ids:
        merged_ids |= set(identity.mydata_ids)
    lookup_identity = AccountIdentity(
        username=identity.username if identity else None,
        display_name=identity.display_name if identity else None,
        mydata_ids=frozenset(merged_ids),
    )
    mydata_ids = merged_ids
    id_tails = {base_id.split("~", 1)[-1][:8].lower() for base_id in mydata_ids if "~" in base_id}

    for root in search_dirs:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            stored = load_account_identity(child)
            if stored and lookup_identity.matches(stored):
                return child.name
            lowered = child.name.lower()
            if id_tails and any(tail and tail in lowered for tail in id_tails):
                return child.name
    return None


_UNKNOWN_ACCOUNT_PATTERN = re.compile(r"^unknown account (\d+)$", re.I)


def next_unknown_account_name(search_dirs: list[Path]) -> str:
    """
    Next free ``Unknown account N`` label for an export with no readable
    username/display name and no other naming clue. Only ever hands out a
    number that isn't already in use as a folder name, so it stays correct
    even after some "Unknown account N" folders were renamed away and others
    were not.
    """
    used: set[int] = set()
    for root in search_dirs:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir():
                continue
            m = _UNKNOWN_ACCOUNT_PATTERN.match(child.name)
            if m:
                used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"Unknown account {n}"


def derive_account_name_from_export(
    seed: Path | list[Path],
    zip_paths: list[Path],
    *,
    search_dirs: list[Path] | None = None,
    detected_identity: AccountIdentity | None | str = "",
) -> str:
    """
    Pick an account folder name from how the user selected their export.

    Priority: formatted identity from the export's account info (display name +
    username when both exist) → existing folder already tied to this account
    (by stored mydata ID - robust to renames - or stored username/display name,
    or a folder name containing the mydata ID tail) → selected folder name →
    parent folder of ZIPs (if not generic) → "Unknown account N" (fresh, unique
    number - used only when nothing above identifies the account at all).

    detected_identity: pass a pre-computed extract_account_identity_from_zip()
    result to avoid re-reading the ZIP; leave at the default "" to compute it,
    or pass None to skip the identity check entirely.
    """
    search_dirs = search_dirs or []
    mydata_ids = export_base_ids(zip_paths)

    identity = (
        extract_account_identity_from_zip(zip_paths)
        if detected_identity == ""
        else detected_identity
    )
    identity_name = format_account_folder_name(identity) if identity else None

    existing = find_existing_account_folder_name(
        search_dirs,
        identity=identity,
        mydata_ids=mydata_ids,
    )
    if identity_name:
        return identity_name
    if existing:
        return existing

    if not isinstance(seed, list):
        folder = Path(seed)
        if folder.is_dir() and is_usable_account_folder_name(folder.name):
            return folder.name

    if zip_paths:
        parent_name = zip_paths[0].parent.name
        if is_usable_account_folder_name(parent_name):
            return parent_name

    return next_unknown_account_name(search_dirs)


def _zip_sort_key(p: Path) -> tuple:
    # Base part (mydata~ID.zip) sorts before numbered parts (…-2.zip, …-3.zip);
    # lowercase name is a stable tiebreaker so generic *.zip lists stay ordered.
    m = re.search(r"-(\d+)\.zip$", p.name, re.I)
    order = (0, 0) if m is None else (1, int(m.group(1)))
    return (*order, p.name.lower())


def analyze_zip_export(seed_path: Path | list[Path]) -> ExportAnalysis:
    """Analyze export from ZIP file(s) or a folder containing ZIPs."""
    zip_paths = resolve_export_zip_paths(
        seed_path if isinstance(seed_path, list) else Path(seed_path)
    )
    if not zip_paths:
        return ExportAnalysis(ExportFormat.EMPTY, message="No ZIP files found.")

    json_rows = 0
    rows_with_link = 0
    https_count = 0
    embedded = 0
    main_count = 0
    overlay_count = 0
    json_path: Path | None = None
    year_min: int | None = None
    year_max: int | None = None
    zip_bytes = 0

    for zpath in zip_paths:
        try:
            zip_bytes += zpath.stat().st_size
        except OSError:
            pass
        try:
            with zipfile.ZipFile(zpath, "r") as zf:
                names = zf.namelist()
                if json_path is None:
                    jmembers = [n for n in names if n.lower().endswith("memories_history.json")]
                    if jmembers:
                        raw = zf.read(jmembers[0]).decode("utf-8", errors="replace")
                        json_rows, link_n, https_n, ymin, ymax = _parse_json_export_stats(raw)
                        rows_with_link = max(rows_with_link, link_n)
                        https_count = max(https_count, https_n)
                        year_min, year_max = ymin, ymax

                for n in names:
                    if not n.startswith("memories/") or n.endswith("/"):
                        continue
                    embedded += 1
                    low = n.lower()
                    if "-main." in low:
                        main_count += 1
                    elif "-overlay." in low:
                        overlay_count += 1
        except zipfile.BadZipFile:
            continue

    zip_n = len(zip_paths)
    if json_rows == 0:
        fmt = ExportFormat.EMPTY
        msg = "No memories_history.json found in export."
    elif main_count > 0 or embedded > 0:
        fmt = ExportFormat.BUNDLED_LOCAL
        url_note = (
            "Download URLs empty (bundled/offline - expected)."
            if rows_with_link == 0
            else f"{rows_with_link} JSON rows also list download URLs (media in ZIP is used)."
        )
        msg = (
            f"Bundled export: {main_count} main files across {zip_n} ZIP(s), "
            f"{json_rows} JSON rows. Processing is fully offline. {url_note}"
        )
    elif rows_with_link > 0:
        fmt = ExportFormat.LINKS_ONLY
        msg = (
            f"Link-only export: {rows_with_link} of {json_rows} JSON rows have download URLs, "
            "but no media files inside the ZIP. SMK is offline-only - request a new export "
            "with Memories included in the ZIP (see Guide tab)."
        )
    else:
        fmt = ExportFormat.JSON_ONLY
        msg = (
            f"JSON-only export ({json_rows} rows, no download URLs). "
            "No bundled media files in the ZIP. Request a new Snapchat export "
            "with Memories included (see Guide tab)."
        )

    return ExportAnalysis(
        format=fmt,
        json_rows=json_rows,
        rows_with_link=rows_with_link,
        https_count=https_count,
        embedded_media_count=embedded,
        main_file_count=main_count,
        overlay_file_count=overlay_count,
        zip_paths=zip_paths,
        json_path=json_path,
        message=msg,
        year_min=year_min,
        year_max=year_max,
        zip_bytes=zip_bytes,
    )


def extract_json_from_zips(zip_paths: list[Path], dest: Path) -> Path:
    """Extract memories_history.json from first ZIP that contains it."""
    from smd.fsutil import atomic_write_bytes

    dest.parent.mkdir(parents=True, exist_ok=True)
    for zpath in zip_paths:
        with zipfile.ZipFile(zpath, "r") as zf:
            member = next((n for n in zf.namelist() if n.lower().endswith("memories_history.json")), None)
            if member:
                data = zf.read(member)
                atomic_write_bytes(dest, data)
                return dest
    raise FileNotFoundError("memories_history.json not found in any ZIP.")
