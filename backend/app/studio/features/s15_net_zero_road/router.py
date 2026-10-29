from datetime import UTC, date, datetime

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.api.errors import ApiError
from app.services import planner
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s13_affordability_stress_test.service import estimate_kwh, heating_fuel_for
from app.studio.features.s15_net_zero_road.config import (
    YEAR_MAX,
    YEAR_MIN,
    load_ccc_pathway,
    load_grid_factors,
)
from app.studio.features.s15_net_zero_road.schemas import NetZeroRoad, NetZeroRoadRequest, YearRow
from app.studio.features.s15_net_zero_road.service import (
    cumulative_saved_kg,
    default_steps_for,
    do_nothing_kg,
    interpolate,
    near_zero_year,
    pathway_kg,
    with_plan_kg,
)

router = APIRouter(prefix="/homes/{ref}/net-zero-road", tags=["studio:s15"])


@router.post("")
async def net_zero_road(
    ref: str,
    body: NetZeroRoadRequest,
    session: SessionDep,
    user: MaybeUser,
) -> NetZeroRoad:
    if len(body.steps) > 12:
        raise ApiError(400, "validation", "Choose up to 12 upgrades.")
    for step in body.steps:
        if not (YEAR_MIN <= step.year <= YEAR_MAX):
            raise ApiError(400, "validation", f"Years must be between {YEAR_MIN} and {YEAR_MAX}.")

    home = await resolve_home(ref, session, user, include_household=True)
    measures = await planner.load_measures(session)
    measures_by_id = {m.id: m for m in measures}

    for step in body.steps:
        if step.measure_id not in measures_by_id:
            raise ApiError(400, "validation", "That measure isn't available.")

    heating_fuel = heating_fuel_for(home.property.main_fuel)
    kwh = estimate_kwh(home.property, heating_fuel)

    grid_series = load_grid_factors()
    ccc_series = load_ccc_pathway()
    baseline_grid_factor = interpolate(grid_series, YEAR_MIN)
    base_do_nothing_2025 = do_nothing_kg(kwh, heating_fuel, YEAR_MIN, grid_series)

    years: list[YearRow] = []
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        applied = [measures_by_id[s.measure_id] for s in body.steps if s.year <= year]
        years.append(
            YearRow(
                year=year,
                co2_kg_do_nothing=round(do_nothing_kg(kwh, heating_fuel, year, grid_series)),
                co2_kg_with_plan=round(
                    with_plan_kg(
                        kwh, heating_fuel, year, grid_series, applied, baseline_grid_factor
                    )
                ),
                pathway_kg=round(pathway_kg(base_do_nothing_2025, year, ccc_series)),
            )
        )

    completed_measures = [m for m in measures if m.id in home.completed_measure_ids]
    ranked = planner.rank(measures, home.risk, home.property, home.household, completed_measures)
    default_steps = default_steps_for(ranked, date.today().year)

    now = datetime.now(UTC)
    return NetZeroRoad(
        years=years,
        cumulative_saved_kg=cumulative_saved_kg(years),
        near_zero_year=near_zero_year(years),
        default_steps=default_steps,
        evidence=[
            Evidence(
                label="Grid electricity emissions factor",
                evidence="official_modelled",
                source="DESNZ: Valuation of energy use and GHG emissions for appraisal",
                source_url=(
                    "https://www.gov.uk/government/publications/"
                    "valuation-of-energy-use-and-greenhouse-gas-emissions-for-appraisal"
                ),
                retrieved_at=now,
            ),
            Evidence(
                label="Residential pathway (illustrative)",
                evidence="estimated",
                source="Climate Change Committee, Seventh Carbon Budget",
                source_url="https://www.theccc.org.uk/publication/the-seventh-carbon-budget/",
                retrieved_at=now,
            ),
        ],
        fallback_used=False,
    )
