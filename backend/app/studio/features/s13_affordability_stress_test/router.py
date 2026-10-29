from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.services import planner
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s13_affordability_stress_test.config import (
    HELP_LINKS,
    INCOME_BAND_MIDPOINT_GBP,
    LILEE_BANDS,
    LILEE_INCOME_BAND,
    OIL_LPG_SOURCE_URL,
    SCENARIOS,
    load_price_cap,
)
from app.studio.features.s13_affordability_stress_test.schemas import (
    Affordability,
    HelpLink,
    Kwh,
    Scenario,
)
from app.studio.features.s13_affordability_stress_test.service import (
    after_plan_cost_gbp,
    annual_cost_gbp,
    build_scenario,
    estimate_kwh,
    heating_fuel_for,
    shock_30_cap,
)

router = APIRouter(prefix="/homes/{ref}/affordability", tags=["studio:s13"])


@router.get("")
async def affordability(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    measure_ids: str | None = Query(None),
) -> Affordability:
    home = await resolve_home(ref, session, user, include_household=True)
    now = datetime.now(UTC)

    heating_fuel = heating_fuel_for(home.property.main_fuel)
    kwh = estimate_kwh(home.property, heating_fuel)

    all_measures = await planner.load_measures(session)
    selected_ids = {i for i in (measure_ids or "").split(",") if i}
    selected = [m for m in all_measures if m.id in selected_ids]

    caps = load_price_cap()
    periods = sorted(caps)
    cap_by_scenario = {
        "pre_crisis_2021": caps[periods[0]],
        "peak_2022": caps[periods[1]],
        "today": caps[periods[2]],
    }
    cap_by_scenario["shock_30"] = shock_30_cap(cap_by_scenario["today"])
    today_cost = annual_cost_gbp(kwh, heating_fuel, cap_by_scenario["today"])

    income_midpoint = None
    if home.home_id is not None and home.household is not None:
        income_midpoint = INCOME_BAND_MIDPOINT_GBP.get(home.household.income_band)

    scenarios: list[Scenario] = []
    for entry in SCENARIOS:
        cap = cap_by_scenario[entry["id"]]
        cost = annual_cost_gbp(kwh, heating_fuel, cap)
        price_ratio = cost / today_cost if today_cost else 1.0
        standing_floor = annual_cost_gbp(Kwh(heating_fuel=0, electricity=0), heating_fuel, cap)
        cost_after = (
            after_plan_cost_gbp(cost, selected, price_ratio, standing_floor) if selected else None
        )
        scenarios.append(
            build_scenario(entry["id"], entry["label"], cost, cost_after, income_midpoint)
        )

    lilee_indicator = None
    if (
        home.home_id is not None
        and home.household is not None
        and home.property.epc_rating is not None
    ):
        lilee_indicator = (
            home.property.epc_rating in LILEE_BANDS
            and home.household.income_band == LILEE_INCOME_BAND
        )

    return Affordability(
        kwh=kwh,
        kwh_source="estimated",
        heating_fuel=heating_fuel,
        scenarios=scenarios,
        lilee_indicator=lilee_indicator,
        help_links=[HelpLink(**link) for link in HELP_LINKS],
        evidence=[
            Evidence(
                label="Price cap scenarios",
                evidence="official_modelled",
                source="Ofgem energy price cap and the 2022-23 Energy Price Guarantee",
                source_url="https://www.ofgem.gov.uk/energy-price-cap",
                retrieved_at=now,
            ),
            Evidence(
                label="Oil/LPG unit prices",
                evidence="estimated",
                source="Placeholder, not read from DESNZ quarterly energy prices this session",
                source_url=OIL_LPG_SOURCE_URL,
                retrieved_at=now,
            ),
        ],
        fallback_used=False,
    )
