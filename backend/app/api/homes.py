"""Home routes (spec §4.2).

A user's own homes are stored in Postgres (`app/services/homes.py`, N10) and assessed with real
data (`app/services/assessment.py`, N9). The five demo homes answer from their fixtures and are
readable by every logged-in user. Plans are built by `app/services/planner.py` (N11); funding
still comes from the fixtures (L6);
certificate files are kept in memory until N14.
"""

import secrets
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.api.deps import ApiCacheDep, CurrentUser, SessionDep, rate_limit
from app.api.errors import ApiError
from app.api.stub_store import StubHome, fixture_by_postcode, now, store
from app.config import (
    CERTIFICATE_NAME_MAX_CHARS,
    RATE_LIMIT_ASSESS,
    SHARE_TOKEN_BYTES,
    UPLOAD_MAX_BYTES,
    get_settings,
)
from app.schemas import FundingBundle, Passport, PassportEvent, Plan
from app.schemas.api import (
    Assessment,
    FundingRequest,
    HomeCreate,
    HomeCreated,
    HomeSummary,
    PlanRequest,
    ShareLink,
)
from app.scoring import match_funding
from app.services import assessment, homes, planner
from app.services import passport as passports

router = APIRouter(prefix="/homes", tags=["homes"])

# CONTRACT §6: the file's first bytes decide its type, never its name or Content-Type.
MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b"%PDF": ("pdf", "application/pdf"),
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG": ("png", "image/png"),
}


