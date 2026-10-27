"""The scoring interface N calls (spec §4.3) returns schema-valid, deterministic results."""

import inspect

import pytest

import app.scoring as scoring
from app.schemas import (
    HAZARD_ORDER,
    FundingBundle,
    FundingOption,
    HazardInputs,
    Household,
    Measure,
    Plan,
    PropertyFacts,
    ResilienceScore,
    RiskProfile,
)
from app.scoring import SCORING_VERSION, assess_risk, compute_score, match_funding
from app.scoring.config import MAX_POINTS


def _inputs(fx: dict) -> HazardInputs:
    return HazardInputs.model_validate(fx["inputs"])


def _options(fx: dict) -> list[FundingOption]:
    return [FundingOption.model_validate(ln["option"]) for ln in fx["funding"]["lines"]]


def test_public_names() -> None:
    assert set(scoring.__all__) == {
        "SCORING_VERSION",
        "assess_risk",
        "compute_score",
        "match_funding",
    }
    assert SCORING_VERSION == "v1"
    params = inspect.signature(compute_score).parameters
    assert list(params) == ["risk", "prop", "completed_measures"]
    assert params["completed_measures"].default == ()


def test_assess_risk_contract(demo_fixture: dict) -> None:
    risk = assess_risk(_inputs(demo_fixture))
    RiskProfile.model_validate(risk.model_dump())
    assert tuple(lv.hazard for lv in risk.levels) == HAZARD_ORDER
    sw = risk.levels[-1]
    assert (sw.today, sw.y2050) == ("medium", "medium")
    assert sw.why == "Surface-water data is coming in a later version"
    assert assess_risk(_inputs(demo_fixture)) == risk  # deterministic


def test_compute_score_contract(demo_fixture: dict) -> None:
    inputs = _inputs(demo_fixture)
    risk = assess_risk(inputs)
    score = compute_score(risk, inputs.property)
    ResilienceScore.model_validate(score.model_dump())
    assert 0 <= score.value <= 100
    assert [c.name for c in score.components] == list(MAX_POINTS)
    assert all(0 <= c.points <= c.max_points for c in score.components)
    assert score.version == SCORING_VERSION

    measures = [Measure.model_validate(i["measure"]) for i in demo_fixture["plan"]["items"]]
    with_measures = compute_score(risk, inputs.property, measures)
    assert 0 <= with_measures.value <= 100


def test_compute_score_accepts_unknown_property() -> None:
    risk = assess_risk(HazardInputs(property=PropertyFacts(property_type="other", source="user")))
    assert 0 <= compute_score(risk, PropertyFacts(property_type="other", source="user")).value


def test_match_funding_contract(demo_fixture: dict) -> None:
    plan = Plan.model_validate(demo_fixture["plan"])
    household = Household.model_validate(demo_fixture["household"])
    bundle = match_funding(plan, household, _options(demo_fixture))
    FundingBundle.model_validate(bundle.model_dump())
    assert bundle.covered_gbp + bundle.gap_gbp == plan.total_cost_low_gbp
    assert [ln.option.kind for ln in bundle.lines] == sorted(
        (ln.option.kind for ln in bundle.lines), key=lambda k: k != "grant"
    )


@pytest.mark.parametrize("fn", [assess_risk, compute_score, match_funding])
def test_functions_are_pure(fn) -> None:
    """No I/O imports in the scoring package (no network, no database)."""
    source = inspect.getsource(inspect.getmodule(fn))
    for banned in ("httpx", "sqlalchemy", "requests", "open(", "app.db", "app.adapters"):
        assert banned not in source, f"{fn.__name__} module uses {banned}"
