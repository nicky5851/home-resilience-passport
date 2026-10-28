from datetime import date, datetime
from typing import Literal

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence

Kind = Literal["wind", "rain", "heat"]


class LocalPeak(Contract):
    value: float
    unit: str
    at: datetime


class EventSummary(Contract):
    id: str
    name: str
    kind: Kind
    start_date: date
    end_date: date
    local_peak: LocalPeak
    severity: float
    headline: str


class StormReplayIndex(Contract):
    events: list[EventSummary]
    hardest_event_id: str
    evidence: list[Evidence]
    fallback_used: bool


class HourlyReplayPoint(Contract):
    at: datetime
    temp_c: float
    gust_kmh: float
    wind_kmh: float
    rain_mm: float
    indoor_now_c: float | None
    indoor_with_measures_c: float | None


class PeakMoment(Contract):
    at: datetime
    label: str


class Lesson(Contract):
    text: str
    measure_id: str | None


class Replay(Contract):
    event: EventSummary
    hourly: list[HourlyReplayPoint]
    peak_moments: list[PeakMoment]
    lessons: list[Lesson]
    evidence: list[Evidence]
    fallback_used: bool
