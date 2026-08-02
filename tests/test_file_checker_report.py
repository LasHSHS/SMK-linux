from smd.file_checker_report import (
    build_library_check_report,
    format_year_histogram,
    parse_filename_date_year,
    parse_filename_date_ymd,
    top_gps_places,
)
from smd.resolution_notes import parse_resolution_key, resolution_note


def test_parse_filename_date_year():
    assert parse_filename_date_year("2026-04-17_09-14-49.jpg") == 2026
    assert parse_filename_date_year("2016-01-02_12-00-00_abc123.mp4") == 2016
    assert parse_filename_date_year("random.jpg") is None


def test_parse_filename_date_ymd():
    assert parse_filename_date_ymd("2026-04-17_09-14-49.jpg") == "2026-04-17"
    assert parse_filename_date_ymd("random.jpg") is None


def test_top_gps_places():
    locs = [
        {"coords": (56.1553, 10.1870)},
        {"coords": (56.1553, 10.1870)},
        {"coords": (55.6761, 12.5683)},
    ]
    top = top_gps_places(locs, limit=2)
    assert top[0][1] == 2
    assert "56.1553" in top[0][0]


def test_format_year_histogram():
    assert format_year_histogram({"2016": 45, "2015": 12}) == "2015: 12, 2016: 45"
    assert "unknown: 3" in format_year_histogram({"unknown": 3, "2017": 1})


def test_resolution_note_snapchat_export():
    assert resolution_note(1008, 1792) == "common Snapchat export size"
    assert resolution_note(1792, 1008) == "common Snapchat export size"


def test_resolution_note_no_phone_brands():
    note = resolution_note(1170, 2532)
    assert note is None or "iPhone" not in note
    assert note is None or "Samsung" not in note


def test_parse_resolution_key():
    assert parse_resolution_key("1008x1792") == (1008, 1792)


def test_build_library_check_report_shape():
    report = {
        "total_media": 3,
        "total_images": 2,
        "total_videos": 1,
        "file_types": {
            ".jpg": {"count": 2, "size": 1024},
            ".mp4": {"count": 1, "size": 2048},
        },
        "extension_mismatches": 0,
        "resolution_counts": {"1008x1792": 2},
        "gps_embedded": {"image": 0, "video": 1},
        "gps_json": {"image": 1, "video": 0},
        "gps_missing": {"image": 1, "video": 0},
        "with_date": 3,
        "without_date": 0,
        "no_gps_years": {"2016": 1},
        "date_earliest": "2016-05-01",
        "date_latest": "2026-04-17",
    }
    locations = [
        {"coords": (56.1553, 10.1870), "type": "video"},
        {"coords": (56.1553, 10.1870), "type": "image"},
        {"coords": (55.6761, 12.5683), "type": "image"},
    ]
    text = build_library_check_report(report, locations, "merged", as_html=False)
    assert "LIBRARY CHECK — merged/" in text
    assert "READY FOR UPLOAD" in text
    assert "Date range: 2016-05-01 → 2026-04-17" in text
    assert "TOP PLACES" in text
    assert "WORTH KNOWING" in text
    assert "PHOTO SIZES" in text
    assert "1008x1792 · 2" in text
    assert "common Snapchat export size" in text
    assert "By year: 2016: 1" in text
    assert "Extensions: all look correct" in text
    assert "iPhone" not in text

    html_out = build_library_check_report(report, locations, "merged", as_html=True)
    assert "LIBRARY CHECK" in html_out
    assert "font-weight:800" in html_out
    assert "READY FOR UPLOAD" in html_out
    assert "Date range" in html_out
    assert "TOP PLACES" in html_out
    assert "common Snapchat export size" in html_out
    assert "iPhone" not in html_out
