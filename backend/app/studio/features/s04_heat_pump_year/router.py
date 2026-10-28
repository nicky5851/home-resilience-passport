from datetime import UTC, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s04_heat_pump_year.config import (
    BUS_GRANT_GBP,
    INSTALL_COST_HIGH_GBP,
    INSTALL_COST_LOW_GBP,
)
from app.studio.features.s04_heat_pump_year.era5_hourly import (
    hourly_temps,
    last_full_year,
    synthetic_hourly_temps,
)
from app.studio.features.s04_heat_pump_year.schemas import HeatPumpYear, HeatPumpYearRequest
from app.studio.features.s04_heat_pump_year.service import build_year, estimate_htc_w_per_k
from app.studio.features.s04_heat_pump_year.sim import recommended_kw, simulate_year

router = APIRouter(prefix="/homes/{ref}/heat-pump-year", tags=["studio:s04"])


@router.post("")
async def heat_pump_year(
    ref: str,
    body: HeatPumpYearRequest,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
) -> HeatPumpYear:
    home = await resolve_home(ref, session, user)

    if body.htc_w_per_k is not None:
        htc = float(body.htc_w_per_k)
        htc_source = "user"
    else:
        htc = float(estimate_htc_w_per_k(home.property))
        htc_source = "estimated_from_age_band"

    year = last_full_year()
    fallback_used = False
    try:
        hourly = await hourly_temps(home.address.lat, home.address.lon, year, cache)
    except UpstreamUnavailable:
        hourly = synthetic_hourly_temps(home.address.lat, year)
        fallback_used = True
    results = simulate_year(htc, body.flow_temp_c, hourly)
    recommended = recommended_kw(htc)

    computed = build_year(results, htc, htc_source, recommended, body.keep_gas_standing_charge)

    net_cost_low = max(0, INSTALL_COST_LOW_GBP - BUS_GRANT_GBP)
    net_cost_high = max(0, INSTALL_COST_HIGH_GBP - BUS_GRANT_GBP)

    now = datetime.now(UTC)
    evidence = [
        Evidence(
            label="Outdoor temperature",
            evidence="estimated" if fallback_used else "observed",
            source="Open-Meteo ERA5 reanalysis"
            if not fallback_used
            else "A typical-year estimate (ERA5 was unreachable)",
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            retrieved_at=now,
        ),
        Evidence(
            label="Energy prices",
            evidence="official_modelled",
            source="Ofgem Direct Debit price cap, Oct-Dec 2026",
            source_url="https://www.ofgem.gov.uk/information-consumers/energy-advice-households/energy-price-cap-unit-rates-and-standing-charges",
            retrieved_at=now,
        ),
        Evidence(
            label="Boiler Upgrade Scheme grant",
            evidence="official_modelled",
            source="GOV.UK Boiler Upgrade Scheme",
            source_url="https://www.gov.uk/apply-boiler-upgrade-scheme",
            retrieved_at=now,
        ),
        Evidence(
            label="Heat demand simulation",
            evidence="estimated",
            source="HRP degree-day heat-pump model",
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            retrieved_at=now,
            note="A simplified single-zone model; your actual bill will vary",
        ),
    ]

    return HeatPumpYear(
        year=year,
        htc_used_w_per_k=round(htc),
        htc_source=htc_source,
        recommended_kw=recommended,
        scop=computed["scop"],
        annual=computed["annual"],
        monthly=computed["monthly"],
        daily=computed["daily"],
        coldest_hour=computed["coldest_hour"],
        bus_grant_gbp=BUS_GRANT_GBP,
        install_cost_low_gbp=INSTALL_COST_LOW_GBP,
        install_cost_high_gbp=INSTALL_COST_HIGH_GBP,
        net_cost_low_gbp=net_cost_low,
        net_cost_high_gbp=net_cost_high,
        prices=computed["prices"],
        evidence=evidence,
        fallback_used=fallback_used,
    )
