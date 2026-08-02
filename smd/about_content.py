"""About tab HTML — app info, trust, system status, and support."""
from __future__ import annotations

import html
import platform
import sys
from typing import Any

from smd.ffmpeg_bundle import bundled_status, resolve_ffmpeg, resolve_ffprobe, verify_tool
from smd.help_content import _callout, headed_title
from smd.runtime import (
    app_root,
    display_path,
    internal_root,
    is_frozen,
    sanitize_user_text,
)
from smd.support_links import AUTHOR_URL, support_options_html
from smd.version import __version__

_BODY = (
    "line-height: 1.65; font-size: 16px;"
    " p { margin: 0 0 12px; }"
    " ul { margin: 8px 0 12px 22px; padding: 0; }"
    " li { margin-bottom: 6px; }"
    " code { font-family: Consolas, monospace; font-size: 13px; "
    "background: rgba(128,128,128,0.15); padding: 1px 5px; border-radius: 4px; }"
    " table { width: 100%; border-collapse: collapse; margin: 12px 0 16px; font-size: 15px; }"
    " th, td { text-align: left; vertical-align: top; padding: 8px 10px; "
    "border-bottom: 1px solid rgba(128,128,128,0.3); }"
    " th { font-weight: 700; width: 34%; }"
)
# Title spacing from headed_title (level 3); light section separator only.
_SECTION = (
    "margin: 8px 0 8px; padding: 0 0 18px; border-bottom: 1px solid rgba(128,128,128,0.35);"
)
_MUTED = "opacity:0.85;font-size:14px;"


def _status_badge(ok: bool, ok_label: str = "OK", fail_label: str = "Missing") -> str:
    color = "rgba(45,138,62,0.9)" if ok else "rgba(196,92,10,0.95)"
    label = ok_label if ok else fail_label
    return f'<span style="font-weight:700; color:{color};">{html.escape(label)}</span>'


def _info_table(rows: list[tuple[str, str]]) -> str:
    cells = [
        f"<tr><th>{html.escape(key)}</th><td>{value}</td></tr>"
        for key, value in rows
    ]
    return f"<table>{''.join(cells)}</table>"


def _tool_version(exe_path: str | None) -> str:
    if not exe_path or not verify_tool(exe_path):
        return "-"
    from smd.procutil import run_tool

    r = run_tool([exe_path, "-version"], timeout=6)
    if r is not None and r.stdout:
        try:
            text = r.stdout.decode("utf-8", errors="replace")
        except Exception:
            text = str(r.stdout)
        line = text.splitlines()[0].strip() if text else ""
        if line:
            return line
    return "-"


def gather_about_facts(*, web_engine_available: bool) -> dict[str, Any]:
    """Collect runtime facts for the About tab."""
    tool_status = bundled_status()
    ffmpeg_path = resolve_ffmpeg()
    ffprobe_path = resolve_ffprobe()
    ffmpeg_ok = tool_status.get("ffmpeg") == "ok"
    ffprobe_ok = tool_status.get("ffprobe") == "ok"
    frozen = is_frozen()

    return {
        "version": __version__,
        "frozen": frozen,
        "package_mode": "Portable Windows build" if frozen else "Source / development run",
        "package_blurb": (
            "Self-contained - no Python or ffmpeg install required."
            if frozen
            else "Running from project source; bundled tools under tools/ffmpeg when present."
        ),
        "tools_ok": ffmpeg_ok and ffprobe_ok,
        "platform": html.escape(platform.platform()),
        "machine": html.escape(platform.machine()),
        "app_root": html.escape(display_path(app_root())),
        "internal_root": html.escape(display_path(internal_root())),
        "internal_same_as_install": display_path(internal_root()) == display_path(app_root()),
        "tool_source": html.escape(tool_status.get("source", "")),
        "ffmpeg_ok": ffmpeg_ok,
        "ffprobe_ok": ffprobe_ok,
        "ffmpeg_path": html.escape(display_path(ffmpeg_path)),
        "ffprobe_path": html.escape(display_path(ffprobe_path)),
        "ffmpeg_version": html.escape(_tool_version(ffmpeg_path)),
        "ffprobe_version": html.escape(_tool_version(ffprobe_path)),
        "web_engine_ok": web_engine_available,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_build": html.escape(
            sanitize_user_text(sys.version.split("\n", 1)[0])
        ),
    }


def _component_cell(ok: bool, path: str, version: str, ok_hint: str, fail_hint: str) -> str:
    status = _status_badge(ok, ok_label="Ready", fail_label="Not found")
    hint = ok_hint if ok else fail_hint
    return (
        f"{status}<br/>"
        f"<code>{path}</code><br/>"
        f"<span style='{_MUTED}'>{version}</span><br/>"
        f"<span style='{_MUTED}'>{hint}</span>"
    )


