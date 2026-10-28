"""A certificate boiled down to what Street Proof needs, built from the EPC register's raw
JSON (not `PropertyFacts` — that drops the description text the inference rules read)."""

import json
import re
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.adapters.epc import decode_field, property_type_from_certificate
from app.studio.features.s02_street_proof.config import fuel_family


def _text(v: Any) -> str:
    if isinstance(v, dict):
        v = v.get("value")
    return v.strip() if isinstance(v, str) else ""


def _first_desc(v: Any) -> str:
    rows = v if isinstance(v, list) else [v] if v else []
    return _text((rows[0] or {}).get("description")) if rows else ""


class Cert(BaseModel):
    certificate_number: str
    uprn: str | None
    address_key: str
    registered: date
    sap: int | None
    band: str | None
    property_type: str | None
    built_form: str | None
    age_band: str | None
    fuel_family: str
    wall_desc: str
    roof_desc: str
    window_desc: str
    heating_desc: str
    lighting_desc: str
    other_text: str


def address_key(row: dict[str, Any]) -> str:
    uprn = row.get("uprn")
    if uprn:
        return f"uprn:{uprn}"
    line = (row.get("addressLine1") or row.get("address_line_1") or "").strip().lower()
    postcode = (row.get("postcode") or "").strip().upper().replace(" ", "")
    return f"addr:{line}:{postcode}"


def cert_from_raw(summary_row: dict[str, Any], raw_cert: dict[str, Any] | None) -> Cert | None:
    """`summary_row` is one `/api/domestic/search` row; `raw_cert` is its `/api/certificate`
    body, when fetched. Returns `None` if even the registration date is unparseable."""
    try:
        registered = date.fromisoformat((summary_row.get("registrationDate") or "")[:10])
    except ValueError:
        return None

    c = raw_cert or {}
    heating_desc = _first_desc(c.get("main_heating"))
    sap = c.get("energy_rating_current")
    return Cert(
        certificate_number=summary_row.get("certificateNumber") or c.get("certificate_number", ""),
        uprn=str(summary_row["uprn"]) if summary_row.get("uprn") is not None else None,
        address_key=address_key(summary_row),
        registered=registered,
        sap=int(sap) if isinstance(sap, int | float) else None,
        band=c.get("current_energy_efficiency_band")
        or summary_row.get("currentEnergyEfficiencyBand"),
        property_type=property_type_from_certificate(c) if c else None,
        built_form=_decode_built_form(c),
        age_band=_decode_age_band(c),
        fuel_family=fuel_family(heating_desc or None),
        wall_desc=_first_desc(c.get("walls")).lower(),
        roof_desc=_first_desc(c.get("roofs")).lower(),
        window_desc=_text(c.get("windows")).lower(),
        heating_desc=heating_desc.lower(),
        lighting_desc=_text((c.get("lighting") or {}).get("description")).lower(),
        other_text=json.dumps(c).lower(),
    )


def _decode_built_form(c: dict[str, Any]) -> str | None:
    schema = c.get("schema_type") or ""
    form = decode_field(schema, "built_form", c.get("built_form"))
    return None if form and form.lower() == "not recorded" else form


def _decode_age_band(c: dict[str, Any]) -> str | None:
    schema = c.get("schema_type") or ""
    parts = c.get("sap_building_parts") or [{}]
    age = decode_field(schema, "construction_age_band", parts[0].get("construction_age_band"))
    if not age:
        return None
    age = age.removeprefix("England and Wales: ")
    return None if age.lower() in ("not applicable", "not recorded") else age


_PCT_RE = re.compile(r"(\d+)\s*%")


def lighting_percent(desc: str) -> int | None:
    m = _PCT_RE.search(desc)
    return int(m.group(1)) if m else None
