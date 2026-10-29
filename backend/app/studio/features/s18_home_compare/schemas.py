from typing import Literal

from app.schemas.base import Contract
from app.schemas.hazards import RiskProfile
from app.schemas.property import PropertyFacts
from app.schemas.score import ResilienceScore
from app.studio.common.schemas import Evidence

Label = Literal["A", "B", "C"]
Component = Literal["flood", "heat", "storm", "subsidence", "carbon", "overall"]


class Candidate(Contract):
    postcode: str
    line1: str
    uprn: str | None = None


class CompareRequest(Contract):
    candidates: list[Candidate]


class TopMeasure(Contract):
    measure_id: str
    name: str
    cost_low_gbp: int
    cost_high_gbp: int
    score_uplift: int


class CompareHome(Contract):
    label: Label
    line1: str
    postcode: str
    property: PropertyFacts
    risk: RiskProfile
    score: ResilienceScore
    top_measures: list[TopMeasure]
    cost_to_70_low_gbp: int | None
    cost_to_70_high_gbp: int | None


class Winners(Contract):
    flood: Label
    heat: Label
    storm: Label
    subsidence: Label
    carbon: Label
    overall: Label


class Compare(Contract):
    homes: list[CompareHome]
    winners: Winners
    summary: str
    evidence: list[Evidence]
    fallback_used: bool
