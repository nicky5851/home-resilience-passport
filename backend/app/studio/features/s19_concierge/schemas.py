from typing import Literal

from pydantic import Field

from app.schemas.base import Contract
from app.studio.features.s19_concierge.config import (
    MAX_ANSWER_CHARS,
    MAX_MESSAGE_CHARS,
    MAX_MESSAGES,
    MAX_SUGGESTED,
)


class ConciergeMessage(Contract):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class ConciergeRequest(Contract):
    messages: list[ConciergeMessage] = Field(min_length=1, max_length=MAX_MESSAGES)


class Citation(Contract):
    tool: str
    label: str


class ConciergeReply(Contract):
    answer: str = Field(max_length=MAX_ANSWER_CHARS)
    citations: list[Citation]
    suggested: list[str] = Field(max_length=MAX_SUGGESTED)
    source: Literal["llm", "template"]
