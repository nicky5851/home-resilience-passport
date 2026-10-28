from datetime import UTC, datetime

from fastapi import APIRouter

from app.adapters.http import UpstreamUnavailable
from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s06_grid_carbon_clock.carbon_intensity import (
    current_mix,
    forecast_48h,
    outcode_from_postcode,
    synthetic_periods,
)
from app.studio.features.s06_grid_carbon_clock.schemas import GridCarbon
from app.studio.features.s06_grid_carbon_clock.service import (
    best_windows_for_all,
    greenest_and_dirtiest,
    parse_current,
    parse_forecast,
)

router = APIRouter(prefix="/homes/{ref}/grid-carbon", tags=["studio:s06"])


@router.get("")
async def grid_carbon(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> GridCarbon:
    home = await resolve_home(ref, session, user)
    outcode = outcode_from_postcode(home.address.postcode)
    now = datetime.now(UTC)
    from_iso = now.strftime("%Y-%m-%dT%H:%MZ")

    fallback_used = False
    try:
        current = await current_mix(outcode, cache)
        forecast_data = await forecast_48h(outcode, from_iso, cache)
        region_name = current["region_name"]
        current_period = current["periods"][0]
        forecast_periods = forecast_data["periods"]
    except (UpstreamUnavailable, IndexError, KeyError):
        region_name = "your region"
        fallback_periods = synthetic_periods(outcode, now, 96)
        current_period = fallback_periods[0]
        forecast_periods = fallback_periods
        fallback_used = True

    now_intensity = parse_current(current_period)
    forecast = parse_forecast(forecast_periods)
    best_windows = best_windows_for_all(forecast, now_intensity.intensity_g_per_kwh)
    greenest, dirtiest = greenest_and_dirtiest(forecast)

    evidence = [
        Evidence(
            label="Grid carbon intensity",
            evidence="estimated" if fallback_used else "official_modelled",
            source="A typical day/night estimate (the live forecast was unreachable)"
            if fallback_used
            else "NESO Carbon Intensity forecast",
            source_url="https://carbon-intensity.github.io/api-definitions/",
            retrieved_at=now,
        )
    ]

    return GridCarbon(
        region_name=region_name,
        now=now_intensity,
        forecast=forecast,
        best_windows=best_windows,
        greenest_slot=greenest,
        dirtiest_slot=dirtiest,
        evidence=evidence,
        fallback_used=fallback_used,
    )
