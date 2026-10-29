"""Orchestrates one Concierge turn: scrub the message, try the LLM tool-use loop, verify its
numbers, and fall back to the template intent router for any reason (docs/studio/N_20_function
.md §S19 Algorithm). The LLM path is tried only for the (scrubbed) latest user message plus
history; tool outputs never leave this process."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import llm, planner
from app.studio.common.schemas import StudioHome
from app.studio.features.s19_concierge.config import (
    MAX_ANSWER_CHARS,
    MAX_SUGGESTED,
    MAX_TOOL_ROUNDS,
    SYSTEM_PROMPT,
    TEMPLATE_SUGGESTED,
)
from app.studio.features.s19_concierge.guard import numbers_supported
from app.studio.features.s19_concierge.schemas import Citation, ConciergeMessage, ConciergeReply
from app.studio.features.s19_concierge.scrub import scrub_personal
from app.studio.features.s19_concierge.template import template_reply
from app.studio.features.s19_concierge.tools import TOOL_LABELS, TOOL_SPECS, ToolContext, call_tool


async def concierge_reply(
    home: StudioHome, session: AsyncSession, messages: list[ConciergeMessage]
) -> ConciergeReply:
    scrubbed = [ConciergeMessage(role=m.role, content=scrub_personal(m.content)) for m in messages]
    measures = await planner.load_measures(session)
    funding = await planner.load_funding_options(session)
    ctx = ToolContext(home=home, measures=measures, funding=funding)

    reply = await _try_llm(scrubbed, ctx)
    if reply is not None:
        return reply
    return template_reply(scrubbed[-1].content, ctx)


async def _try_llm(messages: list[ConciergeMessage], ctx: ToolContext) -> ConciergeReply | None:
    anthropic_messages: list[dict] = [{"role": m.role, "content": m.content} for m in messages]
    tool_outputs_text = ""
    citations: dict[str, Citation] = {}

    for _round in range(MAX_TOOL_ROUNDS):
        response = await llm.tool_call(SYSTEM_PROMPT, anthropic_messages, TOOL_SPECS)
        if response is None:
            return None

        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason == "tool_use" and tool_blocks:
            anthropic_messages.append(
                {"role": "assistant", "content": [b.model_dump() for b in response.content]}
            )
            tool_results = []
            for block in tool_blocks:
                result = call_tool(block.name, block.input, ctx)
                result_text = json.dumps(result, sort_keys=True)
                tool_outputs_text += result_text
                citations[block.name] = Citation(
                    tool=block.name, label=TOOL_LABELS.get(block.name, block.name)
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                )
            anthropic_messages.append({"role": "user", "content": tool_results})
            continue

        answer = " ".join(b.text for b in response.content if b.type == "text").strip()
        if not answer:
            return None
        answer = answer[:MAX_ANSWER_CHARS]
        if not numbers_supported(answer, tool_outputs_text):
            return None
        return ConciergeReply(
            answer=answer,
            citations=list(citations.values()),
            suggested=TEMPLATE_SUGGESTED[:MAX_SUGGESTED],
            source="llm",
        )

    return None
