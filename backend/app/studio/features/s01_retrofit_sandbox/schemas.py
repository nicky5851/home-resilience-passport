from typing import Literal

from app.schemas import Measure, ResilienceScore
from app.schemas.base import Contract
from app.studio.common.schemas import Evidence, StudioHomeSummary

HotspotId = Literal["roof", "walls", "windows", "door", "ground", "services"]


class Hotspot(Contract):
    id: HotspotId
    label: str
    measure_ids: list[str]


class SandboxMeasure(Contract):
    measure: Measure
    hotspot: HotspotId
    already_done: bool


class ScoreComponentDelta(Contract):
    name: str
    before: float
    after: float
    max_points: float


class SandboxState(Contract):
    score: ResilienceScore
    delta_points: int
    cost_low_gbp: int
    cost_high_gbp: int
    bill_saving_gbp_per_year: int
    co2_saved_kg_per_year: int
    components: list[ScoreComponentDelta]
    payback_years: float | None


class SandboxInit(Contract):
    home: StudioHomeSummary
    baseline: SandboxState
    hotspots: list[Hotspot]
    measures: list[SandboxMeasure]
    evidence: list[Evidence]
    fallback_used: bool


class SimulateRequest(Contract):
    measure_ids: list[str]
