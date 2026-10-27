from typing import Literal

from app.schemas.base import Contract, ExplanationText, MeasureCategory
from app.schemas.score import ResilienceScore


class Measure(Contract):
    """One row of data/reference/measures.csv (CONTRACT §5)."""

    id: str
    name: str
    category: MeasureCategory
    hazards_reduced: list[str] = []
    cost_low_gbp: int
    cost_high_gbp: int
    annual_bill_saving_gbp: int
    co2_saved_kg_per_year: int
    resilience_points: int
    property_types: list[str] = []  # empty = all
    renter_ok: bool
    needs_landlord: bool
    source_url: str


class PlanItem(Contract):
    measure: Measure
    rank: int
    score_uplift: int
    payback_years: float | None = None
    explanation: ExplanationText
    selected: bool


class Plan(Contract):
    items: list[PlanItem] = []
    total_cost_low_gbp: int
    total_cost_high_gbp: int
    projected_score: ResilienceScore
    explanation_source: Literal["llm", "template"]
