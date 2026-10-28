from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s08_flood_memory.config import (
    RADIUS_DEFAULT_M,
    RADIUS_MAX_M,
    RADIUS_MIN_M,
    WALES_COMING_SOON,
)
from app.studio.features.s08_flood_memory.ea_flood_outlines import fetch_outlines
from app.studio.features.s08_flood_memory.schemas import FloodMemory
from app.studio.features.s08_flood_memory.service import build_flood_memory

router = APIRouter(prefix="/homes/{ref}/flood-memory", tags=["studio:s08"])


@router.get("")
async def flood_memory(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
    radius_m: int = Query(RADIUS_DEFAULT_M, ge=RADIUS_MIN_M, le=RADIUS_MAX_M),
) -> FloodMemory:
    home = await resolve_home(ref, session, user)
    now = datetime.now(UTC)
    center = (home.address.lat, home.address.lon)

    if home.address.country == "wales":
        result = build_flood_memory([], center)
        result.caveat = WALES_COMING_SOON
        result.evidence = [
            Evidence(
                label="Historic flood records",
                evidence="estimated",
                source=WALES_COMING_SOON,
                source_url="https://datamap.gov.wales/",
                retrieved_at=now,
            )
        ]
        return result

    fallback_used = False
    try:
        features = await fetch_outlines(center, radius_m, cache)
    except UpstreamUnavailable:
        features = []
        fallback_used = True

    result = build_flood_memory(features, center)
    result.fallback_used = fallback_used
    result.evidence = [
        Evidence(
            label="Recorded flood outlines",
            evidence="estimated" if fallback_used else "observed",
            source="Live records were unreachable" if fallback_used else "EA Recorded Flood Outlines",
            source_url="https://environment.data.gov.uk/spatialdata/recorded-flood-outlines/ogc/features/v1",
            retrieved_at=now,
        )
    ]
    return result
