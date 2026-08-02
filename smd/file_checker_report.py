"""Build the File Checker library-check summary (reassurance-focused)."""
from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path

from smd.media_types import format_bytes
from smd.resolution_notes import parse_resolution_key, resolution_note

# Matches SMK output stems: 2026-04-17_09-14-49 or with disambiguation suffix.
_DATE_STEM_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})")


def parse_filename_date_ymd(filename: str) -> str | None:
    """Return YYYY-MM-DD from an SMK-style media filename, or None."""
    stem = Path(filename).stem
    match = _DATE_STEM_RE.match(stem)
    if not match:
        return None
    try:
        year = int(match.group(1))
    except ValueError:
        return None
    if not (1990 <= year <= 2100):
        return None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def parse_filename_date_year(filename: str) -> int | None:
    """Return year from an SMK-style media filename, or None if not dated."""
    ymd = parse_filename_date_ymd(filename)
    if not ymd:
        return None
    return int(ymd[:4])


def top_gps_places(locations: list, *, limit: int = 5) -> list[tuple[str, int]]:
    """Busiest GPS clusters as (lat, lon label, file count), most first."""
    counts: Counter[tuple[float, float]] = Counter()
    for loc in locations:
        coords = loc.get("coords")
        if not coords or len(coords) < 2:
            continue
        try:
            key = (round(float(coords[0]), 4), round(float(coords[1]), 4))
        except (TypeError, ValueError):
            continue
        counts[key] += 1
    return [
        (f"{lat:.4f}, {lon:.4f}", count)
        for (lat, lon), count in counts.most_common(limit)
    ]


def format_year_histogram(years: dict[str, int] | Counter) -> str:
    """Format year → count as '2015: 12, 2016: 45' (sorted ascending)."""
    items: list[tuple[str, int]] = []
    for key, count in years.items():
        if count:
            items.append((str(key), int(count)))
    if not items:
        return ""
    items.sort(key=lambda kv: (kv[0] == "unknown", kv[0]))
    return ", ".join(f"{year}: {count:,}" for year, count in items)


def _esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def build_library_check_report(
    scan_report: dict,
    locations: list,
    folder_name: str,
    *,
    extension_mismatches_from_scan: int | None = None,
    as_html: bool = True,
) -> str:
    """One coherent reassurance summary for the metadata panel.

    Returns HTML suitable for QTextEdit.setHtml by default (font hierarchy,
    short rules). Pass as_html=False for plain text (tests / logging).
    """
    file_types = scan_report.get("file_types") or {}
    total_media = int(scan_report.get("total_media") or 0)
    total_images = int(scan_report.get("total_images") or 0)
    total_videos = int(scan_report.get("total_videos") or 0)
    total_size = sum(info.get("size", 0) for info in file_types.values())

    embedded = scan_report.get("gps_embedded") or {}
    json_gps = scan_report.get("gps_json") or {}
    missing = scan_report.get("gps_missing") or {}
    emb_photos = int(embedded.get("image", 0))
    emb_videos = int(embedded.get("video", 0))
    json_photos = int(json_gps.get("image", 0))
    json_videos = int(json_gps.get("video", 0))
    miss_photos = int(missing.get("image", 0))
    miss_videos = int(missing.get("video", 0))
    with_gps = emb_photos + emb_videos + json_photos + json_videos
    without_gps = miss_photos + miss_videos

    with_date = int(scan_report.get("with_date") or 0)
    without_date = int(scan_report.get("without_date") or 0)
    if with_date + without_date == 0 and total_media:
        without_date = 0

    mismatches = scan_report.get("extension_mismatches", 0)
    if extension_mismatches_from_scan is not None:
        mismatches = max(int(mismatches), int(extension_mismatches_from_scan))

    try:
        unique_locs = len(
            {
                (round(loc["coords"][0], 4), round(loc["coords"][1], 4))
                for loc in locations
                if loc.get("coords")
            }
        )
    except Exception:
        unique_locs = 0

    folder = folder_name or "folder"
    size_label = format_bytes(total_size)
    year_hist = scan_report.get("no_gps_years") or {}
    year_line = format_year_histogram(year_hist)
    date_earliest = scan_report.get("date_earliest")
    date_latest = scan_report.get("date_latest")
    date_range = None
    if date_earliest and date_latest:
        if date_earliest == date_latest:
            date_range = str(date_earliest)
        else:
            date_range = f"{date_earliest} → {date_latest}"
    places = top_gps_places(locations, limit=5)

    emb_parts = []
    if emb_photos:
        emb_parts.append(f"{emb_photos:,} photos")
    if emb_videos:
        emb_parts.append(f"{emb_videos:,} videos")
    json_parts = []
    if json_photos:
        json_parts.append(f"{json_photos:,} photos")
    if json_videos:
        json_parts.append(f"{json_videos:,} videos")

    common = dict(
        folder=folder,
        total_media=total_media,
        total_images=total_images,
        total_videos=total_videos,
        size_label=size_label,
        with_date=with_date,
        without_date=without_date,
        with_gps=with_gps,
        without_gps=without_gps,
        unique_locs=unique_locs,
        emb_parts=emb_parts,
        json_parts=json_parts,
        mismatches=mismatches,
        miss_photos=miss_photos,
        miss_videos=miss_videos,
        year_line=year_line,
        date_range=date_range,
        top_places=places,
        file_types=file_types,
        resolution_counts=scan_report.get("resolution_counts") or {},
    )
    if not as_html:
        return _build_plain(**common)
    return _build_html(**common)


