"""Model features (spec §2 "AI: our own model"), shared by training (N12) and serving (N13).

Seven features: property type, built form, age band, floor area, region, heating, fuel. Each
is built the same way from a bulk-CSV row (training) and from `PropertyFacts` plus the home's
region (serving), so the model never sees a value it could not get in the app.
"""

from typing import Any

from app.adapters.epc import _property_type, simplify_fuel

CATEGORICAL = ("property_type", "built_form", "age_band", "region", "heating", "fuel")
NUMERIC = ("floor_area_m2",)
FEATURES = (*CATEGORICAL, *NUMERIC)
BANDS = ("A", "B", "C", "D", "E", "F", "G")
OTHER = "other"

# Bulk-data region codes (ONS) → the region names postcodes.io returns (`PostcodeInfo.region`).
REGIONS = {
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
}
NOT_RECORDED = {"", "no data!", "not recorded", "not applicable", "invalid!", "unknown"}


def simplify_heating(description: str | None) -> str | None:
    """Main heating system type from its description ("Boiler and radiators, mains gas")."""
    if not description:
        return None
    t = description.lower()
    for needle, name in (
        ("heat pump", "heat pump"),
        ("community", "community"),
        ("heat network", "community"),
        ("storage heater", "storage heaters"),
        ("boiler", "boiler"),
        ("warm air", "warm air"),
        ("room heater", "room heaters"),
        ("electric", "electric other"),
        ("portable", "room heaters"),
    ):
        if needle in t:
            return name
    return OTHER


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = " ".join(str(value).split())
    return None if v.lower() in NOT_RECORDED else v


def age_band(value: str | None) -> str | None:
    """Drop the "England and Wales: " prefix of age bands, as the EPC adapter does."""
    v = _clean(value)
    return v.removeprefix("England and Wales: ") if v else None


def from_bulk(row: dict[str, str]) -> dict[str, Any]:
    """Features from a row of the EPC bulk CSV (`certificates-<year>.csv`)."""
    built_form = _clean(row.get("built_form"))
    heating = _clean(row.get("mainheat_description"))
    area = row.get("total_floor_area") or ""
    try:
        floor_area = float(area) if area else None
    except ValueError:
        floor_area = None
    return {
        "property_type": _property_type(_clean(row.get("property_type")), built_form, ""),
        "built_form": built_form,
        "age_band": age_band(row.get("construction_age_band")),
        "region": REGIONS.get(row.get("region") or ""),
        # Same rule as the EPC adapter: the description's fuel first, the coded fuel second.
        "heating": simplify_heating(heating),
        "fuel": simplify_fuel(heating) or simplify_fuel(_clean(row.get("main_fuel"))),
        "floor_area_m2": floor_area,
    }


def from_facts(facts: Any, region: str | None) -> dict[str, Any]:
    """Features from `PropertyFacts` (and `PostcodeInfo.region`) at prediction time."""
    return {
        "property_type": facts.property_type,
        "built_form": _clean(facts.built_form),
        "age_band": age_band(facts.construction_age_band),
        "region": region,
        "heating": simplify_heating(facts.main_heating),
        "fuel": facts.main_fuel or simplify_fuel(facts.main_heating),
        "floor_area_m2": facts.floor_area_m2,
    }
