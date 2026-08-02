"""Auto-dedupe: keeper pick + permanent delete of extras."""
from __future__ import annotations

from pathlib import Path

from smd.account_layout import AccountPaths
from smd.duplicates import (
    DuplicateEntry,
    DuplicateScanReport,
    auto_delete_duplicate_extras,
    dedupe_staging_items,
    keeper_filename,
)


def test_keeper_filename_prefers_oldest_timestamp():
    assert (
        keeper_filename(
            [
                "2025-08-20_00-34-27.jpg",
                "2023-08-20_16-08-00.jpg",
            ]
        )
        == "2023-08-20_16-08-00.jpg"
    )


def test_keeper_filename_same_second_prefers_shorter_name():
    assert (
        keeper_filename(
            [
                "2024-08-29_15-31-23_5e1cadacef6d.mp4",
                "2024-08-29_15-31-23.mp4",
            ]
        )
        == "2024-08-29_15-31-23.mp4"
    )


def test_auto_delete_keeps_oldest_in_merged_and_raw(tmp_path: Path):
    account = tmp_path / "Acct-memories"
    merged = account / "Memories" / "merged"
    raw = account / "Memories" / "raw"
    reports = account / "technical" / "reports"
    for d in (merged, raw, reports):
        d.mkdir(parents=True)

    keep = "2023-01-01_12-00-00.jpg"
    drop = "2025-01-01_12-00-00.jpg"
    for folder in (merged, raw):
        (folder / keep).write_bytes(b"same-bytes-aaaa")
        (folder / drop).write_bytes(b"same-bytes-aaaa")

    paths = AccountPaths.for_account(account, keep_raw=True)
    report = DuplicateScanReport(
        scanned_at="2026-01-01T00:00:00+00:00",
        merged_scanned=2,
        duplicate_groups=1,
        kind="byte",
        entries=[
            DuplicateEntry(keep, keep, "abc123"),
            DuplicateEntry(drop, keep, "abc123"),
        ],
    )
    deleted, labels = auto_delete_duplicate_extras(paths, report, require_raw=True)
    assert deleted == 2  # merged + raw
    assert (merged / keep).is_file()
    assert (raw / keep).is_file()
    assert not (merged / drop).exists()
    assert not (raw / drop).exists()
    assert any(drop in x for x in labels)


class _Item:
    def __init__(self, stem: str, main: Path, overlay: Path | None = None):
        self.stem = stem
        self.main_path = main
        self.overlay_path = overlay
        self.main_ext = main.suffix
        self.date_prefix = stem[:10]
        self.uid = stem.split("_", 1)[-1]


def test_dedupe_staging_byte_drops_extras(tmp_path: Path):
    staging = tmp_path / "staging"
    reports = tmp_path / "reports"
    staging.mkdir()
    reports.mkdir()

    keep_stem = "2020-01-01_AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"
    drop_stem = "2020-01-01_BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"
    payload = b"identical-main-payload-xyz"
    keep_main = staging / f"{keep_stem}-main.jpg"
    drop_main = staging / f"{drop_stem}-main.jpg"
    drop_ov = staging / f"{drop_stem}-overlay.png"
    keep_main.write_bytes(payload)
    drop_main.write_bytes(payload)
    drop_ov.write_bytes(b"ov")

    items = {
        keep_stem: _Item(keep_stem, keep_main),
        drop_stem: _Item(drop_stem, drop_main, drop_ov),
    }
    out, groups, dropped = dedupe_staging_items(
        items, reports_dir=reports, mode="byte", hash_workers=1
    )
    assert groups == 1
    assert dropped == 1
    assert keep_stem in out
    assert drop_stem not in out
    assert keep_main.is_file()
    assert not drop_main.exists()
    assert not drop_ov.exists()


def test_staging_visual_cache_and_cancel(tmp_path: Path):
    from smd.duplicates import (
        STAGING_VISUAL_HASH_CACHE_NAME,
        DuplicateScanCancelled,
        dedupe_staging_items,
    )

    staging = tmp_path / "staging"
    reports = tmp_path / "reports"
    staging.mkdir()
    reports.mkdir()

    # Distinct RGB images so visual hash runs; not duplicates.
    try:
        from PIL import Image
    except ImportError:
        return

    stems = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        stem = f"2020-01-0{i+1}_AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA{i}"
        stems.append(stem)
        path = staging / f"{stem}-main.jpg"
        Image.new("RGB", (8, 8), color).save(path, format="JPEG")

    items = {s: _Item(s, staging / f"{s}-main.jpg") for s in stems}
    out, groups, dropped = dedupe_staging_items(
        items, reports_dir=reports, mode="visual", hash_workers=1
    )
    assert groups == 0
    assert dropped == 0
    assert len(out) == 3
    cache_path = reports / STAGING_VISUAL_HASH_CACHE_NAME
    assert cache_path.is_file()

    # Second pass should reuse cache (no cancel).
    out2, _, _ = dedupe_staging_items(
        dict(items), reports_dir=reports, mode="visual", hash_workers=1
    )
    assert len(out2) == 3

    # Cancel during byte hashing of same-size twins.
    a = "2021-01-01_AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"
    b = "2021-01-01_BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"
    payload = b"same-bytes-for-cancel-test"
    pa = staging / f"{a}-main.jpg"
    pb = staging / f"{b}-main.jpg"
    pa.write_bytes(payload)
    pb.write_bytes(payload)
    twin_items = {a: _Item(a, pa), b: _Item(b, pb)}
    raised = False
    try:
        dedupe_staging_items(
            twin_items,
            reports_dir=reports,
            mode="byte",
            hash_workers=1,
            should_stop=lambda: True,
        )
    except DuplicateScanCancelled:
        raised = True
    assert raised
