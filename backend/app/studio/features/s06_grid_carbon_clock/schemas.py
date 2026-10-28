from datetime import datetime
from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Index = Literal["very low", "low", "moderate", "high", "very high"]


class MixShare(Contract):
    fuel: str
    percent: float


class CurrentIntensity(Contract):
    intensity_g_per_kwh: int
    index: Index
    mix: list[MixShare]


class ForecastSlot(Contract):
    from_at: datetime
    to_at: datetime
    intensity_g_per_kwh: int
    index: Index


class BestWindow(Contract):
    appliance_id: str
    label: str
    start_at: datetime
    end_at: datetime
    avg_intensity_g_per_kwh: float
    saving_pct_vs_now: float
    saving_g: float


class Slot(Contract):
    from_at: datetime
    intensity_g_per_kwh: int


class GridCarbon(Contract):
    region_name: str
    now: CurrentIntensity
    forecast: list[ForecastSlot]
    best_windows: list[BestWindow]
    greenest_slot: Slot
    dirtiest_slot: Slot
    evidence: list[Evidence]
    fallback_used: bool
