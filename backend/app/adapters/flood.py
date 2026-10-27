"""River/sea flood band and live warnings (spec §5, step N7).

- `rofrs_band`: the EA RoFRS postcode band loaded by `app.db.load_rofrs` into `flood_postcodes`.
  `none` when the postcode is not in the dataset; `None` (unknown) for Wales (the dataset is
  England only, CONTRACT §1 rule 9), when the table has not been loaded, or the database is down.
- `active_flood_warnings`: EA real-time flood-monitoring API, warnings and alerts in force within
  5 km. Free, no key, cached 15 minutes. Fallback: 0 (CONTRACT §2).
"""

import logging
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.cache import Cache
from app.adapters.http import UpstreamUnavailable, new_client
from app.config import FLOOD_WARNINGS_CACHE_TTL, FLOOD_WARNINGS_MAX, FLOOD_WARNINGS_RADIUS_KM
from app.db.models import FloodPostcode

log = logging.getLogger(__name__)

RofrsBand = Literal["high", "medium", "low", "very_low", "none"]
BAND_ORDER: tuple[RofrsBand, ...] = ("high", "medium", "low", "very_low")

WARNINGS_SOURCE = "EA flood-monitoring"
FLOOD_WARNINGS_URL = "https://environment.data.gov.uk/flood-monitoring/id/floods"
# severityLevel 1 severe flood warning, 2 flood warning, 3 flood alert; 4 = no longer in force.
IN_FORCE_LEVELS = (1, 2, 3)


async def rofrs_band(postcode: str, country: str, session: AsyncSession) -> RofrsBand | None:
    """Highest RoFRS band for a normalised postcode (CONTRACT §2)."""
    if country != "england":
        return None
    try:
        bands = set(
            await session.scalars(
                select(FloodPostcode.band).where(FloodPostcode.postcode == postcode)
            )
        )
        if bands:
            return next((b for b in BAND_ORDER if b in bands), None)
        loaded = await session.scalar(select(FloodPostcode.postcode).limit(1))
    except (SQLAlchemyError, OSError) as e:
        log.warning("flood_postcodes read failed (%s); band unknown", type(e).__name__)
        try:
            await session.rollback()
        except (SQLAlchemyError, OSError):
            pass
        return None
    if loaded is None:
        log.warning("flood_postcodes is empty; run `make flood-data`. Band unknown")
        return None
    return "none"


async def active_flood_warnings(lat: float, lon: float, cache: Cache) -> int:
    """Flood warnings and alerts in force within 5 km; 0 when the EA API cannot answer."""
    key = f"ea-floods:{lat:.3f},{lon:.3f}"  # about 100 m, well inside the 5 km radius
    if (hit := await cache.get(key)) is not None:
        return hit["count"]
    try:
        count = await _fetch_count(lat, lon)
    except UpstreamUnavailable:
        log.warning("EA flood-monitoring unavailable; active_flood_warnings = 0")
        return 0
    await cache.put(key, "ea-floods", {"count": count}, FLOOD_WARNINGS_CACHE_TTL)
    return count


async def _fetch_count(lat: float, lon: float) -> int:
    params = {"lat": lat, "long": lon, "dist": FLOOD_WARNINGS_RADIUS_KM}
    try:
        async with new_client() as client:
            res = await client.get(FLOOD_WARNINGS_URL, params=params)
    except httpx.HTTPError as e:
        raise UpstreamUnavailable(WARNINGS_SOURCE) from e
    if res.status_code != 200:
        raise UpstreamUnavailable(WARNINGS_SOURCE)
    try:
        items = res.json()["items"]
        count = sum(1 for i in items if i.get("severityLevel") in IN_FORCE_LEVELS)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise UpstreamUnavailable(WARNINGS_SOURCE) from e
    return min(count, FLOOD_WARNINGS_MAX)
