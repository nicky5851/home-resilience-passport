from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.deps import ApiCacheDep, SessionDep
from app.api.errors import ApiError
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s03_meter_fingerprint.config import MAX_UPLOAD_BYTES
from app.studio.features.s03_meter_fingerprint.era5 import daily_mean_temps
from app.studio.features.s03_meter_fingerprint.parser import UnreadableFile, parse_consumption_csv
from app.studio.features.s03_meter_fingerprint.sample import sample_csv_text, sample_temps
from app.studio.features.s03_meter_fingerprint.schemas import Fingerprint, Fuel, Unit
from app.studio.features.s03_meter_fingerprint.service import (
    NotEnoughWinterData,
    build_fingerprint,
    join_weather,
)

router = APIRouter(prefix="/homes/{ref}/meter-fingerprint", tags=["studio:s03"])


def _evidence() -> list[Evidence]:
    now = datetime.now(UTC)
    return [
        Evidence(
            label="Outside temperature",
            evidence="observed",
            source="Open-Meteo ERA5 reanalysis",
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            retrieved_at=now,
        ),
        Evidence(
            label="Heat-loss coefficient",
            evidence="estimated",
            source="HRP change-point regression on your meter data",
            source_url="https://open-meteo.com/en/docs/historical-weather-api",
            retrieved_at=now,
            note="Internal/solar gains are folded into the base temperature",
        ),
    ]


@router.post("")
async def meter_fingerprint(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
    file: UploadFile,
    fuel: Annotated[Fuel, Form()],
    unit: Annotated[Unit, Form()],
) -> Fingerprint:
    home = await resolve_home(ref, session, user)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "file_too_large")
    try:
        readings = parse_consumption_csv(raw, unit)
    except UnreadableFile as e:
        raise ApiError(415, "unsupported_file", str(e)) from e

    temps = await daily_mean_temps(
        home.address.lat, home.address.lon, readings[0].day, readings[-1].day, cache
    )
    points = join_weather(readings, temps)
    try:
        result = build_fingerprint(readings, points, fuel, home.property.floor_area_m2)
    except NotEnoughWinterData as e:
        raise ApiError(400, "validation", "We need at least 60 days of winter readings.") from e
    result.evidence = _evidence()
    return result


@router.get("/sample.csv", response_class=PlainTextResponse)
async def sample_csv(ref: str) -> str:
    return sample_csv_text()


@router.get("/sample")
async def sample_fingerprint(ref: str, fuel: Fuel = "gas") -> Fingerprint:
    readings = parse_consumption_csv(sample_csv_text().encode("utf-8"), "kwh")
    temps = sample_temps()
    points = join_weather(readings, temps)
    result = build_fingerprint(readings, points, fuel, floor_area_m2=82.0)
    result.evidence = _evidence()
    result.fallback_used = False
    return result
