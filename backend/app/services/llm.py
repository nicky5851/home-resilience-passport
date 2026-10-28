"""Plain-English measure explanations from Claude (spec §7 rule 5, step N11).

The one place that talks to the LLM: model, 8 s timeout, `llm_cache`, daily call cap. Returns
None whenever there is no answer (no key, cap reached, error, timeout, refusal); the planner
then uses its template, so the app always works.

The prompt holds only property facts, hazard levels, score components and measures. Nothing
personal ever goes in (CONTRACT §6 rule 2): the caller builds `facts` from those parts only.
"""

import hashlib
import json
import logging
from datetime import UTC, date, datetime
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import EXPLANATION_MAX_CHARS, LLM_TIMEOUT_S, get_settings
from app.db.models import LlmCache
from app.scoring import SCORING_VERSION

log = logging.getLogger(__name__)

MAX_WORDS = 30  # spec §7 rule 5
MAX_TOKENS = 2000  # 8 short sentences need a few hundred; headroom without a long wait
SYSTEM = (
    "You explain home-resilience improvements to UK homeowners. For each measure in the JSON "
    "you are given, write one sentence of plain English (at most 30 words) saying what it "
    "does for this home's risks. Use only the facts given: never invent numbers, prices, "
    "grants or savings. No jargon, no exclamation marks."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["explanations"],
    "additionalProperties": False,
}


class _DailyCap:
    """LLM calls made today (UTC), in memory: resets with the API, fine for one instance."""

    def __init__(self) -> None:
        self.day: date | None = None
        self.calls = 0

    def take(self, limit: int) -> bool:
        today = datetime.now(UTC).date()
        if self.day != today:
            self.day, self.calls = today, 0
        if self.calls >= limit:
            return False
        self.calls += 1
        return True


daily_cap = _DailyCap()


def cache_key(facts: dict[str, Any], model: str) -> str:
    """Spec §7 rule 5: property facts, hazard levels, measure ids, scoring version, model.
    Budget and selection are never part of `facts`, so the budget slider never misses."""
    material = {
        "property": facts["property"],
        "hazards": facts["hazards"],
        "measure_ids": [m["id"] for m in facts["measures"]],
        "scoring_version": SCORING_VERSION,
        "model": model,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def prompt(facts: dict[str, Any]) -> str:
    return json.dumps(facts, sort_keys=True, ensure_ascii=False)


async def explanations(facts: dict[str, Any], session: AsyncSession) -> dict[str, str] | None:
    """Measure id → sentence for the measures in `facts`, or None to use the template."""
    settings = get_settings()
    model = settings.anthropic_model
    key = cache_key(facts, model)
    if (hit := await _cache_get(session, key)) is not None:
        return hit
    if not settings.anthropic_api_key:
        return None
    if not daily_cap.take(settings.llm_daily_call_limit):
        log.warning("LLM daily call limit reached; using template explanations")
        return None
    text = await _create(prompt(facts))
    if text is None:
        return None
    wanted = {m["id"] for m in facts["measures"]}
    found = _parse(text, wanted)
    if not found:
        return None
    await _cache_put(session, key, model, found)
    return found


async def _create(user_prompt: str) -> str | None:
    """One Messages API call; the JSON text, or None on any failure. Tests replace this."""
    settings = get_settings()
    try:
        async with anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key, timeout=LLM_TIMEOUT_S, max_retries=0
        ) as client:
            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": SCHEMA},
                },
            )
    except anthropic.APITimeoutError:
        log.warning("LLM slower than %.0f s; using template explanations", LLM_TIMEOUT_S)
        return None
    except anthropic.APIConnectionError:
        log.warning("LLM unreachable; using template explanations")
        return None
    except anthropic.APIStatusError as e:
        log.warning("LLM answered %s; using template explanations", e.status_code)
        return None
    if response.stop_reason != "end_turn":
        log.warning("LLM stopped with %s; using template explanations", response.stop_reason)
        return None
    return next((b.text for b in response.content if b.type == "text"), None)


def _parse(text: str, wanted: set[str]) -> dict[str, str]:
    """Keep only sentences for measures we asked about that fit the length rules."""
    try:
        items = json.loads(text)["explanations"]
    except (ValueError, KeyError, TypeError):
        return {}
    out: dict[str, str] = {}
    for item in items if isinstance(items, list) else []:
        mid, sentence = item.get("id"), " ".join(str(item.get("text", "")).split())
        if mid in wanted and sentence and len(sentence) <= EXPLANATION_MAX_CHARS:
            if len(sentence.split()) <= MAX_WORDS:
                out[mid] = sentence
    return out


async def _cache_get(session: AsyncSession, key: str) -> dict[str, str] | None:
    try:
        value = await session.scalar(select(LlmCache.value).where(LlmCache.key == key))
    except SQLAlchemyError as e:
        log.warning("llm_cache read failed (%s); continuing without the cache", type(e).__name__)
        await session.rollback()
        return None
    return None if value is None else value["explanations"]


async def _cache_put(session: AsyncSession, key: str, model: str, found: dict[str, str]) -> None:
    stmt = insert(LlmCache).values(key=key, model=model, value={"explanations": found})
    try:
        await session.execute(stmt.on_conflict_do_nothing(index_elements=[LlmCache.key]))
        await session.commit()
    except SQLAlchemyError as e:
        log.warning("llm_cache write failed (%s)", type(e).__name__)
        await session.rollback()
