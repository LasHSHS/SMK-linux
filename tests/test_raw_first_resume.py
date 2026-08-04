"""Raw-first processing + no re-encode when only raw copies are missing."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image

from smd.local_pipeline import (
    BundledMediaItem,
    _missing_outputs_message,
    _process_single_item,
)
from smd.models import Memory


def _jpeg(path: Path, color: str = "red") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # >512 bytes so _output_file_valid accepts the file.
    Image.new("RGB", (64, 64), color=color).save(path, format="JPEG", quality=90)


def _memory() -> Memory:
    return Memory(
        Date="2026-04-17 09:14:49 UTC",
        **{"Media Type": "Image", "Download Link": ""},
    )


def _dirs(tmp_path: Path) -> dict[str, Path]:
    out = {
        "merged": tmp_path / "merged",
        "raw": tmp_path / "raw",
        "quarantine": tmp_path / "quarantine",
        "staging": tmp_path / "staging",
    }
    for d in out.values():
        d.mkdir(parents=True, exist_ok=True)
    return out


def _item(tmp_path: Path, *, overlay: bool = False) -> BundledMediaItem:
    main = tmp_path / "staging" / "2026-04-17_abc-main.jpg"
    _jpeg(main, "blue")
    overlay_path = None
    if overlay:
        overlay_path = tmp_path / "staging" / "2026-04-17_abc-overlay.png"
        Image.new("RGBA", (64, 64), (0, 255, 0, 180)).save(overlay_path, format="PNG")
    return BundledMediaItem(
        stem="2026-04-17_abc",
        date_prefix="2026-04-17",
        uid="abc",
        main_path=main,
        overlay_path=overlay_path,
        main_ext=".jpg",
    )


def test_merged_exists_raw_missing_does_not_re_overlay(tmp_path: Path):
    """Las case: flip raw on later — copy raw only, leave merged untouched."""
    dirs = _dirs(tmp_path)
    item = _item(tmp_path, overlay=True)
    memory = _memory()
    planned = f"{memory.filename}.jpg"
    merged_out = dirs["merged"] / planned
    # Distinct "already baked" merged bytes (not equal to staging main).
    _jpeg(merged_out, "yellow")
    before = merged_out.read_bytes()

    with patch("smd.local_pipeline.merge_image_overlay") as mock_merge:
        mock_merge.side_effect = AssertionError("must not re-encode overlay")
        out = _process_single_item(
            item.stem,
            item,
            memory,
            merged_dir=dirs["merged"],
            raw_dir=dirs["raw"],
            quarantine_dir=dirs["quarantine"],
            staging_dir=dirs["staging"],
            merge_overlays=True,
            keep_raw=True,
            repair_videos=False,
            apply_meta=False,
            ffmpeg_sem=None,
            planned_output_name=planned,
        )

    assert out.done
    assert out.failed == 0
    assert out.raw_copied == 1
    assert mock_merge.call_count == 0
    assert merged_out.read_bytes() == before
    raw_out = dirs["raw"] / planned
    assert raw_out.is_file()
    assert raw_out.read_bytes() == item.main_path.read_bytes()


def test_raw_phase_then_merged_phase_for_overlay(tmp_path: Path):
    dirs = _dirs(tmp_path)
    item = _item(tmp_path, overlay=True)
    memory = _memory()
    planned = f"{memory.filename}.jpg"

    raw_out = _process_single_item(
        item.stem,
        item,
        memory,
        merged_dir=dirs["merged"],
        raw_dir=dirs["raw"],
        quarantine_dir=dirs["quarantine"],
        staging_dir=dirs["staging"],
        merge_overlays=True,
        keep_raw=True,
        repair_videos=False,
        apply_meta=False,
        ffmpeg_sem=None,
        planned_output_name=planned,
        only="raw",
    )
    assert not raw_out.done
    assert raw_out.raw_copied == 1
    assert (dirs["raw"] / planned).is_file()
    assert not (dirs["merged"] / planned).exists()

    merged = _process_single_item(
        item.stem,
        item,
        memory,
        merged_dir=dirs["merged"],
        raw_dir=dirs["raw"],
        quarantine_dir=dirs["quarantine"],
        staging_dir=dirs["staging"],
        merge_overlays=True,
        keep_raw=True,
        repair_videos=False,
        apply_meta=False,
        ffmpeg_sem=None,
        planned_output_name=planned,
        only="merged",
    )
    assert merged.done
    assert merged.merged == 1
    assert (dirs["merged"] / planned).is_file()
    assert (dirs["raw"] / planned).read_bytes() != (dirs["merged"] / planned).read_bytes()


def test_missing_outputs_message_raw_only():
    merged = Path("does-not-matter")
    msg = _missing_outputs_message(
        ["a", "b"],
        output_by_stem={"a": "a.jpg", "b": "b.jpg"},
        output_names={},
        merged_dir=merged,
        keep_raw=True,
    )
    # Without real files on disk, both count as full repairs.
    assert "Repairing 2 items" in msg


def test_missing_outputs_message_when_merged_present(tmp_path: Path):
    merged = tmp_path / "merged"
    merged.mkdir()
    _jpeg(merged / "a.jpg", "red")
    _jpeg(merged / "b.jpg", "green")
    msg = _missing_outputs_message(
        ["s1", "s2"],
        output_by_stem={"s1": "a.jpg", "s2": "b.jpg"},
        output_names={},
        merged_dir=merged,
        keep_raw=True,
    )
    assert "Adding 2 raw copies" in msg
    assert "not re-encoding" in msg
