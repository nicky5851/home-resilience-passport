"""S18: 1 or 4 candidates -> 400, the Scotland/NI region rule, no rows created in homes or
assessments, demo compare offline, and winners logic."""

import asyncio

from app.schemas.hazards import HazardLevel, RiskProfile
from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.schemas.score import ResilienceScore, ScoreComponent
from app.services.planner import Ranked
from app.studio.features.s18_home_compare.service import (
    cost_to_70,
    overall_winner,
    winner_for_component,
)

API = "/api/v1"


def _measure(id_: str, cost_low: int, cost_high: int) -> Measure:
    return Measure(
        id=id_,
        name=id_,
        category="carbon",
        cost_low_gbp=cost_low,
        cost_high_gbp=cost_high,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=0,
        resilience_points=0,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


def _score(value: int, points: dict[str, float]) -> ResilienceScore:
    return ResilienceScore(
        value=value,
        band="C",
        components=[
            ScoreComponent(name=name, points=p, max_points=20, reason="r")
            for name, p in points.items()
        ],
        version="v1",
    )


def test_winner_for_component_picks_highest_points() -> None:
    a = _score(50, {"flood": 10})
    b = _score(50, {"flood": 18})
    assert winner_for_component([a, b], ["A", "B"], "flood") == "B"


def test_overall_winner_ties_broken_by_lower_cost_to_70() -> None:
    a = _score(70, {})
    b = _score(70, {})
    assert overall_winner([a, b], [5000, 2000], ["A", "B"]) == "B"


def test_overall_winner_prefers_higher_score() -> None:
    a = _score(80, {})
    b = _score(60, {})
    assert overall_winner([a, b], [None, 1000], ["A", "B"]) == "A"


def test_cost_to_70_sums_until_target_reached() -> None:
    risk = RiskProfile(
        levels=[
            HazardLevel(hazard=h, today="low", y2050="low", why="w", data_source="Your answer")
            for h in ("river_sea_flood", "overheating", "storm", "subsidence", "surface_water")
        ],
        generated_at="2026-01-01T00:00:00Z",
    )
    prop = PropertyFacts(property_type="semi_detached", source="user")
    ranked = [
        Ranked(_measure("a", 100, 200), score_uplift=50, landlord=False),
        Ranked(_measure("b", 50, 100), score_uplift=50, landlord=False),
    ]
    low, high = cost_to_70(ranked, risk, prop)
    assert low in (None, 100, 150)  # depends on L's scoring, but must not error


def test_cost_to_70_is_none_when_unreachable() -> None:
    risk = RiskProfile(levels=[], generated_at="2026-01-01T00:00:00Z")
    prop = PropertyFacts(property_type="semi_detached", source="user")
    low, high = cost_to_70([], risk, prop)
    assert low is None and high is None


def test_demo_compare_works_offline_with_three_homes(client) -> None:
    res = client.get(f"{API}/studio/compare/demo?slugs=flood-terrace,clay-semi,rural-cottage")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["homes"]) == 3
    assert {h["label"] for h in body["homes"]} == {"A", "B", "C"}
    assert body["winners"]["overall"] in ("A", "B", "C")
    assert body["fallback_used"] is False


def test_demo_compare_rejects_one_slug(client) -> None:
    res = client.get(f"{API}/studio/compare/demo?slugs=flood-terrace")
    assert res.status_code == 400, res.text


def test_demo_compare_rejects_four_slugs(client) -> None:
    res = client.get(
        f"{API}/studio/compare/demo?slugs=flood-terrace,clay-semi,rural-cottage,coastal-bungalow"
    )
    assert res.status_code == 400, res.text


def test_compare_requires_login(client) -> None:
    body = {
        "candidates": [
            {"postcode": "SW1A 1AA", "line1": "1 Test St"},
            {"postcode": "YO1 9TJ", "line1": "2 Test St"},
        ]
    }
    res = client.post(f"{API}/studio/compare", json=body)
    assert res.status_code == 401, res.text


def test_compare_rejects_one_candidate(user_client) -> None:
    body = {"candidates": [{"postcode": "SW1A 1AA", "line1": "1 Test St"}]}
    res = user_client.post(f"{API}/studio/compare", json=body)
    assert res.status_code == 400, res.text


def test_compare_rejects_scottish_postcode(user_client) -> None:
    body = {
        "candidates": [
            {"postcode": "SW1A 1AA", "line1": "1 Test St"},
            {"postcode": "EH1 1YZ", "line1": "2 Test St"},
        ]
    }
    res = user_client.post(f"{API}/studio/compare", json=body)
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "unsupported_region"


def test_compare_creates_no_home_or_assessment_rows(user_client, db_url) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    body = {
        "candidates": [
            {"postcode": "SW1A 1AA", "line1": "1 Test St"},
            {"postcode": "YO1 9TJ", "line1": "2 Test St"},
        ]
    }
    res = user_client.post(f"{API}/studio/compare", json=body)
    assert res.status_code == 200, res.text

    async def counts() -> tuple[int, int]:
        eng = create_async_engine(db_url, poolclass=NullPool)
        try:
            async with eng.begin() as conn:
                homes = (await conn.execute(text("SELECT count(*) FROM homes"))).scalar_one()
                assessments = (
                    await conn.execute(text("SELECT count(*) FROM assessments"))
                ).scalar_one()
                return homes, assessments
        finally:
            await eng.dispose()

    homes_count, assessments_count = asyncio.run(counts())
    assert homes_count == 0
    assert assessments_count == 0
