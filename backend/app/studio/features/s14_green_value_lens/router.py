from datetime import UTC, date, datetime

from fastapi import APIRouter, Query

from app.adapters.http import UpstreamUnavailable
from app.adapters.postcodes import PostcodeNotFound, lookup_postcode, nearest_postcodes
from app.api.deps import ApiCacheDep, SessionDep
from app.services import homes as homes_service
from app.services import planner
from app.studio.common.geo import haversine_m
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s14_green_value_lens.config import (
    DISCLAIMER,
    MAX_COMPS,
    MIN_COMPS_FOR_MEDIAN,
    NEAREST_POSTCODES_LIMIT,
    NEAREST_POSTCODES_RADIUS_M,
    PPD_TYPE_FOR_PROPERTY_TYPE,
    YEARS_BACK,
    load_premium_sources,
)
from app.studio.features.s14_green_value_lens.hpi import (
    fetch_hpi_month,
    latest_available_month,
    month_key,
    region_slug,
)
from app.studio.features.s14_green_value_lens.price_paid import fetch_sales
from app.studio.features.s14_green_value_lens.schemas import Comp, GreenValue, PremiumSource
from app.studio.features.s14_green_value_lens.service import median_and_iqr, uplift_gbp

router = APIRouter(prefix="/homes/{ref}/green-value", tags=["studio:s14"])


@router.get("")
async def green_value(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
    target_band: str = Query("B"),
) -> GreenValue:
    home = await resolve_home(ref, session, user, include_household=True)
    now = datetime.now(UTC)
    today = date.today()
    since = today.replace(year=today.year - YEARS_BACK)

    ppd_type = PPD_TYPE_FOR_PROPERTY_TYPE.get(home.property.property_type)
    fallback_used = False
    slug = home.address.local_authority and region_slug(home.address.local_authority)
    latest_month = latest_available_month(today)
    latest_hpi = (
        await fetch_hpi_month(slug, latest_month, ppd_type, cache) if slug and ppd_type else None
    )

    comps: list[Comp] = []
    if ppd_type is not None:
        try:
            postcodes = await nearest_postcodes(
                home.address.lat,
                home.address.lon,
                NEAREST_POSTCODES_RADIUS_M,
                NEAREST_POSTCODES_LIMIT,
            )
        except UpstreamUnavailable:
            postcodes = []
            fallback_used = True

        for postcode in postcodes:
            try:
                sales = await fetch_sales(postcode, since, cache)
            except UpstreamUnavailable:
                fallback_used = True
                continue
            if not sales:
                continue
            try:
                info = await lookup_postcode(postcode, cache)
                distance_m = round(
                    haversine_m((home.address.lat, home.address.lon), (info.lat, info.lon))
                )
            except (UpstreamUnavailable, PostcodeNotFound):
                distance_m = 0
            for sale in sales:
                if sale.ppd_type != ppd_type:
                    continue
                sale_hpi = (
                    await fetch_hpi_month(slug, month_key(sale.at), ppd_type, cache)
                    if slug
                    else None
                )
                if sale_hpi and latest_hpi:
                    indexed = round(sale.price_gbp * latest_hpi["index"] / sale_hpi["index"])
                else:
                    indexed = sale.price_gbp
                comps.append(
                    Comp(
                        month=month_key(sale.at),
                        price_gbp=sale.price_gbp,
                        indexed_gbp=indexed,
                        property_type=home.property.property_type,
                        distance_m=distance_m,
                    )
                )
            if len(comps) >= MAX_COMPS:
                break

    comps = comps[:MAX_COMPS]

    if len(comps) >= MIN_COMPS_FOR_MEDIAN:
        method = "comparables"
        median, low, high = median_and_iqr([c.indexed_gbp for c in comps])
    elif latest_hpi is not None and latest_hpi.get("average_price"):
        method = "hpi_average"
        median = round(latest_hpi["average_price"] / 1000) * 1000
        low, high = median, median
    else:
        method = "hpi_average"
        median, low, high = 0, 0, 0
        fallback_used = True

    premium_sources_raw = load_premium_sources()
    pct_low = min(p["pct_low"] for p in premium_sources_raw)
    pct_high = max(p["pct_high"] for p in premium_sources_raw)
    current_band = home.property.epc_rating
    uplift_low, uplift_high = uplift_gbp(current_band, target_band, median, pct_low, pct_high)

    measures = await planner.load_measures(session)
    plan_items = None
    if home.home_id is not None:
        plan = await homes_service.latest_plan(session, home.home_id)
        if plan is not None:
            plan_items = [i.measure for i in plan.items if i.selected]
    if not plan_items:
        ranked = planner.rank(measures, home.risk, home.property, home.household, [])
        plan_items = [r.measure for r in ranked[:3]]

    plan_cost_low = sum(m.cost_low_gbp for m in plan_items) if plan_items else None
    plan_cost_high = sum(m.cost_high_gbp for m in plan_items) if plan_items else None

    return GreenValue(
        comparables_count=len(comps),
        method=method,
        indexed_median_gbp=median,
        range_low_gbp=low,
        range_high_gbp=high,
        comps=comps,
        current_band=current_band,
        target_band=target_band,
        uplift_low_gbp=uplift_low,
        uplift_high_gbp=uplift_high,
        plan_cost_low_gbp=plan_cost_low,
        plan_cost_high_gbp=plan_cost_high,
        premium_sources=[PremiumSource(**p) for p in premium_sources_raw],
        disclaimer=DISCLAIMER,
        evidence=[
            Evidence(
                label="Comparable sales",
                evidence="estimated" if fallback_used else "observed",
                source="Live sales data was unreachable"
                if fallback_used
                else "HM Land Registry Price Paid Data",
                source_url="https://landregistry.data.gov.uk/app/doc/ppd",
                retrieved_at=now,
            ),
            Evidence(
                label="House Price Index",
                evidence="official_modelled",
                source="UK House Price Index",
                source_url="https://landregistry.data.gov.uk/app/ukhpi",
                retrieved_at=now,
            ),
        ],
        fallback_used=fallback_used,
    )
