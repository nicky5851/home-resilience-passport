from fastapi import APIRouter, Request

from app.api.deps import SessionDep, client_ip, rate_limit
from app.api.errors import ApiError
from app.studio.common.home_ref import MaybeUser, resolve_home
from app.studio.features.s19_concierge.config import (
    RATE_LIMIT_CONCIERGE_DEMO_IP,
    RATE_LIMIT_CONCIERGE_USER,
)
from app.studio.features.s19_concierge.schemas import ConciergeReply, ConciergeRequest
from app.studio.features.s19_concierge.service import concierge_reply

router = APIRouter(prefix="/homes/{ref}/concierge", tags=["studio:s19"])


@router.post("")
async def concierge(
    ref: str,
    body: ConciergeRequest,
    request: Request,
    session: SessionDep,
    user: MaybeUser,
) -> ConciergeReply:
    home = await resolve_home(ref, session, user)

    if home.is_demo:
        rate_limit("studio_concierge_demo", client_ip(request), RATE_LIMIT_CONCIERGE_DEMO_IP)
    else:
        rate_limit("studio_concierge", str(user.id), RATE_LIMIT_CONCIERGE_USER)  # type: ignore[union-attr]

    if body.messages[-1].role != "user":
        raise ApiError(400, "validation", "The last message must be from the user.")

    return await concierge_reply(home, session, body.messages)
