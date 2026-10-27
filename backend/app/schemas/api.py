"""Request and response bodies of the routes in spec §4.2 that are not §4.1 models."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import Band, Contract
from app.schemas.hazards import HazardInputs, RiskProfile
from app.schemas.household import Household
from app.schemas.property import Address, PropertyFacts
from app.schemas.score import ResilienceScore

ErrorCode = Literal[
    "validation",
    "unauthorised",
    "forbidden",
    "not_found",
    "unsupported_region",
    "conflict",
    "file_too_large",
    "unsupported_file",
    "rate_limited",
    "upstream_unavailable",
    "internal",
]


class ErrorBody(Contract):
    """Every error response (CONTRACT §3). `detail` is always one plain-English string."""

    detail: str
    code: ErrorCode


class Health(Contract):
    status: Literal["ok"]


class LookupAddress(Contract):
    line1: str
    uprn: str | None = None
    epc_rating: Band | None = None


class PostcodeLookup(Contract):
    postcode: str
    lat: float
    lon: float
    local_authority: str | None = None
    addresses: list[LookupAddress] = []


class HomeCreate(Contract):
    address: Address
    household: Household
    property_override: PropertyFacts | None = None


class HomeCreated(Contract):
    home_id: UUID


class HomeSummary(Contract):
    home_id: UUID
    line1: str
    postcode: str
    score: ResilienceScore | None = None


class Assessment(Contract):
    risk: RiskProfile
    score: ResilienceScore
    inputs: HazardInputs


class PlanRequest(Contract):
    budget_gbp: int | None = Field(default=None, ge=0, le=100_000)
    selected_ids: list[str] | None = None


class FundingRequest(Contract):
    selected_ids: list[str] = []


class ShareLink(Contract):
    share_token: str
    url: str


class ModelInfo(Contract):
    version: str
    trained_on: str
    metrics: dict[str, float] = {}


class ForgotPassword(Contract):
    email: str


class ResetPassword(Contract):
    token: str
    password: str
