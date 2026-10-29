from datetime import date, datetime
from typing import Literal

from app.schemas.base import Contract, Level
from app.studio.common.schemas import Evidence

Glyph = Literal["sun", "cloud", "rain", "heavy_rain", "wind", "frost", "snow", "storm"]
AlertKind = Literal["frost", "hard_frost", "heat", "wind", "strong_wind", "heavy_rain"]


class Alert(Contract):
    kind: AlertKind
    level: Level
    title: str
    actions: list[str]
    when: str


class Day(Contract):
    date: date
    t_max_c: float | None
    t_min_c: float | None
    rain_mm: float | None
    gust_kmh: float | None
    uv_index: float | None
    glyph: Glyph
    alerts: list[Alert]


class WeekAhead(Contract):
    issued_at: datetime
    model: str
    headline: str
    days: list[Day]
    evidence: list[Evidence]
    fallback_used: bool
