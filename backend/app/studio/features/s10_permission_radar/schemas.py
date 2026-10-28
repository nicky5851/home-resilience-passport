from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Verdict = Literal["likely_permitted", "check_council", "consent_needed", "not_applicable"]


class Constraint(Contract):
    dataset: str
    label: str
    name: str | None
    reference: str | None
    entity_url: str | None
    applies: bool | None


class MeasureVerdict(Contract):
    measure_id: str
    name: str
    verdict: Verdict
    reasons: list[str]
    guidance_url: str


class PermissionRadar(Contract):
    local_planning_authority: str | None
    constraints: list[Constraint]
    measures: list[MeasureVerdict]
    disclaimer: str
    evidence: list[Evidence]
    fallback_used: bool
