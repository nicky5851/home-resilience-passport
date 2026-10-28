"""S05: roof-area estimator, PVGIS response parsing, flat suitability, rose scaling, payback
edge cases, and the route (mocked PVGIS, then offline)."""

import httpx
import pytest

from app.schemas.property import PropertyFacts
from app.studio.features.s05_solar_roof_studio.config import PVGIS_URL
from app.studio.features.s05_solar_roof_studio.pvgis import pvcalc
from app.studio.features.s05_solar_roof_studio.service import (
    build_solar,
    estimate_kwp_from_roof,
    suitability_for,
)

API = "/api/v1"
pytestmark = pytest.mark.anyio


def _prop(**kwargs) -> PropertyFacts:
    defaults = {"property_type": "detached", "built_form": "Detached", "source": "demo"}
    defaults.update(kwargs)
    return PropertyFacts(**defaults)


def test_flats_get_no_roof_estimate() -> None:
    assert estimate_kwp_from_roof(_prop(property_type="flat")) is None


def test_houses_get_a_capped_roof_estimate() -> None:
    kwp = estimate_kwp_from_roof(_prop(floor_area_m2=400, property_type="detached"))
    assert kwp is not None
    assert kwp <= 6.0


def test_suitability_bands() -> None:
    assert suitability_for(1000, is_flat=False) == (
        "good",
        "This orientation and pitch generate well above the UK typical range.",
    )
    assert suitability_for(800, is_flat=False)[0] == "fair"
    assert suitability_for(500, is_flat=False)[0] == "poor"
    assert suitability_for(1000, is_flat=True)[0] == "freeholder_needed"


def _pvgis_response(annual_per_month: float) -> dict:
    return {"outputs": {"monthly": {"fixed": [{"E_m": annual_per_month} for _ in range(12)]}}}


async def test_pvgis_response_parses_into_annual_and_monthly(mock_http, memory_cache) -> None:
    mock_http.get(url__startswith=PVGIS_URL).mock(
        return_value=httpx.Response(200, json=_pvgis_response(80))
    )
    result = await pvcalc(51.5, -0.1, kwp=2.0, pitch_deg=35, aspect_deg=0, cache=memory_cache)
    assert result["annual_kwh"] == round(80 * 12 * 2.0)
    assert len(result["monthly_kwh"]) == 12
    assert result["monthly_kwh"][0] == round(80 * 2.0)


async def test_rose_scales_linearly_with_kwp(mock_http, memory_cache) -> None:
    mock_http.get(url__startswith=PVGIS_URL).mock(
        return_value=httpx.Response(200, json=_pvgis_response(100))
    )
    small = await pvcalc(51.5, -0.1, kwp=1.0, pitch_deg=35, aspect_deg=0, cache=memory_cache)
    large = await pvcalc(51.5, -0.1, kwp=3.0, pitch_deg=35, aspect_deg=0, cache=memory_cache)
    assert large["annual_kwh"] == pytest.approx(small["annual_kwh"] * 3, rel=0.01)


async def test_payback_is_null_when_saving_is_zero(mock_http, memory_cache) -> None:
    mock_http.get(url__startswith=PVGIS_URL).mock(
        return_value=httpx.Response(200, json=_pvgis_response(0))
    )
    result = await build_solar(
        _prop(floor_area_m2=100), 51.5, -0.1, 0, 35, None, 0, 0.0, memory_cache
    )
    assert result.annual_saving_gbp == 0
    assert result.payback_years is None
    assert result.breakeven_year is None


@pytest.fixture
def pvgis_working(mock_http):
    return mock_http.get(url__startswith=PVGIS_URL).mock(
        return_value=httpx.Response(200, json=_pvgis_response(90))
    )


def test_route_demo_home_solar(client, pvgis_working) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-clay-semi/solar",
        json={"aspect_deg": 0, "pitch_deg": 35},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["kwp_source"] == "estimated_from_roof"
    assert len(body["orientation_rose"]) == 8
    assert body["fallback_used"] is False


def test_route_flat_needs_freeholder_permission(client, pvgis_working) -> None:
    res = client.post(f"{API}/studio/homes/demo-city-top-flat/solar", json={})
    assert res.status_code == 200, res.text
    assert res.json()["suitability"] == "freeholder_needed"


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=PVGIS_URL).mock(side_effect=httpx.ConnectError("offline"))
    res = client.post(f"{API}/studio/homes/demo-clay-semi/solar", json={})
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True


def test_route_clamps_out_of_range_angles(client, pvgis_working) -> None:
    res = client.post(
        f"{API}/studio/homes/demo-clay-semi/solar",
        json={"aspect_deg": 999, "pitch_deg": -50},
    )
    assert res.status_code == 200, res.text
