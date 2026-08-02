"""Overlay merge: scale full-frame overlays to main media size."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from smd.ffmpeg_bundle import ffmpeg_available, resolve_ffmpeg, resolve_ffprobe
from smd.overlays import _VIDEO_OVERLAY_FILTER, merge_image_overlay, merge_video_overlay


def test_video_overlay_filter_scales_overlay_to_main():
    assert "scale2ref" in _VIDEO_OVERLAY_FILTER
    assert _VIDEO_OVERLAY_FILTER.startswith("[1:v][0:v]")


def test_merge_image_overlay_scales_larger_overlay_to_main(tmp_path: Path):
    main = tmp_path / "main.jpg"
    overlay = tmp_path / "overlay.png"
    out = tmp_path / "merged.jpg"

    Image.new("RGB", (100, 200), (10, 20, 30)).save(main, quality=95)
    # Larger full-frame overlay: opaque red band across the middle third.
    ov = Image.new("RGBA", (300, 600), (0, 0, 0, 0))
    for y in range(200, 400):
        for x in range(300):
            ov.putpixel((x, y), (255, 0, 0, 180))
    ov.save(overlay)

    assert merge_image_overlay(main, overlay, out)
    merged = Image.open(out)
    assert merged.size == (100, 200)
    # After scale-to-main, the band should land around y 67-133 of the 200px frame.
    mid = merged.getpixel((50, 100))
    top = merged.getpixel((50, 10))
    assert mid[0] > 100  # red influence from overlay
    assert top[0] < 80  # mostly original dark blue-grey


@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not available")
def test_merge_video_overlay_scales_to_video_dimensions(tmp_path: Path):
    ffmpeg = resolve_ffmpeg()
    assert ffmpeg
    main = tmp_path / "main.mp4"
    overlay = tmp_path / "overlay.png"
    out = tmp_path / "merged.mp4"

    # 320x240 solid video, ~0.5s
    subprocess.run(
        [
            str(ffmpeg),
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(main),
        ],
        check=True,
        capture_output=True,
    )
    # Overlay ~1.5x larger (common Snapchat mismatch pattern)
    Image.new("RGBA", (480, 360), (255, 0, 0, 128)).save(overlay)

    assert merge_video_overlay(main, overlay, out)
    assert out.exists() and out.stat().st_size > 500

    ffprobe = resolve_ffprobe()
    assert ffprobe
    r = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=width,height,nb_read_frames",
            "-of",
            "json",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stream = json.loads(r.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (320, 240)
    # Must keep real motion - a non-looped PNG + shortest=1 used to emit 1 frame.
    assert int(stream["nb_read_frames"]) >= 10
