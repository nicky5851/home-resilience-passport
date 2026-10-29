"""S13: scenario maths on known numbers, savings scaling, income fields null for demo refs,
and income band never logged."""

import logging

from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.studio.features.s13_affordability_stress_test.config import load_price_cap
from app.studio.features.s13_affordability_stress_test.schemas import Kwh
from app.studio.features.s13_affordability_stress_test.service import (
    after_plan_cost_gbp,
    annual_cost_gbp,
    estimate_kwh,
    heating_fuel_for,
)

API = "/api/v1"


def test_heating_fuel_mapping() -> None:
    assert heating_fuel_for("mains gas") == "gas"
    assert heating_fuel_for("electricity") == "electric"
    assert heating_fuel_for("oil") == "oil"
    assert heating_fuel_for("LPG") == "lpg"
    assert heating_fuel_for("wood") == "other"
    assert heating_fuel_for(None) == "gas"


def test_annual_cost_known_numbers() -> None:
    cap = {
        "gas_p_per_kwh": 10.0,
        "elec_p_per_kwh": 20.0,
        "gas_standing_p_per_day": 30.0,
        "elec_standing_p_per_day": 50.0,
    }
    kwh = Kwh(heating_fuel=1000, electricity=500)
    cost = annual_cost_gbp(kwh, "gas", cap)
    # (1000*10 + 500*20) p = 20000p = £200, plus standing (30+50)*365p = 29200p = £292
    assert cost == 492.0


def test_electric_heating_has_no_gas_standing_charge() -> None:
    cap = {
        "gas_p_per_kwh": 10.0,
        "elec_p_per_kwh": 20.0,
        "gas_standing_p_per_day": 30.0,
        "elec_standing_p_per_day": 50.0,
    }
    kwh = Kwh(heating_fuel=0, electricity=1000)
    cost = annual_cost_gbp(kwh, "electric", cap)
    # 1000*20p = 20000p = £200, plus only electricity standing 50*365p = 18250p = £182.5
    assert cost == 382.5


def _measure(saving: int) -> Measure:
    return Measure(
        id="m",
        name="Measure",
        category="storm",
        cost_low_gbp=0,
        cost_high_gbp=0,
        annual_bill_saving_gbp=saving,
        co2_saved_kg_per_year=0,
        resilience_points=0,
        renter_ok=True,
        needs_landlord=False,
        source_url="https://example.com",
    )


def test_savings_scale_with_price_ratio() -> None:
    cost_at_1x = after_plan_cost_gbp(
        1000, [_measure(100)], price_ratio_to_today=1.0, standing_floor_gbp=0
    )
    cost_at_2x = after_plan_cost_gbp(
        1000, [_measure(100)], price_ratio_to_today=2.0, standing_floor_gbp=0
    )
    assert cost_at_2x < cost_at_1x


def test_after_plan_cost_floors_at_standing_charges() -> None:
    cost = after_plan_cost_gbp(
        100, [_measure(10_000)], price_ratio_to_today=1.0, standing_floor_gbp=80
    )
    assert cost == 80


def test_estimate_kwh_electric_heating_is_all_electricity() -> None:
    prop = PropertyFacts(property_type="flat", construction_age_band="2007 onwards", source="demo")
    kwh = estimate_kwh(prop, "electric")
    assert kwh.heating_fuel == 0
    assert kwh.electricity > 0


def test_price_cap_csv_has_three_periods() -> None:
    caps = load_price_cap()
    assert len(caps) == 3


def test_route_nulls_income_fields_for_demo_homes(client) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/affordability")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["scenarios"]) == 4
    assert all(s["pct_income"] is None for s in body["scenarios"])
    assert body["lilee_indicator"] is None
    assert body["kwh_source"] == "estimated"


def test_route_shrinks_with_measures_selected(client) -> None:
    base = client.get(f"{API}/studio/homes/demo-flood-terrace/affordability").json()
    with_plan = client.get(
        f"{API}/studio/homes/demo-flood-terrace/affordability?measure_ids=flood-door,loft-insulation"
    ).json()
    today_before = base["scenarios"][0]["annual_cost_gbp"]
    today_after = with_plan["scenarios"][0]["annual_cost_after_gbp"]
    assert today_after is not None
    assert today_after <= today_before


def test_income_band_never_logged(client, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        client.get(f"{API}/studio/homes/demo-coastal-bungalow/affordability")
    for record in caplog.records:
        assert "under_20k" not in record.getMessage()
