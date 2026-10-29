"""S12: DAQI banding against the DEFRA table, null pollen -> none, sensitivity changes
scores, the request body is never logged, and the offline fallback."""

import logging
from datetime import datetime

import httpx
import pytest

from app.studio.features.s12_breathe_easy.config import AIR_QUALITY_URL, FORECAST_URL
from app.studio.features.s12_breathe_easy.scoring import (
    daqi_band,
    daqi_for,
    pollen_level,
    score_for,
)

API = "/api/v1"


def test_daqi_banding_against_defra_table() -> None:
    assert daqi_for(pm2_5=5, pm10=None, no2=None, o3=None) == 1
    assert daqi_for(pm2_5=40, pm10=None, no2=None, o3=None) == 4
    assert daqi_for(pm2_5=56, pm10=None, no2=None, o3=None) == 7
    assert daqi_for(pm2_5=80, pm10=None, no2=None, o3=None) == 10
    assert daqi_band(1) == "low"
    assert daqi_band(4) == "moderate"
    assert daqi_band(7) == "high"
    assert daqi_band(10) == "very_high"
    assert daqi_for(pm2_5=None, pm10=None, no2=None, o3=None) is None


def test_null_pollen_is_none() -> None:
    assert pollen_level(None) is None
    assert pollen_level(0) == "none"
    assert pollen_level(20) == "low"
    assert pollen_level(200) == "high"


def test_sensitivity_lowers_score() -> None:
    at = datetime(2026, 1, 15, 12, 0)
    base = score_for(
        at=at,
        daqi_band_value="high",
        pollen_level_value=None,
        temp_c=10,
        dew_point_c=10,
        pollution_sensitive=False,
        pollen_sensitive=False,
    )
    sensitive = score_for(
        at=at,
        daqi_band_value="high",
        pollen_level_value=None,
        temp_c=10,
        dew_point_c=10,
        pollution_sensitive=True,
        pollen_sensitive=False,
    )
    assert sensitive < base


@pytest.fixture
def open_meteo_apis(mock_http):
    aq_body = {
        "hourly": {
            "time": ["2026-10-29T00:00", "2026-10-29T01:00"],
            "pm2_5": [5.0, 6.0],
            "pm10": [10.0, 11.0],
            "nitrogen_dioxide": [20.0, 21.0],
            "ozone": [30.0, 31.0],
            "grass_pollen": [None, None],
            "birch_pollen": [None, None],
            "alder_pollen": [None, None],
        }
    }
    wx_body = {
        "hourly": {
            "time": ["2026-10-29T00:00", "2026-10-29T01:00"],
            "temperature_2m": [10.0, 9.0],
            "relative_humidity_2m": [80.0, 82.0],
            "dew_point_2m": [6.0, 5.5],
            "wind_speed_10m": [10.0, 12.0],
        }
    }
    mock_http.get(url__startswith=AIR_QUALITY_URL).mock(
        return_value=httpx.Response(200, json=aq_body)
    )
    mock_http.get(url__startswith=FORECAST_URL).mock(return_value=httpx.Response(200, json=wx_body))


def test_route_returns_ribbon_with_best_window(client, open_meteo_apis) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/breathe-easy",
        json={"pollen_sensitive": False, "pollution_sensitive": False},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["hours"]) >= 1
    assert body["hours"][0]["pollen_level"] is None


def test_request_body_is_never_logged(client, open_meteo_apis, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        client.post(
            f"{API}/studio/homes/demo-flood-terrace/breathe-easy",
            json={"pollen_sensitive": True, "pollution_sensitive": True},
        )
    for record in caplog.records:
        assert "pollen_sensitive" not in record.getMessage()
        assert "pollution_sensitive" not in record.getMessage()


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=AIR_QUALITY_URL).mock(side_effect=httpx.ConnectError("offline"))
    mock_http.get(url__startswith=FORECAST_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.post(
        f"{API}/studio/homes/demo-flood-terrace/breathe-easy",
        json={"pollen_sensitive": False, "pollution_sensitive": False},
    )
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True
