from datetime import UTC, date, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s16_week_ahead.adapter import fetch_week, synthetic_week
from app.studio.features.s16_week_ahead.config import MODEL_LABEL, PRIMARY_MODEL, SOURCE_URL
from app.studio.features.s16_week_ahead.rules import (
    frost_alert,
    glyph_for,
    heat_alert,
    rain_alert,
    wind_alert,
)
from app.studio.features.s16_week_ahead.schemas import Day, WeekAhead

router = APIRouter(prefix="/homes/{ref}/week-ahead", tags=["studio:s16"])


def _level_for(risk, hazard: str) -> str:
    return next((lvl.today for lvl in risk.levels if lvl.hazard == hazard), "low")


def _headline(days: list[Day]) -> str:
    kinds = {a.kind for d in days for a in d.alerts}
    if "hard_frost" in kinds:
        return "A hard frost is coming this week - protect your pipes."
    if "strong_wind" in kinds:
        return "Strong winds this week - secure loose items outside."
    if "heavy_rain" in kinds:
        return "Heavy rain this week - check your gutters and drains."
    if "heat" in kinds:
        return "A hot spell this week - keep the home cool."
    if kinds:
        return "A mild week, with one or two things worth doing."
    return "A quiet week ahead - nothing urgent for your home."


@router.get("")
async def week_ahead(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
) -> WeekAhead:
    home = await resolve_home(ref, session, user)

    fallback_used = False
    try:
        forecast = await fetch_week(home.address.lat, home.address.lon, cache)
    except UpstreamUnavailable:
        forecast = synthetic_week(ref, date.today())
        fallback_used = True

    top_floor = bool(home.property.top_floor)
    storm_high = _level_for(home.risk, "storm") == "high"
    flood_risk = _level_for(home.risk, "river_sea_flood") in ("medium", "high")

    days: list[Day] = []
    for row in forecast:
        when = row.at.strftime("%A")
        alerts = [
            a
            for a in (
                frost_alert(row.t_min_c, when),
                heat_alert(row.t_max_c, top_floor, when),
                wind_alert(row.gust_kmh, storm_high, when),
                rain_alert(row.rain_mm, flood_risk, when),
            )
            if a is not None
        ]
        days.append(
            Day(
                date=row.at,
                t_max_c=row.t_max_c,
                t_min_c=row.t_min_c,
                rain_mm=row.rain_mm,
                gust_kmh=row.gust_kmh,
                uv_index=row.uv_index,
                glyph=glyph_for(row.t_max_c, row.t_min_c, row.rain_mm, row.gust_kmh),
                alerts=alerts,
            )
        )

    return WeekAhead(
        issued_at=datetime.now(UTC),
        model=f"{PRIMARY_MODEL} (synthetic fallback)" if fallback_used else PRIMARY_MODEL,
        headline=_headline(days),
        days=days,
        evidence=[
            Evidence(
                label="Weather forecast",
                evidence="estimated" if fallback_used else "official_modelled",
                source=MODEL_LABEL,
                source_url=SOURCE_URL,
                retrieved_at=datetime.now(UTC),
            )
        ],
        fallback_used=fallback_used,
    )
