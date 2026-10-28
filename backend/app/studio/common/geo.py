"""Pure geometry helpers shared by Studio features (docs/studio/N_20_function.md §1.2)."""

import math

Point = tuple[float, float]  # (lat, lon)

_EARTH_RADIUS_M = 6_371_000


def haversine_m(a: Point, b: Point) -> float:
    """Great-circle distance in metres between two (lat, lon) points."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    """Ray-casting test; `polygon` is a list of (lat, lon) vertices, open (no repeated first)."""
    x, y = point[1], point[0]
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i][1], polygon[i][0]
        x2, y2 = polygon[(i + 1) % n][1], polygon[(i + 1) % n][0]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
    return inside


def bbox(points: list[Point]) -> tuple[Point, Point]:
    """(south_west, north_east) corners containing every point."""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return (min(lats), min(lons)), (max(lats), max(lons))


def _perp_distance(point: Point, start: Point, end: Point) -> float:
    if start == end:
        return haversine_m(point, start)
    x, y = point
    x1, y1 = start
    x2, y2 = end
    num = abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1))
    den = math.hypot(x2 - x1, y2 - y1)
    return num / den if den else 0.0


def _point_to_segment_m(point: Point, a: Point, b: Point) -> float:
    """Distance from `point` to segment a-b, metres, via an equirectangular projection around
    `point` (accurate to metres at the scales these features use)."""
    lat0 = math.radians(point[0])
    kx, ky = math.cos(lat0) * _EARTH_RADIUS_M, _EARTH_RADIUS_M

    def to_xy(p: Point) -> tuple[float, float]:
        return (math.radians(p[1] - point[1]) * kx, math.radians(p[0] - point[0]) * ky)

    px, py = 0.0, 0.0
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def point_to_polygon_distance_m(point: Point, polygon: list[Point]) -> float:
    """Minimum distance from `point` to any edge of `polygon` (open ring, no repeated first)."""
    n = len(polygon)
    return min(
        _point_to_segment_m(point, polygon[i], polygon[(i + 1) % n]) for i in range(n)
    )


def douglas_peucker(points: list[Point], epsilon: float) -> list[Point]:
    """Simplify a line/outline to fewer points within tolerance `epsilon` (degrees)."""
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    max_dist, max_idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perp_distance(points[i], start, end)
        if d > max_dist:
            max_dist, max_idx = d, i
    if max_dist > epsilon:
        left = douglas_peucker(points[: max_idx + 1], epsilon)
        right = douglas_peucker(points[max_idx:], epsilon)
        return left[:-1] + right
    return [start, end]
