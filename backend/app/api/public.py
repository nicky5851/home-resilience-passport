"""Routes that need no login: demo homes, public passports, model info."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.api.errors import ApiError
from app.api.stub_store import fixtures, store
from app.schemas import DemoHome, PassportEvent, PublicPassport
from app.schemas.api import ModelInfo
from app.services import homes, passport
from ml import predict

demo = APIRouter(prefix="/demo", tags=["demo"])
public = APIRouter(prefix="/public", tags=["public"])
model = APIRouter(prefix="/model", tags=["model"])


@demo.get("/homes")
def demo_homes() -> list[DemoHome]:
    return [f.demo for f in fixtures().values()]


def _public_event(ev: PassportEvent) -> PassportEvent:
    """Public passports show has_certificate but never the certificate's name (CONTRACT §6)."""
    detail: dict[str, Any] = {k: v for k, v in ev.detail.items() if k != "certificate_name"}
    return ev.model_copy(update={"detail": detail})


@public.get("/passport/{share_token}")
async def public_passport(share_token: str, session: SessionDep) -> PublicPassport:
    home = store.by_share_token(share_token) or await homes.by_share_token(session, share_token)
    full = None if home is None else await passport.build(session, home)
    if full is None:
        raise ApiError(404, "not_found", "This link is no longer active.")
    data = full.model_dump(exclude={"household", "share_token", "events"})
    return PublicPassport(**data, events=[_public_event(e) for e in full.events])


@model.get("/info")
def model_info() -> ModelInfo:
    # For the Technology slide: version, training data and test metrics (docs/model_card.md).
    return ModelInfo(**predict.info())
