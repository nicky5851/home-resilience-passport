"""GeoJSON Polygon/MultiPolygon helpers: holes and multi-polygons, on top of the pure
point-in-polygon and distance primitives in `studio/common/geo.py`."""

from app.studio.common.geo import Point, point_in_polygon, point_to_polygon_distance_m


def rings_from_geometry(geometry: dict) -> list[list[Point]]:
    """Every ring (exterior + holes, across every polygon of a MultiPolygon) as (lat, lon)
    point lists."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = coords if gtype == "MultiPolygon" else [coords]
    rings = []
    for polygon in polygons:
        for ring in polygon:
            rings.append([(lat, lon) for lon, lat in ring])
    return rings


def exterior_rings_from_geometry(geometry: dict) -> list[list[Point]]:
    """Just the outer ring of each polygon (index 0), for simplification/display."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = coords if gtype == "MultiPolygon" else [coords]
    return [[(lat, lon) for lon, lat in polygon[0]] for polygon in polygons if polygon]


def contains_point(geometry: dict, point: Point) -> bool:
    """True if `point` is inside any polygon's exterior and not inside any of its holes."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = coords if gtype == "MultiPolygon" else [coords]
    for polygon in polygons:
        if not polygon:
            continue
        exterior = [(lat, lon) for lon, lat in polygon[0]]
        if not point_in_polygon(point, exterior):
            continue
        in_hole = any(
            point_in_polygon(point, [(lat, lon) for lon, lat in hole]) for hole in polygon[1:]
        )
        if not in_hole:
            return True
    return False


def distance_to_geometry_m(geometry: dict, point: Point) -> float:
    rings = rings_from_geometry(geometry)
    if not rings:
        return float("inf")
    return min(point_to_polygon_distance_m(point, ring) for ring in rings)
