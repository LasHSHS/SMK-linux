"""Regression tests for the post-run session summary HTML.

summary_html() is the last step before the completion popup; if it raises,
the user sees no summary at all. A stray bare-name reference once silently
broke this, so exercise every conditional branch here.
"""
from smd.session_report import SessionReport


def _report(**overrides) -> SessionReport:
    base = dict(
        generated_at="2026-04-17T09:14:49+00:00",
        account_name="Mary",
        success=True,
        steps_completed=["Detected export", "Merged overlays"],
        merged_count=10,
        raw_count=10,
        overlays_merged=4,
        metadata_applied=10,
        staging_files=10,
        staging_bytes=1024,
        merged_bytes=2048,
        safe_to_delete_staging=True,
    )
    base.update(overrides)
    return SessionReport(**base)


def test_summary_html_renders_when_staging_cleaned():
    html = _report(staging_deleted=True, staging_freed="1.0 MB").summary_html()
    assert "Processing summary" in html
    assert "1.0 MB freed" in html


def test_summary_html_renders_when_staging_kept():
    html = _report(staging_deleted=False, staging_freed="").summary_html()
    assert "Staging check passed" in html


def test_summary_html_with_duplicates_and_notes():
    html = _report(
        duplicate_groups=3,
        webp_outputs=2,
        corrupt_images_found=1,
        corrupt_image_names=["bad.jpg"],
        notes=["1 item(s) failed."],
        safe_to_delete_staging=False,
    ).summary_html()
    assert "Identical-file duplicate groups" in html
    assert "auto-removed" in html
    assert "run again with the same name" in html
    assert "Notes" in html


def test_summary_html_failure_state():
    html = _report(success=False, failed=2).summary_html()
    assert "Finished with issues" in html


def test_summary_html_with_visual_duplicates():
    html = _report(visual_duplicate_groups=5).summary_html()
    assert "Same-content groups (different bytes)" in html
    assert "oldest filename kept" in html


def test_summary_html_memory_counts_section():
    html = _report(
        json_row_count=915,
        media_found_in_zip=696,
        staging_byte_dupes_removed=15,
        staging_visual_dupes_removed=0,
        json_matched=681,
        library_kept=681,
        this_run_processed=0,
        skipped_already_complete=True,
        merged_count=681,
    ).summary_html()
    assert "How many memories" in html
    assert "915" in html
    assert "Duplicates removed before saving" in html
    assert "15" in html
    assert "Your library now" in html
    assert "This run processed" in html
    assert "already complete" in html
    assert "not always the same number as the JSON" in html