def _build_plain(
    *,
    folder: str,
    total_media: int,
    total_images: int,
    total_videos: int,
    size_label: str,
    with_date: int,
    without_date: int,
    with_gps: int,
    without_gps: int,
    unique_locs: int,
    emb_parts: list[str],
    json_parts: list[str],
    mismatches: int,
    miss_photos: int,
    miss_videos: int,
    year_line: str,
    date_range: str | None,
    top_places: list[tuple[str, int]],
    file_types: dict,
    resolution_counts: dict,
) -> str:
    lines: list[str] = [
        "",
        "——",
        f"📋 LIBRARY CHECK — {folder}/",
        "——",
        (
            f"🎞️ {total_media:,} memories "
            f"({total_images:,} photos, {total_videos:,} videos) · {size_label}"
        ),
        "",
        "✨ READY FOR UPLOAD",
        f"- 📅 Dates on filenames: {with_date:,} / {total_media:,}",
    ]
    if date_range:
        lines.append(f"- 🗓️ Date range: {date_range}")
    lines.append(
        f"- 📍 Location available: {with_gps:,} / {total_media:,}"
        + (f" ({unique_locs:,} unique places on the map)" if unique_locs else "")
    )
    if emb_parts:
        lines.append(f"  · Already inside the file: {', '.join(emb_parts)}")
    if json_parts:
        lines.append(
            f"  · From Snapchat export JSON (shown on map): {', '.join(json_parts)}"
        )
    if mismatches:
        lines.append(
            f"- ⚠️ Extensions: {mismatches:,} mismatched "
            '(re-run "Save memories" processing to fix these)'
        )
    else:
        lines.append("- ✅ Extensions: all look correct")

    lines.extend(["", "💡 WORTH KNOWING"])
    if without_gps:
        lines.append(
            f"- {without_gps:,} without location "
            f"({miss_photos:,} photos, {miss_videos:,} videos)"
        )
        if year_line:
            lines.append(f"  By year: {year_line}")
        lines.append(
            "  Likely: no GPS in the original Snapchat export "
            "(common on older memories, or Location Services was off)"
        )
    else:
        lines.append("- ✅ Every file has a location (on the map or from export JSON)")

    if without_date:
        lines.append(f"- {without_date:,} file(s) missing a date in the filename")
    else:
        lines.append("- ✅ 0 files missing a date in the filename")

    if top_places:
        lines.extend(["", "📌 TOP PLACES (busiest on the map)"])
        for i, (coord, count) in enumerate(top_places, start=1):
            lines.append(f"  {i}. {coord} · {count:,} file(s)")

    if file_types:
        lines.extend(["", "📂 FILE TYPES"])
        for ext, info in sorted(
            file_types.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            lines.append(
                f"  {ext:10} · {info['count']:6,} · {format_bytes(info['size'])}"
            )

    if resolution_counts:
        ranked = sorted(resolution_counts.items(), key=lambda kv: kv[1], reverse=True)
        lines.extend(["", f"📐 PHOTO SIZES (all · {len(ranked)} unique)"])
        for res_key, count in ranked:
            note = ""
            parsed = parse_resolution_key(res_key)
            if parsed:
                label = resolution_note(*parsed)
                if label:
                    note = f"  ({label})"
            lines.append(f"  {res_key} · {count:,}{note}")

    lines.append("——")
    lines.append("")
    return "\n".join(lines)


def _build_html(
    *,
    folder: str,
    total_media: int,
    total_images: int,
    total_videos: int,
    size_label: str,
    with_date: int,
    without_date: int,
    with_gps: int,
    without_gps: int,
    unique_locs: int,
    emb_parts: list[str],
    json_parts: list[str],
    mismatches: int,
    miss_photos: int,
    miss_videos: int,
    year_line: str,
    date_range: str | None,
    top_places: list[tuple[str, int]],
    file_types: dict,
    resolution_counts: dict,
) -> str:
    """Rich HTML for QTextEdit — bold section titles, short rules, light emoji."""
    rule = (
        '<div style="margin:8px 0 4px 0; border-top:1px solid #888; '
        'width:28px; height:0;"></div>'
    )
    h1 = (
        f'<div style="font-size:17px; font-weight:800; margin:4px 0 2px 0;">'
        f"📋 LIBRARY CHECK — {_esc(folder)}/</div>"
    )
    hero = (
        f'<div style="font-size:14px; font-weight:700; margin:0 0 8px 0;">'
        f"🎞️ {_esc(f'{total_media:,}')} memories "
        f"({_esc(f'{total_images:,}')} photos, {_esc(f'{total_videos:,}')} videos)"
        f" · {_esc(size_label)}</div>"
    )

    ready_items = [
        f"📅 Dates on filenames: <b>{with_date:,}</b> / {total_media:,}",
    ]
    if date_range:
        ready_items.append(f"🗓️ Date range: <b>{_esc(date_range)}</b>")
    ready_items.append(
        f"📍 Location available: <b>{with_gps:,}</b> / {total_media:,}"
        + (
            f" ({unique_locs:,} unique places on the map)"
            if unique_locs
            else ""
        )
    )
    if emb_parts:
        ready_items.append(
            f"&nbsp;&nbsp;· Already inside the file: {_esc(', '.join(emb_parts))}"
        )
    if json_parts:
        ready_items.append(
            "&nbsp;&nbsp;· From Snapchat export JSON (shown on map): "
            f"{_esc(', '.join(json_parts))}"
        )
    if mismatches:
        ready_items.append(
            f"⚠️ Extensions: <b>{mismatches:,}</b> mismatched "
            '(re-run "Save memories" to fix)'
        )
    else:
        ready_items.append("✅ Extensions: all look correct")

    worth: list[str] = []
    if without_gps:
        worth.append(
            f"<b>{without_gps:,}</b> without location "
            f"({miss_photos:,} photos, {miss_videos:,} videos)"
        )
        if year_line:
            worth.append(f"&nbsp;&nbsp;By year: {_esc(year_line)}")
        worth.append(
            "&nbsp;&nbsp;<i>Likely: no GPS in the original Snapchat export "
            "(common on older memories, or Location Services was off)</i>"
        )
    else:
        worth.append("✅ Every file has a location (on the map or from export JSON)")

    if without_date:
        worth.append(
            f"<b>{without_date:,}</b> file(s) missing a date in the filename"
        )
    else:
        worth.append("✅ 0 files missing a date in the filename")

    parts = [
        '<div style="font-family: Segoe UI, sans-serif; line-height:1.45;">',
        rule,
        h1,
        rule,
        hero,
        _section("✨ READY FOR UPLOAD", ready_items),
        _section("💡 WORTH KNOWING", worth),
    ]

    if top_places:
        place_lines = [
            f"{i}. {_esc(coord)} · <b>{count:,}</b> file(s)"
            for i, (coord, count) in enumerate(top_places, start=1)
        ]
        parts.append(_section("📌 TOP PLACES (busiest on the map)", place_lines))

    if file_types:
        type_lines = []
        for ext, info in sorted(
            file_types.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            type_lines.append(
                f"{_esc(ext)} · <b>{info['count']:,}</b> · "
                f"{_esc(format_bytes(info['size']))}"
            )
        parts.append(_section("📂 FILE TYPES", type_lines))

    if resolution_counts:
        ranked = sorted(resolution_counts.items(), key=lambda kv: kv[1], reverse=True)
        size_lines = []
        for res_key, count in ranked:
            note = ""
            parsed = parse_resolution_key(res_key)
            if parsed:
                label = resolution_note(*parsed)
                if label:
                    note = f' <span style="opacity:0.75;">({_esc(label)})</span>'
            size_lines.append(f"{_esc(res_key)} · <b>{count:,}</b>{note}")
        parts.append(
            _section(f"📐 PHOTO SIZES ({len(ranked)} unique)", size_lines)
        )

    parts.append(rule)
    parts.append("</div>")
    return "".join(parts)


def _section(title: str, items: list[str]) -> str:
    body = "".join(
        f'<div style="font-size:12px; margin:2px 0 2px 2px;">{item}</div>'
        for item in items
    )
    return (
        f'<div style="font-size:13px; font-weight:800; margin:12px 0 4px 0;">'
        f"{title}</div>"
        f"{body}"
    )
