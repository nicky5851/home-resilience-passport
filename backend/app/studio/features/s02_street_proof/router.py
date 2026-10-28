from datetime import UTC, datetime

from fastapi import APIRouter, Query

from app.api.deps import ApiCacheDep, SessionDep
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s02_street_proof.config import RADIUS_DEFAULT_M, RADIUS_MAX_M, RADIUS_MIN_M
from app.studio.features.s02_street_proof.schemas import StreetProof
from app.studio.features.s02_street_proof.service import build_street_proof

router = APIRouter(prefix="/homes/{ref}/street-proof", tags=["studio:s02"])


@router.get("")
async def street_proof(
    ref: str,
    session: SessionDep,
    user: MaybeUser,
    cache: ApiCacheDep,
    radius_m: int = Query(RADIUS_DEFAULT_M, ge=RADIUS_MIN_M, le=RADIUS_MAX_M),
) -> StreetProof:
    home = await resolve_home(ref, session, user)
    result = await build_street_proof(
        home.property, home.property.epc_score, home.address.lat, home.address.lon, radius_m, cache
    )
    now = datetime.now(UTC)
    result.evidence = [
        Evidence(
            label="Peer EPC ratings",
            evidence="official_modelled",
            source="EPC register (SAP assessment)",
            source_url="https://www.gov.uk/find-energy-certificate",
            retrieved_at=now,
        ),
        Evidence(
            label="Upgrades peers made",
            evidence="estimated",
            source="Inferred by HRP from certificate changes",
            source_url="https://www.gov.uk/find-energy-certificate",
            retrieved_at=now,
            note="Comparing each home's earliest and latest certificate text",
        ),
    ]
    return result
