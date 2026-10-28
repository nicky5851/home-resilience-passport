from collections import Counter
from datetime import date

from app.studio.common.geo import Point, douglas_peucker
from app.studio.features.s08_flood_memory.config import (
    CAVEAT,
    MAX_EVENTS,
    MAX_OUTLINE_FEATURES,
    SIMPLIFY_TOLERANCE_DEG,
)
from app.studio.features.s08_flood_memory.geojson import (
    contains_point,
    distance_to_geometry_m,
    exterior_rings_from_geometry,
)
from app.studio.features.s08_flood_memory.schemas import DecadeCount, FloodEvent, FloodMemory


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _decade_of(start: date | None) -> int:
    if start is None:
        return 0
    return (start.year // 10) * 10


def build_flood_memory(features: list[dict], home: Point) -> FloodMemory:
    events = []
    inside_any = False
    nearest: float | None = None

    for feature in features:
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        contains = contains_point(geometry, home)
        distance = 0.0 if contains else distance_to_geometry_m(geometry, home)
        inside_any = inside_any or contains
        if nearest is None or distance < nearest:
            nearest = distance

        start = _parse_date(props.get("start_date"))
        events.append(
            FloodEvent(
                name=props.get("name"),
                start_date=start,
                end_date=_parse_date(props.get("end_date")),
                source=props.get("data_src"),
                cause=props.get("flood_src"),
                distance_m=round(distance),
                contains_home=contains,
                decade=_decade_of(start),
            )
        )

    events.sort(key=lambda e: e.start_date or date(1900, 1, 1), reverse=True)
    events = events[:MAX_EVENTS]

    counts = Counter(e.decade for e in events if e.decade)
    by_decade = [DecadeCount(decade=d, count=c) for d, c in sorted(counts.items())]

    outline_features = []
    for i, feature in enumerate(features[:MAX_OUTLINE_FEATURES]):
        geometry = feature.get("geometry") or {}
        simplified_rings = [
            douglas_peucker(ring, SIMPLIFY_TOLERANCE_DEG)
            for ring in exterior_rings_from_geometry(geometry)
        ]
        outline_features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[lon, lat] for lat, lon in ring]] for ring in simplified_rings
                    ],
                },
                "properties": {"event_index": i},
            }
        )

    return FloodMemory(
        inside_any_outline=inside_any,
        nearest_m=round(nearest) if nearest is not None and nearest != float("inf") else None,
        events=events,
        by_decade=by_decade,
        outlines={"type": "FeatureCollection", "features": outline_features},
        caveat=CAVEAT,
        evidence=[],
        fallback_used=False,
    )
