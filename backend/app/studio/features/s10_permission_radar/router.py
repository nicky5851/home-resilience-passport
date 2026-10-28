from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import ApiCacheDep, SessionDep
from app.services import planner
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.common.schemas import Evidence
from app.studio.features.s10_permission_radar.config import DATASETS, DISCLAIMER, FIND_COUNCIL_URL
from app.studio.features.s10_permission_radar.planning_data import fetch_all
from app.studio.features.s10_permission_radar.schemas import Constraint, PermissionRadar
from app.studio.features.s10_permission_radar.service import entity_label, family_for, verdict_for

router = APIRouter(prefix="/homes/{ref}/permission-radar", tags=["studio:s10"])


@router.get("")
async def permission_radar(
    ref: str, session: SessionDep, user: MaybeUser, cache: ApiCacheDep
) -> PermissionRadar:
    home = await resolve_home(ref, session, user)
    now = datetime.now(UTC)

    entities_by_dataset = await fetch_all(list(DATASETS), home.address.lat, home.address.lon, cache)

    constraints: list[Constraint] = []
    applies_by_dataset: dict[str, bool | None] = {}
    fallback_used = False
    for dataset, label in DATASETS.items():
        entities = entities_by_dataset.get(dataset)
        if entities is None:
            applies_by_dataset[dataset] = None
            fallback_used = True
            constraints.append(
                Constraint(
                    dataset=dataset,
                    label=label,
                    name=None,
                    reference=None,
                    entity_url=None,
                    applies=None,
                )
            )
        elif entities:
            applies_by_dataset[dataset] = True
            constraints.append(entity_label(dataset, entities[0]))
        else:
            applies_by_dataset[dataset] = False
            constraints.append(
                Constraint(
                    dataset=dataset,
                    label=label,
                    name=None,
                    reference=None,
                    entity_url=None,
                    applies=False,
                )
            )

    all_measures = await planner.load_measures(session)
    measures = []
    for measure in all_measures:
        family = family_for(measure.id, measure.name)
        measures.append(verdict_for(measure, family, home.property, applies_by_dataset))

    return PermissionRadar(
        local_planning_authority=home.address.local_authority,
        constraints=constraints,
        measures=measures,
        disclaimer=DISCLAIMER,
        evidence=[
            Evidence(
                label="Planning constraints",
                evidence="estimated" if fallback_used else "observed",
                source="Live planning data was unreachable"
                if fallback_used
                else "Planning Data platform",
                source_url="https://www.planning.data.gov.uk/docs",
                retrieved_at=now,
            ),
            Evidence(
                label="Permitted development verdicts",
                evidence="estimated",
                source="HRP rules based on Planning Portal guidance and GPDO 2015 Schedule 2",
                source_url=FIND_COUNCIL_URL,
                retrieved_at=now,
            ),
        ],
        fallback_used=fallback_used,
    )
