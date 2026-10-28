"""Shared Studio response types (docs/studio/N_20_function.md §1.5, §3)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas import (
    Address,
    HazardInputs,
    Household,
    PropertyFacts,
    ResilienceScore,
    RiskProfile,
)
from app.schemas.base import Contract

EvidenceClass = Literal["observed", "official_modelled", "estimated"]


class Evidence(Contract):
    label: str
    evidence: EvidenceClass
    source: str
    source_url: str
    retrieved_at: datetime
    note: str | None = None


Chapter = Literal["understand", "measure", "plan", "live", "money", "ask"]


class FeatureMeta(Contract):
    id: str
    slug: str
    title: str
    chapter: Chapter
    pitch: str
    needs_login: bool
    demo_ok: bool


class StudioHomeSummary(Contract):
    ref: str
    is_demo: bool
    line1: str | None = None
    postcode_district: str | None = None
    lat: float
    lon: float
    property: PropertyFacts
    score: ResilienceScore


class StudioHome(Contract):
    """Resolved by `resolve_home()`: everything the 20 features read, in one place."""

    ref: str
    is_demo: bool
    home_id: UUID | None = None
    address: Address
    property: PropertyFacts
    inputs: HazardInputs
    risk: RiskProfile
    score: ResilienceScore
    household: Household | None = None
    completed_measure_ids: list[str] = []


def postcode_district(postcode: str) -> str:
    """'SW1A 1AA' -> 'SW1A' — never the full postcode in a public response."""
    return postcode.split(" ")[0].strip()
