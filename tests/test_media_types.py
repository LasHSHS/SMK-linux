from pathlib import Path

from smd.media_types import extension_matches_magic, format_bytes, resolve_check_folder


def test_extension_matches_magic_jpg():
    assert extension_matches_magic(".jpg", "jpg") is True
    assert extension_matches_magic(".jpeg", "jpg") is True
    assert extension_matches_magic(".mp4", "jpg") is False


def test_extension_matches_magic_mp4():
    assert extension_matches_magic(".mp4", "mp4") is True
    assert extension_matches_magic(".m4v", "mp4") is True


def test_format_bytes():
    assert format_bytes(512) == "512.0 B"
    assert format_bytes(2048) == "2.0 KB"


def test_resolve_check_folder_prefers_merged(tmp_path: Path):
    parent = tmp_path / "downloads"
    merged = parent / "merged"
    raw = parent / "raw"
    merged.mkdir(parents=True)
    raw.mkdir(parents=True)
    (merged / "2020-01-01_00-00-00.jpg").write_bytes(b"x")
    (raw / "2020-01-01_00-00-00.jpg").write_bytes(b"x")

    scan, note = resolve_check_folder(parent)
    assert scan == merged.resolve()
    assert note is not None
    assert "merged/" in note


def test_resolve_check_folder_keeps_merged_as_is(tmp_path: Path):
    merged = tmp_path / "merged"
    merged.mkdir()
    (merged / "a.jpg").write_bytes(b"x")
    scan, note = resolve_check_folder(merged)
    assert scan == merged.resolve()
    assert note is None


def test_resolve_check_folder_falls_back_to_raw(tmp_path: Path):
    parent = tmp_path / "downloads"
    raw = parent / "raw"
    raw.mkdir(parents=True)
    (parent / "merged").mkdir()
    (raw / "a.mp4").write_bytes(b"x")

    scan, note = resolve_check_folder(parent)
    assert scan == raw.resolve()
    assert note is not None
    assert "raw/" in note
