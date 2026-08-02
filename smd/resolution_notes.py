"""Soft labels for photo resolutions in File Checker (no phone brand guesses)."""
from __future__ import annotations

# Known Snapchat export / story crops — not native phone screens.
# Empirically common in memories_history exports after SMK processing.
_SNAPCHAT_EXPORT_SIZES: frozenset[tuple[int, int]] = frozenset(
    {
        (1008, 1792),
        (1792, 1008),
        (720, 1280),
        (1280, 720),
        (540, 960),
        (960, 540),
    }
)


def resolution_note(width: int, height: int) -> str | None:
    """Short parenthetical note for a WxH size, or None.

    Never names phone brands — Snapchat strips Make/Model and often crops
    away from native screen size, so brand guesses would be wrong too often.
    """
    pair = (int(width), int(height))
    if pair in _SNAPCHAT_EXPORT_SIZES or (pair[1], pair[0]) in _SNAPCHAT_EXPORT_SIZES:
        return "common Snapchat export size"

    w, h = pair
    if w <= 0 or h <= 0:
        return None
    ratio = max(w, h) / min(w, h)
    if ratio >= 1.7:
        return "tall phone portrait" if h > w else "wide landscape"
    return None


def parse_resolution_key(key: str) -> tuple[int, int] | None:
    """Parse '1008x1792' into (1008, 1792)."""
    try:
        left, right = key.lower().split("x", 1)
        return int(left), int(right)
    except (ValueError, AttributeError):
        return None
