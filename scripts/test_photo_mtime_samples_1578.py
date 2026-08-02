"""Focused check: samples 1/5/7/8 photo matching via export mtime.

Uses the already-extracted memories folder (with ZIP mtimes preserved),
NOT a full SMK pipeline run. Compares old UID-order pairing vs mtime sort.

Expected GPS values are what Snap verification + AIO agreed on for the
picture content (see chat 2026-07-26).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from smd.local_pipeline import (
    BundledMediaItem,
    MEDIA_RE,
    build_deterministic_match_map,
)
from smd.utils import load_memories

MEMORIES = Path(r"C:\Users\lasis\Documents\Las\extracted\memories")
JSON_PATH = Path(r"C:\Users\lasis\Documents\Las\extracted\json\memories_history.json")

# Day buckets that contain samples 1, 5, 7, 8 (images only).
SAMPLE_DAYS = ("2016-08-16", "2021-07-28", "2023-07-03", "2024-07-07")

# After mtime match, these stems should get these JSON UTC times / GPS
# (validated against Snap via AIO output).
EXPECTED = {
    # sample 1 day
    "2016-08-16_280E0D88-330B-4C99-80F2-90FD14878DFF": "2016-08-16 13:34:00 UTC",
    "2016-08-16_E49A1971-E724-4E02-962F-5506AA6BBE5C": "2016-08-16 13:39:24 UTC",
    "2016-08-16_F0793F6C-6277-4F68-8FD6-65F535435B44": "2016-08-16 08:52:10 UTC",
    # sample 8 day (the swap proof)
    "2024-07-07_380ed6de-5f56-bd60-c5c3-03268d57420b": "2024-07-07 17:20:48 UTC",
    "2024-07-07_a2702e51-d00b-0cce-10f0-6d579d6a93f0": "2024-07-07 14:21:56 UTC",
    # sample 7: Vejle evening content was on 1d4a93d1 (mtime 18:56:38)
    "2023-07-03_1d4a93d1-7271-fecc-d4d9-908a0d115898": "2023-07-03 18:56:38 UTC",
    "2023-07-03_ea48e3e3-aa86-2282-3607-2e563f2c2a75": "2023-07-03 14:46:36 UTC",
    "2023-07-03_48cb8f9b-7a85-4732-1c13-2c87869cdec6": "2023-07-03 18:56:05 UTC",
}


def _load_day_items(day: str) -> dict[str, BundledMediaItem]:
    items: dict[str, BundledMediaItem] = {}
    for path in sorted(MEMORIES.glob(f"{day}_*-main.jpg")):
        m = MEDIA_RE.match(path.name)
        if not m:
            continue
        stem = f"{m.group('date')}_{m.group('uid')}"
        items[stem] = BundledMediaItem(
            stem=stem,
            date_prefix=m.group("date"),
            uid=m.group("uid"),
            main_path=path,
            main_ext=".jpg",
        )
    return items


def _uid_order_map(items, memories):
    """Old photo behavior: sort stems alphabetically, JSON by Date."""
    from collections import defaultdict

    mem_groups = defaultdict(list)
    for mem in memories:
        if mem.date.strftime("%Y-%m-%d") not in SAMPLE_DAYS:
            continue
        if (mem.media_type or "").lower().startswith("vid"):
            continue
        mem_groups[mem.date.strftime("%Y-%m-%d")].append(mem)
    for g in mem_groups.values():
        g.sort(key=lambda m: m.date)

    out = {}
    by_day = defaultdict(list)
    for stem, item in items.items():
        by_day[item.date_prefix].append((stem, item))
    for day, group in by_day.items():
        group.sort(key=lambda x: x[0])
        mems = mem_groups.get(day, [])
        for i, (stem, _) in enumerate(group):
            out[stem] = mems[i] if i < len(mems) else None
    return out


def main() -> int:
    if not MEMORIES.is_dir() or not JSON_PATH.is_file():
        print("MISSING extract at", MEMORIES)
        print("Point this script at an extract that kept ZIP mtimes.")
        return 2

    memories = load_memories(JSON_PATH)
    print(f"JSON memories: {len(memories)}")
    print(f"Source: {MEMORIES}\n")

    all_items: dict[str, BundledMediaItem] = {}
    for day in SAMPLE_DAYS:
        day_items = _load_day_items(day)
        all_items.update(day_items)
        print(f"{day}: {len(day_items)} jpg mains")

    day_memories = [
        m
        for m in memories
        if m.date.strftime("%Y-%m-%d") in SAMPLE_DAYS
        and not (m.media_type or "").lower().startswith("vid")
    ]

    old_map = _uid_order_map(all_items, memories)
    new_map = build_deterministic_match_map(all_items, day_memories)

    print("\n=== PER-FILE RESULT (mtime match vs old UID order) ===\n")
    ok = 0
    bad = 0
    for stem in sorted(all_items):
        item = all_items[stem]
        mtime = item.main_path.stat().st_mtime
        from datetime import datetime

        mtime_s = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        def fmt(mem):
            if not mem:
                return "None"
            utc = mem.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            return f"{utc} | {mem.location}"

        old = old_map.get(stem)
        new = new_map.get(stem)
        old_s = fmt(old)
        new_s = fmt(new)
        changed = (old is not new) or (
            old and new and (old.date != new.date or old.location != new.location)
        )
        expect = EXPECTED.get(stem)
        new_utc = new.date.strftime("%Y-%m-%d %H:%M:%S UTC") if new else None
        expect_ok = (expect is None) or (new_utc == expect)
        flag = "OK" if expect_ok else "FAIL"
        if expect is not None:
            if expect_ok:
                ok += 1
            else:
                bad += 1
        mark = " *" if changed else ""
        print(f"{stem}")
        print(f"  file mtime wall: {mtime_s}")
        print(f"  OLD UID-order:  {old_s}")
        print(f"  NEW mtime:      {new_s}{mark}")
        if expect:
            print(f"  expected UTC:   {expect}  [{flag}]")
        print()

    print("=== SAMPLE 8 HIGHLIGHT (swap day) ===")
    for stem in (
        "2024-07-07_380ed6de-5f56-bd60-c5c3-03268d57420b",
        "2024-07-07_a2702e51-d00b-0cce-10f0-6d579d6a93f0",
    ):
        n = new_map[stem]
        o = old_map[stem]
        print(
            f"{stem[-12:]}  OLD {o.date.strftime('%Y-%m-%d %H:%M:%S UTC')} GPS {o.location}"
        )
        print(
            f"             NEW {n.date.strftime('%Y-%m-%d %H:%M:%S UTC')} GPS {n.location}"
        )

    print(f"\nExpected-stem checks: {ok} OK, {bad} FAIL")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
