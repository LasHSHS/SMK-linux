"""Tests for export format detection (offline bundled vs unsupported)."""
import json
import tempfile
import zipfile
from pathlib import Path

from smd.export_detect import ExportFormat, analyze_zip_export


def _write_bundled_zip(path: Path, *, with_links: bool = False, multi_year: bool = False) -> None:
    rows = [
        {
            "Date": "2026-04-17 09:14:49 UTC",
            "Media Type": "Image",
            "Location": "",
        }
    ]
    if multi_year:
        rows.insert(
            0,
            {
                "Date": "2016-07-12 12:00:00 UTC",
                "Media Type": "Image",
                "Location": "",
            },
        )
    if with_links:
        rows[-1]["Download Link"] = (
            "https://app.snapchat.com/dmd/memories?uid=x&mid=0aaa0107-7afa-01c7-c3fc-0e31fc14ad8b"
        )
    payload = {"Saved Media": rows}
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("memories_history.json", json.dumps(payload))
        zf.writestr(
            "memories/2026-04-17_0aaa0107-7afa-01c7-c3fc-0e31fc14ad8b-main.jpg",
            b"\xff\xd8\xff" + b"\x00" * 1024,
        )


def _write_links_only_zip(path: Path) -> None:
    payload = {
        "Saved Media": [
            {
                "Date": "2026-04-17 09:14:49 UTC",
                "Media Type": "Image",
                "Download Link": "https://example.test/memories?mid=abc",
            }
        ]
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("memories_history.json", json.dumps(payload))


def test_bundled_export_detected_even_with_links_in_json():
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "mydata~123.zip"
        _write_bundled_zip(zpath, with_links=True)
        analysis = analyze_zip_export(zpath)
        assert analysis.format == ExportFormat.BUNDLED_LOCAL
        assert analysis.is_bundled
        assert analysis.is_supported
        assert "offline" in analysis.message.lower()
        assert analysis.year_min == 2026
        assert analysis.year_max == 2026
        assert analysis.zip_bytes > 0
        assert analysis.rows_with_link == 1


def test_bundled_export_reports_year_span_and_empty_urls():
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "mydata~789.zip"
        _write_bundled_zip(zpath, multi_year=True)
        analysis = analyze_zip_export(zpath)
        assert analysis.format == ExportFormat.BUNDLED_LOCAL
        assert analysis.json_rows == 2
        assert analysis.rows_with_link == 0
        assert analysis.year_min == 2016
        assert analysis.year_max == 2026
        assert "empty" in analysis.message.lower()


def test_links_only_export_is_unsupported():
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "mydata~456.zip"
        _write_links_only_zip(zpath)
        analysis = analyze_zip_export(zpath)
        assert analysis.format == ExportFormat.LINKS_ONLY
        assert not analysis.is_bundled
        assert not analysis.is_supported
        assert "link-only" in analysis.message.lower()
        assert "offline-only" in analysis.message.lower()


def test_empty_export():
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "empty.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("readme.txt", "hello")
        analysis = analyze_zip_export(zpath)
        assert analysis.format == ExportFormat.EMPTY
