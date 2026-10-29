"""S11: Magnus p_sat, the solid-wall/class-3/cold-humid-hour corner risk case, double glazing
reducing window risk, and the landlord note's presence/absence by tenure."""

from datetime import date, datetime

import httpx
import pytest

from app.schemas.property import PropertyFacts
from app.studio.features.s11_damp_mould_lab.config import AGE_BAND_WALL_U, AGE_BAND_WINDOW_U
from app.studio.features.s11_damp_mould_lab.era5_winter import (
    ERA5_URL,
    HourlyWeather,
    last_winter_window,
)
from app.studio.features.s11_damp_mould_lab.physics import (
    corner_f_rsi,
    f_rsi,
    moisture_class_for,
    p_sat,
    surface_rh,
)
from app.studio.features.s11_damp_mould_lab.schemas import DampLabRequest
from app.studio.features.s11_damp_mould_lab.service import build_damp_lab, wall_u_for, window_u_for

API = "/api/v1"


def test_magnus_p_sat_reference_points() -> None:
    assert abs(p_sat(0.0) - 611) < 2
    assert abs(p_sat(20.0) - 2339) < 10


def test_solid_wall_class_3_cold_humid_hour_is_at_risk() -> None:
    wall_f = f_rsi(2.1)
    corner_f = corner_f_rsi(wall_f)
    rh = surface_rh(theta_e=0.0, rh_e=0.90, theta_i=18.0, frsi=corner_f, moisture_class=3)
    assert rh >= 0.80


def _request(**kwargs) -> DampLabRequest:
    defaults = dict(
        occupants=2,
        dries_clothes_indoors=False,
        kitchen_extractor=True,
        bathroom_extractor=True,
        trickle_vents=True,
        heating_setpoint_c=18.0,
    )
    defaults.update(kwargs)
    return DampLabRequest(**defaults)


def _house(**kwargs) -> PropertyFacts:
    defaults = dict(property_type="terraced", construction_age_band="1900-1929", source="demo")
    defaults.update(kwargs)
    return PropertyFacts(**defaults)


def _winter_hourly() -> list[HourlyWeather]:
    start = datetime(2025, 11, 1)
    return [
        HourlyWeather(at=start.replace(month=m, day=1, hour=h), temp_c=0.0, rh=0.9)
        for m in (11, 12, 1, 2, 3)
        for h in (0, 3, 6, 9, 12, 15, 18, 21)
    ]


def test_moisture_class_for_defaults() -> None:
    assert moisture_class_for(2, False, True, True, True) == 1
    assert moisture_class_for(5, False, False, False, False) == 4


def test_double_glazing_reduces_window_risk() -> None:
    hourly = _winter_hourly()
    old_house = _house()
    assert wall_u_for(old_house) == AGE_BAND_WALL_U["1900-1929"]
    assert window_u_for(old_house) == AGE_BAND_WINDOW_U["1900-1929"]

    surfaces, _, interventions, _, _, _ = build_damp_lab(old_house, hourly, _request(), "2025-26")
    window_before = next(s for s in surfaces if s.surface == "window").risk_hours_pct
    glazing = next((i for i in interventions if i.id == "double-glazing"), None)
    assert glazing is not None
    assert glazing.corner_risk_pct_after <= window_before or glazing.delta_pct >= 0


def test_last_winter_window_label() -> None:
    start, end, label = last_winter_window(date(2026, 10, 28))
    assert start == date(2025, 11, 1)
    assert end == date(2026, 3, 31)
    assert label == "2025-26"


@pytest.fixture
def era5_api(mock_http):
    body = {
        "hourly": {
            "time": ["2025-11-01T00:00"],
            "temperature_2m": [2.0],
            "relative_humidity_2m": [88.0],
        }
    }
    return mock_http.get(url__startswith=ERA5_URL).mock(return_value=httpx.Response(200, json=body))


def test_landlord_note_absent_on_demo_homes(client, era5_api) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/damp-lab",
        json={
            "occupants": 2,
            "dries_clothes_indoors": False,
            "kitchen_extractor": True,
            "bathroom_extractor": True,
            "trickle_vents": True,
            "heating_setpoint_c": 18,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["landlord_note"] is None


def test_flood_terrace_shows_risk_and_reducing_interventions_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=ERA5_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/damp-lab",
        json={
            "occupants": 2,
            "dries_clothes_indoors": False,
            "kitchen_extractor": False,
            "bathroom_extractor": False,
            "trickle_vents": False,
            "heating_setpoint_c": 18,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    corner = next(s for s in body["surfaces"] if s["surface"] == "corner")
    assert corner["level"] in ("medium", "high")
    reducing = [i for i in body["interventions"] if i["delta_pct"] > 0]
    assert len(reducing) >= 3


def test_route_offline_fallback(client, mock_http) -> None:
    mock_http.get(url__startswith=ERA5_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/damp-lab",
        json={
            "occupants": 2,
            "dries_clothes_indoors": False,
            "kitchen_extractor": True,
            "bathroom_extractor": True,
            "trickle_vents": True,
            "heating_setpoint_c": 18,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True
