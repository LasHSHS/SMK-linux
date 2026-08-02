"""Rough processing time estimates for bundled exports."""
from __future__ import annotations

from smd.system_profile import PERF_MODES, SystemProfile, compute_workers, get_system_profile

# Calibration (Maximum mode, same PC class: 8c/16t, SSD, AMD GPU encode):
# - Las: 13 442 memories (~61% video, ~17% overlays), **~49 GB ZIP parts**
#   (≈ Snapchat’s ~50.6 GB cloud; folder looked ~2× when an extracted/ copy
#   sat beside the ZIPs), ~53 GB merged / ~44 GB raw; **3 h 33 min** wall.
# - Mary: 681 memories (~50% video, ~0.4% overlays), ~6.1 GB ZIP ≈ library;
#   **~7 min** wall (look-alike duplicate scans dominate).
#
# ETA uses file count + video/overlay mix; ZIP GB only for extract read cost.


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)} sec"
    if seconds < 3600:
        return f"{int(seconds // 60)} min {int(seconds % 60)} sec"
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    return f"{hours} hr {mins} min"


def estimate_bundled_processing(
    file_count: int,
    *,
    profile: SystemProfile | None = None,
    overlay_fraction: float = 0.24,
    video_fraction: float = 0.40,
    needs_zip_extract: bool = False,
    staging_gb: float = 0.0,
) -> dict[str, dict[str, str | float]]:
    """
    Estimate full-run wall time per performance mode (extract + duplicate
    checks + merge/encode + metadata).

    Returns {mode: {seconds, label, workers, note}}.
    """
    profile = profile or get_system_profile()
    file_count = max(1, int(file_count))
    overlay_fraction = min(1.0, max(0.0, float(overlay_fraction)))
    video_fraction = min(1.0, max(0.0, float(video_fraction)))

    # Serial-equivalent seconds per memory before dividing by merge workers.
    # base ≈ photo EXIF + typical video metadata remux (GPU/stream copy path).
    # overlay_vid ≈ filter bake + re-encode (AMF/NVENC/QSV when available).
    base = 0.85
    overlay_img = 2.0
    overlay_vid = 48.0
    per_item = (
        base
        + overlay_fraction * overlay_img
        + overlay_fraction * video_fraction * overlay_vid
    )

    extract_sec = 0.0
    if needs_zip_extract:
        # ZIP folder GB (bytes read), not finished library size.
        gb = staging_gb if staging_gb > 0 else max(1.0, file_count * 0.003)
        extract_sec = gb * 6.0

    # Staging + post-run look-alike passes. Sublinear-ish: fixed overhead plus
    # per-file cost (Mary needs the per-file term; huge libraries don't scale
    # purely linearly with hash workers).
    dup_scan_sec = 2.0 * (35.0 + file_count * 0.195)

    results: dict[str, dict[str, str | float]] = {}
    for mode in PERF_MODES:
        settings = compute_workers(mode, profile, task="export")
        workers = max(1, settings.max_workers)
        merge_sec = (file_count * per_item) / workers
        if mode == "conservative":
            merge_sec *= 1.35
        elif mode == "balanced":
            merge_sec *= 1.1
        total = extract_sec + dup_scan_sec + merge_sec
        note_parts = ["rough guide — video-heavy libraries take hours"]
        if needs_zip_extract:
            note_parts.append("includes ZIP extract")
        if mode == "conservative":
            note_parts.append("leaves CPU headroom for other work")
        elif mode == "maximum":
            note_parts.append("uses most of your CPU")
        results[mode] = {
            "seconds": total,
            "label": _format_duration(total),
            "workers": workers,
            "note": "; ".join(note_parts),
        }
    return results
