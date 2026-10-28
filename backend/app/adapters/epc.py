"""Addresses and property facts from the EPC register developer API (spec §5, step N6).

API guide: get-energy-performance-data.communities.gov.uk/api-technical-documentation.
Base URL from `EPC_API_BASE_URL` (live by default; integration tokens need the integration
host). `GET /api/domestic/search` lists certificate summaries (address, UPRN, band); the full
certificate (`GET /api/certificate`) has the property facts. Both need `EPC_API_TOKEN` as a
bearer token. Answers are cached for 30 days. Fallback: no token, the register is down or it has
nothing → an empty address list and `None` facts, so the user fills `PropertyFacts` by hand.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel

from app.adapters.cache import Cache
from app.adapters.http import UpstreamUnavailable, new_client
from app.config import (
    EPC_CACHE_TTL,
    EPC_SEARCH_PAGE_SIZE,
    MAX_LIST_ITEMS,
    get_settings,
)
from app.schemas import PropertyFacts
from app.schemas.base import PropertyType

SOURCE = "EPC register"
CACHE_SOURCE = "epc"
CODES_PATH = Path(__file__).with_name("epc_codes.json")  # built by scripts/epc_codes.py
BANDS = ("A", "B", "C", "D", "E", "F", "G")
TOP_FLOOR_LEVEL = "3"  # `sap_flat_details.level` code: 0 basement, 1 ground, 2 mid, 3 top


class EpcAddress(BaseModel):
    line1: str
    uprn: str | None
    epc_rating: str | None
    certificate_number: str
    registration_date: str


# --- HTTP ---------------------------------------------------------------------------------


async def _get(path: str, params: dict[str, str | int]) -> dict[str, Any] | None:
    """The JSON body, or None when the register has nothing (404)."""
    settings = get_settings()
    token = settings.epc_api_token
    if not token:
        raise UpstreamUnavailable(SOURCE)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        async with new_client() as client:
            res = await client.get(
                settings.epc_api_base_url.rstrip("/") + path, params=params, headers=headers
            )
    except httpx.HTTPError as e:
        raise UpstreamUnavailable(SOURCE) from e
    if res.status_code == 404:
        return None
    if res.status_code != 200:
        raise UpstreamUnavailable(SOURCE)
    try:
        return res.json()
    except ValueError as e:
        raise UpstreamUnavailable(SOURCE) from e


def _key(name: str) -> str:
    """Cache key per environment: live and integration hold different data."""
    return f"epc:{urlsplit(get_settings().epc_api_base_url).hostname}:{name}"


async def _cached(cache: Cache, key: str, fetch) -> dict[str, Any]:
    if (hit := await cache.get(key)) is not None:
        return hit
    value = await fetch()
    await cache.put(key, CACHE_SOURCE, value, EPC_CACHE_TTL)
    return value


# --- Search: addresses in a postcode --------------------------------------------------------


async def search_postcode(postcode: str, cache: Cache) -> list[EpcAddress]:
    """Every address in the postcode with its latest certificate, in street order.

    `postcode` must already be normalised. Raises `UpstreamUnavailable` (no token, timeout,
    error), which the caller turns into an empty list.
    """
    rows = await search_postcode_rows(postcode, cache)
    return latest_per_address(rows)


async def search_postcode_rows(postcode: str, cache: Cache) -> list[dict[str, Any]]:
    """Every certificate summary row in the postcode, not deduplicated to one per address
    (Studio S02 needs each address's full history to spot improvers)."""

    async def fetch() -> dict[str, Any]:
        body = await _get(
            "/api/domestic/search",
            {"postcode": postcode, "page_size": EPC_SEARCH_PAGE_SIZE},
        )
        return {"data": (body or {}).get("data") or []}

    return (await _cached(cache, _key(f"search:{postcode}"), fetch))["data"]


async def certificate_by_number(certificate_number: str, cache: Cache) -> dict[str, Any] | None:
    """The raw certificate body (Studio S02 compares full certs, not just `PropertyFacts`)."""

    async def fetch() -> dict[str, Any]:
        body = await _get("/api/certificate", {"certificate_number": certificate_number})
        return {"data": (body or {}).get("data")}

    return (await _cached(cache, _key(f"certificate:{certificate_number}"), fetch))["data"]


def latest_per_address(rows: list[dict[str, Any]]) -> list[EpcAddress]:
    latest: dict[str, EpcAddress] = {}
    for r in rows:
        try:
            a = EpcAddress(
                line1=_address_line(r),
                uprn=str(r["uprn"]) if r.get("uprn") is not None else None,
                epc_rating=r.get("currentEnergyEfficiencyBand"),
                certificate_number=r["certificateNumber"],
                registration_date=r.get("registrationDate") or "",
            )
        except (KeyError, ValueError):
            continue
        if a.epc_rating not in BANDS:
            a.epc_rating = None
        key = a.uprn or a.line1.lower()
        # Same-day certificates happen; the certificate number breaks the tie so the
        # answer never depends on the order the register returns rows in.
        if key not in latest or _newer(a, latest[key]):
            latest[key] = a
    return sorted(latest.values(), key=lambda a: _street_order(a.line1))[:MAX_LIST_ITEMS]


def _newer(a: EpcAddress, b: EpcAddress) -> bool:
    return (a.registration_date, a.certificate_number) > (b.registration_date, b.certificate_number)


def _address_line(r: dict[str, Any]) -> str:
    parts = [r.get(f"addressLine{i}") for i in range(1, 5)]
    town = (r.get("postTown") or "").strip().lower()
    line = ", ".join(p.strip() for p in parts if p and p.strip() and p.strip().lower() != town)
    if not line:
        raise ValueError("no address")
    return line


def _street_order(line: str) -> list:
    """`2 High St` before `10 High St`: numbers compare as numbers."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", line.lower())]


# --- Certificate: property facts ------------------------------------------------------------


async def property_facts_for_uprn(uprn: str, cache: Cache) -> PropertyFacts | None:
    """Facts from the address's latest certificate, or None if it has none (N9 calls this)."""

    async def fetch_search() -> dict[str, Any]:
        body = await _get(
            "/api/domestic/search",
            {"uprn": uprn.zfill(12), "page_size": EPC_SEARCH_PAGE_SIZE},
        )
        return {"data": (body or {}).get("data") or []}

    rows = (await _cached(cache, _key(f"uprn:{uprn}"), fetch_search))["data"]
    found = latest_per_address(rows)
    if not found:
        return None
    number = found[0].certificate_number

    async def fetch_certificate() -> dict[str, Any]:
        body = await _get("/api/certificate", {"certificate_number": number})
        return {"data": (body or {}).get("data")}

    cert = (await _cached(cache, _key(f"certificate:{number}"), fetch_certificate))["data"]
    return map_certificate(cert) if cert else None


@lru_cache
def _codes() -> dict[str, dict[str, dict[str, str]]]:
    return json.loads(CODES_PATH.read_text())


def _decode(schema: str, code: str, raw: Any) -> str | None:
    """Meaning of a coded answer for this schema; text answers are passed through."""
    if raw is None or raw == "":
        return None
    value = _codes().get(schema, {}).get(code, {}).get(str(raw))
    if value is not None:
        return value
    return str(raw) if isinstance(raw, str) and not raw.isdigit() else None


def decode_field(schema: str, field: str, raw: Any) -> str | None:
    """Public `_decode`, for Studio S02 to read `built_form`/`construction_age_band` off a raw
    certificate the same way `map_certificate` does."""
    return _decode(schema, field, raw)


def property_type_from_certificate(c: dict[str, Any]) -> PropertyType:
    """The same `PropertyType` `map_certificate` derives, exposed for Studio S02's peer
    matching (it needs this without the rest of `PropertyFacts`)."""
    schema = c.get("schema_type") or ""
    kind = _decode(schema, "property_type", c.get("property_type"))
    built_form = _decode(schema, "built_form", c.get("built_form"))
    dwelling = (_text(c.get("dwelling_type")) or "").lower()
    return _property_type(kind, built_form, dwelling)


def _text(v: Any) -> str | None:
    """Descriptions are a string in some schemas and `{"value": ..., "language": ...}` in others."""
    if isinstance(v, dict):
        v = v.get("value")
    return v.strip() if isinstance(v, str) and v.strip() else None


def _number(v: Any) -> float | None:
    if isinstance(v, dict):
        v = v.get("value")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def map_certificate(c: dict[str, Any]) -> PropertyFacts:
    schema = c.get("schema_type") or ""
    kind = _decode(schema, "property_type", c.get("property_type"))  # House, Flat, ...
    built_form = _decode(schema, "built_form", c.get("built_form"))
    if built_form and built_form.lower() == "not recorded":
        built_form = None
    dwelling = (_text(c.get("dwelling_type")) or "").lower()
    property_type = _property_type(kind, built_form, dwelling)

    parts = c.get("sap_building_parts") or [{}]
    age = _decode(schema, "construction_age_band", parts[0].get("construction_age_band"))
    if age:
        age = age.removeprefix("England and Wales: ")
        age = None if age.lower() in ("not applicable", "not recorded") else age

    floor_level, top_floor = 0, None
    if property_type == "flat":
        flat = c.get("sap_flat_details") or {}
        floor_level = _storey(flat.get("flat_location"))
        top_floor = (
            str(flat.get("level")) == TOP_FLOOR_LEVEL
            or flat.get("top_storey") == "Y"
            or dwelling.startswith("top-floor")
        )

    heating = c.get("main_heating") or [{}]
    main_heating = _text(heating[0].get("description"))
    details = (c.get("sap_heating") or {}).get("main_heating_details") or [{}]
    # The description ("Boiler and radiators, mains gas") is what the user sees, so its fuel
    # wins; the coded fuel is the fallback (some certificates code a different fuel).
    fuel = simplify_fuel(main_heating) or simplify_fuel(
        _decode(schema, "main_fuel", details[0].get("main_fuel_type"))
    )

    band = c.get("current_energy_efficiency_band")
    score = _number(c.get("energy_rating_current"))
    return PropertyFacts(
        property_type=property_type,
        built_form=built_form,
        construction_age_band=age,
        floor_area_m2=_number(c.get("total_floor_area")),
        floor_level=floor_level,
        top_floor=top_floor,
        main_heating=main_heating,
        main_fuel=fuel,
        epc_rating=band if band in BANDS else None,
        epc_score=int(score) if score is not None else None,
        co2_tonnes_per_year=_number(c.get("co2_emissions_current")),
        source="epc_api",
    )


def _property_type(kind: str | None, built_form: str | None, dwelling: str) -> PropertyType:
    kind = (kind or "").lower() or dwelling
    form = (built_form or "").lower() or dwelling
    if "flat" in kind or "maisonette" in kind:
        return "flat"
    if "bungalow" in kind:
        return "bungalow"
    if "park home" in kind:
        return "other"
    if "semi" in form:
        return "semi_detached"
    if "terrace" in form:
        return "terraced"
    if "detached" in form:
        return "detached"
    return "other"


def _storey(raw: Any) -> int | None:
    """`flat_location` storey: `-1` basement, `00` ground, `05` 5th, `20+` above 20."""
    if raw is None:
        return None
    s = str(raw).strip().rstrip("+")
    try:
        return int(s) + (1 if str(raw).endswith("+") else 0)
    except ValueError:
        return None


def simplify_fuel(value: str | None) -> str | None:
    """Short fuel names matching the bulk EPC data (`mains gas`, `electricity`, `oil`, ...)."""
    if not value:
        return None
    t = value.lower().split(" - this is for backwards")[0]
    for needle, name in (
        ("mains gas", "mains gas"),
        ("lpg", "LPG"),
        ("electric", "electricity"),
        ("bio", "biofuel"),  # biomass, biogas, biodiesel, bioethanol
        ("wood", "wood"),
        ("coal", "coal"),
        ("anthracite", "coal"),
        ("solid fuel", "coal"),
        ("oil", "oil"),
        ("heat network", "heat network"),
    ):
        if needle in t:
            return name
    return None
