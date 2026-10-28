"""S06: window search on a hand-made series, outcode extraction, a Welsh postcode mapping to
a Wales region, and the route (mocked Carbon Intensity API, then offline)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.studio.features.s06_grid_carbon_clock.carbon_intensity import (
    CARBON_INTENSITY_BASE,
    outcode_from_postcode,
)
from app.studio.features.s06_grid_carbon_clock.schemas import ForecastSlot
from app.studio.features.s06_grid_carbon_clock.service import best_window, greenest_and_dirtiest

API = "/api/v1"


def test_outcode_extraction() -> None:
    assert outcode_from_postcode("SW1A 1AA") == "SW1A"
    assert outcode_from_postcode("CF10 1EP") == "CF10"


def _slots(intensities: list[int], start: datetime) -> list[ForecastSlot]:
    return [
        ForecastSlot(
            from_at=start + timedelta(minutes=30 * i),
            to_at=start + timedelta(minutes=30 * (i + 1)),
            intensity_g_per_kwh=v,
            index="moderate",
        )
        for i, v in enumerate(intensities)
    ]


def test_window_search_finds_the_lowest_mean_window() -> None:
    start = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)
    # washing machine needs 4 slots; the cheapest 4-slot run is indices 6-9 (all 50)
    intensities = [200, 200, 200, 200, 200, 200, 50, 50, 50, 50, 200, 200]
    slots = _slots(intensities, start)
    w = best_window(slots, "washing_machine", now_intensity=200)
    assert w is not None
    assert w.avg_intensity_g_per_kwh == 50.0
    assert w.start_at == start + timedelta(hours=3)
    assert w.saving_pct_vs_now == 75.0


def test_window_search_returns_none_when_series_too_short() -> None:
    start = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)
    slots = _slots([100, 100], start)
    assert best_window(slots, "ev_charge", now_intensity=100) is None


def test_greenest_and_dirtiest_slots() -> None:
    start = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)
    slots = _slots([100, 20, 300, 150], start)
    greenest, dirtiest = greenest_and_dirtiest(slots)
    assert greenest.intensity_g_per_kwh == 20
    assert dirtiest.intensity_g_per_kwh == 300


def _region_response(shortname: str, postcode: str, intensities: list[int]) -> dict:
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    periods = [
        {
            "from": (now + timedelta(minutes=30 * i)).strftime("%Y-%m-%dT%H:%MZ"),
            "to": (now + timedelta(minutes=30 * (i + 1))).strftime("%Y-%m-%dT%H:%MZ"),
            "intensity": {"forecast": v, "index": "moderate"},
            "generationmix": [{"fuel": "gas", "perc": 100.0}],
        }
        for i, v in enumerate(intensities)
    ]
    return {
        "regionid": 1,
        "dnoregion": "test",
        "shortname": shortname,
        "postcode": postcode,
        "data": periods,
    }


@pytest.fixture
def carbon_intensity_api(mock_http):
    current_body = {"data": [_region_response("Wales", "CF10", [120])]}
    forecast_body = {"data": _region_response("Wales", "CF10", [120] * 96)}
    mock_http.get(url__regex=rf"{CARBON_INTENSITY_BASE}/regional/postcode/.*").mock(
        return_value=httpx.Response(200, json=current_body)
    )
    mock_http.get(url__regex=rf"{CARBON_INTENSITY_BASE}/regional/intensity/.*").mock(
        return_value=httpx.Response(200, json=forecast_body)
    )


def test_route_welsh_postcode_maps_to_wales_region(client, carbon_intensity_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-coastal-bungalow/grid-carbon")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["region_name"] == "Wales"
    assert len(body["best_windows"]) >= 4
    assert body["fallback_used"] is False


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__regex=rf"{CARBON_INTENSITY_BASE}/.*").mock(
        side_effect=httpx.ConnectError("offline")
    )
    res = client.get(f"{API}/studio/homes/demo-rural-cottage/grid-carbon")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["fallback_used"] is True
    assert len(body["forecast"]) == 96
