from app.schemas.base import Contract
from app.studio.common.schemas import Evidence


class Step(Contract):
    measure_id: str
    year: int


class NetZeroRoadRequest(Contract):
    steps: list[Step] = []


class YearRow(Contract):
    year: int
    co2_kg_do_nothing: int
    co2_kg_with_plan: int
    pathway_kg: int


class NetZeroRoad(Contract):
    years: list[YearRow]
    cumulative_saved_kg: int
    near_zero_year: int | None
    default_steps: list[Step]
    evidence: list[Evidence]
    fallback_used: bool
