"""Assessment pipeline (spec step N9): adapters → HazardInputs → L's scoring.

Never fails because a data source is down: each adapter degrades on its own (CONTRACT §2
nulls, regional climate defaults, 0 warnings), and scoring handles the gaps.
"""

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import climate, epc, flood, postcodes
from app.adapters.cache import Cache
from app.adapters.http import UpstreamUnavailable
from app.config import ASSESS_WARNINGS_BUDGET_S
from app.schemas import Address, HazardInputs, Measure, PropertyFacts
from app.schemas.api import Assessment
from app.scoring import assess_risk, compute_score
from ml import predict

log = logging.getLogger(__name__)


async def property_for(
    address: Address, override: PropertyFacts | None, cache: Cache
) -> PropertyFacts | None:
    """The user's own facts win; else the address's latest EPC; None if neither exists."""
    if override is not None:
        return override
    if not address.uprn:
        return None
    try:
        return await epc.property_facts_for_uprn(address.uprn, cache)
    except UpstreamUnavailable:
        log.warning("EPC register unavailable; asking the user for property details")
        return None


async def _region(postcode: str, cache: Cache) -> str | None:
    try:
        return (await postcodes.lookup_postcode(postcode, cache)).region
    except (UpstreamUnavailable, postcodes.PostcodeNotFound):
        return None  # climate falls back to the nearest region


async def with_estimate(prop: PropertyFacts, address: Address, cache: Cache) -> PropertyFacts:
    """No EPC band: our model estimates band and CO2 (`source="model"`, spec N13).

    A certificate's or the user's facts are never replaced, only gaps filled. Without a model
    file the facts stay as they are and scoring handles the missing band.
    """
    if prop.epc_rating is not None:
        return prop
    est = predict.estimate(prop, await _region(address.postcode, cache))
    if est is None:
        return prop
    co2 = prop.co2_tonnes_per_year
    return prop.model_copy(
        update={
            "epc_rating": est.band,
            "co2_tonnes_per_year": est.co2_tonnes_per_year if co2 is None else co2,
            "source": "model",
        }
    )


async def _warnings(address: Address, cache: Cache) -> int:
    """Live warnings within the assessment's time budget; 0 if the feed is slow, as when down."""
    try:
        return await asyncio.wait_for(
            flood.active_flood_warnings(address.lat, address.lon, cache), ASSESS_WARNINGS_BUDGET_S
        )
    except TimeoutError:
        log.warning("EA flood warnings slower than %.0f s; counting 0", ASSESS_WARNINGS_BUDGET_S)
        return 0


async def _climate(address: Address, cache: Cache) -> climate.ClimateStats:
    region = await _region(address.postcode, cache)  # cached by the lookup step
    return await climate.climate_stats(address.lat, address.lon, cache, region=region)


async def hazard_inputs(
    address: Address, prop: PropertyFacts, session: AsyncSession, cache: Cache
) -> HazardInputs:
    # The flood band reads `session` directly, so it runs before the network calls that share
    # the session through the cache (one operation at a time per AsyncSession).
    band = await flood.rofrs_band(address.postcode, address.country, session)
    warnings, stats = await asyncio.gather(
        _warnings(address, cache),
        _climate(address, cache),
    )
    return HazardInputs(
        rofrs_band=band,
        active_flood_warnings=warnings,
        **stats.model_dump(exclude={"from_defaults"}),
        property=prop,
    )


async def assess(
    address: Address,
    prop: PropertyFacts,
    session: AsyncSession,
    cache: Cache,
    completed: Sequence[Measure] = (),
) -> Assessment:
    prop = await with_estimate(prop, address, cache)
    inputs = await hazard_inputs(address, prop, session, cache)
    # L's assess_risk is pure, so its `generated_at` is fixed; stamp the real time here.
    risk = assess_risk(inputs).model_copy(
        update={"generated_at": datetime.now(UTC).replace(microsecond=0)}
    )
    return Assessment(inputs=inputs, risk=risk, score=compute_score(risk, prop, completed))
