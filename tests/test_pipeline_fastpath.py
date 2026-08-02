"""Already-complete resume fast path + cancel helpers."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from PIL import Image

from smd.duplicates import (
    STAGING_BYTE_DELETED_REPORT,
    load_staging_removed_stems,
)
from smd.local_pipeline import (
    CHECKPOINT_VERSION,
    checkpoint_outputs_present,
    library_already_complete,
    list_zip_main_stems,
)


def _valid_jpeg(path: Path) -> None:
    """Write a real JPEG large enough for ``_output_file_valid`` (>512 bytes)."""
    Image.new("RGB", (64, 64), "red").save(path, format="JPEG", quality=90)


def _write_mini_zip(path: Path, stems: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for stem in stems:
            date, uid = stem.split("_", 1)
            name = f"memories/{date}_{uid}-main.jpg"
            zf.writestr(name, b"fake-jpeg-bytes")


def test_list_zip_main_stems(tmp_path: Path):
    z = tmp_path / "mydata.zip"
    _write_mini_zip(
        z,
        [
            "2024-01-01_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "2024-01-02_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ],
    )
    stems = list_zip_main_stems([z])
    assert len(stems) == 2


def test_library_already_complete_accounts_for_staging_dedupe(tmp_path: Path):
    account = tmp_path / "Mary-memories"
    merged = account / "Memories"
    raw = account / "Memories" / "raw"
    reports = account / "technical" / "reports"
    merged.mkdir(parents=True)
    reports.mkdir(parents=True)

    keep_stem = "2024-01-01_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    drop_stem = "2024-01-01_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    keep_name = "2024-01-01_12-00-00.jpg"
    _valid_jpeg(merged / keep_name)

    (reports / STAGING_BYTE_DELETED_REPORT).write_text(
        json.dumps(
            {
                "stems_removed": [drop_stem],
                "groups_resolved": 1,
            }
        ),
        encoding="utf-8",
    )

    z = tmp_path / "export.zip"
    _write_mini_zip(z, [keep_stem, drop_stem])

    done = {keep_stem}
    outputs = {keep_stem: keep_name}
    complete, zip_stems = library_already_complete(
        [z],
        done_stems=done,
        skipped_stems=set(),
        output_by_stem=outputs,
        reports_dir=reports,
        merged_dir=merged,
        raw_dir=raw,
        keep_raw=False,
    )
    assert zip_stems == {keep_stem, drop_stem}
    assert complete is True
    assert load_staging_removed_stems(reports) == {drop_stem}


def test_library_not_complete_when_output_missing(tmp_path: Path):
    account = tmp_path / "Mary-memories"
    merged = account / "Memories"
    reports = account / "technical" / "reports"
    merged.mkdir(parents=True)
    reports.mkdir(parents=True)

    stem = "2024-01-01_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    z = tmp_path / "export.zip"
    _write_mini_zip(z, [stem])

    complete, _ = library_already_complete(
        [z],
        done_stems={stem},
        skipped_stems=set(),
        output_by_stem={stem: "2024-01-01_12-00-00.jpg"},
        reports_dir=reports,
        merged_dir=merged,
        raw_dir=merged / "raw",
        keep_raw=False,
    )
    assert complete is False


def test_checkpoint_outputs_present_requires_files(tmp_path: Path):
    merged = tmp_path / "merged"
    merged.mkdir()
    _valid_jpeg(merged / "a.jpg")
    assert checkpoint_outputs_present(
        {"s1"},
        {"s1": "a.jpg"},
        merged,
        tmp_path / "raw",
        keep_raw=False,
    )
    assert not checkpoint_outputs_present(
        {"s1", "s2"},
        {"s1": "a.jpg", "s2": "missing.jpg"},
        merged,
        tmp_path / "raw",
        keep_raw=False,
    )


def test_checkpoint_version_constant():
    assert CHECKPOINT_VERSION >= 1
