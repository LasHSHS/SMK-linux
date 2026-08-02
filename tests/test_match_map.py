"""Tests for UID-based JSON matching in the bundled pipeline."""
from datetime import datetime, timezone

from smd.local_pipeline import (
    BundledMediaItem,
    _restore_zip_entry_mtime,
    build_deterministic_match_map,
    build_match_map,
)
from smd.models import Memory


def _memory(date_utc: str, media_type: str, mid: str | None = None) -> Memory:
    link = ""
    if mid:
        link = f"https://app.snapchat.com/dmd/memories?uid=x&sid=y&mid={mid}&ts=1&sig=z"
    return Memory(
        Date=date_utc,
        **{"Media Type": media_type, "Download Link": link},
    )


def _item(date_prefix: str, uid: str, ext: str = ".jpg") -> BundledMediaItem:
    from pathlib import Path

    stem = f"{date_prefix}_{uid}"
    return BundledMediaItem(
        stem=stem,
        date_prefix=date_prefix,
        uid=uid,
        main_path=Path(f"{stem}-main{ext}"),
        main_ext=ext,
    )


def test_uid_match_beats_positional_order():
    # Two images same day; JSON rows listed in the "wrong" order relative to
    # filename sort - UID matching must still pair them correctly.
    uid_a = "0aaa0107-7afa-01c7-c3fc-0e31fc14ad8b"
    uid_b = "fed50595-692d-55e1-2391-58c7607af190"
    mem_a = _memory("2026-04-17 09:14:49 UTC", "Image", uid_a)
    mem_b = _memory("2026-04-17 08:00:00 UTC", "Image", uid_b)

    items = {
        f"2026-04-17_{uid_a}": _item("2026-04-17", uid_a),
        f"2026-04-17_{uid_b}": _item("2026-04-17", uid_b),
    }

    match_map = build_match_map(items, [mem_a, mem_b])
    assert match_map[f"2026-04-17_{uid_a}"] is mem_a
    assert match_map[f"2026-04-17_{uid_b}"] is mem_b

    # Positional fallback alone would swap them (sorted by time vs by stem).
    positional = build_deterministic_match_map(items, [mem_a, mem_b])
    assert positional[f"2026-04-17_{uid_a}"] is mem_b


def test_unmatched_uids_fall_back_to_positional():
    uid = "1111aaaa-bbbb-cccc-dddd-eeeeffff0000"
    mem = _memory("2026-04-17 09:14:49 UTC", "Image")  # no mid= link
    items = {f"2026-04-17_{uid}": _item("2026-04-17", uid)}

    match_map = build_match_map(items, [mem])
    assert match_map[f"2026-04-17_{uid}"] is mem


def test_memory_dates_parse_as_utc():
    mem = _memory("2026-04-17 09:14:49 UTC", "Image")
    assert mem.date == datetime(2026, 4, 17, 9, 14, 49, tzinfo=timezone.utc)


def test_video_positional_fallback_sorts_by_own_capture_time(monkeypatch):
    """Regression test for the 'Las' account mismatch: same-day videos with
    no Snapchat media id must be ordered by each file's own embedded
    creation_time, not by UID-stem string (which has no relation to actual
    capture order and silently swapped clips)."""
    from smd import local_pipeline

    uid_early = "zzzz0000-0000-0000-0000-000000000000"  # sorts LAST as a string
    uid_late = "aaaa0000-0000-0000-0000-000000000000"  # sorts FIRST as a string
    assert uid_late < uid_early  # confirms the string order is the trap

    mem_early = _memory("2026-04-17 14:00:00 UTC", "Video")
    mem_late = _memory("2026-04-17 15:00:00 UTC", "Video")

    item_early = _item("2026-04-17", uid_early, ext=".mp4")
    item_late = _item("2026-04-17", uid_late, ext=".mp4")
    items = {item_early.stem: item_early, item_late.stem: item_late}

    times_by_path = {
        item_early.main_path: datetime(2026, 4, 17, 13, 59, 40, tzinfo=timezone.utc),
        item_late.main_path: datetime(2026, 4, 17, 14, 59, 50, tzinfo=timezone.utc),
    }
    monkeypatch.setattr(
        local_pipeline, "read_video_capture_time", lambda path: times_by_path.get(path)
    )

    match_map = build_deterministic_match_map(items, [mem_early, mem_late])
    assert match_map[item_early.stem] is mem_early
    assert match_map[item_late.stem] is mem_late


def test_video_with_unreadable_capture_time_falls_back_after_timed_ones(monkeypatch):
    """A video ffprobe can't read shouldn't silently bump a correctly-timed
    neighbor out of place - it should sort after all timed videos."""
    from smd import local_pipeline

    uid_timed = "aaaa0000-0000-0000-0000-000000000000"
    uid_unreadable = "bbbb0000-0000-0000-0000-000000000000"

    mem_first = _memory("2026-04-17 14:00:00 UTC", "Video")
    mem_second = _memory("2026-04-17 15:00:00 UTC", "Video")

    item_timed = _item("2026-04-17", uid_timed, ext=".mp4")
    item_unreadable = _item("2026-04-17", uid_unreadable, ext=".mp4")
    items = {item_timed.stem: item_timed, item_unreadable.stem: item_unreadable}

    times_by_path = {item_timed.main_path: datetime(2026, 4, 17, 13, 59, 40, tzinfo=timezone.utc)}
    monkeypatch.setattr(
        local_pipeline, "read_video_capture_time", lambda path: times_by_path.get(path)
    )

    match_map = build_deterministic_match_map(items, [mem_first, mem_second])
    assert match_map[item_timed.stem] is mem_first
    assert match_map[item_unreadable.stem] is mem_second


