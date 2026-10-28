"""S04: COP bounds/defrost, exact demand at a constant outdoor temperature, size rounding,
flow-temp switch, flat form factor, and the route (mocked ERA5, then offline)."""

import math
from datetime import datetime, timedelta

import httpx
import pytest

from app.studio.features.s04_heat_pump_year.config import (
    COP_MAX,
    COP_MIN,
    DAY_START_HOUR,
    INTERNAL_GAIN_K,
    SIZE_STEPS_KW,
    T_SET_DAY_C,
    T_SET_NIGHT_C,
)
from app.studio.features.s04_heat_pump_year.era5_hourly import ERA5_URL
from app.studio.features.s04_heat_pump_year.service import form_factor_for
from app.studio.features.s04_heat_pump_year.sim import cop_for, demand_kw, recommended_kw

API = "/api/v1"


def test_cop_is_clipped_to_bounds() -> None:
    assert cop_for(t_out_c=19.9, flow_temp_c=35) <= COP_MAX
    assert cop_for(t_out_c=-30, flow_temp_c=55) >= COP_MIN


def _raw_cop(t_out_c: float, flow_temp_c: int) -> float:
    t_flow_k, t_out_k = flow_temp_c + 273.15, t_out_c + 273.15
    return 0.45 * t_flow_k / (t_flow_k - t_out_k)


def test_defrost_penalty_applies_between_minus_two_and_five_degrees() -> None:
    raw = _raw_cop(0.0, 45)
    assert cop_for(t_out_c=0.0, flow_temp_c=45) == pytest.approx(raw * 0.9)

    raw_outside_band = _raw_cop(10.0, 45)
    assert cop_for(t_out_c=10.0, flow_temp_c=45) == pytest.approx(raw_outside_band)


def test_constant_outdoor_temp_gives_exact_demand() -> None:
    htc = 300.0
    day_demand = demand_kw(htc, t_out_c=-2.0, hour=12)
    night_demand = demand_kw(htc, t_out_c=-2.0, hour=23)
    assert day_demand == pytest.approx(htc * (T_SET_DAY_C - (-2.0) - INTERNAL_GAIN_K) / 1000)
    assert night_demand == pytest.approx(htc * (T_SET_NIGHT_C - (-2.0) - INTERNAL_GAIN_K) / 1000)
    assert day_demand > night_demand


def test_demand_is_zero_when_outdoor_temp_meets_setpoint() -> None:
    assert demand_kw(300.0, t_out_c=T_SET_DAY_C, hour=DAY_START_HOUR) == 0.0


def test_size_rounds_up_to_the_next_step() -> None:
    # needed = htc * 23 / 1000; pick an htc that lands just above a step
    htc = (SIZE_STEPS_KW[2] - 0.1) * 1000 / 23
    assert recommended_kw(htc) == SIZE_STEPS_KW[2]


def test_size_never_exceeds_the_largest_step() -> None:
    assert recommended_kw(100_000.0) == SIZE_STEPS_KW[-1]


def test_flat_gets_a_lower_form_factor() -> None:
    from app.schemas.property import PropertyFacts

    flat = PropertyFacts(property_type="flat", built_form=None, source="demo")
    detached = PropertyFacts(property_type="detached", built_form="Detached", source="demo")
    assert form_factor_for(flat) == 0.7
    assert form_factor_for(detached) == 1.0


def _era5_hourly_response(year: int) -> dict:
    start = datetime(year, 1, 1)
    hours = 365 * 24
    times, temps = [], []
    for h in range(hours):
        at = start + timedelta(hours=h)
        t = 8.0 - 6.0 * math.cos(2 * math.pi * h / (24 * 365))
        times.append(at.strftime("%Y-%m-%dT%H:%M"))
        temps.append(round(t, 1))
    return {"hourly": {"time": times, "temperature_2m": temps}}


@pytest.fixture
def era5_hourly(mock_http):
    from app.studio.features.s04_heat_pump_year.era5_hourly import last_full_year

    year = last_full_year()
    return mock_http.get(url__startswith=ERA5_URL).mock(
        return_value=httpx.Response(200, json=_era5_hourly_response(year))
    )


def test_route_demo_home_heat_pump_year(client, era5_hourly) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-rural-cottage/heat-pump-year",
        json={"flow_temp_c": 45},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert 2.0 <= body["scop"] <= 5.0
    assert len(body["monthly"]) == 12
    assert body["fallback_used"] is False
    assert body["htc_source"] == "estimated_from_age_band"


def test_route_flow_temp_changes_the_result(client, era5_hourly) -> None:
    low = client.post(
        f"{API}/studio/homes/demo-rural-cottage/heat-pump-year", json={"flow_temp_c": 35}
    ).json()
    high = client.post(
        f"{API}/studio/homes/demo-rural-cottage/heat-pump-year", json={"flow_temp_c": 55}
    ).json()
    assert low["scop"] > high["scop"]


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=ERA5_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.post(f"{API}/studio/homes/demo-rural-cottage/heat-pump-year", json={})
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True


def test_route_unknown_uuid_requires_login(client) -> None:
    import uuid

    res = client.post(
        f"{API}/studio/homes/{uuid.uuid4()}/heat-pump-year",
        json={},
    )
    assert res.status_code == 401
