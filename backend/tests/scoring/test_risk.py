"""Risk engine v1 (spec §6, docs/scoring.md). L owns this file."""

import json
from pathlib import Path

import pytest

from app.schemas import HazardInputs, PropertyFacts
from app.scoring.risk import assess_risk

EXPECTED_DIR = Path(__file__).parent / "expected"


def _prop(**kw) -> PropertyFacts:
    return PropertyFacts(property_type="terraced", source="demo", **kw)


def _inputs(**kw) -> HazardInputs:
    prop = kw.pop("property", None) or _prop()
    return HazardInputs(property=prop, **kw)


def _levels(risk) -> dict[str, tuple[str, str]]:
    return {lv.hazard: (lv.today, lv.y2050) for lv in risk.levels}


# --- River/sea flood -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("band", "warnings", "expected"),
    [
        ("none", 0, "low"),
        ("very_low", 0, "low"),
        ("low", 0, "medium"),
        ("medium", 0, "high"),
        ("high", 0, "high"),
        (None, 0, "medium"),
        # active warnings bump one level, capped at high
        ("none", 1, "medium"),
        ("very_low", 2, "medium"),
        ("low", 1, "high"),
        ("medium", 1, "high"),
        ("high", 1, "high"),
    ],
)
def test_flood_level(band, warnings, expected) -> None:
    risk = assess_risk(_inputs(rofrs_band=band, active_flood_warnings=warnings))
    today, y2050 = _levels(risk)["river_sea_flood"]
    assert (today, y2050) == (expected, expected)


def test_flood_why_mentions_warning_count() -> None:
    risk = assess_risk(_inputs(rofrs_band="high", active_flood_warnings=2))
    lv = next(lv for lv in risk.levels if lv.hazard == "river_sea_flood")
    assert "2 active flood warnings" in lv.why


def test_flood_unknown_band_says_unavailable() -> None:
    risk = assess_risk(_inputs(rofrs_band=None))
    lv = next(lv for lv in risk.levels if lv.hazard == "river_sea_flood")
    assert "unavailable" in lv.why


# --- Overheating ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "low"),
        (4.9, "low"),
        (5, "medium"),
        (15, "medium"),
        (15.1, "high"),
        (30, "high"),
        (None, "medium"),
    ],
)
def test_heat_threshold_edges(value, expected) -> None:
    risk = assess_risk(_inputs(hot_days_baseline=value, hot_days_2050=value))
    today, y2050 = _levels(risk)["overheating"]
    assert (today, y2050) == (expected, expected)


@pytest.mark.parametrize(
    ("top_floor", "epc_rating", "bumped"),
    [
        (None, None, False),
        (None, "C", False),
        (True, None, True),
        (False, "A", True),
        (None, "B", True),
    ],
)
def test_heat_bump_top_floor_or_epc_ab(top_floor, epc_rating, bumped) -> None:
    prop = _prop(top_floor=top_floor, epc_rating=epc_rating)
    risk = assess_risk(_inputs(hot_days_baseline=10, hot_days_2050=10, property=prop))
    today, _ = _levels(risk)["overheating"]
    assert today == ("high" if bumped else "medium")


def test_heat_bump_caps_at_high() -> None:
    prop = _prop(epc_rating="A")
    risk = assess_risk(_inputs(hot_days_baseline=30, hot_days_2050=30, property=prop))
    today, y2050 = _levels(risk)["overheating"]
    assert (today, y2050) == ("high", "high")


def test_heat_missing_data_says_unavailable() -> None:
    lv = next(
        lv
        for lv in assess_risk(_inputs(hot_days_baseline=None, hot_days_2050=None)).levels
        if lv.hazard == "overheating"
    )
    assert "unavailable" in lv.why


# --- Storm ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (10, "low"),
        (49.9, "low"),
        (50, "medium"),
        (65, "medium"),
        (65.1, "high"),
        (150, "high"),
        (None, "medium"),
    ],
)
def test_storm_threshold_edges(value, expected) -> None:
    risk = assess_risk(_inputs(max_wind_baseline_kmh=value, max_wind_2050_kmh=value))
    today, y2050 = _levels(risk)["storm"]
    assert (today, y2050) == (expected, expected)


def test_storm_missing_data_says_unavailable() -> None:
    lv = next(
        lv
        for lv in assess_risk(_inputs(max_wind_baseline_kmh=None, max_wind_2050_kmh=None)).levels
        if lv.hazard == "storm"
    )
    assert "unavailable" in lv.why


# --- Subsidence --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("signal", "expected"),
    [
        ("none_reported", "low"),
        ("unknown", "medium"),
        ("clay_reported", "high"),
        ("cracks_reported", "high"),
    ],
)
def test_subsidence_level(signal, expected) -> None:
    risk = assess_risk(_inputs(subsidence_signal=signal))
    today, y2050 = _levels(risk)["subsidence"]
    assert (today, y2050) == (expected, expected)


# --- Surface water (fixed, M1 has no data yet) -------------------------------------------------


def test_surface_water_is_fixed_medium() -> None:
    today, y2050 = _levels(assess_risk(_inputs()))["surface_water"]
    assert (today, y2050) == ("medium", "medium")


# --- Demo homes: real inputs give the expected narrative per home ------------------------------


@pytest.mark.parametrize(
    "slug",
    ["flood-terrace", "coastal-bungalow", "city-top-flat", "clay-semi", "rural-cottage"],
)
def test_demo_home_matches_expected(slug: str) -> None:
    fixtures_dir = Path(__file__).parents[1] / "fixtures" / "demo_homes"
    fx = json.loads((fixtures_dir / f"{slug}.json").read_text())
    expected = json.loads((EXPECTED_DIR / f"{slug}.json").read_text())
    risk = assess_risk(HazardInputs.model_validate(fx["inputs"]))
    assert risk.model_dump(mode="json") == expected["risk"]
