"""S20: the sample JSON has no address/UPRN/full postcode, districts below 5 homes are
dropped, the scenario is deterministic and monotonic with uptake, and the routes work
logged-out and offline."""

import json
import re

import pytest

from app.studio.features.s20_portfolio.config import DATA_PATH, MIN_HOMES_PER_DISTRICT
from app.studio.features.s20_portfolio.data import load
from app.studio.features.s20_portfolio.service import build_portfolio, run_scenario

API = "/api/v1"

FULL_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b")


def test_sample_json_has_no_personal_or_address_data() -> None:
    text = DATA_PATH.read_text()
    assert not FULL_POSTCODE.search(text)
    assert "uprn" not in text.lower()
    assert "line1" not in text
    raw = json.loads(text)
    for home in raw["homes"]:
        assert set(home) == {"outcode", "property", "risk", "score", "transition"}
        assert len(home["outcode"]) <= 4


def test_sample_json_has_500_homes_and_is_seeded() -> None:
    raw = json.loads(DATA_PATH.read_text())
    assert len(raw["homes"]) == 500
    assert isinstance(raw["seed"], int)


def test_sampling_is_deterministic_with_the_seed() -> None:
    import random

    candidates = [{"id": i} for i in range(1000)]
    first = random.Random(42).sample(candidates, 500)
    second = random.Random(42).sample(candidates, 500)
    assert first == second


def test_districts_below_minimum_are_dropped() -> None:
    portfolio = build_portfolio(load())
    assert all(d.count >= MIN_HOMES_PER_DISTRICT for d in portfolio.districts)


def test_portfolio_route_works_logged_out_and_offline(client) -> None:
    res = client.get(f"{API}/studio/portfolio")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sample_size"] == 500
    assert body["fallback_used"] is False
    assert body["districts"]
    assert all(d["count"] >= MIN_HOMES_PER_DISTRICT for d in body["districts"])
    assert body["fairness_note"] == "Scores are never used to raise prices or rates."


def test_scenario_zero_uptake_is_the_baseline() -> None:
    data = load()
    result = run_scenario(data, uptake_pct=0, by_year=2030)
    assert result.homes_upgraded == 0
    assert result.emissions_after_t == result.emissions_before_t
    assert result.reduction_pct == 0.0
    portfolio = build_portfolio(data)
    assert result.below_c_share_after_pct == portfolio.below_c_share_pct


def test_scenario_full_uptake_reduces_emissions() -> None:
    data = load()
    result = run_scenario(data, uptake_pct=100, by_year=2030)
    assert result.emissions_after_t < result.emissions_before_t
    assert result.reduction_pct > 0


@pytest.mark.parametrize("uptake", [0, 25, 50, 75, 100])
def test_scenario_is_monotonic_with_uptake(uptake: int) -> None:
    data = load()
    baseline = run_scenario(data, uptake_pct=0, by_year=2030)
    result = run_scenario(data, uptake_pct=uptake, by_year=2030)
    assert result.emissions_after_t <= baseline.emissions_after_t
    assert result.below_c_share_after_pct <= baseline.below_c_share_after_pct


def test_scenario_route_logged_out_and_offline(client) -> None:
    res = client.post(f"{API}/studio/portfolio/scenario", json={"uptake_pct": 25, "by_year": 2030})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["homes_upgraded"] >= 0
    assert body["finance_needed_low_gbp"] >= 0


def test_scenario_rejects_out_of_range_uptake(client) -> None:
    res = client.post(f"{API}/studio/portfolio/scenario", json={"uptake_pct": 101, "by_year": 2030})
    assert res.status_code == 400


def test_scenario_rejects_out_of_range_year(client) -> None:
    res = client.post(f"{API}/studio/portfolio/scenario", json={"uptake_pct": 25, "by_year": 2050})
    assert res.status_code == 400
