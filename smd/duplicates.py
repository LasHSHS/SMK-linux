"""Detect duplicate content; auto-remove extras (keep oldest filename)."""
from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from smd.account_layout import AccountPaths
from smd.media_types import is_image_file, is_video_file

VISUAL_REPORT_NAME = "duplicates_visual_report.json"
BYTE_REPORT_NAME = "duplicates_report.json"
STAGING_BYTE_DELETED_REPORT = "duplicates_staging_byte_auto_deleted.json"
STAGING_VISUAL_DELETED_REPORT = "duplicates_staging_visual_auto_deleted.json"
STAGING_VISUAL_HASH_CACHE_NAME = "duplicates_staging_visual_hash_cache.json"


class DuplicateScanCancelled(Exception):
    """User requested stop during a hash/scan pass."""


def keeper_filename(names: list[str]) -> str:
    """Pick the copy to keep: oldest ``YYYY-MM-DD_HH-MM-SS…`` name, then shortest.

    ISO-ish Snapchat output names sort chronologically as plain strings, so the
    earliest capture/re-export wins over a later Snapchat re-save. Same-second
    collision twins prefer the name without a UID suffix.
    """
    if not names:
        raise ValueError("keeper_filename requires at least one name")
    return sorted(names, key=lambda n: (n[:19], len(n), n))[0]


def group_filenames_by_hash(report: DuplicateScanReport) -> dict[str, list[str]]:
    """sha256 prefix -> filenames in that duplicate group."""
    groups: dict[str, list[str]] = defaultdict(list)
    for entry in report.entries:
        groups[entry.sha256].append(entry.filename)
    return {k: sorted(set(v)) for k, v in groups.items() if len(v) >= 2}


@dataclass
class DuplicateEntry:
    filename: str
    duplicate_of: str
    sha256: str
    moved_to: str | None = None


@dataclass
class DuplicateScanReport:
    scanned_at: str
    merged_scanned: int = 0
    duplicate_groups: int = 0
    files_moved: int = 0
    entries: list[DuplicateEntry] = field(default_factory=list)
    # "byte": whole-file SHA-256 match (exact duplicate, cheap, always run first).
    # "visual": decoded video/image content matches but file bytes differ - this is
    # what catches a memory Snapchat itself exported twice under separate UUIDs
    # (different container metadata/encode, same actual photo/video). Much slower
    # to compute since every file must be decoded - see scan_visual_duplicates().
    kind: str = "byte"

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _video_content_hash(path: Path, ffmpeg: str) -> str | None:
    """Hash of the decoded video stream only - ignores container/metadata bytes
    (timestamps, GPS, etc.) so two remuxes/re-exports of the same recording match."""
    from smd.procutil import run_tool

    proc = run_tool(
        [ffmpeg, "-v", "error", "-i", str(path), "-map", "0:v", "-f", "md5", "-"],
        timeout=120,
    )
    if proc is None or proc.returncode != 0:
        return None
    out = proc.stdout.decode("utf-8", errors="ignore").strip()
    if out.startswith("MD5="):
        return out[4:]
    return None


