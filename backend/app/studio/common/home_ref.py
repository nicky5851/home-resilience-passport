"""`resolve_home(ref, ...)`: a home UUID (owner, login) or `demo-<slug>` (public), one way in
for every Studio feature (docs/studio/N_20_function.md §3 step 1)."""

import uuid
from typing import Annotated

from fastapi import Depends, Request

from app.api.deps import SessionDep
from app.api.errors import ApiError
from app.api.stub_store import fixtures, store
from app.auth.users import UserManager, UserStore, jwt_strategy
from app.config import AUTH_COOKIE_NAME
from app.db.models import User
from app.schemas import Household
from app.services import homes as homes_service
from app.services import passport as passports
from app.services import planner
from app.studio.common.schemas import StudioHome

DEMO_PREFIX = "demo-"

DEMO_LABELS = {
    "flood-terrace": "Demo · Flood-zone terrace",
    "clay-semi": "Demo · Clay-soil semi",
    "coastal-bungalow": "Demo · Coastal bungalow",
    "city-top-flat": "Demo · City top-floor flat",
    "rural-cottage": "Demo · Rural cottage",
}


def demo_label(slug: str) -> str:
    return DEMO_LABELS.get(slug, f"Demo · {slug.replace('-', ' ').title()}")


async def _maybe_user(request: Request, session: SessionDep) -> User | None:
    """Like `current_user_row`, but `None` instead of 401 — demo refs need no login."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    manager = UserManager(UserStore(session))
    user = await jwt_strategy().read_token(token, manager)
    return user if user is not None and user.is_active else None


MaybeUser = Annotated[User | None, Depends(_maybe_user)]


async def resolve_home(
    ref: str, session: SessionDep, user: MaybeUser, *, include_household: bool = False
) -> StudioHome:
    """A demo ref is public; a UUID ref needs login and ownership, same 404 as `/homes/{id}`."""
    if ref.startswith(DEMO_PREFIX):
        slug = ref[len(DEMO_PREFIX) :]
        fixture = fixtures().get(slug)
        if fixture is None:
            raise ApiError(404, "not_found", "We couldn't find that home.")
        demo = fixture.demo
        measures = await planner.load_measures(session)
        stub = store.homes[fixture.passport.home_id]
        completed = [m.id for m in passports.completed(stub, measures)]
        return StudioHome(
            ref=ref,
            is_demo=True,
            home_id=None,
            address=demo.address,
            property=demo.property,
            inputs=fixture.inputs,
            risk=demo.risk,
            score=demo.score,
            household=demo.household if include_household else None,
            completed_measure_ids=completed,
        )

    try:
        home_id = uuid.UUID(ref)
    except ValueError:
        raise ApiError(404, "not_found", "We couldn't find that home.") from None
    if user is None:
        raise ApiError(401, "unauthorised")
    home = await homes_service.load(session, home_id, user.id)
    if home is None or home.real is None:
        raise ApiError(404, "not_found", "We couldn't find that home.")
    if not home.assessed or home.assessment is None:
        raise ApiError(404, "not_found", "This home has not been assessed yet.")
    measures = await planner.load_measures(session)
    completed = [m.id for m in passports.completed(home, measures)]
    household: Household | None = home.real["household"] if include_household else None
    return StudioHome(
        ref=ref,
        is_demo=False,
        home_id=home.home_id,
        address=home.real["address"],
        property=home.real["property"],
        inputs=home.assessment.inputs,
        risk=home.assessment.risk,
        score=home.assessment.score,
        household=household,
        completed_measure_ids=completed,
    )
