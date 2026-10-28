"""Postcode → lat/lon, local authority and country via postcodes.io (spec §5, step N5).

Free, no key. Answers are cached for 30 days. There is no fallback for an unknown postcode;
the route turns `PostcodeNotFound` into `400 validation`.
"""

from typing import Literal

import httpx
from pydantic import BaseModel

from app.adapters.cache import Cache
from app.adapters.http import UpstreamUnavailable, new_client
from app.config import POSTCODE_CACHE_TTL

SOURCE = "postcodes.io"
POSTCODES_IO_URL = "https://api.postcodes.io/postcodes/"

Country = Literal["england", "wales", "scotland", "northern_ireland"]
# postcodes.io also returns "Channel Islands" and "Isle of Man"; those map to None (unsupported).
_COUNTRIES: dict[str, Country] = {
    "England": "england",
    "Wales": "wales",
    "Scotland": "scotland",
    "Northern Ireland": "northern_ireland",
}


class PostcodeNotFound(Exception):
    """postcodes.io does not know the postcode, or has no location for it."""


class PostcodeInfo(BaseModel):
    postcode: str
    lat: float
    lon: float
    local_authority: str | None
    country: Country | None
    region: str | None = None  # English region name ("South West"), or "Wales"


async def lookup_postcode(postcode: str, cache: Cache) -> PostcodeInfo:
    """`postcode` must already be normalised (`SW1A 1AA`, CONTRACT §1 rule 7)."""
    key = cache_key(postcode)
    if (hit := await cache.get(key)) is not None:
        return PostcodeInfo.model_validate(hit)
    info = await _fetch(postcode)
    await cache.put(key, SOURCE, info.model_dump(mode="json"), POSTCODE_CACHE_TTL)
    return info


def cache_key(postcode: str) -> str:
    return f"{SOURCE}:{postcode}"


async def _fetch(postcode: str) -> PostcodeInfo:
    try:
        async with new_client() as client:
            res = await client.get(POSTCODES_IO_URL + postcode.replace(" ", ""))
    except httpx.HTTPError as e:
        raise UpstreamUnavailable(SOURCE) from e
    if res.status_code == 404:
        raise PostcodeNotFound(postcode)
    if res.status_code != 200:
        raise UpstreamUnavailable(SOURCE)
    try:
        r = res.json()["result"]
        lat, lon = r["latitude"], r["longitude"]
    except (ValueError, KeyError, TypeError) as e:
        raise UpstreamUnavailable(SOURCE) from e
    if lat is None or lon is None:  # a few live postcodes have no grid reference
        raise PostcodeNotFound(postcode)
    country = _COUNTRIES.get(r.get("country") or "")
    return PostcodeInfo(
        postcode=postcode,
        lat=lat,
        lon=lon,
        local_authority=r.get("admin_district"),
        country=country,
        # postcodes.io has English regions only; Wales is one row of the climate defaults.
        region=r.get("region") or ("Wales" if country == "wales" else None),
    )