async def _home(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> StubHome:
    """A demo home, or one of the user's own; someone else's home is 404 like a missing one."""
    home = store.get(home_id) or await homes.load(session, home_id, user.id)
    if home is None:
        raise ApiError(404, "not_found", "We couldn't find that home.")
    return home


async def _add_event(session: SessionDep, home: StubHome, event: PassportEvent) -> None:
    home.events.append(event)
    if home.stored:
        await homes.add_event(session, home.home_id, event)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_home(
    body: HomeCreate, user: CurrentUser, session: SessionDep, cache: ApiCacheDep
) -> HomeCreated:
    prop = await assessment.property_for(body.address, body.property_override, cache)
    if prop is None and (demo := fixture_by_postcode(body.address.postcode)) is not None:
        prop = demo.demo.property  # a demo address without a certificate in the register
    if prop is None:
        raise ApiError(
            400,
            "validation",
            "property_override: we couldn't find an energy certificate for this address. "
            "Please add the property details.",
        )
    home_id = await homes.create(session, user.id, body.address, prop, body.household)
    return HomeCreated(home_id=home_id)


@router.get("")
async def list_homes(user: CurrentUser, session: SessionDep) -> list[HomeSummary]:
    measures = await planner.load_measures(session)
    return [
        HomeSummary(
            home_id=h.home_id,
            line1=h.line1,
            postcode=h.postcode,
            score=passports.score(h, measures) if h.assessed else None,
        )
        for h in await homes.owned_by(session, user.id)
    ]


@router.delete("/{home_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_home(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    home = await _home(home_id, user, session)
    if not home.stored:
        raise ApiError(404, "not_found", "We couldn't find that home.")  # demo homes stay
    await homes.delete_home(session, home)


@router.post("/{home_id}/assess")
async def assess(
    home_id: uuid.UUID, user: CurrentUser, session: SessionDep, cache: ApiCacheDep
) -> Assessment:
    rate_limit("assess", str(user.id), RATE_LIMIT_ASSESS)
    home = await _home(home_id, user, session)
    if not home.stored:
        return store.assess(home)  # the five demo homes answer from their fixtures, offline
    done = passports.completed(home, await planner.load_measures(session))  # work keeps counting
    result = await assessment.assess(
        home.real["address"], home.real["property"], session, cache, completed=done
    )
    event = PassportEvent(
        id=uuid.uuid4(), kind="assessed", at=now(), score_after=result.score.value, detail={}
    )
    await homes.save_assessment(session, home.home_id, result, event)
    return result


@router.get("/{home_id}/risk")
async def latest_risk(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Assessment:
    home = await _home(home_id, user, session)
    if not home.assessed:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    return store.latest_assessment(home)


@router.post("/{home_id}/plan")
async def plan(
    home_id: uuid.UUID, user: CurrentUser, session: SessionDep, body: PlanRequest | None = None
) -> Plan:
    home = await _home(home_id, user, session)
    if not home.stored:
        return store.plan(home)  # demo homes: the fixture's plan, offline
    if home.assessment is None:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    measures = await planner.load_measures(session)
    body = body or PlanRequest()
    result = await planner.build_plan(
        session,
        measures,
        home.assessment.risk,
        home.real["property"],
        home.real["household"],
        passports.completed(home, measures),
        budget_gbp=body.budget_gbp,
        selected_ids=body.selected_ids,
    )
    budget = home.real["household"].budget_gbp if body.budget_gbp is None else body.budget_gbp
    await homes.save_plan(session, home.home_id, budget, result)
    return result


@router.post("/{home_id}/funding")
async def funding(
    home_id: uuid.UUID, body: FundingRequest, user: CurrentUser, session: SessionDep
) -> FundingBundle:
    home = await _home(home_id, user, session)
    if not home.stored:
        return store.funding(home)  # demo homes: the fixture's funding, offline
    if home.assessment is None:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    measures = await planner.load_measures(session)
    options = await planner.load_funding_options(session)
    plan_result = await planner.build_plan(
        session,
        measures,
        home.assessment.risk,
        home.real["property"],
        home.real["household"],
        passports.completed(home, measures),
        selected_ids=body.selected_ids,
    )
    return match_funding(plan_result, home.real["household"], options)


@router.get("/{home_id}/passport")
async def passport(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Passport:
    result = await passports.build(session, await _home(home_id, user, session))
    if result is None:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    return result


@router.post("/{home_id}/work")
async def record_work(
    home_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    measure_id: Annotated[str, Form()],
    completed_on: Annotated[date, Form()],
    cost_gbp: Annotated[int | None, Form(ge=0)] = None,
    certificate: Annotated[UploadFile | None, File()] = None,
) -> PassportEvent:
    home = await _home(home_id, user, session)
    measures = await passports.measures_for(session, home)
    if measure_id not in {m.id for m in measures}:
        raise ApiError(400, "validation", "measure_id: unknown measure for this home.")
    if completed_on > date.today():
        raise ApiError(400, "validation", "completed_on: the date cannot be in the future.")

    cert: homes.Certificate | None = None
    if certificate is not None and certificate.filename:
        data = await certificate.read(UPLOAD_MAX_BYTES + 1)
        if len(data) > UPLOAD_MAX_BYTES:
            raise ApiError(413, "file_too_large", "The file is larger than 5 MB.")
        kind = next((v for magic, v in MAGIC_BYTES.items() if data.startswith(magic)), None)
        if kind is None:
            raise ApiError(415, "unsupported_file", "Please upload a PDF, JPEG or PNG file.")
        name = certificate.filename[:CERTIFICATE_NAME_MAX_CHARS]
        cert = homes.Certificate(data=data, ext=kind[0], content_type=kind[1], name=name)

    assessed = home.assessed or not home.stored  # demo homes always have their fixture
    event = PassportEvent(
        id=uuid.uuid4(),
        kind="work_recorded",
        at=now(),
        # The score with this measure done too (None before a stored home's first assessment).
        score_after=passports.score(home, measures, extra=measure_id).value if assessed else None,
        detail={
            "measure_id": measure_id,
            "completed_on": completed_on.isoformat(),
            "cost_gbp": cost_gbp,
            "has_certificate": cert is not None,
            "certificate_name": cert.name if cert else None,
        },
    )
    if home.stored:
        await homes.add_work(session, home.home_id, event, cert)
    elif cert is not None:
        home.certificates[event.id] = (cert.data, cert.content_type)  # demo homes: in memory
    home.events.append(event)
    return event


@router.get(
    "/{home_id}/work/{event_id}/certificate",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "image/jpeg": {}, "image/png": {}}}},
)
async def certificate(
    home_id: uuid.UUID, event_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Response:
    home = await _home(home_id, user, session)  # someone else's home is 404 here
    if home.stored:
        found = await homes.certificate(session, home.home_id, event_id)
    else:
        found = home.certificates.get(event_id)
    if found is None:
        raise ApiError(404, "not_found", "We couldn't find that certificate.")
    data, content_type = found
    return Response(content=data, media_type=content_type)


@router.post("/{home_id}/share")
async def share(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ShareLink:
    home = await _home(home_id, user, session)
    if home.stored:
        token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
        await homes.set_share_token(session, home.home_id, token)
        shared = PassportEvent(
            id=uuid.uuid4(), kind="shared", at=now(), score_after=None, detail={}
        )
        await _add_event(session, home, shared)
    else:
        token = store.share(home)
    url = f"{get_settings().next_public_app_url.rstrip('/')}/p/{token}"
    return ShareLink(share_token=token, url=url)


@router.delete("/{home_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def stop_sharing(home_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    home = await _home(home_id, user, session)
    if home.stored:
        await homes.set_share_token(session, home.home_id, None)
    home.share_token = None
