from fastapi import APIRouter

from app.api.deps import SessionDep
from app.api.errors import ApiError
from app.services import planner
from app.studio.common.home_ref import MaybeUser, resolve_home, summarize
from app.studio.features.s01_retrofit_sandbox.schemas import (
    SandboxInit,
    SandboxState,
    SimulateRequest,
)
from app.studio.features.s01_retrofit_sandbox.service import (
    MAX_SELECTED,
    build_hotspots,
    build_sandbox_measures,
    eligible_measures,
    simulate,
)

router = APIRouter(prefix="/homes/{ref}/sandbox", tags=["studio:s01"])


@router.get("")
async def sandbox_init(ref: str, session: SessionDep, user: MaybeUser) -> SandboxInit:
    home = await resolve_home(ref, session, user, include_household=False)
    measures = await planner.load_measures(session)
    sandbox_measures = build_sandbox_measures(
        measures, home.property.property_type, set(home.completed_measure_ids)
    )
    baseline = simulate(home.risk, home.property, measures, [], [])
    return SandboxInit(
        home=summarize(home),
        baseline=baseline,
        hotspots=build_hotspots(sandbox_measures),
        measures=sandbox_measures,
        evidence=[],
        fallback_used=False,
    )


@router.post("/simulate")
async def sandbox_simulate(
    ref: str, body: SimulateRequest, session: SessionDep, user: MaybeUser
) -> SandboxState:
    home = await resolve_home(ref, session, user, include_household=False)
    measures = await planner.load_measures(session)

    ids = body.measure_ids
    if len(ids) > MAX_SELECTED or len(set(ids)) != len(ids):
        raise ApiError(400, "validation", "Choose up to 30 different measures.")
    allowed_ids = {m.id for m in eligible_measures(measures, home.property.property_type)}
    if not set(ids) <= allowed_ids:
        raise ApiError(400, "validation", "That measure isn't available for this home.")

    by_id = {m.id: m for m in measures}
    already_done = [
        by_id[mid] for mid in home.completed_measure_ids if mid in by_id and mid not in ids
    ]
    return simulate(home.risk, home.property, measures, already_done, ids)
