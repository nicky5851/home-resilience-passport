from datetime import UTC, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.api.errors import ApiError
from app.services.planner import load_measures
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s07_storm_replay.config import EVENTS
from app.studio.features.s07_storm_replay.era5_event import (
    fetch_event_window,
    synthetic_event_window,
)
from app.studio.features.s07_storm_replay.schemas import Replay, StormReplayIndex
from app.studio.features.s07_storm_replay.service import build_replay, event_by_id, summarise_event

router = APIRouter(prefix="/homes/{ref}/storm-replay", tags=["studio:s07"])


def _evidence(now: datetime, fallback_used: bool) -> list[Evidence]:
    return [
        Evidence(
            label="Weather during this event",
            evidence="estimated" if fallback_used else "observed",
            source="A typical-event estimate (ERA5 was unreachable)"
            if fallback_used
            else "Open-Meteo ERA5 reanalysis",
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            retrieved_at=now,
        )
    ]


async def _window(home, event: dict, cache) -> tuple[list, bool]:
    try:
        hourly = await fetch_event_window(
            home.address.lat, home.address.lon, event["start_date"], event["end_date"], cache
        )
        return hourly, False
    except UpstreamUnavailable:
        return synthetic_event_window(
            home.address.lat, event["start_date"], event["end_date"], event["kind"]
        ), True


@router.get("")
async def storm_replay_index(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> StormReplayIndex:
    home = await resolve_home(ref, session, user)
    now = datetime.now(UTC)
    fallback_used = False
    summaries = []
    for event in EVENTS:
        hourly, event_fallback = await _window(home, event, cache)
        fallback_used = fallback_used or event_fallback
        summaries.append(summarise_event(event, hourly))

    hardest = max(summaries, key=lambda s: s.severity)
    return StormReplayIndex(
        events=summaries,
        hardest_event_id=hardest.id,
        evidence=_evidence(now, fallback_used),
        fallback_used=fallback_used,
    )


@router.get("/{event_id}")
async def storm_replay(
    ref: str, event_id: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> Replay:
    event = event_by_id(event_id)
    if event is None:
        raise ApiError(404, "not_found", "Unknown event.")

    home = await resolve_home(ref, session, user)
    hourly, fallback_used = await _window(home, event, cache)
    measures = await load_measures(session)
    summary, points, peak_moments, lessons = build_replay(event, hourly, home.property, measures)

    now = datetime.now(UTC)
    return Replay(
        event=summary,
        hourly=points,
        peak_moments=peak_moments,
        lessons=lessons,
        evidence=_evidence(now, fallback_used),
        fallback_used=fallback_used,
    )
