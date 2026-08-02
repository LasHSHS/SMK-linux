"""Illustrative Help tab HTML (Qt QTextBrowser) - same visual language as the Guide."""
from __future__ import annotations

import html

_BODY = (
    "line-height: 1.65; font-size: 16px;"
    " p { margin: 0 0 12px; }"
    " ul { margin: 8px 0 12px 22px; padding: 0; }"
    " li { margin-bottom: 6px; }"
    " code { font-family: Consolas, monospace; font-size: 13px; "
    "background: rgba(128,128,128,0.15); padding: 1px 5px; border-radius: 4px; }"
)
# Title spacing comes from headed_title (level 3 top margin). Keep a light
# section separator only — Qt often collapses/ignores section margin-top.
_SECTION = (
    "margin: 8px 0 8px; padding: 0 0 20px; border-bottom: 1px solid rgba(128,128,128,0.35);"
)
# Kept for any leftover call sites; prefer headed_title().
_H2 = "margin: 0 0 12px; font-size: 22px; font-weight: 700;"
_H3 = "margin: 0 0 10px; font-size: 18px; font-weight: 700;"
_TOC = (
    "font-size: 15px; line-height: 2; margin: 16px 0 24px; padding: 14px 18px; "
    "background: rgba(128,128,128,0.1); border-radius: 10px;"
)


# Document image name for short title rules (see inject_title_rule_image).
TITLE_RULE_IMAGE = "smk_title_rule.png"


def _title_rule_width(text: str, size_px: int) -> int:
    """Pixel width for the short bar — match title text like Save Memories."""
    try:
        from PyQt5.QtGui import QFont, QFontMetrics

        from smd.theme import FONT_STACK_DISPLAY

        font = QFont()
        # QSS uses a CSS stack; pick the first family for measuring.
        family = FONT_STACK_DISPLAY.split(",")[0].strip().strip('"').strip("'")
        font.setFamily(family or "Segoe UI")
        font.setPixelSize(size_px)
        font.setWeight(QFont.DemiBold)
        return max(24, QFontMetrics(font).horizontalAdvance(text))
    except Exception:
        return max(24, int(len(text) * size_px * 0.52))


def headed_title(text: str, *, level: int = 2, accent: str | None = None) -> str:
    """Title + short accent underline under the text (Save Memories style).

    Uses a 2-row table so Qt cannot place the rule image inline after the
    title (``<div>``+``<img>`` was rendering the bar at the end of the line).
    Call :func:`inject_title_rule_image` after ``setHtml`` so the image exists.
    """
    # accent kept for API/theme sync; color comes from the injected image.
    _ = accent
    safe = html.escape(text)
    size = 22 if level <= 2 else 18
    # Main page title: no extra top gap. Section/step titles: ~one blank line.
    margin_top = 0 if level <= 2 else 26
    margin_bottom = 12 if level <= 2 else 10
    rule_w = _title_rule_width(text, size)
    # Two rows: title, then bar — same structure as QLabel + QFrame#sectionTitleRule.
    return (
        f'<table border="0" cellspacing="0" cellpadding="0" '
        f'style="margin:{margin_top}px 0 {margin_bottom}px 0;">'
        f'<tr><td style="font-size:{size}px; font-weight:700; '
        f'line-height:1.2; padding:0;">{safe}</td></tr>'
        f'<tr><td style="padding:4px 0 0 0; line-height:2px;">'
        f'<img src="{TITLE_RULE_IMAGE}" width="{rule_w}" height="2" /></td></tr>'
        f"</table>"
    )


def inject_title_rule_image(browser, accent: str) -> None:
    """Install a solid accent bar image used by :func:`headed_title`."""
    from PyQt5.QtCore import QUrl
    from PyQt5.QtGui import QColor, QImage, QTextDocument

    img = QImage(8, 2, QImage.Format_ARGB32)
    img.fill(QColor(accent))
    browser.document().addResource(
        QTextDocument.ImageResource,
        QUrl(TITLE_RULE_IMAGE),
        img,
    )
    # Ensure the layout picks up the newly available image.
    browser.document().markContentsDirty(0, max(1, browser.document().characterCount()))
    browser.viewport().update()


