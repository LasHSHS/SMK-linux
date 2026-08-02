"""Resolve bundled ffmpeg/ffprobe (all-in-one SMK package) or system PATH fallback."""
from __future__ import annotations

import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from smd.runtime import app_root, bundled_dir, is_frozen


def _exe_names(tool: str) -> tuple[str, ...]:
    """Windows uses .exe; macOS/Linux use bare names."""
    if sys.platform.startswith("win"):
        return (f"{tool}.exe",)
    return (tool, f"{tool}.exe")


def _bundled_tool_dir() -> Path:
    found = bundled_dir("tools", "ffmpeg")
    if found is not None:
        for name in _exe_names("ffmpeg"):
            if (found / name).is_file():
                return found
    return app_root() / "tools" / "ffmpeg"


def _resolve_tool(tool: str) -> str | None:
    base = _bundled_tool_dir()
    for name in _exe_names(tool):
        candidate = base / name
        if candidate.is_file():
            return str(candidate)
    return shutil.which(tool)


def resolve_ffmpeg() -> str | None:
    """Path to ffmpeg executable, or None if unavailable."""
    return _resolve_tool("ffmpeg")


def resolve_ffprobe() -> str | None:
    """Path to ffprobe executable, or None if unavailable."""
    return _resolve_tool("ffprobe")


def ffmpeg_available() -> bool:
    return resolve_ffmpeg() is not None


def ffprobe_available() -> bool:
    return resolve_ffprobe() is not None


@lru_cache(maxsize=16)
def verify_tool(exe_path: str | None, version_args: tuple[str, ...] = ("-version",)) -> bool:
    if not exe_path:
        return False
    from smd.procutil import subprocess_flags

    startupinfo, creationflags = subprocess_flags()
    try:
        r = subprocess.run(
            [exe_path, *version_args],
            capture_output=True,
            timeout=8,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


@lru_cache(maxsize=1)
def bundled_status() -> dict[str, str]:
    """Human-readable status for About / startup checks."""
    ff = resolve_ffmpeg()
    fp = resolve_ffprobe()
    bundled_dir_path = _bundled_tool_dir()
    using_bundle = any((bundled_dir_path / name).is_file() for name in _exe_names("ffmpeg"))
    if is_frozen():
        source = "bundled" if using_bundle else "missing from package"
    else:
        source = "bundled" if using_bundle else "system PATH"
    return {
        "source": source,
        "frozen": is_frozen(),
        "ffmpeg": "ok" if verify_tool(ff) else "missing",
        "ffprobe": "ok" if verify_tool(fp) else "missing",
        "ffmpeg_path": ff or "",
        "ffprobe_path": fp or "",
    }
