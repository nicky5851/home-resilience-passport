"""Database tables (spec N4).

Every table hanging off a user or a home uses ON DELETE CASCADE, so deleting a user removes
everything they own in one statement (uploaded files are removed by the storage service, N14).
JSONB columns hold contract models (`app.schemas`) dumped with `model_dump(mode="json")`.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import CERTIFICATE_NAME_MAX_CHARS


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[str]: ARRAY(Text),
        datetime: DateTime(timezone=True),
        uuid.UUID: UUID(as_uuid=True),
    }


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(server_default=func.now())


def _home_fk(**kw: Any) -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("homes.id", ondelete="CASCADE"), **kw)


# --- Accounts -----------------------------------------------------------------------------


class User(Base):
    """fastapi-users' SQLAlchemyBaseUserTableUUID columns, plus our own (CONTRACT §4)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(1024))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy_accepted_at: Mapped[datetime | None]
    privacy_version: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = _created_at()
    last_seen_at: Mapped[datetime | None]


# --- Homes and everything hanging off them ------------------------------------------------


class Home(Base):
    __tablename__ = "homes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    uprn: Mapped[str | None] = mapped_column(String(20))
    line1: Mapped[str] = mapped_column(String(200))
    postcode: Mapped[str] = mapped_column(String(8), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    local_authority: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(20))
    property: Mapped[dict[str, Any]]  # PropertyFacts
    created_at: Mapped[datetime] = _created_at()


class Household(Base):
    """One per home. `vulnerable` is special category data (CONTRACT §6)."""

    __tablename__ = "households"

    home_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True
    )
    tenure: Mapped[str] = mapped_column(String(20))
    income_band: Mapped[str] = mapped_column(String(20))
    budget_gbp: Mapped[int] = mapped_column(Integer)
    priorities: Mapped[list[str]] = mapped_column(default=list)
    vulnerable: Mapped[bool | None]
    consent_lloyds_data: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    home_id: Mapped[uuid.UUID] = _home_fk(index=True)
    inputs: Mapped[dict[str, Any]]  # HazardInputs
    risk: Mapped[dict[str, Any]]  # RiskProfile
    score: Mapped[dict[str, Any]]  # ResilienceScore
    scoring_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = _created_at()


class SavedPlan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = _uuid_pk()
    home_id: Mapped[uuid.UUID] = _home_fk(index=True)
    budget_gbp: Mapped[int] = mapped_column(Integer)
    selected_ids: Mapped[list[str]] = mapped_column(default=list)
    plan: Mapped[dict[str, Any]]  # Plan
    created_at: Mapped[datetime] = _created_at()


class PassportEvent(Base):
    __tablename__ = "passport_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    home_id: Mapped[uuid.UUID] = _home_fk(index=True)
    kind: Mapped[str] = mapped_column(String(20))
    at: Mapped[datetime] = mapped_column(server_default=func.now())
    score_after: Mapped[int | None]
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict)


class WorkFile(Base):
    """A certificate uploaded with a work record (CONTRACT §6). The file lives in storage."""

    __tablename__ = "work_files"

    id: Mapped[uuid.UUID] = _uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("passport_events.id", ondelete="CASCADE"), unique=True
    )
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    certificate_name: Mapped[str] = mapped_column(String(CERTIFICATE_NAME_MAX_CHARS))
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = _created_at()


class ShareLink(Base):
    """At most one live link per home; a new token replaces the old one."""

    __tablename__ = "share_links"

    home_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created_at()


# --- Reference data (A's CSVs, CONTRACT §5) -----------------------------------------------


class Measure(Base):
    __tablename__ = "measures"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(20))
    hazards_reduced: Mapped[list[str]]
    cost_low_gbp: Mapped[int]
    cost_high_gbp: Mapped[int]
    annual_bill_saving_gbp: Mapped[int]
    co2_saved_kg_per_year: Mapped[int]
    resilience_points: Mapped[int]
    property_types: Mapped[list[str]]
    renter_ok: Mapped[bool]
    needs_landlord: Mapped[bool]
    source_url: Mapped[str] = mapped_column(Text)


class FundingOption(Base):
    __tablename__ = "funding_options"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30))
    max_amount_gbp: Mapped[int | None]
    apr_percent: Mapped[float | None] = mapped_column(Float)
    income_bands: Mapped[list[str]]
    tenures: Mapped[list[str]]
    categories: Mapped[list[str]]
    is_mock: Mapped[bool]
    source_url: Mapped[str] = mapped_column(Text)


class FloodPostcode(Base):
    """EA RoFRS 'Postcodes in Areas at Risk'; one row per postcode and band (N7 loads it)."""

    __tablename__ = "flood_postcodes"

    postcode: Mapped[str] = mapped_column(String(8), primary_key=True)
    band: Mapped[str] = mapped_column(String(10), primary_key=True)


# --- Caches (no personal data) ------------------------------------------------------------


class ApiCache(Base):
    __tablename__ = "api_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    value: Mapped[dict[str, Any]]
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(index=True)


class LlmCache(Base):
    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 hex
    model: Mapped[str] = mapped_column(String(100))
    value: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = _created_at()
