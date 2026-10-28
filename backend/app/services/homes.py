"""A user's homes in Postgres (spec N10): homes, households, assessments, passport events and
share links.

Routes work on `StubHome` views, so the five demo homes (fixtures, in memory, readable by every
logged-in user) and stored homes share one code path. Certificates of stored homes are rows in
`work_files` with the file in `services/storage.py` (N14). Funding is still the fixture's until L6.
"""

import logging
import uuid
from dataclasses import dataclass
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
from app.services.storage import get_storage, new_key

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Certificate:
    """An upload that passed the CONTRACT §6 checks."""

    data: bytes
    ext: str  # pdf, jpg, png
    content_type: str
    name: str  # the user's file name, metadata only (≤ 100 chars)


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
    """The home, everything hanging off it (ON DELETE CASCADE) and its certificate files."""
    keys = await storage_keys(session, db.Home.id == home.home_id)
    await session.execute(delete(db.Home).where(db.Home.id == home.home_id))
    await session.commit()
    remove_files(keys)


async def storage_keys(session: AsyncSession, where) -> list[str]:  # type: ignore[no-untyped-def]
    """Storage keys of the certificates of the homes matching `where` (a `db.Home` filter)."""
    stmt = (
        select(db.WorkFile.storage_key)
        .join(db.PassportEvent, db.PassportEvent.id == db.WorkFile.event_id)
        .join(db.Home, db.Home.id == db.PassportEvent.home_id)
        .where(where)
    )
    return list((await session.scalars(stmt)).all())


def remove_files(keys: list[str]) -> None:
    """After the rows are gone: a file left behind is logged, never a failed delete."""
    storage = get_storage()
    for key in keys:
        try:
            storage.delete(key)
        except OSError:
            log.exception("Could not delete certificate file %s", key)


async def add_work(
    session: AsyncSession, home_id: uuid.UUID, event: PassportEvent, cert: Certificate | None
) -> None:
    """The work_recorded event and, if any, its certificate (file first, then both rows)."""
    key = None
    try:
        session.add(_event_row(home_id, event))
        if cert is not None:
            key = new_key(cert.ext)
            get_storage().put(key, cert.data)
            await session.flush()  # the event row first: the work file points at it
            session.add(
                db.WorkFile(
                    event_id=event.id,
                    storage_key=key,
                    certificate_name=cert.name,
                    content_type=cert.content_type,
                    size_bytes=len(cert.data),
                )
            )
        await session.commit()
    except Exception:
        if key is not None:
            remove_files([key])  # no row points at it
        raise


async def certificate(
    session: AsyncSession, home_id: uuid.UUID, event_id: uuid.UUID
) -> tuple[bytes, str] | None:
    """(bytes, content type) of an event's certificate, only if the event is this home's."""
    row = await session.scalar(
        select(db.WorkFile)
        .join(db.PassportEvent, db.PassportEvent.id == db.WorkFile.event_id)
        .where(db.WorkFile.event_id == event_id, db.PassportEvent.home_id == home_id)
    )
    if row is None:
        return None
    data = get_storage().get(row.storage_key)
    return None if data is None else (data, row.content_type)


async def latest_plan(session: AsyncSession, home_id: uuid.UUID) -> Plan | None:
    row = await session.scalar(select(db.SavedPlan).where(db.SavedPlan.home_id == home_id))
    return None if row is None else Plan.model_validate(row.plan)


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
    session.add(_event_row(home_id, event))
    await session.commit()


def _event_row(home_id: uuid.UUID, event: PassportEvent) -> db.PassportEvent:
    # Stored to the microsecond so events in the same second keep their order.
    return db.PassportEvent(
        id=event.id,
        home_id=home_id,
        kind=event.kind,
        at=datetime.now(UTC),
        score_after=event.score_after,
        detail=event.detail,
    )


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
