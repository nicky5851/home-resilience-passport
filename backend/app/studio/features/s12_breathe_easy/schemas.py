from datetime import datetime
from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

DaqiBand = Literal["low", "moderate", "high", "very_high"]
PollenLevel = Literal["none", "low", "moderate", "high"]
Advice = Literal["open", "brief_airing", "keep_closed"]


class BreatheEasyRequest(Contract):
    pollen_sensitive: bool = False
    pollution_sensitive: bool = False


class HourReading(Contract):
    at: datetime
    daqi: int | None
    daqi_band: DaqiBand | None
    pm2_5: float | None
    no2: float | None
    o3: float | None
    pollen_level: PollenLevel | None
    temp_c: float | None
    rh_pct: float | None
    score: int
    advice: Advice


class Window(Contract):
    start_at: datetime
    end_at: datetime
    reason: str


class BreatheEasy(Contract):
    hours: list[HourReading]
    best_windows: list[Window]
    avoid_windows: list[Window]
    today_summary: str
    evidence: list[Evidence]
    fallback_used: bool