def _callout(kind: str, title: str, body: str) -> str:
    styles = {
        "warn": "background: rgba(196,92,10,0.16); border: 2px solid rgba(196,92,10,0.55);",
        "ok": "background: rgba(45,138,62,0.14); border: 2px solid rgba(45,138,62,0.45);",
        "info": "background: rgba(128,128,128,0.12); border: 2px solid rgba(128,128,128,0.4);",
        "tip": "background: rgba(245,196,0,0.14); border: 2px solid rgba(184,148,26,0.5);",
    }
    box = styles.get(kind, styles["info"])
    return (
        f'<div style="{box} border-radius: 10px; padding: 14px 16px; margin: 16px 0;">'
        f'<p style="margin:0 0 8px; font-size:17px; font-weight:700;">{html.escape(title)}</p>'
        f'<div style="{_BODY}">{body}</div></div>'
    )


def _flow_diagram(steps: list[tuple[str, str]]) -> str:
    cells = []
    for i, (label, caption) in enumerate(steps):
        cells.append(
            '<td style="text-align:center; vertical-align:top; padding:4px 6px;">'
            f'<div style="background:rgba(128,128,128,0.15); border:1px solid rgba(128,128,128,0.45); '
            f'border-radius:8px; padding:10px 12px; min-width:80px;">'
            f'<div style="font-weight:700; font-size:14px;">{html.escape(label)}</div>'
            f'<div style="font-size:12px; margin-top:4px; opacity:0.85;">{html.escape(caption)}</div>'
            "</div></td>"
        )
        if i < len(steps) - 1:
            cells.append(
                '<td style="text-align:center; vertical-align:middle; '
                'font-size:18px; padding:0 3px; color:rgba(128,128,128,0.9);">→</td>'
            )
    return (
        '<table style="width:100%; border-collapse:collapse; margin:16px 0 8px;">'
        f"<tr>{''.join(cells)}</tr></table>"
    )


def _pipeline_ladder(steps: list[tuple[str, str]]) -> str:
    rows = []
    for i, (title, detail) in enumerate(steps, start=1):
        rows.append(
            "<tr>"
            f'<td style="width:44px; vertical-align:top; padding:6px 10px 6px 0;">'
            f'<div style="width:32px; height:32px; line-height:32px; text-align:center; '
            f'border-radius:16px; font-weight:700; font-size:14px; '
            f'background:rgba(196,92,10,0.25); border:1px solid rgba(196,92,10,0.5);">{i}</div>'
            "</td>"
            f'<td style="vertical-align:top; padding:6px 0 14px;">'
            f'<div style="font-weight:700; font-size:15px; margin-bottom:4px;">{html.escape(title)}</div>'
            f'<div style="font-size:14px; line-height:1.5; opacity:0.9;">{detail}</div>'
            "</td></tr>"
        )
    return (
        '<table style="width:100%; border-collapse:collapse; margin:12px 0;">'
        f"{''.join(rows)}</table>"
    )


def _checklist(items: list[tuple[str, str]]) -> str:
    rows = []
    for title, detail in items:
        rows.append(
            "<tr>"
            '<td style="width:28px; vertical-align:top; padding:4px 10px 10px 0;">'
            '<div style="width:22px; height:22px; border:2px solid rgba(196,92,10,0.6); '
            'border-radius:4px; text-align:center; line-height:20px; font-size:14px;">☐</div>'
            "</td>"
            f'<td style="vertical-align:top; padding:4px 0 10px;">'
            f'<div style="font-weight:700; font-size:15px;">{html.escape(title)}</div>'
            f'<div style="font-size:14px; line-height:1.5; opacity:0.9; margin-top:3px;">{detail}</div>'
            "</td></tr>"
        )
    return (
        '<table style="width:100%; border-collapse:collapse; margin:14px 0;">'
        f"{''.join(rows)}</table>"
    )


def _tree_block(text: str) -> str:
    return (
        f'<pre style="font-family:Consolas,monospace; font-size:13px; line-height:1.45; '
        f"background:rgba(128,128,128,0.1); border-left:4px solid rgba(196,92,10,0.7); "
        f'border-radius:0 8px 8px 0; padding:14px 16px; margin:12px 0; white-space:pre-wrap;">'
        f"{html.escape(text)}</pre>"
    )


