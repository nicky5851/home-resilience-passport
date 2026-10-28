"""S07: severity ranking on a hand-made series, the indoor model's step-response convergence
and shading effect, unknown event -> 404, and the route (mocked ERA5, then offline)."""

from datetime import datetime, timedelta

import httpx
import pytest

from app.schemas.property import PropertyFacts
from app.studio.features.s07_storm_replay.era5_event import ERA5_URL, HourlyWeather
from app.studio.features.s07_storm_replay.service import summarise_event, tau_for
from app.studio.features.s07_storm_replay.sim import (
    heat_severity,
    max_24h_rolling_rain,
    rain_severity,
    simulate_indoor,
    wind_severity,
)

API = "/api/v1"


def _hours(n: int, temp_c: float = 10.0) -> list[HourlyWeather]:
    start = datetime(2026, 1, 1)
    return [HourlyWeather(start + timedelta(hours=i), temp_c, 0.0, 0.0, 0.0) for i in range(n)]


def test_wind_rain_heat_severity_rank_correctly() -> None:
    assert wind_severity(120) == 1.0
    assert wind_severity(60) == 0.5
    assert rain_severity(30) == 0.5
    assert heat_severity(25) == 0.0
    assert heat_severity(40) == 1.0


def test_max_24h_rolling_rain_finds_the_worst_window() -> None:
    hours = _hours(48)
    for i in range(10, 20):
        hours[i] = HourlyWeather(hours[i].at, 10.0, 0.0, 0.0, 5.0)
    assert max_24h_rolling_rain(hours) == pytest.approx(50.0)


def test_indoor_model_converges_to_outdoor_temp_with_tau() -> None:
    start = datetime(2026, 1, 1, 2, 0)  # fixed at hour 2 every step: never in the solar window
    hourly = [HourlyWeather(start + timedelta(days=i), 5.0, 0, 0, 0) for i in range(200)]
    indoor = simulate_indoor(
        hourly,
        tau_hours=18.0,
        is_top_floor_flat=False,
        shading=False,
        night_vent=False,
        start_indoor_c=22.0,
    )
    assert indoor[-1] == pytest.approx(5.0, abs=0.1)
    assert indoor[0] > indoor[-1]


def test_shading_reduces_the_daytime_peak() -> None:
    start = datetime(2026, 7, 19, 10, 0)  # inside the 10:00-18:00 solar window throughout
    hourly = [HourlyWeather(start + timedelta(hours=i), 30.0, 0, 0, 0) for i in range(8)]
    no_measures = simulate_indoor(hourly, 18.0, False, shading=False, night_vent=False)
    with_measures = simulate_indoor(hourly, 18.0, False, shading=True, night_vent=False)
    assert max(with_measures) < max(no_measures)


def test_tau_for_construction_heuristic() -> None:
    old_house = PropertyFacts(
        property_type="detached", construction_age_band="before 1900", source="demo"
    )
    flat = PropertyFacts(property_type="flat", source="demo")
    modern_semi = PropertyFacts(
        property_type="semi_detached", construction_age_band="1996-2002", source="demo"
    )
    assert tau_for(old_house) == 30.0
    assert tau_for(flat) == 10.0
    assert tau_for(modern_semi) == 18.0


def test_summarise_event_wind() -> None:
    event = {
        "id": "x",
        "name": "Test Storm",
        "kind": "wind",
        "start_date": datetime(2026, 1, 1).date(),
        "end_date": datetime(2026, 1, 2).date(),
    }
    hours = [
        HourlyWeather(datetime(2026, 1, 1, h), 8.0, gust, 10.0, 0.0)
        for h, gust in enumerate([40, 90, 50])
    ]
    summary = summarise_event(event, hours)
    assert summary.local_peak.value == 90
    assert summary.severity == pytest.approx(0.75)


def _era5_body(hours: int) -> dict:
    start = datetime(2026, 1, 1)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "hourly": {
            "time": times,
            "temperature_2m": [8.0] * hours,
            "wind_gusts_10m": [50.0] * hours,
            "wind_speed_10m": [20.0] * hours,
            "precipitation": [0.0] * hours,
        }
    }


@pytest.fixture
def era5_event_api(mock_http):
    return mock_http.get(url__startswith=ERA5_URL).mock(
        return_value=httpx.Response(200, json=_era5_body(96))
    )


def test_route_index_returns_hardest_event(client, era5_event_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/storm-replay")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["events"]) == 8
    assert body["hardest_event_id"] in {e["id"] for e in body["events"]}


def test_route_unknown_event_id_404(client, era5_event_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/storm-replay/not-a-real-event")
    assert res.status_code == 404, res.text


def test_route_replay_for_a_known_event(client, era5_event_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/storm-replay/storm-eunice-2022")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["event"]["id"] == "storm-eunice-2022"
    assert len(body["hourly"]) > 0


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=ERA5_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/storm-replay/storm-eunice-2022")
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True