def build_about_html(
    *,
    web_engine_available: bool,
    accent: str | None = None,
    facts: dict[str, Any] | None = None,
) -> str:
    # facts may be cached across theme toggles (ffmpeg -version is slow).
    if facts is None:
        facts = gather_about_facts(web_engine_available=web_engine_available)
    map_status = (
        "Available - interactive map in File Checker."
        if facts["web_engine_ok"]
        else "Not in this build - GPS scan and file analysis still work."
    )

    parts = [
        f'<div style="{_BODY}">',
        # --- Header ---
        f"<section style='{_SECTION}'>",
        headed_title('Snapchat Memories Keeper (SMK)', level=2, accent=accent),
        f"<p>Version <b>{html.escape(facts['version'])}</b> - turns your Snapchat Memories export "
        "into a normal photo and video library on your PC, with capture dates, GPS, and filters "
        "preserved where Snapchat included them.</p>",
        f"<p>Created by <a href='{AUTHOR_URL}'><b>Las HS</b></a>. "
        "Source and releases: "
        "<a href='https://github.com/LasHSHS/SMK'><b>github.com/LasHSHS/SMK</b></a>. "
        "<b>Not affiliated with Snap Inc.</b></p>",
        "<p><b>Contributors welcome</b> — especially help making SMK work on "
        "<b>macOS</b> and <b>Linux</b>, plus bug fixes and performance. "
        "Open an issue or PR on the GitHub repo.</p>",
        f"<p style='{_MUTED}'>For step-by-step instructions and troubleshooting, see the "
        "<b>Guide</b> and <b>Help</b> tabs.</p>",
        "</section>",
        # --- Privacy ---
        f"<section style='{_SECTION}'>",
        headed_title('Privacy & trust', level=3, accent=accent),
        _callout(
            "ok",
            "Your data stays on your machine",
            "<ul style='margin:0 0 0 18px;padding:0;'>"
            "<li><b>No telemetry</b> - SMK does not phone home or collect usage analytics</li>"
            "<li><b>Local processing</b> - export ZIPs and output media never leave your PC</li>"
            "<li><b>Offline by default</b> - memory processing needs no internet; "
            "the optional GPS map may load map tiles when you open File Checker</li>"
            "</ul>",
        ),
        "<p>SMK only opens files and folders you choose. It does not access your Snapchat account "
        "or anything outside the export you provide.</p>",
        "</section>",
        # --- System status ---
        f"<section style='{_SECTION}'>",
        headed_title('System status', level=3, accent=accent),
        "<p>Quick check that this copy of SMK is ready to process video and maps.</p>",
        _info_table(
            [
                (
                    "Install type",
                    f"{html.escape(facts['package_mode'])}<br/>"
                    f"<span style='{_MUTED}'>{html.escape(facts['package_blurb'])}</span>",
                ),
                (
                    "This PC",
                    f"<code>{facts['platform']}</code> · {facts['machine']}<br/>"
                    f"<span style='{_MUTED}'>Official target: Windows 10/11 (64-bit).</span>",
                ),
                (
                    "ffmpeg",
                    _component_cell(
                        facts["ffmpeg_ok"],
                        facts["ffmpeg_path"],
                        facts["ffmpeg_version"],
                        "Video overlays and metadata tagging.",
                        "Missing - reinstall SMK or add tools under "
                        "<code>{install}\\tools\\ffmpeg\\</code>.",
                    ),
                ),
                (
                    "ffprobe",
                    _component_cell(
                        facts["ffprobe_ok"],
                        facts["ffprobe_path"],
                        facts["ffprobe_version"],
                        "Reads video streams and embedded GPS.",
                        "Missing - video processing needs both ffmpeg and ffprobe.",
                    ),
                ),
                (
                    "GPS map",
                    f"{_status_badge(facts['web_engine_ok'], ok_label='Available', fail_label='Unavailable')}<br/>"
                    f"<span style='{_MUTED}'>{html.escape(map_status)}</span>",
                ),
                (
                    "Tool source",
                    f"{facts['tool_source']}<br/>"
                    f"<span style='{_MUTED}'>"
                    "<code>bundled</code> = shipped with SMK · "
                    "<code>system PATH</code> = dev/source runs only</span>",
                ),
            ]
        ),
        "</section>",
        # --- Support ---
        f"<section style='{_SECTION}'>",
        headed_title('Support the project', level=3, accent=accent),
        support_options_html(),
        f"<p>Source code, issues, and releases: <a href='{AUTHOR_URL}'>GitHub - LasHSHS</a></p>",
        "</section>",
        # --- Technical details ---
        f"<section style='{_SECTION} border-bottom:none;'>",
        headed_title('Technical details', level=3, accent=accent),
        f"<p style='{_MUTED}'>For bug reports. Paths use placeholders - "
        "<code>{install}</code> is this app's folder - so nothing personal is exposed.</p>",
    ]

    tech_rows: list[tuple[str, str]] = [
        ("Install folder", f"<code>{facts['app_root']}</code>"),
    ]
    if facts["internal_same_as_install"]:
        tech_rows.append(
            (
                "Internal resources",
                f"<code>{facts['internal_root']}</code><br/>"
                f"<span style='{_MUTED}'>Same as install folder in this run.</span>",
            )
        )
    else:
        tech_rows.append(
            (
                "Internal resources",
                f"<code>{facts['internal_root']}</code><br/>"
                f"<span style='{_MUTED}'>Bundled assets extracted at startup (portable build).</span>",
            )
        )
    if not facts["frozen"]:
        tech_rows.append(
            (
                "Python",
                f"{facts['python']}<br/>"
                f"<span style='{_MUTED}'>{facts['python_build']}</span>",
            )
        )

    parts.append(_info_table(tech_rows))
    parts.append(
        "<p style='opacity:0.85;font-size:14px;'>Snapchat, Snap, and related marks are trademarks of Snap Inc. "
        "This project is an independent tool for personal data exports.</p>"
    )
    parts.append("</section></div>")
    return "".join(parts)
