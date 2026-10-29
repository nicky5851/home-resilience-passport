from datetime import UTC, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s12_breathe_easy.config import AQ_SOURCE, WEATHER_SOURCE
from app.studio.features.s12_breathe_easy.open_meteo import (
    fetch_air_quality,
    fetch_weather,
    synthetic_air_quality,
    synthetic_weather,
)
from app.studio.features.s12_breathe_easy.schemas import BreatheEasy, BreatheEasyRequest
from app.studio.features.s12_breathe_easy.service import (
    avoid_windows,
    best_windows,
    build_hours,
    today_summary,
)

router = APIRouter(prefix="/homes/{ref}/breathe-easy", tags=["studio:s12"])


@router.post("")
async def breathe_easy(
    ref: str, body: BreatheEasyRequest, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> BreatheEasy:
    home = await resolve_home(ref, session, user)
    now = datetime.now(UTC)

    fallback_used = False
    try:
        aq = await fetch_air_quality(home.address.lat, home.address.lon, cache)
    except UpstreamUnavailable:
        aq = synthetic_air_quality(home.address.lat, now)
        fallback_used = True
    try:
        wx = await fetch_weather(home.address.lat, home.address.lon, cache)
    except UpstreamUnavailable:
        wx = synthetic_weather(home.address.lat, now)
        fallback_used = True

    hours = build_hours(aq, wx, body)
    best = best_windows(hours)
    avoid = avoid_windows(hours)

    return BreatheEasy(
        hours=hours,
        best_windows=best,
        avoid_windows=avoid,
        today_summary=today_summary(hours, best, avoid),
        evidence=[
            Evidence(
                label="Air quality and pollen",
                evidence="estimated" if fallback_used else "official_modelled",
                source="Live air quality was unreachable" if fallback_used else AQ_SOURCE,
                source_url="https://open-meteo.com/en/docs/air-quality-api",
                retrieved_at=now,
            ),
            Evidence(
                label="Weather",
                evidence="estimated" if fallback_used else "official_modelled",
                source="Live weather was unreachable" if fallback_used else WEATHER_SOURCE,
                source_url="https://open-meteo.com/en/docs",
                retrieved_at=now,
            ),
        ],
        fallback_used=fallback_used,
    )
