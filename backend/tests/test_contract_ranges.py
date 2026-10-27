"""Seam 2: every fixture's HazardInputs is inside the valid ranges in CONTRACT.md §2."""

from app.schemas import HAZARD_INPUT_RANGES, HazardInputs


def test_inputs_in_range(demo_fixture: dict) -> None:
    inputs = HazardInputs.model_validate(demo_fixture["inputs"])
    for field, (lo, hi) in HAZARD_INPUT_RANGES.items():
        value = getattr(inputs, field)
        if value is None:
            continue
        assert lo <= value <= hi, f"{demo_fixture['slug']}: {field}={value} not in [{lo}, {hi}]"


def test_pairs_known_together(demo_fixture: dict) -> None:
    """A baseline and its 2050 value are both known or both unknown."""
    inputs = HazardInputs.model_validate(demo_fixture["inputs"])
    for base, future in (
        ("hot_days_baseline", "hot_days_2050"),
        ("heavy_rain_days_baseline", "heavy_rain_days_2050"),
        ("max_wind_baseline_kmh", "max_wind_2050_kmh"),
    ):
        assert (getattr(inputs, base) is None) == (getattr(inputs, future) is None)


def test_top_floor_only_for_flats(demo_fixture: dict) -> None:
    prop = HazardInputs.model_validate(demo_fixture["inputs"]).property
    if prop.top_floor:
        assert prop.property_type == "flat"


def test_wales_has_no_rofrs(demo_fixture: dict) -> None:
    if demo_fixture["address"]["country"] == "wales":
        assert demo_fixture["inputs"]["rofrs_band"] is None