def _image_content_hash(path: Path) -> str | None:
    """Hash of decoded RGB pixels only - ignores EXIF/metadata bytes."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            return hashlib.sha256(img.convert("RGB").tobytes()).hexdigest()
    except Exception:
        return None


def _content_hash(path: Path, ffmpeg: str | None) -> str | None:
    if is_video_file(path):
        return _video_content_hash(path, ffmpeg) if ffmpeg else None
    if is_image_file(path):
        return _image_content_hash(path)
    return None


VISUAL_HASH_CACHE_NAME = "duplicates_visual_hash_cache.json"


def _load_staging_visual_hash_cache(reports_dir: Path) -> dict[str, dict]:
    """size+mtime cache for staging visual dedupe (survives staging delete)."""
    cache_path = reports_dir / STAGING_VISUAL_HASH_CACHE_NAME
    if not cache_path.is_file():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _save_staging_visual_hash_cache(reports_dir: Path, cache: dict[str, dict]) -> None:
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / STAGING_VISUAL_HASH_CACHE_NAME).write_text(
            json.dumps(cache, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def load_staging_removed_stems(reports_dir: Path) -> set[str]:
    """Stems dropped by prior staging auto-dedupe (byte and/or visual)."""
    stems: set[str] = set()
    for name in (STAGING_BYTE_DELETED_REPORT, STAGING_VISUAL_DELETED_REPORT):
        path = reports_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        for stem in data.get("stems_removed") or []:
            stems.add(str(stem))
    return stems


def _load_visual_hash_cache(paths: AccountPaths) -> dict[str, dict]:
    """filename -> {size, mtime_ns, hash} from the last visual scan. Lets repeat
    scans skip decoding any file whose size+mtime haven't changed since last
    time - the expensive full decode only has to happen once per file, not once
    per run. (An earlier attempt at speeding this up by fingerprinting videos
    with ffprobe before deciding whether to decode them made things *worse* in
    practice - spawning thousands of extra ffprobe processes in parallel bogged
    the whole machine down - so this cache is the approach that was kept.)"""
    cache_path = paths.reports_dir / VISUAL_HASH_CACHE_NAME
    if not cache_path.is_file():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def _save_visual_hash_cache(paths: AccountPaths, cache: dict[str, dict]) -> None:
    try:
        paths.reports_dir.mkdir(parents=True, exist_ok=True)
        (paths.reports_dir / VISUAL_HASH_CACHE_NAME).write_text(
            json.dumps(cache, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def load_cached_duplicate_group_count(paths: AccountPaths) -> int:
    """Read duplicate_groups from a prior byte scan without re-hashing merged/."""
    report = load_cached_duplicate_report(paths)
    return report.duplicate_groups if report else 0


def load_cached_visual_duplicate_group_count(paths: AccountPaths) -> int:
    """Read duplicate_groups from a prior visual/deep scan without re-decoding merged/."""
    report = load_cached_visual_duplicate_report(paths)
    return report.duplicate_groups if report else 0


def _load_report(paths: AccountPaths, report_name: str) -> DuplicateScanReport | None:
    report_path = paths.reports_dir / report_name
    if not report_path.is_file():
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        entries = [
            DuplicateEntry(
                filename=e["filename"],
                duplicate_of=e["duplicate_of"],
                sha256=e["sha256"],
                moved_to=e.get("moved_to"),
            )
            for e in data.get("entries", [])
        ]
        return DuplicateScanReport(
            scanned_at=data.get("scanned_at", ""),
            merged_scanned=int(data.get("merged_scanned", 0) or 0),
            duplicate_groups=int(data.get("duplicate_groups", 0) or 0),
            files_moved=int(data.get("files_moved", 0) or 0),
            entries=entries,
            kind=data.get("kind", "byte"),
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
        return None


def load_cached_duplicate_report(paths: AccountPaths) -> DuplicateScanReport | None:
    """Load duplicates_report.json (byte-identical scan) from the last scan."""
    return _load_report(paths, BYTE_REPORT_NAME)


def load_cached_visual_duplicate_report(paths: AccountPaths) -> DuplicateScanReport | None:
    """Load duplicates_visual_report.json (same-content-different-bytes scan)."""
    return _load_report(paths, VISUAL_REPORT_NAME)


def scan_content_duplicates(
    paths: AccountPaths,
    *,
    move_to_folder: bool = False,
    status_callback: Callable[[str], None] | None = None,
    hash_workers: int = 4,
    should_stop: Callable[[], bool] | None = None,
) -> DuplicateScanReport:
    """
    Find byte-identical files in `merged/`.

    Only scans `downloads/merged/` — not `raw/`. Two files are duplicates only when
    every byte matches (same photo/video saved twice under different names).

    If `move_to_folder=True`, copy the *entire duplicate groups* (every file in each
    identical-content group) into `downloads/duplicates/` for manual assessment.

    If `move_to_folder=False`, no files are written/mutated; only a JSON report is produced.
    """
    def status(msg: str) -> None:
        if status_callback:
            status_callback(msg)

    report = DuplicateScanReport(scanned_at=datetime.now(timezone.utc).isoformat())
    merged = paths.merged_dir
    if not merged.is_dir():
        return report

    duplicates_dir = paths.downloads_dir / "duplicates"

    files = sorted(p for p in merged.iterdir() if p.is_file())
    total = len(files)
    if not files:
        return report

    status(f"Checking for duplicate files (0/{total})...")
    size_buckets: dict[int, list[Path]] = {}
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        size_buckets.setdefault(size, []).append(path)

    digest_to_files: dict[str, list[Path]] = {}
    paths_to_hash: list[Path] = []
    for size, bucket in size_buckets.items():
        if len(bucket) < 2:
            continue
        paths_to_hash.extend(bucket)

    hash_total = len(paths_to_hash)
    if hash_total == 0:
        report.merged_scanned = total
        paths.reports_dir.mkdir(parents=True, exist_ok=True)
        (paths.reports_dir / BYTE_REPORT_NAME).write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
        return report

    status(
        f"Found {hash_total:,} files that share a file size with something else "
        f"(possible identical duplicates) — checking those carefully "
        f"(skipping {total - hash_total:,} unique-sized files)..."
    )

    workers = max(1, min(int(hash_workers), 16))
    progress_every = max(25, hash_total // 40)
    done = 0

    def _stop() -> bool:
        return bool(should_stop and should_stop())

    if workers == 1 or hash_total < 50:
        for path in paths_to_hash:
            if _stop():
                raise DuplicateScanCancelled()
            digest = _file_hash(path)
            digest_to_files.setdefault(digest, []).append(path)
            done += 1
            report.merged_scanned = done
            if done == 1 or done == hash_total or done % progress_every == 0:
                status(
                    f"Checking possible identical duplicates "
                    f"({done}/{hash_total})..."
                )
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_file_hash, path): path for path in paths_to_hash}
            for fut in as_completed(futures):
                if _stop():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise DuplicateScanCancelled()
                path = futures[fut]
                digest = fut.result()
                digest_to_files.setdefault(digest, []).append(path)
                done += 1
                report.merged_scanned = done
                if done == 1 or done == hash_total or done % progress_every == 0:
                    status(
                        f"Checking possible identical duplicates "
                        f"({done}/{hash_total})..."
                    )
    report.merged_scanned = total

    # Optional second pass: copy entire duplicate groups out for inspection.
    if move_to_folder:
        duplicates_dir.mkdir(parents=True, exist_ok=True)

    for digest, files in sorted(digest_to_files.items(), key=lambda kv: kv[0]):
        if len(files) < 2:
            continue

        report.duplicate_groups += 1
        rep = sorted(files, key=lambda p: p.name)[0].name  # deterministic representative name

        # Stable order for easier review.
        for path in sorted(files, key=lambda p: p.name):
            moved_to = None
            if move_to_folder:
                group_dir = duplicates_dir / digest[:16]
                group_dir.mkdir(parents=True, exist_ok=True)

                dest = group_dir / path.name
                if dest.exists():
                    # Extremely defensive: keep multiple copies even if filenames collide.
                    dest = group_dir / f"{path.stem}_dup{report.files_moved + 1}{path.suffix}"

                shutil.copy2(str(path), str(dest))
                moved_to = str(dest)
                report.files_moved += 1

            report.entries.append(
                DuplicateEntry(
                    filename=path.name,
                    duplicate_of=rep,
                    sha256=digest[:16],
                    moved_to=moved_to,
                )
            )

    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    (paths.reports_dir / BYTE_REPORT_NAME).write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    return report


def scan_visual_duplicates(
    paths: AccountPaths,
    *,
    status_callback: Callable[[str], None] | None = None,
    hash_workers: int = 8,
    should_stop: Callable[[], bool] | None = None,
) -> DuplicateScanReport:
    """
    Find files in `merged/` with identical *decoded* content (same actual photo or
    video) even when the file bytes differ.

    This catches memories that Snapchat's own export logged twice under separate
    UUIDs/timestamps - each one gets processed into its own output file by SMK
    (correctly, since they are distinct JSON entries), but the underlying recording
    is the same. scan_content_duplicates() above only matches exact byte-for-byte
    files and will not find these, since the container/metadata bytes differ.

    There is no same-size shortcut like the byte scan has (re-exported copies can
    differ in size), so every file needs a full decode *the first time it's seen*.
    What makes this practical to run on every processing run is a persistent
    per-file hash cache (duplicates_visual_hash_cache.json): a file is only
    re-decoded if its size or modified-time changed since the last scan. On a
    library that was already scanned, only genuinely new/changed files pay the
    decode cost - unchanged files (the vast majority on a repeat run) are free.
    The very first scan of a large existing library still has to decode
    everything once (~20 minutes on a 13,900-file library) - there's no way
    around that, short compares can't tell two videos apart, only full playback
    can.
    """
    from smd.ffmpeg_bundle import resolve_ffmpeg

    def status(msg: str) -> None:
        if status_callback:
            status_callback(msg)

    report = DuplicateScanReport(scanned_at=datetime.now(timezone.utc).isoformat(), kind="visual")
    merged = paths.merged_dir
    if not merged.is_dir():
        return report

    files = sorted(p for p in merged.iterdir() if p.is_file())
    total = len(files)
    if not files:
        return report

    ffmpeg = resolve_ffmpeg()
    workers = max(1, min(int(hash_workers), 16))

    old_cache = _load_visual_hash_cache(paths)
    new_cache: dict[str, dict] = {}
    to_hash: list[Path] = []
    hash_to_files: dict[str, list[Path]] = {}

    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        cached = old_cache.get(path.name)
        if cached and cached.get("size") == stat.st_size and cached.get("mtime_ns") == stat.st_mtime_ns:
            digest = cached.get("hash")
            new_cache[path.name] = cached
            if digest:
                hash_to_files.setdefault(digest, []).append(path)
        else:
            to_hash.append(path)

    hash_total = len(to_hash)
    reused = total - hash_total
    progress_every = max(25, hash_total // 40) if hash_total else 1
    done = 0

    def _hash_one(path: Path) -> tuple[Path, str | None]:
        return path, _content_hash(path, ffmpeg)

    def _stop() -> bool:
        return bool(should_stop and should_stop())

    if hash_total:
        status(
            f"Checking duplicates (look-alikes): {hash_total} new/changed file(s) "
            f"({reused} already checked) (0/{hash_total})..."
        )
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_hash_one, path): path for path in to_hash}
            for fut in as_completed(futures):
                if _stop():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise DuplicateScanCancelled()
                path, digest = fut.result()
                done += 1
                if digest:
                    hash_to_files.setdefault(digest, []).append(path)
                try:
                    stat = path.stat()
                    new_cache[path.name] = {
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                        "hash": digest,
                    }
                except OSError:
                    pass
                if done == 1 or done == hash_total or done % progress_every == 0:
                    status(
                        f"Checking duplicates (look-alikes): "
                        f"({done}/{hash_total})..."
                    )
    else:
        status(
            f"Checking duplicates (look-alikes): all {total} files already "
            f"checked - nothing new to decode."
        )

    _save_visual_hash_cache(paths, new_cache)
    report.merged_scanned = total

    for digest, group in sorted(hash_to_files.items(), key=lambda kv: kv[0]):
        if len(group) < 2:
            continue
        report.duplicate_groups += 1
        rep = sorted(group, key=lambda p: p.name)[0].name
        for path in sorted(group, key=lambda p: p.name):
            report.entries.append(
                DuplicateEntry(
                    filename=path.name,
                    duplicate_of=rep,
                    sha256=digest[:16],
                    moved_to=None,
                )
            )

    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    (paths.reports_dir / VISUAL_REPORT_NAME).write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    return report


def auto_delete_duplicate_extras(
    paths: AccountPaths,
    report: DuplicateScanReport,
    *,
    require_raw: bool = True,
) -> tuple[int, list[str]]:
    """Permanently delete non-keeper files from merged/ (and raw/ when present).

    Keeper = :func:`keeper_filename` (oldest timestamp name). Returns
    ``(files_deleted, deleted_path_labels)``. Rewrites the scan report so only
    keepers remain (groups disappear once size < 2).
    """
    groups = group_filenames_by_hash(report)
    if not groups:
        return 0, []

    folders: list[tuple[str, Path]] = [("merged", paths.merged_dir)]
    raw_dir = getattr(paths, "raw_dir", None)
    if require_raw and raw_dir is not None and raw_dir.is_dir():
        folders.append(("raw", raw_dir))

    deleted_labels: list[str] = []
    group_selections: dict[str, dict] = {}
    keepers_all: set[str] = set()
    for sha, names in groups.items():
        keeper = keeper_filename(names)
        keepers_all.add(keeper)
        extras = [n for n in names if n != keeper]
        group_selections[sha] = {"keepers": [keeper], "deleted": extras}
        for name in extras:
            for label, folder in folders:
                target = folder / name
                try:
                    if target.is_file():
                        target.unlink()
                        deleted_labels.append(f"{label}/{name}")
                except OSError:
                    pass

    # Drop resolved groups from the cached scan report.
    report.entries = [e for e in report.entries if e.filename in keepers_all]
    report.duplicate_groups = 0
    report.files_moved = len(deleted_labels)
    report_name = VISUAL_REPORT_NAME if report.kind == "visual" else BYTE_REPORT_NAME
    try:
        paths.reports_dir.mkdir(parents=True, exist_ok=True)
        (paths.reports_dir / report_name).write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        kind = report.kind or "byte"
        (paths.reports_dir / f"duplicates_deleted_report_{ts}.json").write_text(
            json.dumps(
                {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "account_name": paths.account_dir.name,
                    "action": "auto_permanent_delete",
                    "scan_kind": kind,
                    "deleted_count": len(deleted_labels),
                    "group_selections": group_selections,
                    "deleted_files": deleted_labels,
                    "errors": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass

    return len(deleted_labels), deleted_labels


def _hash_paths(
    paths_to_hash: list[Path],
    *,
    mode: Literal["byte", "visual"],
    hash_workers: int,
    status: Callable[[str], None] | None,
    label: str,
    should_stop: Callable[[], bool] | None = None,
    known_digests: dict[Path, str] | None = None,
) -> dict[str, list[Path]]:
    digest_to_files: dict[str, list[Path]] = {}
    if known_digests:
        for path, digest in known_digests.items():
            if digest:
                digest_to_files.setdefault(digest, []).append(path)
    if not paths_to_hash:
        return digest_to_files

    ffmpeg = None
    if mode == "visual":
        from smd.ffmpeg_bundle import resolve_ffmpeg

        ffmpeg = resolve_ffmpeg()

    workers = max(1, min(int(hash_workers), 16))
    total = len(paths_to_hash)
    every = max(25, total // 40)
    done = 0

    def _stop() -> bool:
        return bool(should_stop and should_stop())

    def one(path: Path) -> tuple[Path, str | None]:
        if mode == "byte":
            return path, _file_hash(path)
        return path, _content_hash(path, ffmpeg)

    def note() -> None:
        if status and (done == 1 or done == total or done % every == 0):
            status(f"{label} ({done}/{total})...")

    if workers == 1 or total < 40:
        for path in paths_to_hash:
            if _stop():
                raise DuplicateScanCancelled()
            p, digest = one(path)
            done += 1
            if digest:
                digest_to_files.setdefault(digest, []).append(p)
            note()
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(one, path): path for path in paths_to_hash}
            for fut in as_completed(futures):
                if _stop():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise DuplicateScanCancelled()
                p, digest = fut.result()
                done += 1
                if digest:
                    digest_to_files.setdefault(digest, []).append(p)
                note()
    return digest_to_files


def dedupe_staging_items(
    items: dict,
    *,
    reports_dir: Path,
    mode: Literal["byte", "visual"] = "byte",
    status_callback: Callable[[str], None] | None = None,
    hash_workers: int = 8,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[dict, int, int]:
    """Drop byte/visual-duplicate staging mains before processing (keep oldest stem name).

    Deletes discarded ``*-main`` / ``*-overlay`` files on disk and removes those
    stems from ``items``. JSON rows for discarded stems are simply unused -
    each memory is matched by its own UID/stem; other files' GPS/dates are
    untouched. Returns ``(items, groups_resolved, stems_removed)``.
    """
    def status(msg: str) -> None:
        if status_callback:
            status_callback(msg)

    mains: list[tuple[str, Path]] = []
    for stem, item in items.items():
        main = getattr(item, "main_path", None)
        if main is not None and Path(main).is_file():
            mains.append((stem, Path(main)))

    if len(mains) < 2:
        return items, 0, 0

    # Byte: only hash same-size buckets. Visual: hash everything (sizes differ).
    paths_to_hash: list[Path] = []
    known_digests: dict[Path, str] = {}
    new_staging_cache: dict[str, dict] = {}
    if mode == "byte":
        size_buckets: dict[int, list[Path]] = {}
        for _stem, path in mains:
            try:
                size_buckets.setdefault(path.stat().st_size, []).append(path)
            except OSError:
                continue
        for bucket in size_buckets.values():
            if len(bucket) >= 2:
                paths_to_hash.extend(bucket)
        label = "Removing duplicate staged copies (identical files)"
        if status and paths_to_hash:
            status(
                f"Found {len(paths_to_hash):,} staged files that share a file size "
                f"with something else (possible identical duplicates) — "
                f"checking those carefully..."
            )
    else:
        old_cache = _load_staging_visual_hash_cache(reports_dir)
        for _stem, path in mains:
            try:
                stat = path.stat()
            except OSError:
                continue
            cached = old_cache.get(path.name)
            if (
                cached
                and cached.get("size") == stat.st_size
                and cached.get("mtime_ns") == stat.st_mtime_ns
                and cached.get("hash")
            ):
                known_digests[path] = str(cached["hash"])
                new_staging_cache[path.name] = cached
            else:
                paths_to_hash.append(path)
        label = "Removing duplicate staged copies (look-alikes)"
        reused = len(known_digests)
        if reused and status:
            status(
                f"{label}: {reused} already checked in a previous run, "
                f"{len(paths_to_hash)} to decode..."
            )

    if status and (paths_to_hash or not known_digests):
        status(f"{label} (0/{max(1, len(paths_to_hash) or len(mains))})...")

    digest_to_files = _hash_paths(
        paths_to_hash,
        mode=mode,
        hash_workers=hash_workers,
        status=status,
        label=label,
        should_stop=should_stop,
        known_digests=known_digests or None,
    )

    if mode == "visual":
        path_to_digest = {
            path: dig for dig, files in digest_to_files.items() for path in files
        }
        for path in paths_to_hash:
            dig = path_to_digest.get(path)
            if not dig:
                continue
            try:
                stat = path.stat()
                new_staging_cache[path.name] = {
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "hash": dig,
                }
            except OSError:
                pass
        _save_staging_visual_hash_cache(reports_dir, new_staging_cache)

    path_to_stem = {p: stem for stem, p in mains}
    stems_to_drop: set[str] = set()
    groups = 0
    group_selections: dict[str, dict] = {}

    for digest, files in digest_to_files.items():
        if len(files) < 2:
            continue
        groups += 1
        names = [path_to_stem[p] for p in files if p in path_to_stem]
        # Keeper by stem/filename date (stem is YYYY-MM-DD_<uid>).
        keeper_stem = keeper_filename(names)
        extras = [s for s in names if s != keeper_stem]
        group_selections[digest[:16]] = {
            "keepers": [keeper_stem],
            "deleted": extras,
        }
        stems_to_drop.update(extras)

    removed = 0
    for stem in sorted(stems_to_drop):
        item = items.pop(stem, None)
        if item is None:
            continue
        for attr in ("main_path", "overlay_path"):
            path = getattr(item, attr, None)
            if path is None:
                continue
            try:
                p = Path(path)
                if p.is_file():
                    p.unlink()
                    removed += 1
            except OSError:
                pass

    if groups:
        try:
            reports_dir.mkdir(parents=True, exist_ok=True)
            out_name = (
                STAGING_VISUAL_DELETED_REPORT
                if mode == "visual"
                else STAGING_BYTE_DELETED_REPORT
            )
            (reports_dir / out_name).write_text(
                json.dumps(
                    {
                        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "action": "staging_auto_dedupe",
                        "scan_kind": mode,
                        "groups_resolved": groups,
                        "stems_removed": sorted(stems_to_drop),
                        "files_unlinked": removed,
                        "group_selections": group_selections,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    return items, groups, len(stems_to_drop)
