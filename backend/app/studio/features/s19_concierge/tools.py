"""Read-only tools over one home's own data (docs/studio/N_20_function.md §S19 Algorithm 1).

Every function returns JSON-safe data with no personal fields: no address, postcode, house
number, income band, budget, tenure or `vulnerable` (CONTRACT.md §6 rule 2) — only the
property facts, hazard levels, score and the measure/funding catalogues."""

from dataclasses import dataclass
from typing import Any

from app.schemas.funding import FundingOption
from app.schemas.plan import Measure
from app.studio.common.schemas import StudioHome
from app.studio.features.s19_concierge.config import GLOSSARY


@dataclass
class ToolContext:
    home: StudioHome
    measures: list[Measure]
    funding: list[FundingOption]


def get_property_facts(ctx: ToolContext, _args: dict[str, Any]) -> dict[str, Any]:
    return ctx.home.property.model_dump(mode="json")


def get_risk_levels(ctx: ToolContext, _args: dict[str, Any]) -> dict[str, Any]:
    return {"levels": [lvl.model_dump(mode="json") for lvl in ctx.home.risk.levels]}


def get_score_breakdown(ctx: ToolContext, _args: dict[str, Any]) -> dict[str, Any]:
    return ctx.home.score.model_dump(mode="json")


def list_measures(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    category = args.get("category")
    renter_ok = args.get("renter_ok")
    out = []
    for m in ctx.measures:
        if category is not None and m.category != category:
            continue
        if renter_ok is not None and m.renter_ok != bool(renter_ok):
            continue
        out.append(
            {
                "id": m.id,
                "name": m.name,
                "category": m.category,
                "cost_low_gbp": m.cost_low_gbp,
                "cost_high_gbp": m.cost_high_gbp,
                "annual_bill_saving_gbp": m.annual_bill_saving_gbp,
                "co2_saved_kg_per_year": m.co2_saved_kg_per_year,
                "resilience_points": m.resilience_points,
                "renter_ok": m.renter_ok,
                "needs_landlord": m.needs_landlord,
                "completed": m.id in ctx.home.completed_measure_ids,
            }
        )
    return {"measures": out}


def get_measure(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    measure_id = args.get("id")
    m = next((m for m in ctx.measures if m.id == measure_id), None)
    if m is None:
        return {"error": "unknown measure id"}
    return {
        "id": m.id,
        "name": m.name,
        "category": m.category,
        "cost_low_gbp": m.cost_low_gbp,
        "cost_high_gbp": m.cost_high_gbp,
        "annual_bill_saving_gbp": m.annual_bill_saving_gbp,
        "co2_saved_kg_per_year": m.co2_saved_kg_per_year,
        "resilience_points": m.resilience_points,
        "renter_ok": m.renter_ok,
        "needs_landlord": m.needs_landlord,
        "source_url": m.source_url,
        "completed": m.id in ctx.home.completed_measure_ids,
    }


def list_funding(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    kind = args.get("kind")
    out = []
    for f in ctx.funding:
        if kind is not None and f.kind != kind:
            continue
        out.append(
            {
                "id": f.id,
                "name": f.name,
                "provider": f.provider,
                "kind": f.kind,
                "max_amount_gbp": f.max_amount_gbp,
                "apr_percent": f.apr_percent,
                "categories": f.categories,
                "is_mock": f.is_mock,
            }
        )
    return {"funding": out}


def explain_term(_ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    term = str(args.get("term", "")).strip().lower()
    definition = GLOSSARY.get(term)
    if definition is None:
        return {"error": "term not in the glossary", "known_terms": sorted(GLOSSARY)}
    return {"term": term, "definition": definition}


TOOL_LABELS: dict[str, str] = {
    "get_property_facts": "This home's property facts",
    "get_risk_levels": "This home's hazard levels",
    "get_score_breakdown": "This home's resilience score",
    "list_measures": "The measures catalogue",
    "get_measure": "A measure's details",
    "list_funding": "The funding catalogue",
    "explain_term": "Glossary",
}

_DISPATCH = {
    "get_property_facts": get_property_facts,
    "get_risk_levels": get_risk_levels,
    "get_score_breakdown": get_score_breakdown,
    "list_measures": list_measures,
    "get_measure": get_measure,
    "list_funding": list_funding,
    "explain_term": explain_term,
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "get_property_facts",
        "description": "This home's property type, EPC band and other building facts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_risk_levels",
        "description": "This home's hazard levels today and in 2050 (flood, heat, storm, "
        "subsidence, surface water).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_score_breakdown",
        "description": "This home's resilience score and its five component scores.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_measures",
        "description": "The catalogue of possible resilience measures, optionally filtered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "renter_ok": {"type": "boolean"},
            },
        },
    },
    {
        "name": "get_measure",
        "description": "Full details of one measure by id.",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "list_funding",
        "description": "The catalogue of funding products (grants, loans, cashback), "
        "optionally filtered by kind. Catalogue only, not personalised eligibility.",
        "input_schema": {
            "type": "object",
            "properties": {"kind": {"type": "string"}},
        },
    },
    {
        "name": "explain_term",
        "description": "Plain-English definition of a glossary term used in the passport.",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"}},
            "required": ["term"],
        },
    },
]


def call_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": "unknown tool"}
    return fn(ctx, args)
