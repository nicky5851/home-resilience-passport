"""UK House Price Index adapter (see config.py's docstring for the verified shape)."""

from datetime import date, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import UpstreamUnavailable, get_json
from app.studio.features.s14_green_value_lens.config import (
    CACHE_DAYS,
    HPI_BASE,
    HPI_FIELD_FOR_PPD_TYPE,
)

SOURCE = "UK House Price Index"


def region_slug(local_authority: str) -> str:
    return local_authority.strip().lower().replace(" ", "-")


async def fetch_hpi_month(slug: str, month: str, ppd_type: str, cache: Cache) -> dict | None:
    """`{index, average_price}` for this month and type, or `None` if unavailable."""
    key = studio_key("s14", "hpi", slug, month)
    hit = await cache.get(key)
    body = hit["body"] if hit is not None else None
    if body is None:
        try:
            body = await get_json(f"{HPI_BASE}/{slug}/month/{month}.json", source=SOURCE)
        except UpstreamUnavailable:
            return None
        await cache.put(key, "hpi", {"body": body}, timedelta(days=CACHE_DAYS))

    topic = body.get("primaryTopic") if body else None
    if not topic:
        return None
    field = HPI_FIELD_FOR_PPD_TYPE.get(ppd_type)
    index = topic.get(f"housePriceIndex{field}") if field else topic.get("housePriceIndex")
    avg = topic.get(f"averagePrice{field}") if field else topic.get("averagePrice")
    if index is None:
        return None
    return {"index": index, "average_price": avg}


def latest_available_month(today: date) -> str:
    """HPI publishes with a lag; the month before last is reliably available."""
    month = today.month - 2
    year = today.year
    if month <= 0:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}"


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"
