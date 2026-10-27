from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from app.schemas.base import Contract
from app.schemas.hazards import RiskProfile
from app.schemas.household import Household
from app.schemas.plan import Plan
from app.schemas.property import Address, PropertyFacts
from app.schemas.score import ResilienceScore


class PassportEvent(Contract):
    id: UUID
    kind: Literal["assessed", "plan_saved", "work_recorded", "shared"]
    at: datetime
    score_after: int | None = None
    # work_recorded: {measure_id, completed_on, cost_gbp, has_certificate, certificate_name}
    detail: dict[str, Any] = {}


class PublicPassport(Contract):
    """What a share link shows: no household, no share token, no certificate names."""

    home_id: UUID
    address: Address
    property: PropertyFacts
    latest_risk: RiskProfile
    latest_score: ResilienceScore
    plan: Plan | None = None
    events: list[PassportEvent] = []


class Passport(PublicPassport):
    household: Household
    share_token: str | None = None
