from datetime import date

from app.schemas.base import Contract
from app.studio.common.schemas import Evidence


class FloodEvent(Contract):
    name: str | None
    start_date: date | None
    end_date: date | None
    source: str | None
    cause: str | None
    distance_m: int
    contains_home: bool
    decade: int


class DecadeCount(Contract):
    decade: int
    count: int


class FloodMemory(Contract):
    inside_any_outline: bool
    nearest_m: int | None
    events: list[FloodEvent]
    by_decade: list[DecadeCount]
    outlines: dict
    caveat: str
    evidence: list[Evidence]
    fallback_used: bool
