from typing import Literal

from pydantic import Field

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Surface = Literal["wall", "corner", "window"]
Level = Literal["low", "medium", "high"]


class DampLabRequest(Contract):
    occupants: int = Field(ge=1, le=10)
    dries_clothes_indoors: bool
    kitchen_extractor: bool
    bathroom_extractor: bool
    trickle_vents: bool
    heating_setpoint_c: float = 18.0


class SurfaceRisk(Contract):
    surface: Surface
    risk_hours_pct: float
    level: Level


class MonthlyCornerRisk(Contract):
    month: str
    corner_risk_pct: float


class Intervention(Contract):
    id: str
    label: str
    corner_risk_pct_after: float
    delta_pct: float


class DampLab(Contract):
    winter: str
    wall_u: float
    window_u: float
    wall_u_source: Literal["epc_description", "age_band_default"]
    moisture_class: Literal[1, 2, 3, 4]
    surfaces: list[SurfaceRisk]
    monthly: list[MonthlyCornerRisk]
    interventions: list[Intervention]
    landlord_note: str | None
    evidence: list[Evidence]
    fallback_used: bool
