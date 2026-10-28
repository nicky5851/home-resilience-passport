from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s05_solar_roof_studio.config import (
    ASPECT_MAX,
    ASPECT_MIN,
    KWP_MAX,
    KWP_MIN,
    PITCH_MAX,
    PITCH_MIN,
)
from app.studio.features.s05_solar_roof_studio.schemas import SolarRequest, SolarResult
from app.studio.features.s05_solar_roof_studio.service import build_solar

router = APIRouter(prefix="/homes/{ref}/solar", tags=["studio:s05"])


@router.post("")
async def solar(
    ref: str,
    body: SolarRequest,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
) -> SolarResult:
    home = await resolve_home(ref, session, user)

    aspect = max(ASPECT_MIN, min(ASPECT_MAX, body.aspect_deg))
    pitch = max(PITCH_MIN, min(PITCH_MAX, body.pitch_deg))
    kwp = None if body.kwp is None else max(KWP_MIN, min(KWP_MAX, body.kwp))

    result = await build_solar(
        home.property,
        home.address.lat,
        home.address.lon,
        aspect,
        pitch,
        kwp,
        body.battery_kwh,
        body.export_p_per_kwh,
        cache,
    )

    now = datetime.now(UTC)
    result.evidence = [
        Evidence(
            label="Solar generation estimate",
            evidence="estimated" if result.fallback_used else "official_modelled",
            source="PVGIS 5.3 (EU Joint Research Centre)"
            if not result.fallback_used
            else "A typical-roof estimate (PVGIS was unreachable)",
            source_url="https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en",
            retrieved_at=now,
        ),
        Evidence(
            label="Import/export prices",
            evidence="estimated",
            source="Ofgem price cap (import) and a typical SEG fixed rate (export, overridable)",
            source_url="https://www.ofgem.gov.uk/environmental-and-social-schemes/smart-export-guarantee-seg",
            retrieved_at=now,
        ),
    ]
    return result