def _compare_two(left_title: str, left_body: str, right_title: str, right_body: str) -> str:
    return (
        '<table style="width:100%; border-collapse:collapse; margin:14px 0;">'
        "<tr>"
        '<td style="width:50%; vertical-align:top; padding:6px;">'
        '<div style="border:2px solid rgba(196,92,10,0.45); border-radius:10px; padding:14px;">'
        f'<div style="font-weight:700; font-size:16px; margin-bottom:8px;">{html.escape(left_title)}</div>'
        f'<div style="{_BODY}">{left_body}</div></div></td>'
        '<td style="width:50%; vertical-align:top; padding:6px;">'
        '<div style="border:2px solid rgba(128,128,128,0.45); border-radius:10px; padding:14px;">'
        f'<div style="font-weight:700; font-size:16px; margin-bottom:8px;">{html.escape(right_title)}</div>'
        f'<div style="{_BODY}">{right_body}</div></div></td>'
        "</tr></table>"
    )


def build_help_html(process_tab_name: str = "Save memories", *, accent: str | None = None) -> str:
    p = html.escape(process_tab_name)
    parts = [
        "<div style='line-height:1.55;'>",
        headed_title('Help', level=2, accent=accent),
        f"<p style='{_BODY} margin-bottom:12px;'>"
        "Turn your Snapchat export into dated photos and videos on your PC - filters, GPS, and all. "
        "Use the <b>Guide</b> tab for Snapchat steps; this page covers SMK itself.</p>",
        f'<nav style="{_TOC}">'
        "<b>On this page</b><br>"
        '<a href="#start">1. Start here</a><br>'
        '<a href="#before">2. Before export</a><br>'
        f'<a href="#run">3. Run processing</a><br>'
        '<a href="#folders">4. Where files go</a><br>'
        '<a href="#after">5. After processing</a><br>'
        '<a href="#fix">6. Troubleshooting</a>'
        "</nav>",
        f'<section id="start" style="{_SECTION}">',
        headed_title('1. Start here', level=3, accent=accent),
        _flow_diagram(
            [
                ("Guide tab", "Request export"),
                ("Email", "Download all ZIPs"),
                (process_tab_name, "Start processing"),
                ("Desktop folder", "Your library"),
            ]
        ),
        _checklist(
            [
                (
                    "All ZIP parts in one folder",
                    "Names like <code>mydata~123.zip</code>, <code>mydata~123-2.zip</code>. "
                    f"Pick any one file or the whole folder on the <b>{p}</b> tab.",
                ),
                (
                    "Export summary looks right",
                    "Yellow banner should say <b>Bundled export</b> with ZIP part count and media file count.",
                ),
                (
                    "Project name set",
                    "Example <code>Mary</code> - folder is created when processing <b>starts</b>, not while typing.",
                ),
                (
                    "Enough disk space",
                    "Plan about <b>ZIP size + ~5 GB</b> free (Windows headroom). "
                    "Filters-only finish is usually near the ZIP size; "
                    "<b>Also save without filters</b> needs about <b>2× ZIP + ~5 GB</b>. "
                    "SMK warns before Start if space looks tight — you can still continue.",
                ),
            ]
        ),
        _callout(
            "tip",
            "New to Snapchat export?",
            "Open the <b>Guide</b> tab first - it has screenshots for requesting your data.",
        ),
        _callout(
            "info",
            "Stopped, crashed, or closed mid-run?",
            "<p>SMK saves progress as it goes. To continue:</p>"
            "<ol>"
            "<li>Open the same account (Existing account / same name).</li>"
            "<li>Select the <b>same</b> Snapchat export folder (same ZIP parts).</li>"
            "<li>Click <b>Start processing</b> again.</li>"
            "</ol>"
            "<p>Finished files are skipped; work resumes from what is left. "
            "If the PC ran out of disk space, free space first, then Start again the same way.</p>"
            "<p>Do <b>not</b> delete <code>technical/checkpoint/</code> or rename the account "
            "folder if you want a clean resume.</p>",
        ),
        "</section>",
        f'<section id="before" style="{_SECTION}">',
        headed_title('2. Before export', level=3, accent=accent),
        _callout(
            "warn",
            "My Eyes Only is never included",
            "<p>Unlock <b>My Eyes Only</b> and move snaps into <b>Memories</b> "
            "<b>before</b> you submit the data request. SMK cannot recover what Snapchat omitted.</p>"
            "<p>Snaps never saved to Memories (Camera Roll only, chats, expired stories) are excluded too.</p>",
        ),
        _compare_two(
            "Download link - expires",
            "<p>Snapchat’s email link for each ZIP part - often only a few days.</p>"
            "<p>Download <b>every part</b> before it expires.</p>",
            "ZIP on disk - permanent",
            "<p>Once saved, process offline anytime.</p>"
            "<p>Keep ZIPs as backup until your library looks complete.</p>",
        ),
        f"<p style='{_BODY}'>Inside each ZIP part:</p>",
        _tree_block(
            "memories_history.json     dates, GPS, titles\n"
            "memories/\n"
            "  abc-main.jpg + abc-overlay.png    filter layer\n"
            "  def-main.mp4 + def-overlay.png\n"
            "  …"
        ),
        _callout(
            "ok",
            "Bundled export (current Snapchat format)",
            "<p>Media is already inside the ZIP. JSON rows with <b>no URL</b> or <code>N/A</code> are "
            "<b>normal</b> - files live in <code>memories/</code>, not on the web.</p>"
            "<p>Older exports without bundled media are <b>not supported</b> - request a fresh export from Snapchat.</p>",
        ),
        "</section>",
        f'<section id="run" style="{_SECTION}">',
        headed_title('3. Run processing', level=3, accent=accent),
        f"<p style='{_BODY}'>On the <b>{p}</b> tab:</p>",
        _pipeline_ladder(
            [
                (
                    "Select ZIP files or folder",
                    "<b>Select ZIP folder</b> is easiest when all parts sit together.",
                ),
                (
                    "Choose performance + estimate",
                    "<b>Maximum</b> / <b>Balanced</b> / <b>Eco</b>. The estimate under Performance "
                    "updates from your ZIP (file count, video/filter mix) — rough guide only; "
                    "big libraries can take hours.",
                ),
                (
                    "Run block options",
                    "Filters are always included. Optionally tick <b>Also save without filters</b> for plain copies "
                    "(uses about twice the disk). "
                    "Tick <b>Technical view</b> only if you need logs, duplicate review, or run-info copies "
                    "(see section 4).",
                ),
                (
                    "Start processing",
                    "Extract → match JSON → merge overlays → embed metadata → summary popup. "
                    "New account name? The folder is created then.",
                ),
            ]
        ),
        f"<p style='{_BODY}'>During the run:</p>",
        _pipeline_ladder(
            [
                (
                    "Checkpoint every 25 files",
                    "Progress saved under technical storage so you can cancel and resume later.",
                ),
                (
                    "Output filenames",
                    "From JSON date/time, e.g. <code>2019-07-04_18-32-01.jpg</code>. "
                    "Collisions get a suffix - see <code>technical/reports/filename_collisions.json</code> "
                    "(Technical view).",
                ),
                (
                    "Metadata",
                    "JPEG EXIF date + GPS when available. Same for MP4/MOV container tags.",
                ),
            ]
        ),
        _callout(
            "info",
            "Privacy",
            "Bundled processing stays on your PC. SMK is not affiliated with Snap Inc.",
        ),
        "</section>",
        f'<section id="folders" style="{_SECTION}">',
        headed_title('4. Where files go', level=3, accent=accent),
        f"<p style='{_BODY}'>Layout depends on <b>Technical view</b> on the Run card (off by default):</p>",
        _compare_two(
            "Simple (default)",
            "<p><b>Your photos/videos:</b> <code>Desktop/&lt;name&gt;-memories/</code></p>"
            "<p>If <b>Also save without filters</b> is on:</p>"
            "<ul>"
            "<li><code>…/merged/</code> - with filters</li>"
            "<li><code>…/raw/</code> - plain copies</li>"
            "</ul>"
            "<p><b>Working data</b> (staging, JSON, checkpoints) lives under "
            "<code>%LOCALAPPDATA%\\SnapchatMemoriesDownloader\\accounts\\…\\technical\\</code> "
            "- out of the way for normal browsing.</p>",
            "Technical view (advanced)",
            "<p>Account folder under your chosen base (default <code>Desktop/</code>): "
            "<code>&lt;base&gt;/&lt;name&gt;-memories/</code></p>"
            "<ul>"
            "<li>Photos/videos in that folder (or <code>merged/</code> + <code>raw/</code> "
            "if Also save without filters)</li>"
            "<li><code>technical/staging/</code> - large temp extract</li>"
            "<li><code>technical/reports/</code>, <code>checkpoint/</code>, <code>logs/</code></li>"
            "</ul>"
            "<p>Enables <b>Keep duplicates for review</b>, <b>Review duplicates</b>, "
            "<b>Add run info to finished folder</b> "
            "(copies a small <code>SMK-run-info/</code> next to your memories), "
            "<b>Open debug folder</b>, and storage size labels.</p>",
        ),
        _callout(
            "warn",
            "Disk space",
            "<p>Plan <b>ZIP size + ~5 GB</b> free for filters-only "
            "(finished library is usually near the ZIP size; Windows needs headroom). "
            "With <b>Also save without filters</b>, plan about <b>2× ZIP + ~5 GB</b>.</p>"
            "<p>During a run, <code>staging/</code> is a temporary unpack about the ZIP size; "
            "SMK removes it after a successful finish when safe.</p>"
            "<p>If space runs out mid-run: free space, same account name, same export, "
            "Start again — see <a href=\"#start\">Stopped mid-run</a> above.</p>",
        ),
        _callout(
            "tip",
            "ZIP folder looks twice as big as Snapchat’s cloud size?",
            "<p>Folder Properties counts <b>everything</b> inside — including an "
            "<code>extracted</code> unpack next to the ZIPs. Only the "
            "<code>mydata~….zip</code> parts matter for SMK; their total should be "
            "close to Snapchat’s Memories size. You can delete a leftover "
            "<code>extracted</code> folder; SMK reads the ZIPs.</p>",
        ),
        "</section>",
        f'<section id="after" style="{_SECTION}">',
        headed_title('5. After processing', level=3, accent=accent),
        _pipeline_ladder(
            [
                ("Read the summary popup", "Check failed count and file totals."),
                (
                    "Open finished folder",
                    "Opens your library folder (<code>Desktop/&lt;name&gt;-memories/</code>, "
                    "or the same under your Technical-view base folder).",
                ),
                (
                    "Spot-check a few files",
                    "Filters, dates, and GPS look correct in Properties or File Checker.",
                ),
                (
                    "Review duplicates (Technical view, optional)",
                    "With <b>Keep duplicates for review</b> on, or to re-check later: "
                    "tick the copies to keep in each group (or Keep both); the ones you "
                    "do not keep are permanently deleted. A JSON record is saved in "
                    "<code>technical/reports/</code>.",
                ),
                (
                    "Add run info (Technical view, optional)",
                    "Copies a small <code>SMK-run-info/</code> folder next to your memories "
                    "(JSON, reports, logs — not the large staging extract).",
                ),
            ]
        ),
        _callout(
            "ok",
            "Resume after cancel or crash",
            "<p>Same project name + same ZIPs → finished files are skipped automatically.</p>"
            "<p>Deleted <code>merged/</code> but kept ZIPs → re-run re-merges. "
            "Deleted staging → re-extracts from ZIPs (slower).</p>",
        ),
        _callout(
            "tip",
            "File Checker tab",
            "<b>Check folder</b> then <b>Load GPS map</b> to confirm location metadata. "
            "Empty map with GPS count &gt; 0 in the metadata panel usually means zoom or filter - "
            "no GPS on a file is normal for indoor snaps.",
        ),
        "</section>",
        f'<section id="fix" style="{_SECTION} border-bottom:none;">',
        headed_title('6. Troubleshooting', level=3, accent=accent),
        _callout(
            "info",
            "Incomplete library / low file count",
            "<p>Almost always <b>missing ZIP parts</b>. You need every <code>mydata~…-N.zip</code> in one folder.</p>",
        ),
        _callout(
            "info",
            "Banner says export not supported",
            "<p>Your ZIP has no bundled media. Request a new Snapchat export with "
            "<b>Export your Memories</b> and <b>Export JSON files</b> enabled (see Guide tab).</p>",
        ),
        _callout(
            "warn",
            "Specific snaps missing",
            "<p>(1) Was it in My Eyes Only? (2) All ZIP parts? (3) Saved to Memories before export? "
            "(4) Search <code>memories_history.json</code> for the date.</p>",
        ),
        _callout(
            "warn",
            "Video overlays missing or black",
            "<p>Video merge needs bundled <b>ffmpeg</b>. Check <code>technical/quarantine/</code> for failed items.</p>",
        ),
        _callout(
            "warn",
            "Out of disk space",
            "<p>Free space on the drive holding your project "
            "(aim for ZIP + ~5 GB, or 2× ZIP + ~5 GB if saving without filters), "
            "then resume with the same name. "
            "After a clean finish, staging is removed automatically when safe.</p>",
        ),
        "</section>",
        "</div>",
    ]
    return "".join(parts)
