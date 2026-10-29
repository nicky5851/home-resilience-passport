from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Method = Literal["comparables", "hpi_average"]


class Comp(Contract):
    month: str
    price_gbp: int
    indexed_gbp: int
    property_type: str
    distance_m: int


class PremiumSource(Contract):
    study: str
    url: str
    year: int
    pct_low: float
    pct_high: float


class GreenValue(Contract):
    comparables_count: int
    method: Method
    indexed_median_gbp: int
    range_low_gbp: int
    range_high_gbp: int
    comps: list[Comp]
    current_band: str | None
    target_band: str
    uplift_low_gbp: int | None
    uplift_high_gbp: int | None
    plan_cost_low_gbp: int | None
    plan_cost_high_gbp: int | None
    premium_sources: list[PremiumSource]
    disclaimer: str
    evidence: list[Evidence]
    fallback_used: bool
