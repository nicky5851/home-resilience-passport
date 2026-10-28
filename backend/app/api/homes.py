"""Home routes (spec §4.2).

N9: creating and assessing a home is real (`app/services/assessment.py`). Homes, plans, work
records and sharing still live in the in-memory stub store until real accounts (N10) give homes
a database owner.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.api.deps import ApiCacheDep, CurrentUser, SessionDep
from app.api.errors import ApiError
from app.api.stub_store import StubHome, fixture_by_postcode, now, store
from app.config import CERTIFICATE_NAME_MAX_CHARS, UPLOAD_MAX_BYTES, get_settings
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
from app.services import assessment

router = APIRouter(prefix="/homes", tags=["homes"])

# CONTRACT §6: the file's first bytes decide its type, never its name or Content-Type.
MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b"%PDF": ("pdf", "application/pdf"),
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG": ("png", "image/png"),
}


def _home(home_id: uuid.UUID, user: CurrentUser) -> StubHome:
    home = store.get(home_id, user.email)
    if home is None:
        raise ApiError(404, "not_found", "We couldn't find that home.")
    return home


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_home(body: HomeCreate, user: CurrentUser, cache: ApiCacheDep) -> HomeCreated:
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
    home = store.create_home(user.email, body.address.line1, body.address.postcode)
    home.real = {"address": body.address, "property": prop, "household": body.household}
    return HomeCreated(home_id=home.home_id)


@router.get("")
def list_homes(user: CurrentUser) -> list[HomeSummary]:
    return [
        HomeSummary(
            home_id=h.home_id,
            line1=h.line1,
            postcode=h.postcode,
            score=store.latest(h)[1] if h.assessed else None,
        )
        for h in store.owned_by(user.email)
    ]


@router.delete("/{home_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_home(home_id: uuid.UUID, user: CurrentUser) -> None:
    home = _home(home_id, user)
    if home.owner is None:
        raise ApiError(404, "not_found", "We couldn't find that home.")  # demo homes stay
    del store.homes[home.home_id]


@router.post("/{home_id}/assess")
async def assess(
    home_id: uuid.UUID, user: CurrentUser, session: SessionDep, cache: ApiCacheDep
) -> Assessment:
    home = _home(home_id, user)
    if home.real is None:
        return store.assess(home)  # the five demo homes answer from their fixtures, offline
    result = await assessment.assess(home.real["address"], home.real["property"], session, cache)
    event = PassportEvent(
        id=uuid.uuid4(), kind="assessed", at=now(), score_after=result.score.value, detail={}
    )
    store.record_assessment(home, result, event)
    return result


@router.get("/{home_id}/risk")
def latest_risk(home_id: uuid.UUID, user: CurrentUser) -> Assessment:
    home = _home(home_id, user)
    if not home.assessed:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    return store.latest_assessment(home)


@router.post("/{home_id}/plan")
def plan(home_id: uuid.UUID, user: CurrentUser, body: PlanRequest | None = None) -> Plan:
    return store.plan(_home(home_id, user))


@router.post("/{home_id}/funding")
def funding(home_id: uuid.UUID, body: FundingRequest, user: CurrentUser) -> FundingBundle:
    return store.funding(_home(home_id, user))


@router.get("/{home_id}/passport")
def passport(home_id: uuid.UUID, user: CurrentUser) -> Passport:
    return store.passport(_home(home_id, user))


@router.post("/{home_id}/work")
async def record_work(
    home_id: uuid.UUID,
    user: CurrentUser,
    measure_id: Annotated[str, Form()],
    completed_on: Annotated[date, Form()],
    cost_gbp: Annotated[int | None, Form(ge=0)] = None,
    certificate: Annotated[UploadFile | None, File()] = None,
) -> PassportEvent:
    home = _home(home_id, user)
    if measure_id not in {i.measure.id for i in store.plan(home).items}:
        raise ApiError(400, "validation", "measure_id: unknown measure for this home.")
    if completed_on > date.today():
        raise ApiError(400, "validation", "completed_on: the date cannot be in the future.")

    event_id = uuid.uuid4()
    name = None
    if certificate is not None and certificate.filename:
        data = await certificate.read(UPLOAD_MAX_BYTES + 1)
        if len(data) > UPLOAD_MAX_BYTES:
            raise ApiError(413, "file_too_large", "The file is larger than 5 MB.")
        kind = next((v for magic, v in MAGIC_BYTES.items() if data.startswith(magic)), None)
        if kind is None:
            raise ApiError(415, "unsupported_file", "Please upload a PDF, JPEG or PNG file.")
        name = certificate.filename[:CERTIFICATE_NAME_MAX_CHARS]
        home.certificates[event_id] = (data, kind[1])

    event = PassportEvent(
        id=event_id,
        kind="work_recorded",
        at=now(),
        score_after=store.latest(home)[1].value,
        detail={
            "measure_id": measure_id,
            "completed_on": completed_on.isoformat(),
            "cost_gbp": cost_gbp,
            "has_certificate": name is not None,
            "certificate_name": name,
        },
    )
    home.events.append(event)
    return event


@router.get(
    "/{home_id}/work/{event_id}/certificate",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "image/jpeg": {}, "image/png": {}}}},
)
def certificate(home_id: uuid.UUID, event_id: uuid.UUID, user: CurrentUser) -> Response:
    home = _home(home_id, user)
    if event_id not in home.certificates:
        raise ApiError(404, "not_found", "We couldn't find that certificate.")
    data, content_type = home.certificates[event_id]
    return Response(content=data, media_type=content_type)


@router.post("/{home_id}/share")
def share(home_id: uuid.UUID, user: CurrentUser) -> ShareLink:
    token = store.share(_home(home_id, user))
    url = f"{get_settings().next_public_app_url.rstrip('/')}/p/{token}"
    return ShareLink(share_token=token, url=url)


@router.delete("/{home_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def stop_sharing(home_id: uuid.UUID, user: CurrentUser) -> None:
    _home(home_id, user).share_token = None
