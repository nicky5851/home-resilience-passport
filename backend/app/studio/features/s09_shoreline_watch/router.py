from datetime import UTC, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s09_shoreline_watch.config import COASTAL_RADIUS_M, COLLECTIONS
from app.studio.features.s09_shoreline_watch.ncerm import fetch_collection
from app.studio.features.s09_shoreline_watch.schemas import Shoreline
from app.studio.features.s09_shoreline_watch.service import build_shoreline, synthetic_shoreline

router = APIRouter(prefix="/homes/{ref}/shoreline", tags=["studio:s09"])


@router.get("")
async def shoreline(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> Shoreline:
    home = await resolve_home(ref, session, user)
    center = (home.address.lat, home.address.lon)
    now = datetime.now(UTC)

    fallback_used = False
    features_by_collection: dict[str, list[dict]] = {}
    unreachable_count = 0
    for entry in COLLECTIONS:
        try:
            features_by_collection[entry["collection"]] = await fetch_collection(
                entry["collection"], center, COASTAL_RADIUS_M, cache
            )
        except UpstreamUnavailable:
            features_by_collection[entry["collection"]] = []
            unreachable_count += 1

    if unreachable_count == len(COLLECTIONS):
        result = synthetic_shoreline(center)
        fallback_used = True
    else:
        result = build_shoreline(center, features_by_collection)
        fallback_used = unreachable_count > 0
    result.fallback_used = fallback_used
    result.evidence = [
        Evidence(
            label="Coastal erosion projections",
            evidence="estimated" if fallback_used else "official_modelled",
            source="Live projections were unreachable" if fallback_used else "EA NCERM 2024",
            source_url="https://www.data.gov.uk/dataset/national-coastal-erosion-risk-mapping-ncerm-national-2024",
            retrieved_at=now,
        )
    ]
    return result
