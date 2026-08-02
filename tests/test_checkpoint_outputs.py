"""Checkpoint records the output filename written for each done stem."""
from __future__ import annotations

from pathlib import Path

from smd.local_pipeline import (
    BundledMediaItem,
    _load_checkpoint,
    _save_checkpoint,
    reconcile_checkpoint_with_disk,
)


def test_checkpoint_roundtrip_output_by_stem(tmp_path: Path):
    ck = tmp_path / "local_checkpoint.json"
    _save_checkpoint(
        ck,
        {"2022-08-28_abc"},
        set(),
        {"2022-08-28_abc": "2022-08-28_17-13-22.mp4"},
    )
    done, skipped, _ver, outputs = _load_checkpoint(ck)
    assert done == {"2022-08-28_abc"}
    assert skipped == set()
    assert outputs == {"2022-08-28_abc": "2022-08-28_17-13-22.mp4"}


def test_reconcile_keeps_recorded_name_and_migrates(tmp_path: Path):
    merged = tmp_path / "merged"
    raw = tmp_path / "raw"
    merged.mkdir()
    raw.mkdir()
    old = "2022-08-28_17-13-22.mp4"
    new = "2022-08-28_a1ddf9b9.mp4"
    # Minimal ftyp header so _output_file_valid accepts it as mp4.
    payload = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 600
    (merged / old).write_bytes(payload)
    (raw / old).write_bytes(payload)

    stem = "2022-08-28_a1ddf9b9-a539-a652-fc96-830be4066520"
    staging_main = tmp_path / f"{stem}-main.mp4"
    staging_main.write_bytes(b"staging")
    items = {
        stem: BundledMediaItem(
            stem=stem,
            date_prefix="2022-08-28",
            uid="a1ddf9b9-a539-a652-fc96-830be4066520",
            main_path=staging_main,
            main_ext=".mp4",
        )
    }
    output_by_stem = {stem: old}
    done, skipped, missing = reconcile_checkpoint_with_disk(
        {stem},
        set(),
        items,
        {stem: new},
        merged,
        raw,
        keep_raw=True,
        output_by_stem=output_by_stem,
    )
    assert missing == []
    assert stem in done
    assert (merged / new).is_file()
    assert not (merged / old).exists()
    assert output_by_stem[stem] == new
