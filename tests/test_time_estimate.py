"""Smoke checks for bundled processing time estimates."""
from smd.system_profile import SystemProfile
from smd.time_estimate import estimate_bundled_processing


def _desk() -> SystemProfile:
    return SystemProfile(
        physical_cores=8,
        logical_cpus=16,
        ram_gb=32.0,
        on_battery=False,
        battery_percent=100.0,
    )


def test_mary_like_low_overlay_is_about_seven_minutes():
    # Mary Maximum: 681 mains, ~50% video, ~0.4% overlays, ~6 GB ZIP, ~7 min.
    est = estimate_bundled_processing(
        681,
        profile=_desk(),
        overlay_fraction=0.0044,
        video_fraction=0.50,
        needs_zip_extract=True,
        staging_gb=6.13,
    )
    secs = float(est["maximum"]["seconds"])
    assert 5 * 60 <= secs <= 12 * 60, secs


def test_las_like_matches_three_hours_thirty_three():
    # Las Maximum: 13442 files, ~61% video, ~17% overlays, ~49 GB ZIP parts, 3h33m.
    est = estimate_bundled_processing(
        13442,
        profile=_desk(),
        overlay_fraction=0.168,
        video_fraction=0.607,
        needs_zip_extract=True,
        staging_gb=49.05,
    )
    secs = float(est["maximum"]["seconds"])
    target = 3 * 3600 + 33 * 60
    assert abs(secs - target) <= 20 * 60, secs


def test_modes_ordered_maximum_fastest():
    est = estimate_bundled_processing(2000, profile=_desk())
    assert est["maximum"]["seconds"] <= est["balanced"]["seconds"]
    assert est["balanced"]["seconds"] <= est["conservative"]["seconds"]
