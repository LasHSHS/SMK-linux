"""Shared media extension constants for File Checker and scanners."""
from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".m4v"})
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# Magic-byte extension check (subset used by legacy ScanWorker)
MAGIC_CHECK_EXTENSIONS = frozenset({".jpg", ".jpeg", ".mp4", ".m4v"})


def is_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def is_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def format_bytes(bytes_val: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def extension_matches_magic(suffix: str, actual_type: str | None) -> bool:
    """True when filename extension matches detected magic-byte type."""
    if actual_type is None:
        return True
    suffix = suffix.lower()
    if actual_type == "jpg":
        return suffix in (".jpg", ".jpeg")
    if actual_type == "mp4":
        return suffix in (".mp4", ".m4v")
    return True


def _dir_has_media_files(folder: Path) -> bool:
    """True if folder has at least one media file (shallow, then one rglob pass)."""
    if not folder.is_dir():
        return False
    try:
        for path in folder.iterdir():
            if is_media_file(path):
                return True
        for path in folder.rglob("*"):
            if is_media_file(path):
                return True
    except OSError:
        return False
    return False


def resolve_check_folder(folder: str | Path) -> tuple[Path, str | None]:
    """Pick the folder File Checker should scan.

    If the user selects a parent that contains both ``merged/`` and ``raw/``
    (same memories; scanning both would double-count on the map), prefer
    ``merged/``. Fall back to ``raw/`` only when merged has no media.

    Returns ``(scan_path, note)``. ``note`` explains a redirect, or None when
    the picked folder is used as-is.
    """
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        return path, None

    # Already on an output folder — do not climb.
    if path.name.lower() in ("merged", "raw"):
        return path, None

    merged = path / "merged"
    raw = path / "raw"
    if _dir_has_media_files(merged):
        return merged, (
            f"Using merged/ (you picked {path} — finished files; "
            "same memories as raw/, not both)"
        )
    if _dir_has_media_files(raw):
        return raw, (
            f"Using raw/ (you picked {path} — no media found in merged/)"
        )
    return path, None
