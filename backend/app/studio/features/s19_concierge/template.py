"""Template fallback (docs/studio/N_20_function.md §S19 Algorithm 4): a keyword intent router
over 8 intents, filling sentences from the same tools the LLM path uses. Used whenever there
is no key, the daily cap is reached, the call times out, or the number guard fails."""

from collections.abc import Callable

from app.studio.features.s19_concierge.config import TEMPLATE_SUGGESTED
from app.studio.features.s19_concierge.schemas import Citation, ConciergeReply
from app.studio.features.s19_concierge.tools import TOOL_LABELS, ToolContext, call_tool

LEVEL_WORDS = {"low": "low", "medium": "medium", "high": "high"}
HAZARD_WORDS = {
    "river_sea_flood": "river or sea flooding",
    "overheating": "overheating",
    "storm": "storms",
    "subsidence": "subsidence",
    "surface_water": "surface water flooding",
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "biggest_risk": ["biggest risk", "worst risk", "main risk", "most at risk"],
    "explain_score": ["explain my score", "why is my score", "resilience score", "my score"],
    "cheapest_bill_saving": ["cheapest", "cut my bills", "save money", "bill saving", "cheap"],
    "flood": ["flood"],
    "heat": ["heat", "overheat", "too hot"],
    "funding": ["grant", "funding", "loan", "pay for"],
    "renters": ["renter", "rent", "landlord", "tenant"],
    "what_next": ["what next", "what should i do", "next step"],
}


def detect_intent(message: str) -> str:
    text = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(k in text for k in keywords):
            return intent
    return "what_next"


def _cite(tool: str) -> Citation:
    return Citation(tool=tool, label=TOOL_LABELS[tool])


def template_reply(message: str, ctx: ToolContext) -> ConciergeReply:
    intent = detect_intent(message)
    handler = _HANDLERS[intent]
    answer, citations = handler(ctx)
    return ConciergeReply(
        answer=answer, citations=citations, suggested=TEMPLATE_SUGGESTED, source="template"
    )


def _biggest_risk(ctx: ToolContext) -> tuple[str, list[Citation]]:
    levels = call_tool("get_risk_levels", {}, ctx)["levels"]
    order = {"high": 2, "medium": 1, "low": 0}
    worst = max(levels, key=lambda lvl: order[lvl["today"]])
    hazard = HAZARD_WORDS.get(worst["hazard"], worst["hazard"])
    return (
        f"Your biggest risk right now is {hazard}, at a {worst['today']} level. {worst['why']}",
        [_cite("get_risk_levels")],
    )


def _explain_score(ctx: ToolContext) -> tuple[str, list[Citation]]:
    score = call_tool("get_score_breakdown", {}, ctx)
    weakest = min(score["components"], key=lambda c: c["points"] / max(c["max_points"], 1))
    return (
        f"Your resilience score is {score['value']}/100, band {score['band']}. The component "
        f"pulling it down most is {weakest['name']}: {weakest['reason']}",
        [_cite("get_score_breakdown")],
    )


def _cheapest_bill_saving(ctx: ToolContext) -> tuple[str, list[Citation]]:
    measures = call_tool("list_measures", {}, ctx)["measures"]
    candidates = [m for m in measures if m["annual_bill_saving_gbp"] > 0 and not m["completed"]]
    if not candidates:
        return (
            "None of the measures on your list are forecast to cut your bills, based on the "
            "catalogue we have.",
            [_cite("list_measures")],
        )
    best = min(candidates, key=lambda m: m["cost_low_gbp"])
    return (
        f"{best['name']} costs £{best['cost_low_gbp']:,}-£{best['cost_high_gbp']:,} and is "
        f"forecast to save about £{best['annual_bill_saving_gbp']:,} a year on bills.",
        [_cite("list_measures")],
    )


def _hazard_focus(
    hazard_key: str, category: str
) -> Callable[[ToolContext], tuple[str, list[Citation]]]:
    def handler(ctx: ToolContext) -> tuple[str, list[Citation]]:
        levels = call_tool("get_risk_levels", {}, ctx)["levels"]
        level = next((lvl for lvl in levels if lvl["hazard"] == hazard_key), None)
        measures = call_tool("list_measures", {"category": category}, ctx)["measures"]
        not_done = [m for m in measures if not m["completed"]]
        bits = []
        if level is not None:
            bits.append(
                f"Your {HAZARD_WORDS[hazard_key]} risk is {level['today']} today, "
                f"{level['y2050']} by 2050."
            )
        if not_done:
            top = max(not_done, key=lambda m: m["resilience_points"])
            bits.append(
                f"{top['name']} is the top measure for this, worth "
                f"{top['resilience_points']} points."
            )
        return " ".join(bits) or "We don't have a hazard reading for this yet.", [
            _cite("get_risk_levels"),
            _cite("list_measures"),
        ]

    return handler


def _funding(ctx: ToolContext) -> tuple[str, list[Citation]]:
    funding = call_tool("list_funding", {}, ctx)["funding"]
    if not funding:
        return "There's no funding in the catalogue right now.", [_cite("list_funding")]
    names = ", ".join(f["name"] for f in funding[:3])
    return (
        f"There are {len(funding)} funding options in our catalogue, including {names}. "
        "These are illustrative and not personalised to your income.",
        [_cite("list_funding")],
    )


def _renters(ctx: ToolContext) -> tuple[str, list[Citation]]:
    measures = call_tool("list_measures", {"renter_ok": True}, ctx)["measures"]
    if not measures:
        return "There are no renter-friendly measures in the catalogue right now.", [
            _cite("list_measures")
        ]
    names = ", ".join(m["name"] for m in measures[:3])
    return f"As a renter, you could still do: {names}.", [_cite("list_measures")]


def _what_next(ctx: ToolContext) -> tuple[str, list[Citation]]:
    measures = call_tool("list_measures", {}, ctx)["measures"]
    not_done = [m for m in measures if not m["completed"]]
    if not not_done:
        return "You've already completed every measure we track for this home.", [
            _cite("list_measures")
        ]
    top = max(not_done, key=lambda m: m["resilience_points"])
    return (
        f"The best next step is {top['name']}, worth {top['resilience_points']} resilience "
        f"points, costing £{top['cost_low_gbp']:,}-£{top['cost_high_gbp']:,}.",
        [_cite("list_measures")],
    )


_HANDLERS: dict[str, Callable[[ToolContext], tuple[str, list[Citation]]]] = {
    "biggest_risk": _biggest_risk,
    "explain_score": _explain_score,
    "cheapest_bill_saving": _cheapest_bill_saving,
    "flood": _hazard_focus("river_sea_flood", "flood"),
    "heat": _hazard_focus("overheating", "heat"),
    "funding": _funding,
    "renters": _renters,
    "what_next": _what_next,
}
