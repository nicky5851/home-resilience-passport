"""S15: grid-factor interpolation, heat-pump conversion crossing its break-even point, year
bounds and unknown-measure validation, and the rural-cottage (oil) acceptance scenario."""

from app.schemas.plan import Measure
from app.studio.features.s13_affordability_stress_test.schemas import Kwh
from app.studio.features.s15_net_zero_road.config import FUEL_FACTOR_KG_PER_KWH, HEAT_PUMP_SCOP
from app.studio.features.s15_net_zero_road.schemas import YearRow
from app.studio.features.s15_net_zero_road.service import (
    cumulative_saved_kg,
    interpolate,
    near_zero_year,
    with_plan_kg,
)

API = "/api/v1"


def _measure(id_: str, co2: int = 0) -> Measure:
    return Measure(
        id=id_,
        name=id_,
        category="carbon",
        cost_low_gbp=0,
        cost_high_gbp=0,
        annual_bill_saving_gbp=0,
        co2_saved_kg_per_year=co2,
        resilience_points=0,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


def test_interpolate_is_linear_between_published_points() -> None:
    series = [(2025, 100.0), (2030, 50.0)]
    assert interpolate(series, 2025) == 100.0
    assert interpolate(series, 2030) == 50.0
    assert interpolate(series, 2028) == 100.0 - (100.0 - 50.0) * 3 / 5


def test_interpolate_clamps_outside_the_published_range() -> None:
    series = [(2025, 100.0), (2030, 50.0)]
    assert interpolate(series, 2000) == 100.0
    assert interpolate(series, 2100) == 50.0


def test_heat_pump_conversion_crosses_its_break_even_point() -> None:
    """A heat pump turns 1 kWh of heat demand into 1/SCOP kWh of electricity, so it only cuts
    emissions once the grid factor undercuts the fuel's own combustion factor scaled by SCOP."""
    kwh = Kwh(heating_fuel=10_000, electricity=2_000)
    heat_pump = _measure("heat-pump")
    breakeven = FUEL_FACTOR_KG_PER_KWH["oil"] * HEAT_PUMP_SCOP

    dirty_grid = [(2026, breakeven * 1.5)]
    clean_grid = [(2026, breakeven * 0.5)]

    do_nothing_dirty = (
        kwh.heating_fuel * FUEL_FACTOR_KG_PER_KWH["oil"] + kwh.electricity * breakeven * 1.5
    )
    with_dirty_grid = with_plan_kg(kwh, "oil", 2026, dirty_grid, [heat_pump], breakeven * 1.5)
    assert with_dirty_grid > do_nothing_dirty  # a dirtier-than-breakeven grid: worse off

    do_nothing_clean = (
        kwh.heating_fuel * FUEL_FACTOR_KG_PER_KWH["oil"] + kwh.electricity * breakeven * 0.5
    )
    with_clean_grid = with_plan_kg(kwh, "oil", 2026, clean_grid, [heat_pump], breakeven * 0.5)
    assert with_clean_grid < do_nothing_clean  # a cleaner-than-breakeven grid: better off


def test_cumulative_and_near_zero_year() -> None:
    years = [
        YearRow(year=2025, co2_kg_do_nothing=1000, co2_kg_with_plan=900, pathway_kg=1000),
        YearRow(year=2026, co2_kg_do_nothing=1000, co2_kg_with_plan=400, pathway_kg=900),
    ]
    assert cumulative_saved_kg(years) == 100 + 600
    assert near_zero_year(years) == 2026


def test_route_rejects_too_many_steps(client) -> None:
    steps = [{"measure_id": "loft-insulation", "year": 2026 + i} for i in range(13)]
    res = client.post(f"{API}/studio/homes/demo-rural-cottage/net-zero-road", json={"steps": steps})
    assert res.status_code == 400, res.text


def test_route_rejects_years_outside_bounds(client) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-rural-cottage/net-zero-road",
        json={"steps": [{"measure_id": "loft-insulation", "year": 2051}]},
    )
    assert res.status_code == 400, res.text


def test_route_rejects_unknown_measure(client) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-rural-cottage/net-zero-road",
        json={"steps": [{"measure_id": "not-a-real-measure", "year": 2030}]},
    )
    assert res.status_code == 400, res.text


def test_route_default_steps_and_shape(client) -> None:
    res = client.post(f"{API}/studio/homes/demo-rural-cottage/net-zero-road", json={"steps": []})
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["years"]) == 26
    assert body["years"][0]["year"] == 2025
    assert body["years"][-1]["year"] == 2050
    assert body["fallback_used"] is False
    assert len(body["default_steps"]) >= 1


def test_route_moving_a_measure_earlier_never_reduces_cumulative_savings(client) -> None:
    later = client.post(
        f"{API}/studio/homes/demo-rural-cottage/net-zero-road",
        json={"steps": [{"measure_id": "loft-insulation", "year": 2045}]},
    ).json()
    earlier = client.post(
        f"{API}/studio/homes/demo-rural-cottage/net-zero-road",
        json={"steps": [{"measure_id": "loft-insulation", "year": 2026}]},
    ).json()
    assert earlier["cumulative_saved_kg"] >= later["cumulative_saved_kg"]
