"""S08: point-in-polygon with holes and MultiPolygon, zero distance inside, simplification
keeps the ring closed, decade grouping, empty result, and the route (mocked EA API, then
Welsh/offline fallbacks)."""

import httpx
import pytest

from app.studio.common.geo import douglas_peucker
from app.studio.features.s08_flood_memory.config import EA_BASE
from app.studio.features.s08_flood_memory.geojson import contains_point, distance_to_geometry_m
from app.studio.features.s08_flood_memory.service import build_flood_memory

API = "/api/v1"


def _square(lon_lat_pairs: list[tuple[float, float]]) -> list[list[float]]:
    return [list(p) for p in lon_lat_pairs]


def test_point_inside_a_simple_polygon() -> None:
    square = _square([(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)])
    geometry = {"type": "Polygon", "coordinates": [square]}
    assert contains_point(geometry, (0, 0)) is True
    assert contains_point(geometry, (5, 5)) is False


def test_point_inside_a_hole_is_excluded() -> None:
    exterior = _square([(-10, -10), (-10, 10), (10, 10), (10, -10), (-10, -10)])
    hole = _square([(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)])
    geometry = {"type": "Polygon", "coordinates": [exterior, hole]}
    assert contains_point(geometry, (0, 0)) is False
    assert contains_point(geometry, (5, 5)) is True


def test_point_inside_either_part_of_a_multipolygon() -> None:
    square_a = _square([(-10, -10), (-10, -8), (-8, -8), (-8, -10), (-10, -10)])
    square_b = _square([(8, 8), (8, 10), (10, 10), (10, 8), (8, 8)])
    geometry = {"type": "MultiPolygon", "coordinates": [[square_a], [square_b]]}
    assert contains_point(geometry, (-9, -9)) is True
    assert contains_point(geometry, (9, 9)) is True
    assert contains_point(geometry, (0, 0)) is False


def test_distance_is_zero_when_point_is_on_the_edge() -> None:
    square = _square([(-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)])
    geometry = {"type": "Polygon", "coordinates": [square]}
    assert distance_to_geometry_m(geometry, (0, -1)) == pytest.approx(0.0, abs=1.0)


def test_douglas_peucker_keeps_the_ring_closed() -> None:
    ring = [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
    simplified = douglas_peucker(ring, epsilon=0.3)
    assert simplified[0] == simplified[-1]
    assert len(simplified) <= len(ring)


def _feature(name: str, start: str, lon: float, lat: float) -> dict:
    size = 0.001
    square = [
        [lon - size, lat - size],
        [lon - size, lat + size],
        [lon + size, lat + size],
        [lon + size, lat - size],
        [lon - size, lat - size],
    ]
    return {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[square]]},
        "properties": {
            "name": name,
            "start_date": start,
            "end_date": start,
            "flood_src": "river",
            "data_src": "EA",
        },
    }


def test_decade_grouping_and_distance() -> None:
    home = (51.5, -0.1)
    features = [
        _feature("Event A", "2000-10-30T00:00:00Z", -0.1, 51.5),
        _feature("Event B", "1995-01-01T00:00:00Z", -0.15, 51.55),
    ]
    result = build_flood_memory(features, home)
    assert result.inside_any_outline is True
    assert result.nearest_m == 0
    decades = {d.decade for d in result.by_decade}
    assert decades == {2000, 1990}


def test_empty_result_when_no_features() -> None:
    result = build_flood_memory([], (51.5, -0.1))
    assert result.events == []
    assert result.inside_any_outline is False
    assert result.nearest_m is None


@pytest.fixture
def ea_flood_api(mock_http):
    body = {
        "features": [
            _feature("Winter Flood", "2000-10-30T00:00:00Z", -0.1, 51.5),
        ]
    }
    return mock_http.get(url__startswith=EA_BASE).mock(return_value=httpx.Response(200, json=body))


def test_route_demo_flood_terrace(client, ea_flood_api) -> None:
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/flood-memory")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["events"]) >= 1
    assert "Not every flood" in body["caveat"]


def test_route_falls_back_offline(client, mock_http) -> None:
    mock_http.get(url__startswith=EA_BASE).mock(side_effect=httpx.ConnectError("offline"))
    res = client.get(f"{API}/studio/homes/demo-flood-terrace/flood-memory")
    assert res.status_code == 200, res.text
    assert res.json()["fallback_used"] is True
