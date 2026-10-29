"""HM Land Registry Price Paid Data adapter (see config.py's docstring for the verified shape)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.studio.common.cache import Cache, studio_key
from app.studio.common.http import get_json
from app.studio.features.s14_green_value_lens.config import CACHE_DAYS, PPD_BASE, PPD_PAGE_SIZE

SOURCE = "HM Land Registry Price Paid Data"


@dataclass
class Sale:
    at: date
    price_gbp: int
    ppd_type: str | None


def _parse_rfc_date(value: str) -> date | None:
    for fmt in ("%a, %d %b %Y",):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


async def fetch_sales(postcode: str, since: date, cache: Cache) -> list[Sale]:
    key = studio_key("s14", "ppd", postcode.replace(" ", ""), since.isoformat())
    hit = await cache.get(key)
    if hit is not None:
        return [Sale(date.fromisoformat(r[0]), r[1], r[2]) for r in hit["rows"]]

    body = await get_json(
        PPD_BASE,
        params={
            "propertyAddress.postcode": postcode,
            "min-transactionDate": since.isoformat(),
            "_pageSize": PPD_PAGE_SIZE,
        },
        source=SOURCE,
    )
    items = (body.get("result") or {}).get("items") or []
    rows = []
    for item in items:
        category = ((item.get("transactionCategory") or {}).get("_about") or "").rsplit("/", 1)[-1]
        if category != "standardPricePaidTransaction":
            continue
        at = _parse_rfc_date(item.get("transactionDate") or "")
        price = item.get("pricePaid")
        if at is None or price is None:
            continue
        ppd_type = ((item.get("propertyType") or {}).get("_about") or "").rsplit("/", 1)[-1] or None
        rows.append((at.isoformat(), int(price), ppd_type))

    await cache.put(key, "price_paid", {"rows": rows}, timedelta(days=CACHE_DAYS))
    return [Sale(date.fromisoformat(r[0]), r[1], r[2]) for r in rows]
