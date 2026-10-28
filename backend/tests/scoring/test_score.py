"""Resilience score v1 (spec §6, docs/scoring.md). L owns this file."""

import json
from pathlib import Path

import pytest

from app.schemas import HazardInputs, HazardLevel, Measure, PropertyFacts, RiskProfile
from app.scoring.config import MAX_POINTS
from app.scoring.score import band_for, compute_score

EXPECTED_DIR = Path(__file__).parent / "expected"


def _prop(**kw) -> PropertyFacts:
    return PropertyFacts(property_type="terraced", source="demo", **kw)


def _risk(flood="low", heat="low", storm="low", subsidence="low") -> RiskProfile:
    levels = [
        HazardLevel(
            hazard="river_sea_flood",
            today=flood,
            y2050=flood,
            why="x",
            data_source="Environment Agency",
        ),
        HazardLevel(
            hazard="overheating", today=heat, y2050=heat, why="x", data_source="Open-Meteo (CMIP6)"
        ),
        HazardLevel(
            hazard="storm", today=storm, y2050=storm, why="x", data_source="Open-Meteo (CMIP6)"
        ),
        HazardLevel(
            hazard="subsidence",
            today=subsidence,
            y2050=subsidence,
            why="x",
            data_source="Your answer",
        ),
        HazardLevel(
            hazard="surface_water",
            today="medium",
            y2050="medium",
            why="x",
            data_source="Environment Agency",
        ),
    ]
    return RiskProfile(levels=levels, generated_at="2026-10-27T09:00:00Z")


def _measure(category: str, resilience_points: int) -> Measure:
    return Measure(
        id=f"test-{category}",
        name="Test measure",
        category=category,
        cost_low_gbp=100,
        cost_high_gbp=200,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=resilience_points,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


# --- Hazard points use the 2050 level --------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "fraction"),
    [("low", 1.0), ("medium", 0.5), ("high", 0.1)],
)
def test_hazard_points_follow_level_fraction(level, fraction) -> None:
    risk = _risk(flood=level, heat=level, storm=level, subsidence=level)
    score = compute_score(risk, _prop(epc_score=50))
    by_name = {c.name: c for c in score.components}
    for name in ("flood", "heat", "storm", "subsidence"):
        assert by_name[name].points == round(MAX_POINTS[name] * fraction, 1)


def test_component_order_matches_max_points() -> None:
    score = compute_score(_risk(), _prop())
    assert [c.name for c in score.components] == list(MAX_POINTS)


# --- Carbon points -----------------------------------------------------------------------------


def test_carbon_points_from_epc_score() -> None:
    score = compute_score(_risk(), _prop(epc_score=80))
    carbon = next(c for c in score.components if c.name == "carbon")
    assert carbon.points == 24.0
    assert "80" in carbon.reason


def test_carbon_points_from_epc_rating_midpoint_when_score_missing() -> None:
    score = compute_score(_risk(), _prop(epc_rating="C"))
    carbon = next(c for c in score.components if c.name == "carbon")
    assert carbon.points == pytest.approx(75 * 0.3)


def test_carbon_points_flat_when_both_unknown() -> None:
    score = compute_score(_risk(), _prop())
    carbon = next(c for c in score.components if c.name == "carbon")
    assert carbon.points == 15.0


# --- Measures add resilience_points to their component, capped at max ------------------------


def test_completed_measure_adds_points_to_its_component() -> None:
    base = compute_score(_risk(storm="high"), _prop(epc_score=50))
    base_storm = next(c for c in base.components if c.name == "storm").points

    with_measure = compute_score(_risk(storm="high"), _prop(epc_score=50), [_measure("storm", 4)])
    storm = next(c for c in with_measure.components if c.name == "storm")
    assert storm.points == base_storm + 4


def test_completed_measure_points_capped_at_component_max() -> None:
    score = compute_score(_risk(), _prop(epc_score=50), [_measure("subsidence", 100)])
    subsidence = next(c for c in score.components if c.name == "subsidence")
    assert subsidence.points == MAX_POINTS["subsidence"]


def test_multiple_measures_in_same_category_stack() -> None:
    score = compute_score(
        _risk(heat="high"), _prop(epc_score=50), [_measure("heat", 2), _measure("heat", 3)]
    )
    heat = next(c for c in score.components if c.name == "heat")
    assert heat.points == round(MAX_POINTS["heat"] * 0.1 + 5, 1)


# --- Bounds and bands ----------------------------------------------------------------------


def test_score_never_exceeds_100() -> None:
    measures = [_measure(cat, 1000) for cat in ("flood", "heat", "storm", "subsidence", "carbon")]
    score = compute_score(_risk(), _prop(epc_score=100), measures)
    assert score.value <= 100


def test_score_never_below_0() -> None:
    risk = _risk(flood="high", heat="high", storm="high", subsidence="high")
    score = compute_score(risk, _prop())
    assert score.value >= 0


@pytest.mark.parametrize(
    ("value", "band"),
    [
        (0, "G"),
        (9, "G"),
        (10, "F"),
        (24, "F"),
        (25, "E"),
        (39, "E"),
        (40, "D"),
        (54, "D"),
        (55, "C"),
        (69, "C"),
        (70, "B"),
        (84, "B"),
        (85, "A"),
        (100, "A"),
    ],
)
def test_band_for_edges(value, band) -> None:
    assert band_for(value) == band


def test_compute_score_accepts_unknown_property() -> None:
    score = compute_score(_risk(), PropertyFacts(property_type="other", source="demo"))
    assert 0 <= score.value <= 100


# --- Demo homes: real inputs give the expected score ----------------------------------------


@pytest.mark.parametrize(
    "slug",
    ["flood-terrace", "coastal-bungalow", "city-top-flat", "clay-semi", "rural-cottage"],
)
def test_demo_home_matches_expected(slug: str) -> None:
    from app.scoring.risk import assess_risk

    fixtures_dir = Path(__file__).parents[1] / "fixtures" / "demo_homes"
    fx = json.loads((fixtures_dir / f"{slug}.json").read_text())
    expected = json.loads((EXPECTED_DIR / f"{slug}.json").read_text())
    inputs = HazardInputs.model_validate(fx["inputs"])
    risk = assess_risk(inputs)
    score = compute_score(risk, inputs.property)
    assert score.model_dump(mode="json") == expected["score"]
