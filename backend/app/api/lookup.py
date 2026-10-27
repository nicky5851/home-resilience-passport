"""Postcode lookup. Foundation stub until N5 (postcodes.io) and N6 (EPC register)."""

import re

from fastapi import APIRouter

from app.api.errors import ApiError
from app.api.stub_store import fixture_by_postcode
from app.schemas import normalise_postcode
from app.schemas.api import LookupAddress, PostcodeLookup

router = APIRouter(prefix="/lookup", tags=["lookup"])

UNSUPPORTED_REGION_DETAIL = "Home Resilience Passport covers England and Wales for now."
# Stub only: postcode areas that are (mostly) Scotland or Northern Ireland. N5 uses the
# country from postcodes.io instead, which also handles the border areas correctly.
_NON_EW_AREAS = re.compile(r"^(AB|DD|DG|EH|FK|G|HS|IV|KA|KW|KY|ML|PA|PH|TD|ZE|BT)[0-9]")
# Stub location for postcodes that are not a demo home (central London).
_STUB_LAT, _STUB_LON = 51.5072, -0.1276


@router.get("/postcode/{postcode}")
def lookup_postcode(postcode: str) -> PostcodeLookup:
    try:
        pc = normalise_postcode(postcode)
    except ValueError as e:
        raise ApiError(400, "validation", str(e)) from e
    if _NON_EW_AREAS.match(pc):
        raise ApiError(400, "unsupported_region", UNSUPPORTED_REGION_DETAIL)

    match = fixture_by_postcode(pc)
    if match is None:
        return PostcodeLookup(postcode=pc, lat=_STUB_LAT, lon=_STUB_LON, addresses=[])
    a = match.demo.address
    return PostcodeLookup(
        postcode=pc,
        lat=a.lat,
        lon=a.lon,
        local_authority=a.local_authority,
        addresses=[
            LookupAddress(line1=a.line1, uprn=a.uprn, epc_rating=match.demo.property.epc_rating)
        ],
    )
