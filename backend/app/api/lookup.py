"""Postcode lookup: location from postcodes.io (N5), addresses from the EPC register (N6)."""

import logging

from fastapi import APIRouter

from app.adapters import epc, postcodes
from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep
from app.api.errors import ApiError
from app.api.stub_store import Fixture, fixture_by_postcode
from app.config import MAX_LIST_ITEMS
from app.schemas import normalise_postcode
from app.schemas.api import LookupAddress, PostcodeLookup

log = logging.getLogger(__name__)
router = APIRouter(prefix="/lookup", tags=["lookup"])

UNSUPPORTED_REGION_DETAIL = "Home Resilience Passport covers England and Wales for now."
NOT_FOUND_DETAIL = "We couldn't find that postcode. Please check it and try again."
SUPPORTED_COUNTRIES = ("england", "wales")


def _demo_info(demo: Fixture) -> postcodes.PostcodeInfo:
    """Demo homes keep working when postcodes.io is down (spec N9 check)."""
    a = demo.demo.address
    return postcodes.PostcodeInfo(
        postcode=a.postcode,
        lat=a.lat,
        lon=a.lon,
        local_authority=a.local_authority,
        country=a.country,
    )


@router.get("/postcode/{postcode}")
async def lookup_postcode(postcode: str, cache: ApiCacheDep) -> PostcodeLookup:
    try:
        pc = normalise_postcode(postcode)
    except ValueError as e:
        raise ApiError(400, "validation", str(e)) from e

    demo = fixture_by_postcode(pc)
    try:
        info = await postcodes.lookup_postcode(pc, cache)
    except postcodes.PostcodeNotFound as e:
        raise ApiError(400, "validation", NOT_FOUND_DETAIL) from e
    except UpstreamUnavailable as e:
        if demo is None:
            raise ApiError(502, "upstream_unavailable") from e
        info = _demo_info(demo)
    if info.country not in SUPPORTED_COUNTRIES:
        raise ApiError(400, "unsupported_region", UNSUPPORTED_REGION_DETAIL)

    addresses: list[LookupAddress] = []
    if demo is not None:
        a = demo.demo.address
        addresses.append(
            LookupAddress(line1=a.line1, uprn=a.uprn, epc_rating=demo.demo.property.epc_rating)
        )
    try:
        found = await epc.search_postcode(pc, cache)
    except UpstreamUnavailable:
        # No token or the register is down: the user picks "My address isn't listed" (CONTRACT §3).
        log.warning("EPC register unavailable; returning no addresses")
        found = []
    addresses += [LookupAddress(line1=f.line1, uprn=f.uprn, epc_rating=f.epc_rating) for f in found]
    return PostcodeLookup(
        postcode=pc,
        lat=info.lat,
        lon=info.lon,
        local_authority=info.local_authority,
        addresses=addresses[:MAX_LIST_ITEMS],
    )
