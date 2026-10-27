"""A user's homes in Postgres (spec N10): homes, households, assessments, passport events and
share links.

Routes work on `StubHome` views, so the five demo homes (fixtures, in memory, readable by every
logged-in user) and stored homes share one code path. Still not stored until their steps:
funding (fixture answers until L6) and certificate files (in memory until N14).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.stub_store import DEFAULT_SLUG, StubHome, fixture_by_postcode
from app.db import models as db
from app.schemas import (
    Address,
    HazardInputs,
    Household,
    PassportEvent,
    Plan,
    PropertyFacts,
    ResilienceScore,
    RiskProfile,
)
from app.schemas.api import Assessment
from app.scoring import SCORING_VERSION

# Uploaded certificates of stored homes by event id: (bytes, content type). Moves to storage
# (`work_files`) in N14; lost when the API restarts.
CERTIFICATES: dict[uuid.UUID, tuple[bytes, str]] = {}


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    address: Address,
    prop: PropertyFacts,
    household: Household,
) -> uuid.UUID:
    home = db.Home(
        user_id=user_id,
        uprn=address.uprn,
        line1=address.line1,
        postcode=address.postcode,
        lat=address.lat,
        lon=address.lon,
        local_authority=address.local_authority,
        country=address.country,
        property=prop.model_dump(mode="json"),
    )
    session.add(home)
    await session.flush()
    session.add(db.Household(home_id=home.id, **household.model_dump(mode="json")))
    await session.commit()
    return home.id


async def load(session: AsyncSession, home_id: uuid.UUID, user_id: uuid.UUID) -> StubHome | None:
    """The home if this user owns it; None otherwise (the route answers 404 either way)."""
    stmt = select(db.Home).where(db.Home.id == home_id, db.Home.user_id == user_id)
    home = await session.scalar(stmt)
    return None if home is None else await _view(session, home)


async def owned_by(session: AsyncSession, user_id: uuid.UUID) -> list[StubHome]:
    stmt = select(db.Home).where(db.Home.user_id == user_id).order_by(db.Home.created_at)
    return [await _view(session, h) for h in (await session.scalars(stmt)).all()]


async def by_share_token(session: AsyncSession, token: str) -> StubHome | None:
    link = await session.scalar(select(db.ShareLink).where(db.ShareLink.token == token))
    if link is None:
        return None
    home = await session.get(db.Home, link.home_id)
    return None if home is None else await _view(session, home)


async def delete_home(session: AsyncSession, home: StubHome) -> None:
    forget_certificates(home)
    await session.execute(delete(db.Home).where(db.Home.id == home.home_id))
    await session.commit()


def forget_certificates(home: StubHome) -> None:
    for event in home.events:
        CERTIFICATES.pop(event.id, None)


async def save_assessment(
    session: AsyncSession, home_id: uuid.UUID, result: Assessment, event: PassportEvent
) -> None:
    session.add(
        db.Assessment(
            home_id=home_id,
            inputs=result.inputs.model_dump(mode="json"),
            risk=result.risk.model_dump(mode="json"),
            score=result.score.model_dump(mode="json"),
            scoring_version=SCORING_VERSION,
            created_at=datetime.now(UTC),
        )
    )
    await add_event(session, home_id, event)


async def add_event(session: AsyncSession, home_id: uuid.UUID, event: PassportEvent) -> None:
    # Stored to the microsecond so events in the same second keep their order.
    session.add(
        db.PassportEvent(
            id=event.id,
            home_id=home_id,
            kind=event.kind,
            at=datetime.now(UTC),
            score_after=event.score_after,
            detail=event.detail,
        )
    )
    await session.commit()


async def save_plan(session: AsyncSession, home_id: uuid.UUID, budget_gbp: int, plan: Plan) -> None:
    """Keep the latest plan only: the budget slider re-posts `/plan` on every move."""
    await session.execute(delete(db.SavedPlan).where(db.SavedPlan.home_id == home_id))
    session.add(
        db.SavedPlan(
            home_id=home_id,
            budget_gbp=budget_gbp,
            selected_ids=[i.measure.id for i in plan.items if i.selected],
            plan=plan.model_dump(mode="json"),
        )
    )
    await session.commit()


async def set_share_token(session: AsyncSession, home_id: uuid.UUID, token: str | None) -> None:
    """At most one live link per home: a new token replaces the old one, None revokes it."""
    await session.execute(delete(db.ShareLink).where(db.ShareLink.home_id == home_id))
    if token is not None:
        session.add(db.ShareLink(home_id=home_id, token=token))
    await session.commit()


async def _view(session: AsyncSession, home: db.Home) -> StubHome:
    household = await session.get(db.Household, home.id)
    latest = await session.scalar(
        select(db.Assessment)
        .where(db.Assessment.home_id == home.id)
        .order_by(db.Assessment.created_at.desc())
        .limit(1)
    )
    events = await session.scalars(
        select(db.PassportEvent)
        .where(db.PassportEvent.home_id == home.id)
        .order_by(db.PassportEvent.at, db.PassportEvent.id)
    )
    link = await session.get(db.ShareLink, home.id)
    match = fixture_by_postcode(home.postcode)
    view = StubHome(
        home_id=home.id,
        owner=str(home.user_id),
        slug=match.slug if match else DEFAULT_SLUG,
        line1=home.line1,
        postcode=home.postcode,
        assessed=latest is not None,
        share_token=link.token if link else None,
        events=[
            PassportEvent(
                id=e.id,
                kind=e.kind,
                at=e.at.astimezone(UTC).replace(microsecond=0),
                score_after=e.score_after,
                detail=e.detail,
            )
            for e in events.all()
        ],
        stored=True,
    )
    view.real = {
        "address": Address(
            uprn=home.uprn,
            line1=home.line1,
            postcode=home.postcode,
            lat=home.lat,
            lon=home.lon,
            local_authority=home.local_authority,
            country=home.country,
        ),
        "property": PropertyFacts.model_validate(home.property),
        "household": Household.model_validate(
            {name: getattr(household, name) for name in Household.model_fields}
        ),
    }
    if latest is not None:
        view.assessment = Assessment(
            inputs=HazardInputs.model_validate(latest.inputs),
            risk=RiskProfile.model_validate(latest.risk),
            score=ResilienceScore.model_validate(latest.score),
        )
    return view
