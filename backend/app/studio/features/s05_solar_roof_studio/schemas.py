from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

KwpSource = Literal["user", "estimated_from_roof"]
Suitability = Literal["good", "fair", "poor", "freeholder_needed"]


class OrientationPoint(Contract):
    aspect_deg: int
    annual_kwh: int


class SolarRequest(Contract):
    aspect_deg: int = 0
    pitch_deg: int = 35
    kwp: float | None = None
    battery_kwh: Literal[0, 5, 10] = 0
    export_p_per_kwh: float | None = None


class SolarResult(Contract):
    kwp: float
    kwp_source: KwpSource
    annual_kwh: int
    monthly_kwh: list[int]
    self_use_kwh: int
    export_kwh: int
    annual_saving_gbp: int
    install_cost_low_gbp: int
    install_cost_high_gbp: int
    payback_years: float | None
    breakeven_year: int | None
    lifetime_saving_gbp: int
    co2_saved_kg_per_year: int
    orientation_rose: list[OrientationPoint]
    suitability: Suitability
    suitability_note: str
    evidence: list[Evidence]
    fallback_used: bool
