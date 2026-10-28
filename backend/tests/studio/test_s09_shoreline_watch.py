"""S09: inland homes get coastal=false with a distance, a recorded coastal response parses
into projections, GeoJSON simplification, and the offline fallback."""

import httpx
import pytest

from app.studio.common.geo import douglas_peucker
from app.studio.features.s09_shoreline_watch.config import COLLECTIONS, NCERM_BASE
from app.studio.features.s09_shoreline_watch.service import build_shoreline, nearest_coast_m

API = "/api/v1"


def test_inland_point_returns_a_positive_distance() -> None:
    birmingham = (52.4862, -1.8904)
    distance = nearest_coast_m(birmingham)
    assert distance > 10_000


def test_inland_home_is_not_coastal_with_no_features() -> None:
    result = build_shoreline((52.4862, -1.8904), {c["collection"]: [] for c in COLLECTIONS})
    assert result.coastal is False
    assert result.nearest_coast_m is not None
    assert result.nearest_coast_m > 10_000


def _zone_feature(lon: float, lat: float, policy: str) -> dict:
    size = 0.01
    square = [
        [lon - size, lat - size, 0],
        [lon - size, lat + size, 0],
        [lon + size, lat + size, 0],
        [lon + size, lat - size, 0],
        [lon - size, lat - size, 0],
    ]
    return {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[square]]},
        "properties": {"smp_name": policy, "mt_smp": "Hold The Line"},
    }


def test_coastal_response_parses_into_projections() -> None:
    home = (50.65, -3.5)
    features_by_collection = {
        c["collection"]: [_zone_feature(-3.5, 50.65, "Durlston Head to Rame Head")]
        for c in COLLECTIONS
    }
    result = build_shoreline(home, features_by_collection)
    assert result.coastal is True
    assert len(result.projections) == 4
    assert all(p.home_inside_zone for p in result.projections)
    assert result.smp_policy == "Durlston Head to Rame Head"


def test_simplification_keeps_the_ring_closed() -> None:
    ring = [(50.0, -3.0), (50.0, -2.5), (50.5, -2.5), (50.5, -3.0), (50.0, -3.0)]
    simplified = douglas_peucker(ring, epsilon=0.3)
    assert simplified[0] == simplified[-1]


@pytest.fixture
def ncerm_api_coastal(mock_http):
    body = {"features": [_zone_feature(-3.5, 50.65, "Test Policy")]}
    return mock_http.get(url__startswith=NCERM_BASE).mock(
        return_value=httpx.Response(200, json=body)
    )


def test_route_coastal_bungalow(client, ncerm_api_coastal) -> None:
    res = client.get(f"{API}/studio/homes/demo-coastal-bungalow/shoreline")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["projections"]) == 4


def test_route_inland_flat(client, ncerm_api_coastal) -> None:
    res = client.get(f"{API}/studio/homes/demo-city-top-flat/shoreline")
    assert res.status_code == 200, res.text
    # all collections mocked to return the coastal-bungalow's zone regardless of bbox,
    # so this only proves the route doesn't error for an inland home
    assert "coastal" in res.json()


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=NCERM_BASE).mock(side_effect=httpx.ConnectError("offline"))
    res = client.get(f"{API}/studio/homes/demo-coastal-bungalow/shoreline")
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True
