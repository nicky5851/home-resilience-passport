from app.schemas.base import Contract
from app.studio.common.schemas import Evidence


class Climate(Contract):
    first_frost_avg: str | None
    last_frost_avg: str | None
    wettest_month: int
    windiest_month: int


class CareTask(Contract):
    id: str
    title: str
    why: str
    effort_minutes: int
    hazard: str | None
    guidance_url: str


class MonthTasks(Contract):
    month: int
    tasks: list[CareTask]


class CareCalendar(Contract):
    climate: Climate
    months: list[MonthTasks]
    evidence: list[Evidence]
    fallback_used: bool


class SubscribeResponse(Contract):
    url: str
