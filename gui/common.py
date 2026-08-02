"""Shared constants and helpers for the SMK desktop GUI."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextBrowser

# User-facing name for the main workflow tab (was "Process").
TAB_SAVE_MEMORIES = "Save memories"

# When frozen (PyInstaller), __file__ resolves inside _internal/, which is
# regenerated wholesale on every build - use the exe's own directory instead.
# When running from source, gui/common.py lives one level under the repo root.
ROOT = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)

if os.environ.get("SMD_DISABLE_WEBENGINE") == "1":
    QWebEngineView = None  # type: ignore
    WEB_ENGINE_AVAILABLE = False
else:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView  # Optional; excluded in lightweight builds

        WEB_ENGINE_AVAILABLE = True
    except Exception:
        QWebEngineView = None  # type: ignore
        WEB_ENGINE_AVAILABLE = False

# Optional Windows-only happy tone
try:
    import winsound  # Available on Windows
except Exception:
    winsound = None


def _doc_browser_anchor_clicked(browser: QTextBrowser, url: QUrl) -> None:
    """Scroll in-page for #anchors; open http(s) links externally."""
    scheme = url.scheme().lower()
    if scheme in ("http", "https", "mailto"):
        QDesktopServices.openUrl(url)
        return
    fragment = url.fragment()
    if fragment:
        browser.scrollToAnchor(fragment)


def build_help_panel() -> QWidget:
    """Illustrative help - same DocBrowser style as the Guide tab."""
    from gui.widgets import DocBrowser

    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    from smd.help_content import build_help_html, inject_title_rule_image
    from smd.theme import palette

    accent = palette(True)["secondary"]
    browser = DocBrowser()
    browser.setObjectName("helpDocBrowser")
    browser.setOpenExternalLinks(False)
    # Theme sync rebuilds with live accent; seed dark secondary for first paint.
    browser.setHtml(build_help_html(TAB_SAVE_MEMORIES, accent=accent))
    inject_title_rule_image(browser, accent)
    browser.anchorClicked.connect(lambda url: _doc_browser_anchor_clicked(browser, url))
    lay.addWidget(browser, 1)
    return panel


def build_palestine_panel() -> QWidget:
    """Palestine tab - solidarity framing and external resource links."""
    from gui.widgets import DocBrowser

    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    from smd.help_content import inject_title_rule_image
    from smd.palestine_content import build_palestine_html
    from smd.theme import palette

    accent = palette(True)["secondary"]
    browser = DocBrowser()
    browser.setObjectName("palestineDocBrowser")
    browser.setOpenExternalLinks(False)
    browser.setHtml(build_palestine_html(accent=accent))
    inject_title_rule_image(browser, accent)
    browser.anchorClicked.connect(lambda url: _doc_browser_anchor_clicked(browser, url))
    lay.addWidget(browser, 1)
    return panel


def build_about_panel() -> QWidget:
    """About tab - version, credits, environment, and component status."""
    from gui.widgets import DocBrowser

    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    from smd.about_content import build_about_html
    from smd.help_content import inject_title_rule_image
    from smd.theme import palette

    accent = palette(True)["secondary"]
    browser = DocBrowser()
    browser.setObjectName("aboutDocBrowser")
    browser.setHtml(
        build_about_html(web_engine_available=WEB_ENGINE_AVAILABLE, accent=accent)
    )
    inject_title_rule_image(browser, accent)
    browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))
    lay.addWidget(browser, 1)
    return panel


def build_guide_panel(go_to_process_cb) -> QWidget:
    """Single-column guide: outer scroll only, text and screenshots stacked vertically."""
    from smd.guide_content import build_guide_html, guide_assets_dir
    from smd.help_content import inject_title_rule_image

    from gui.widgets import FlowDocBrowser

    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setSpacing(12)
    lay.setContentsMargins(0, 0, 0, 0)

    from smd.theme import palette

    accent = palette(True)["secondary"]
    browser = FlowDocBrowser()
    browser.setObjectName('guideDocBrowser')
    browser.setSearchPaths([str(guide_assets_dir())])
    # Theme sync rebuilds this with the live accent; seed dark secondary for first paint.
    browser.setHtml(build_guide_html(TAB_SAVE_MEMORIES, accent=accent))
    inject_title_rule_image(browser, accent)
    browser.anchorClicked.connect(lambda url: QDesktopServices.openUrl(url))

    go_btn = QPushButton(f"Go to {TAB_SAVE_MEMORIES}")
    go_btn.setObjectName("accentBtn")
    go_btn.clicked.connect(go_to_process_cb)

    lay.addWidget(browser, 0)
    lay.addWidget(go_btn, 0)
    return panel


def play_happy_tone():
    """Play a short happy completion tone on Windows; no-op elsewhere."""
    try:
        if winsound:
            winsound.Beep(880, 120)
            winsound.Beep(1200, 160)
            winsound.Beep(1500, 140)
    except Exception:
        pass


def friendly_error_message(error_obj):
    """Convert technical Python errors to friendly user messages."""
    error_str = str(error_obj).lower()
    error_type = type(error_obj).__name__
    if "permission" in error_str or "permissionerror" in error_type:
        return "The app doesn't have permission to access that folder. Check your Windows settings."
    elif "connectionerror" in error_type or "timeout" in error_str or "connection" in error_str:
        return "Network error. Please check your internet connection and try again."
    elif "filenotfound" in error_type or "no such file" in error_str:
        return "File not found. The folder or file may have been moved or deleted."
    elif "module" in error_str:
        return "A required component is missing. The app download may be corrupted. Please reinstall."
    elif "invalid" in error_str and "credential" in error_str:
        return "Invalid Snapchat username or password. Please check and try again."
    elif "json" in error_str:
        return "The Snapchat data file is corrupted. Please download again."
    else:
        return "An unexpected error occurred. Please try again. If this persists, contact support."


def configure_webengine_storage() -> None:
    """Use a dedicated WebEngine profile so stray pythonw processes cannot deadlock startup."""
    if not WEB_ENGINE_AVAILABLE:
        return
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineProfile

        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SnapchatMemoriesDownloader" / "WebEngine"
        base.mkdir(parents=True, exist_ok=True)
        profile = QWebEngineProfile.defaultProfile()
        profile.setCachePath(str(base / "cache"))
        profile.setPersistentStoragePath(str(base / "storage"))
    except Exception as exc:
        print(f"DEBUG: WebEngine storage setup skipped: {exc}")


def startup_log(message: str) -> None:
    """Append startup diagnostics to smk_gui.log (works under pythonw)."""
    try:
        with (ROOT / "smk_gui.log").open("a", encoding="utf-8") as log_file:
            log_file.write(message.rstrip() + "\n")
            log_file.flush()
    except OSError:
        pass
