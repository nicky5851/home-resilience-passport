"""Planning Data platform (MHCLG) adapter (docs/studio/N_20_function.md §S10; see config.py's
docstring for the live-verified query shape)."""

import asyncio
from datetime import timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s10_permission_radar.config import ITEMS_LIMIT, PLANNING_DATA_BASE

SOURCE = "Planning Data platform"


async def fetch_entities(dataset: str, lat: float, lon: float, cache: Cache) -> list[dict]:
    key = studio_key("s10", dataset, f"{round(lat, 4)}", f"{round(lon, 4)}")
    hit = await cache.get(key)
    if hit is not None:
        return hit["entities"]

    body = await get_json(
        f"{PLANNING_DATA_BASE}/entity.json",
        params={"latitude": lat, "longitude": lon, "dataset": dataset, "limit": ITEMS_LIMIT},
        source=SOURCE,
    )
    entities = body.get("entities") or []
    await cache.put(key, "planning_data", {"entities": entities}, timedelta(days=30))
    return entities


async def fetch_all(
    datasets: list[str], lat: float, lon: float, cache: Cache
) -> dict[str, list[dict] | None]:
    """`None` for a dataset whose fetch failed; an empty list means the council has coverage
    but no entity applies here."""
    from app.adapters.http import UpstreamUnavailable

    async def one(dataset: str) -> tuple[str, list[dict] | None]:
        try:
            return dataset, await fetch_entities(dataset, lat, lon, cache)
        except UpstreamUnavailable:
            return dataset, None

    results = await asyncio.gather(*(one(d) for d in datasets))
    return dict(results)