def test_single_video_in_bucket_skips_capture_time_probe(monkeypatch):
    """No point paying an ffprobe call when there's nothing to disambiguate."""
    from smd import local_pipeline

    calls = []
    monkeypatch.setattr(
        local_pipeline,
        "read_video_capture_time",
        lambda path: calls.append(path) or None,
    )

    uid = "aaaa0000-0000-0000-0000-000000000000"
    mem = _memory("2026-04-17 14:00:00 UTC", "Video")
    item = _item("2026-04-17", uid, ext=".mp4")

    match_map = build_deterministic_match_map({item.stem: item}, [mem])
    assert match_map[item.stem] is mem
    assert calls == []


def test_photo_positional_fallback_sorts_by_export_mtime(tmp_path):
    """Same-day photos with no media id: ZIP entry mtimes track JSON Date
    order. UID-stem order would swap these two (late UID sorts first)."""
    import os
    from pathlib import Path

    uid_late_string = "aaaa0000-0000-0000-0000-000000000001"  # sorts FIRST
    uid_early_string = "zzzz0000-0000-0000-0000-000000000002"  # sorts LAST
    assert uid_late_string < uid_early_string

    mem_early = _memory("2024-07-07 14:21:56 UTC", "Image")
    mem_late = _memory("2024-07-07 17:20:48 UTC", "Image")

    early_path = tmp_path / f"2024-07-07_{uid_early_string}-main.jpg"
    late_path = tmp_path / f"2024-07-07_{uid_late_string}-main.jpg"
    early_path.write_bytes(b"early")
    late_path.write_bytes(b"late")
    os.utime(early_path, (1_720_358_516, 1_720_358_516))  # ~14:21:56 UTC-ish order
    os.utime(late_path, (1_720_369_248, 1_720_369_248))  # later

    item_early = BundledMediaItem(
        stem=f"2024-07-07_{uid_early_string}",
        date_prefix="2024-07-07",
        uid=uid_early_string,
        main_path=early_path,
        main_ext=".jpg",
    )
    item_late = BundledMediaItem(
        stem=f"2024-07-07_{uid_late_string}",
        date_prefix="2024-07-07",
        uid=uid_late_string,
        main_path=late_path,
        main_ext=".jpg",
    )
    items = {item_early.stem: item_early, item_late.stem: item_late}

    match_map = build_deterministic_match_map(items, [mem_early, mem_late])
    assert match_map[item_early.stem] is mem_early
    assert match_map[item_late.stem] is mem_late


def test_photo_identical_mtimes_fall_back_to_uid_order(tmp_path):
    """Stomped extracts (all mtimes equal) must not invent an order."""
    import os

    uid_a = "aaaa0000-0000-0000-0000-000000000001"
    uid_z = "zzzz0000-0000-0000-0000-000000000002"
    mem_early = _memory("2024-07-07 14:21:56 UTC", "Image")
    mem_late = _memory("2024-07-07 17:20:48 UTC", "Image")

    path_a = tmp_path / f"2024-07-07_{uid_a}-main.jpg"
    path_z = tmp_path / f"2024-07-07_{uid_z}-main.jpg"
    path_a.write_bytes(b"a")
    path_z.write_bytes(b"z")
    same = 1_720_000_000
    os.utime(path_a, (same, same))
    os.utime(path_z, (same, same))

    item_a = BundledMediaItem(
        stem=f"2024-07-07_{uid_a}",
        date_prefix="2024-07-07",
        uid=uid_a,
        main_path=path_a,
        main_ext=".jpg",
    )
    item_z = BundledMediaItem(
        stem=f"2024-07-07_{uid_z}",
        date_prefix="2024-07-07",
        uid=uid_z,
        main_path=path_z,
        main_ext=".jpg",
    )
    items = {item_a.stem: item_a, item_z.stem: item_z}

    # UID order: aaaa first → earliest JSON; zzzz → late JSON (wrong vs real
    # capture, but honest fallback when mtimes are useless).
    match_map = build_deterministic_match_map(items, [mem_early, mem_late])
    assert match_map[item_a.stem] is mem_early
    assert match_map[item_z.stem] is mem_late


def test_restore_zip_entry_mtime(tmp_path):
    import zipfile

    dest = tmp_path / "x.jpg"
    dest.write_bytes(b"x")
    info = zipfile.ZipInfo("memories/x.jpg")
    info.date_time = (2024, 7, 7, 14, 21, 56)
    _restore_zip_entry_mtime(dest, info)
    got = datetime.fromtimestamp(dest.stat().st_mtime)
    assert got.year == 2024 and got.month == 7 and got.day == 7
    assert got.hour == 14 and got.minute == 21 and got.second == 56
