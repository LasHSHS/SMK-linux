"""Product name and short code (user-facing).

Internal package folder remains ``smd/``; AppData and QSettings keep legacy
paths so existing installs do not lose accounts or preferences.
"""
from __future__ import annotations

APP_NAME = "Snapchat Memories Keeper"
APP_SHORT = "SMK"

# Previous product identity (window focus, docs, migration).
APP_NAME_LEGACY = "Snapchat Memories Downloader"
APP_SHORT_LEGACY = "SMD"

# %LOCALAPPDATA%\<this>\accounts\… — keep legacy dirname so technical data stays found.
INTERNAL_APP_DIRNAME = "SnapchatMemoriesDownloader"

# QSettings org/app — keep so registry preferences survive the rebrand.
SETTINGS_ORG = "SnapchatMemories"
SETTINGS_APP = "Downloader"

# Secondary QSettings used for performance mode (legacy).
PERF_SETTINGS_ORG = "SMD"
PERF_SETTINGS_APP = "SnapchatMemoriesDownloader"

APP_USER_MODEL_ID = "SMK.SnapchatMemoriesKeeper"


def window_title(version: str) -> str:
    return f"{APP_NAME} v{version}"


def matches_window_title(title: str) -> bool:
    t = (title or "").strip()
    return t.startswith(APP_NAME) or t.startswith(APP_NAME_LEGACY)
