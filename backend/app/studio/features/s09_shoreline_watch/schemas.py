from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Epoch = Literal[2055, 2105]
Scenario = Literal["with_smp", "no_active_intervention"]


class Projection(Contract):
    epoch: Epoch
    scenario: Scenario
    climate: str
    home_inside_zone: bool
    distance_m: int | None


class AdviceLink(Contract):
    label: str
    url: str


class Shoreline(Contract):
    coastal: bool
    nearest_coast_m: int | None
    projections: list[Projection]
    smp_policy: str | None
    features: dict
    advice_links: list[AdviceLink]
    insurance_note: str
    evidence: list[Evidence]
    fallback_used: bool
