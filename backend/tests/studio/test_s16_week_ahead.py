"""S16: threshold boundaries, top-floor and flood-risk tailoring, missing variable -> null and
skipped, offline, and a recorded windy week for demo-rural-cottage."""

import httpx
import pytest

from app.studio.features.s16_week_ahead.config import FORECAST_URL
from app.studio.features.s16_week_ahead.rules import (
    frost_alert,
    glyph_for,
    heat_alert,
    rain_alert,
    wind_alert,
)

API = "/api/v1"


def test_frost_alert_boundaries() -> None:
    assert frost_alert(0.1, "Monday") is None
    assert frost_alert(0.0, "Monday").kind == "frost"
    assert frost_alert(-3.0, "Monday").kind == "hard_frost"
    assert frost_alert(None, "Monday") is None


def test_heat_alert_top_floor_gets_high_at_27() -> None:
    assert heat_alert(26.9, top_floor=True, when="Monday") is None
    normal = heat_alert(27.0, top_floor=False, when="Monday")
    assert normal.level == "medium"
    top_floor = heat_alert(27.0, top_floor=True, when="Monday")
    assert top_floor.level == "high"


def test_wind_alert_high_threshold_at_60_for_storm_high_homes() -> None:
    normal = wind_alert(65.0, high_threshold_at_60=False, when="Monday")
    assert normal.level == "medium"
    storm_home = wind_alert(65.0, high_threshold_at_60=True, when="Monday")
    assert storm_home.level == "high"
    assert wind_alert(59.9, high_threshold_at_60=True, when="Monday") is None


def test_rain_alert_adds_flood_warning_link_for_flood_risk_homes() -> None:
    plain = rain_alert(20.0, flood_risk=False, when="Monday")
    assert all("Environment Agency" not in a for a in plain.actions)
    flood = rain_alert(20.0, flood_risk=True, when="Monday")
    assert any("Environment Agency" in a for a in flood.actions)


def test_glyph_prefers_storm_then_frost_then_wind() -> None:
    assert glyph_for(10, 5, 20, 70) == "storm"
    assert glyph_for(5, -1, 0, 0) == "frost"
    assert glyph_for(15, 10, 0, 65) == "wind"
    assert glyph_for(15, 10, 35, 0) == "heavy_rain"
    assert glyph_for(15, 10, 0, 0) == "cloud"


def test_missing_variable_gives_null_and_skips_the_rule(client, mock_http) -> None:
    body = {
        "daily": {
            "time": ["2026-11-01"],
            "temperature_2m_max_ukmo_seamless": [None],
            "temperature_2m_min_ukmo_seamless": [None],
            "precipitation_sum_ukmo_seamless": [None],
            "wind_gusts_10m_max_ukmo_seamless": [None],
            "uv_index_max_ukmo_seamless": [None],
            "temperature_2m_max_best_match": [None],
            "temperature_2m_min_best_match": [None],
            "precipitation_sum_best_match": [None],
            "wind_gusts_10m_max_best_match": [None],
            "uv_index_max_best_match": [None],
        }
    }
    mock_http.get(url__startswith=FORECAST_URL).mock(return_value=httpx.Response(200, json=body))
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/week-ahead")
    assert res.status_code == 200, res.text
    day = res.json()["days"][0]
    assert day["t_max_c"] is None
    assert day["alerts"] == []


def test_route_offline_falls_back(client, mock_http) -> None:
    mock_http.get(url__startswith=FORECAST_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/week-ahead")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["fallback_used"] is True
    assert len(body["days"]) == 7


def _mock_daily(mock_http, **overrides) -> None:
    days = 7
    base = {
        "time": [f"2026-11-0{i + 1}" for i in range(days)],
        "temperature_2m_max_ukmo_seamless": [12.0] * days,
        "temperature_2m_min_ukmo_seamless": [5.0] * days,
        "precipitation_sum_ukmo_seamless": [0.0] * days,
        "wind_gusts_10m_max_ukmo_seamless": [20.0] * days,
        "uv_index_max_ukmo_seamless": [1.0] * days,
        "temperature_2m_max_best_match": [12.0] * days,
        "temperature_2m_min_best_match": [5.0] * days,
        "precipitation_sum_best_match": [0.0] * days,
        "wind_gusts_10m_max_best_match": [20.0] * days,
        "uv_index_max_best_match": [1.0] * days,
    }
    base.update(overrides)
    mock_http.get(url__startswith=FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"daily": base})
    )


def test_acceptance_recorded_windy_week_gives_rural_cottage_a_high_wind_alert(
    client, mock_http
) -> None:
    _mock_daily(mock_http, wind_gusts_10m_max_ukmo_seamless=[90.0] * 7)
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/week-ahead")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["days"]) == 7
    kinds = {a["kind"] for d in body["days"] for a in d["alerts"]}
    assert "strong_wind" in kinds


@pytest.mark.parametrize("ref", ["demo-flood-terrace", "demo-clay-semi", "demo-coastal-bungalow"])
def test_all_demo_homes_show_seven_days(client, mock_http, ref) -> None:
    _mock_daily(mock_http)
    res = client.get(f"{API}/studio/homes/{ref}/week-ahead")
    assert res.status_code == 200, res.text
    assert len(res.json()["days"]) == 7
