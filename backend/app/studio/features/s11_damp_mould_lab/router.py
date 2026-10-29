from datetime import UTC, date, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.db import models as db
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s11_damp_mould_lab.config import AWAABS_LAW_URL, LANDLORD_NOTE_BY_TENURE
from app.studio.features.s11_damp_mould_lab.era5_winter import (
    fetch_winter,
    last_winter_window,
    synthetic_winter,
)
from app.studio.features.s11_damp_mould_lab.schemas import DampLab, DampLabRequest
from app.studio.features.s11_damp_mould_lab.service import build_damp_lab

router = APIRouter(prefix="/homes/{ref}/damp-lab", tags=["studio:s11"])


async def _save_answers(session: SessionDep, home_id, body: DampLabRequest) -> None:
    row = await session.get(db.StudioDampAnswers, home_id)
    if row is None:
        row = db.StudioDampAnswers(home_id=home_id)
        session.add(row)
    row.occupants = body.occupants
    row.dries_clothes_indoors = body.dries_clothes_indoors
    row.kitchen_extractor = body.kitchen_extractor
    row.bathroom_extractor = body.bathroom_extractor
    row.trickle_vents = body.trickle_vents
    row.heating_setpoint_c = body.heating_setpoint_c
    await session.commit()


@router.post("")
async def damp_lab(
    ref: str, body: DampLabRequest, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> DampLab:
    home = await resolve_home(ref, session, user, include_household=True)
    now = datetime.now(UTC)

    if home.home_id is not None:
        await _save_answers(session, home.home_id, body)

    start, end, winter_label = last_winter_window(date.today())
    fallback_used = False
    try:
        hourly = await fetch_winter(home.address.lat, home.address.lon, start, end, cache)
    except UpstreamUnavailable:
        hourly = synthetic_winter(home.address.lat, start, end)
        fallback_used = True

    surfaces, monthly, interventions, wall_u, window_u, moisture_class = build_damp_lab(
        home.property, hourly, body, winter_label
    )

    landlord_note = None
    if home.household is not None and home.household.tenure in LANDLORD_NOTE_BY_TENURE:
        landlord_note = LANDLORD_NOTE_BY_TENURE[home.household.tenure]

    return DampLab(
        winter=winter_label,
        wall_u=wall_u,
        window_u=window_u,
        wall_u_source="age_band_default",
        moisture_class=moisture_class,
        surfaces=surfaces,
        monthly=monthly,
        interventions=interventions,
        landlord_note=landlord_note,
        evidence=[
            Evidence(
                label="Condensation risk model",
                evidence="estimated",
                source="Last winter's ERA5 weather and BS EN ISO 13788 surface-humidity criterion"
                if not fallback_used
                else "Synthetic winter weather (ERA5 unreachable) and BS EN ISO 13788",
                source_url=AWAABS_LAW_URL,
                retrieved_at=now,
            )
        ],
        fallback_used=fallback_used,
    )
