import re
from typing import Literal

from pydantic import field_validator

from app.schemas.base import Band, Contract, PropertyType

_POSTCODE_RE = re.compile(r"^([A-Z]{1,2}[0-9][A-Z0-9]?)([0-9][A-Z]{2})$")


def normalise_postcode(raw: str) -> str:
    """Upper-case with one space before the inward code (CONTRACT §1 rule 7)."""
    compact = re.sub(r"\s+", "", raw).upper()
    m = _POSTCODE_RE.match(compact)
    if not m:
        raise ValueError("Enter a full UK postcode, for example SW1A 1AA.")
    return f"{m.group(1)} {m.group(2)}"


class Address(Contract):
    uprn: str | None = None
    line1: str
    postcode: str
    lat: float
    lon: float
    local_authority: str | None = None
    country: Literal["england", "wales", "scotland", "northern_ireland"]

    @field_validator("postcode")
    @classmethod
    def _postcode(cls, v: str) -> str:
        return normalise_postcode(v)


class PropertyFacts(Contract):
    property_type: PropertyType
    built_form: str | None = None
    construction_age_band: str | None = None
    floor_area_m2: float | None = None
    floor_level: int | None = None  # 0 = ground
    top_floor: bool | None = None  # true only for flats on the top storey
    main_heating: str | None = None
    main_fuel: str | None = None
    epc_rating: Band | None = None
    epc_score: int | None = None
    co2_tonnes_per_year: float | None = None
    source: Literal["epc_api", "model", "user", "demo"]
