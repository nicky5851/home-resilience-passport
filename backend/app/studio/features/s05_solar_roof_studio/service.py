import asyncio
import math
from datetime import date

from app.adapters.http import UpstreamUnavailable
from app.schemas.property import PropertyFacts
from app.studio.common.cache import Cache
from app.studio.features.s05_solar_roof_studio.config import (
    CO2_KG_PER_KWH_ELEC,
    DEGRADATION_PER_YEAR,
    EXPORT_P_PER_KWH_DEFAULT,
    IMPORT_P_PER_KWH,
    INSTALL_COST_HIGH_GBP_PER_KWP,
    INSTALL_COST_LOW_GBP_PER_KWP,
    LIFETIME_YEARS,
    ROOF_KWP_CAP,
    ROOF_KWP_PER_M2,
    ROOF_USABLE_FRACTION,
    ROSE_ASPECTS_DEG,
    SELF_USE_FRACTION,
    STOREYS_BY_PROPERTY_TYPE,
    SUITABILITY_FAIR_KWH_PER_KWP,
    SUITABILITY_GOOD_KWH_PER_KWP,
)
from app.studio.features.s05_solar_roof_studio.pvgis import pvcalc, synthetic_pvcalc
from app.studio.features.s05_solar_roof_studio.schemas import OrientationPoint, SolarResult


def estimate_kwp_from_roof(prop: PropertyFacts) -> float | None:
    if prop.property_type == "flat":
        return None
    area = prop.floor_area_m2 or 90.0
    storeys = STOREYS_BY_PROPERTY_TYPE.get(prop.property_type, 2)
    footprint = area / storeys
    pitch_deg = 35
    one_slope_m2 = footprint / math.cos(math.radians(pitch_deg)) / 2
    usable_m2 = one_slope_m2 * ROOF_USABLE_FRACTION
    return min(ROOF_KWP_CAP, round(usable_m2 * ROOF_KWP_PER_M2, 2))


def suitability_for(kwh_per_kwp: float, is_flat: bool) -> tuple[str, str]:
    if is_flat:
        return (
            "freeholder_needed",
            "You'll usually need your freeholder's permission for roof-mounted solar on a flat.",
        )
    if kwh_per_kwp >= SUITABILITY_GOOD_KWH_PER_KWP:
        return "good", "This orientation and pitch generate well above the UK typical range."
    if kwh_per_kwp >= SUITABILITY_FAIR_KWH_PER_KWP:
        return (
            "fair",
            "This orientation and pitch generate a reasonable amount, below the best-case "
            "south-facing roof.",
        )
    return (
        "poor",
        "This orientation and pitch generate well below typical - east/west or flat roofs "
        "do less well.",
    )


async def _pvcalc_or_fallback(
    lat: float, lon: float, kwp: float, pitch_deg: int, aspect_deg: int, cache: Cache
) -> tuple[dict, bool]:
    try:
        return await pvcalc(lat, lon, kwp, pitch_deg, aspect_deg, cache), False
    except UpstreamUnavailable:
        return synthetic_pvcalc(kwp, pitch_deg, aspect_deg), True


async def build_solar(
    prop: PropertyFacts,
    lat: float,
    lon: float,
    aspect_deg: int,
    pitch_deg: int,
    kwp_input: float | None,
    battery_kwh: int,
    export_p_per_kwh: float | None,
    cache: Cache,
) -> SolarResult:
    if kwp_input is not None:
        kwp, kwp_source = kwp_input, "user"
    else:
        estimated = estimate_kwp_from_roof(prop)
        if estimated is None:
            kwp, kwp_source = 0.0, "estimated_from_roof"
        else:
            kwp, kwp_source = estimated, "estimated_from_roof"

    is_flat = prop.property_type == "flat" and kwp_input is None
    fallback_used = False

    if kwp > 0:
        main, main_fallback = await _pvcalc_or_fallback(lat, lon, kwp, pitch_deg, aspect_deg, cache)
        fallback_used = fallback_used or main_fallback

        rose_tasks = [
            _pvcalc_or_fallback(lat, lon, 1.0, pitch_deg, a, cache) for a in ROSE_ASPECTS_DEG
        ]
        rose_raw = await asyncio.gather(*rose_tasks)
        rose = [
            OrientationPoint(aspect_deg=a, annual_kwh=round(r["annual_kwh"] * kwp))
            for a, (r, _) in zip(ROSE_ASPECTS_DEG, rose_raw, strict=True)
        ]
        fallback_used = fallback_used or any(fb for _, fb in rose_raw)
    else:
        main = {"annual_kwh": 0, "monthly_kwh": [0] * 12}
        rose = [OrientationPoint(aspect_deg=a, annual_kwh=0) for a in ROSE_ASPECTS_DEG]

    annual_kwh = main["annual_kwh"]
    self_use_fraction = SELF_USE_FRACTION[battery_kwh]
    self_use_kwh = round(annual_kwh * self_use_fraction)
    export_kwh = annual_kwh - self_use_kwh
    export_rate = export_p_per_kwh if export_p_per_kwh is not None else EXPORT_P_PER_KWH_DEFAULT

    annual_saving_gbp = round(
        self_use_kwh * IMPORT_P_PER_KWH / 100 + export_kwh * export_rate / 100
    )

    install_low = round(kwp * INSTALL_COST_LOW_GBP_PER_KWP)
    install_high = round(kwp * INSTALL_COST_HIGH_GBP_PER_KWP)
    mid_cost = (install_low + install_high) / 2

    payback_years = round(mid_cost / annual_saving_gbp, 1) if annual_saving_gbp > 0 else None
    breakeven_year = date.today().year + math.ceil(payback_years) if payback_years else None

    lifetime_saving = 0.0
    for yr in range(LIFETIME_YEARS):
        lifetime_saving += annual_saving_gbp * ((1 - DEGRADATION_PER_YEAR) ** yr)

    kwh_per_kwp = annual_kwh / kwp if kwp > 0 else 0.0
    suitability, suitability_note = suitability_for(kwh_per_kwp, is_flat)

    return SolarResult(
        kwp=kwp,
        kwp_source=kwp_source,
        annual_kwh=round(annual_kwh),
        monthly_kwh=[round(m) for m in main["monthly_kwh"]],
        self_use_kwh=self_use_kwh,
        export_kwh=export_kwh,
        annual_saving_gbp=annual_saving_gbp,
        install_cost_low_gbp=install_low,
        install_cost_high_gbp=install_high,
        payback_years=payback_years,
        breakeven_year=breakeven_year,
        lifetime_saving_gbp=round(lifetime_saving),
        co2_saved_kg_per_year=round(annual_kwh * CO2_KG_PER_KWH_ELEC),
        orientation_rose=rose,
        suitability=suitability,
        suitability_note=suitability_note,
        evidence=[],
        fallback_used=fallback_used,
    )
