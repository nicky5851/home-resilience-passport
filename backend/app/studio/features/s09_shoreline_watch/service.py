from app.studio.common.geo import Point, douglas_peucker, haversine_m
from app.studio.features.s09_shoreline_watch.config import (
    ADVICE_LINKS,
    CLIMATE_LABEL,
    COARSE_COASTLINE_POINTS,
    COLLECTIONS,
    ERODES_INSURANCE_NOTE,
    MAX_FEATURES,
    SIMPLIFY_TOLERANCE_DEG,
    SYNTHETIC_COASTAL_THRESHOLD_M,
    SYNTHETIC_RETREAT_M,
)
from app.studio.features.s09_shoreline_watch.ncerm import (
    contains_point,
    distance_to_geometry_m,
    polygon_rings,
)
from app.studio.features.s09_shoreline_watch.schemas import AdviceLink, Projection, Shoreline


def nearest_coast_m(point: Point) -> int:
    return round(min(haversine_m(point, p) for p in COARSE_COASTLINE_POINTS))


def synthetic_shoreline(home: Point) -> Shoreline:
    """A deterministic stand-in used only when every NCERM collection is unreachable, so a
    likely-coastal home still demonstrates zones/slider offline (fallback_used: true)."""
    distance = nearest_coast_m(home)
    is_coastal = distance <= SYNTHETIC_COASTAL_THRESHOLD_M
    if not is_coastal:
        return Shoreline(
            coastal=False,
            nearest_coast_m=distance,
            projections=[],
            smp_policy=None,
            features={"type": "FeatureCollection", "features": []},
            advice_links=[AdviceLink(**link) for link in ADVICE_LINKS],
            insurance_note=ERODES_INSURANCE_NOTE,
            evidence=[],
            fallback_used=True,
        )

    projections = [
        Projection(
            epoch=entry["epoch"],
            scenario=entry["scenario"],
            climate=CLIMATE_LABEL,
            home_inside_zone=False,
            distance_m=SYNTHETIC_RETREAT_M[entry["epoch"]],
        )
        for entry in COLLECTIONS
    ]
    size_deg = 0.002
    lat, lon = home
    square = [
        (lat - size_deg, lon - size_deg),
        (lat - size_deg, lon + size_deg),
        (lat + size_deg, lon + size_deg),
        (lat + size_deg, lon - size_deg),
        (lat - size_deg, lon - size_deg),
    ]
    outline_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[lon2, lat2] for lat2, lon2 in square]]],
            },
            "properties": {
                "epoch": entry["epoch"],
                "scenario": entry["scenario"],
                "climate": CLIMATE_LABEL,
            },
        }
        for entry in COLLECTIONS
    ]
    return Shoreline(
        coastal=True,
        nearest_coast_m=0,
        projections=projections,
        smp_policy="Hold The Line (typical)",
        features={"type": "FeatureCollection", "features": outline_features},
        advice_links=[AdviceLink(**link) for link in ADVICE_LINKS],
        insurance_note=ERODES_INSURANCE_NOTE,
        evidence=[],
        fallback_used=True,
    )


def build_shoreline(home: Point, features_by_collection: dict[str, list[dict]]) -> Shoreline:
    any_feature = any(features_by_collection.values())
    if not any_feature:
        return Shoreline(
            coastal=False,
            nearest_coast_m=nearest_coast_m(home),
            projections=[],
            smp_policy=None,
            features={"type": "FeatureCollection", "features": []},
            advice_links=[AdviceLink(**link) for link in ADVICE_LINKS],
            insurance_note=ERODES_INSURANCE_NOTE,
            evidence=[],
            fallback_used=False,
        )

    projections = []
    smp_policy = None
    outline_features = []

    for entry in COLLECTIONS:
        collection_features = features_by_collection.get(entry["collection"], [])
        inside = False
        best_distance: float | None = None
        for feature in collection_features:
            geometry = feature.get("geometry") or {}
            if contains_point(geometry, home):
                inside = True
                best_distance = 0.0
            else:
                d = distance_to_geometry_m(geometry, home)
                if best_distance is None or d < best_distance:
                    best_distance = d
            if smp_policy is None:
                smp_policy = (feature.get("properties") or {}).get("smp_name")

        projections.append(
            Projection(
                epoch=entry["epoch"],
                scenario=entry["scenario"],
                climate=CLIMATE_LABEL,
                home_inside_zone=inside,
                distance_m=round(best_distance) if best_distance is not None else None,
            )
        )

        for feature in collection_features[: MAX_FEATURES // len(COLLECTIONS) or 1]:
            geometry = feature.get("geometry") or {}
            simplified_rings = [
                douglas_peucker(ring, SIMPLIFY_TOLERANCE_DEG) for ring in polygon_rings(geometry)
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
                    "properties": {
                        "epoch": entry["epoch"],
                        "scenario": entry["scenario"],
                        "climate": CLIMATE_LABEL,
                    },
                }
            )

    return Shoreline(
        coastal=True,
        nearest_coast_m=0,
        projections=projections,
        smp_policy=smp_policy,
        features={"type": "FeatureCollection", "features": outline_features[:MAX_FEATURES]},
        advice_links=[AdviceLink(**link) for link in ADVICE_LINKS],
        insurance_note=ERODES_INSURANCE_NOTE,
        evidence=[],
        fallback_used=False,
    )
