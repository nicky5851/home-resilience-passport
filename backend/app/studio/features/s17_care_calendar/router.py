import hashlib
import secrets
from datetime import UTC, date, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, CurrentUserRow, SessionDep
from app.api.errors import ApiError
from app.db import models as db
from app.services import homes as homes_service
from app.services import passport as passports
from app.services import planner
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s17_care_calendar.adapter import fetch_climatology, synthetic_climatology
from app.studio.features.s17_care_calendar.climatology import (
    first_and_last_frost,
    wettest_month,
    windiest_month,
)
from app.studio.features.s17_care_calendar.config import ICAL_TOKEN_BYTES, load_care_tasks
from app.studio.features.s17_care_calendar.ics import write_ics
from app.studio.features.s17_care_calendar.schemas import (
    CareCalendar,
    Climate,
    MonthTasks,
    SubscribeResponse,
)
from app.studio.features.s17_care_calendar.tasks import TaskContext, resolve_day, tasks_by_month

router = APIRouter(tags=["studio:s17"])


def _hazard_level(risk, hazard: str) -> str:
    return next((lvl.today for lvl in risk.levels if lvl.hazard == hazard), "low")


async def _climate_and_months(
    lat: float, lon: float, prop, risk, completed_measure_ids: list[str], cache
) -> tuple[Climate, list[MonthTasks], bool]:
    fallback_used = False
    try:
        series = await fetch_climatology(lat, lon, cache)
    except UpstreamUnavailable:
        series = synthetic_climatology(f"{lat}:{lon}")
        fallback_used = True

    first_frost, last_frost = first_and_last_frost(series)
    wettest = wettest_month(series)
    windiest = windiest_month(series)

    ctx = TaskContext(
        main_heating=prop.main_heating,
        main_fuel=prop.main_fuel,
        storm_level=_hazard_level(risk, "storm"),
        river_sea_flood_level=_hazard_level(risk, "river_sea_flood"),
        completed_measure_ids=completed_measure_ids,
    )
    months = tasks_by_month(load_care_tasks(), ctx, first_frost, wettest, windiest, date.today())
    climate = Climate(
        first_frost_avg=first_frost,
        last_frost_avg=last_frost,
        wettest_month=wettest,
        windiest_month=windiest,
    )
    return climate, [MonthTasks(**m) for m in months], fallback_used


@router.get("/homes/{ref}/care-calendar")
async def care_calendar(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> CareCalendar:
    home = await resolve_home(ref, session, user)
    climate, months, fallback_used = await _climate_and_months(
        home.address.lat,
        home.address.lon,
        home.property,
        home.risk,
        home.completed_measure_ids,
        cache,
    )
    return CareCalendar(
        climate=climate,
        months=months,
        evidence=[
            Evidence(
                label="Local climatology (1991-2020)",
                evidence="estimated" if fallback_used else "official_modelled",
                source="Open-Meteo Historical Weather (ERA5)",
                source_url="https://open-meteo.com/en/docs/historical-weather-api",
                retrieved_at=datetime.now(UTC),
            )
        ],
        fallback_used=fallback_used,
    )


@router.get("/homes/{ref}/care-calendar.ics")
async def care_calendar_ics(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> Response:
    home = await resolve_home(ref, session, user)
    climate, months, _ = await _climate_and_months(
        home.address.lat,
        home.address.lon,
        home.property,
        home.risk,
        home.completed_measure_ids,
        cache,
    )
    home_hash = hashlib.sha256(ref.encode()).hexdigest()[:12]
    tasks = _flatten_for_ics(months, climate.first_frost_avg)
    body = write_ics(tasks, home_hash, datetime.now(UTC))
    return Response(content=body, media_type="text/calendar")


def _flatten_for_ics(months: list[MonthTasks], first_frost_avg: str | None) -> list[dict]:
    schedules = {t["id"]: t["schedule"] for t in load_care_tasks()}
    flat = []
    for m in months:
        for t in m.tasks:
            day = resolve_day(schedules[t.id], first_frost_avg)
            flat.append({"id": t.id, "title": t.title, "why": t.why, "month": m.month, "day": day})
    return flat


@router.post("/homes/{ref}/care-calendar/subscribe")
async def subscribe(
    ref: str, session: SessionDep, user: CurrentUserRow, request: Request
) -> SubscribeResponse:
    home = await resolve_home(ref, session, user)
    if home.home_id is None:
        raise ApiError(400, "validation", "Only your own homes can subscribe to a calendar feed.")

    token = secrets.token_urlsafe(ICAL_TOKEN_BYTES)
    existing = await session.get(db.StudioCalendarToken, home.home_id)
    if existing is not None:
        existing.token = token
    else:
        session.add(db.StudioCalendarToken(home_id=home.home_id, token=token))
    await session.commit()

    url = f"{str(request.base_url).rstrip('/')}/api/v1/studio/ical/{token}.ics"
    return SubscribeResponse(url=url)


@router.delete("/homes/{ref}/care-calendar/subscribe", status_code=204)
async def unsubscribe(ref: str, session: SessionDep, user: CurrentUserRow) -> None:
    home = await resolve_home(ref, session, user)
    if home.home_id is None:
        raise ApiError(400, "validation", "Only your own homes can unsubscribe.")
    existing = await session.get(db.StudioCalendarToken, home.home_id)
    if existing is not None:
        await session.delete(existing)
        await session.commit()


@router.get("/ical/{token}.ics")
async def ical_feed(token: str, session: SessionDep, cache: ApiCacheDep) -> Response:
    row = await session.scalar(
        select(db.StudioCalendarToken).where(db.StudioCalendarToken.token == token)
    )
    if row is None:
        raise ApiError(404, "not_found", "This calendar feed is no longer available.")

    stub = await homes_service.by_id_unchecked(session, row.home_id)
    if stub is None or stub.assessment is None:
        raise ApiError(404, "not_found", "This calendar feed is no longer available.")

    measures = await planner.load_measures(session)
    completed_ids = [m.id for m in passports.completed(stub, measures)]
    prop = stub.real["property"]
    risk = stub.assessment.risk

    climate, months, _ = await _climate_and_months(
        stub.real["address"].lat, stub.real["address"].lon, prop, risk, completed_ids, cache
    )
    home_hash = hashlib.sha256(str(row.home_id).encode()).hexdigest()[:12]
    tasks = _flatten_for_ics(months, climate.first_frost_avg)
    body = write_ics(tasks, home_hash, datetime.now(UTC))
    return Response(content=body, media_type="text/calendar")
