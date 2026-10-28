"""Improvement planner (spec §7 Planner, step N11): rank, cost and explain measures.

`rank` is pure and deterministic (L's `compute_score` gives each measure's uplift);
`build_plan` adds the explanations (one LLM call per home and measure set, cached; template
otherwise) and the budget selection, which never touch the LLM.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as db
from app.schemas import (
    FundingOption,
    Household,
    Measure,
    Plan,
    PlanItem,
    PropertyFacts,
    RiskProfile,
)
from app.scoring import compute_score
from app.services import llm

MIN_COST_MID_GBP = 50  # spec §7 rule 3: free measures do not divide by zero
PRIORITY_WEIGHT = 1.2  # +20% for measures matching the household's priorities
EXPLAINED_MEASURES = 8  # spec §7 rule 5: the prompt has the top 8
RENTER_TENURES = {"private_renter", "social_renter"}
FIRST_FOR_VULNERABLE = {"heat", "flood"}  # spec §7 rule 3

HAZARD_WORDS = {
    "river_sea_flood": "river and sea flooding",
    "overheating": "overheating",
    "storm": "storm",
    "subsidence": "subsidence",
    "surface_water": "surface-water flooding",
}


@dataclass(frozen=True)
class Ranked:
    measure: Measure
    score_uplift: int
    landlord: bool  # True: shown in the separate "ask your landlord" group (renters)


def matches_priority(m: Measure, priorities: list[str]) -> bool:
    """Which household priority a measure serves (spec §7 rule 3 names the boost, not this
    mapping; see docs/decisions/N.md). `home_value`: measures that raise the EPC rating, which
    is set by energy cost and CO2, so any measure with a bill or carbon saving."""
    return any(
        (p == "lower_bills" and m.annual_bill_saving_gbp > 0)
        or (p == "comfort" and m.category == "heat")
        or (p == "flood_safety" and m.category == "flood")
        or (p == "lower_carbon" and m.co2_saved_kg_per_year > 0)
        or (p == "home_value" and (m.annual_bill_saving_gbp > 0 or m.co2_saved_kg_per_year > 0))
        for p in priorities
    )


def cost_mid(m: Measure) -> float:
    return max(MIN_COST_MID_GBP, (m.cost_low_gbp + m.cost_high_gbp) / 2)


def rank(
    measures: list[Measure],
    risk: RiskProfile,
    prop: PropertyFacts,
    household: Household,
    completed: list[Measure],
) -> list[Ranked]:
    """Spec §7 rules 1–3. Main list first, then (renters only) the landlord group."""
    done = {m.id for m in completed}
    base = compute_score(risk, prop, completed).value
    renter = household.tenure in RENTER_TENURES
    out: list[tuple[tuple, Ranked]] = []
    for m in measures:
        if m.id in done or (m.property_types and prop.property_type not in m.property_types):
            continue
        uplift = compute_score(risk, prop, [*completed, m]).value - base
        weight = PRIORITY_WEIGHT if matches_priority(m, household.priorities) else 1.0
        landlord = renter and m.needs_landlord
        key = (
            landlord,
            not (household.vulnerable and m.category in FIRST_FOR_VULNERABLE),
            -(uplift / cost_mid(m)) * weight,
            m.cost_low_gbp,
            m.id,
        )
        out.append((key, Ranked(m, uplift, landlord)))
    return [r for _, r in sorted(out, key=lambda kr: kr[0])]


def template(r: Ranked) -> str:
    """Spec §7 rule 5 fallback text."""
    m = r.measure
    hazard = HAZARD_WORDS.get(m.hazards_reduced[0]) if m.hazards_reduced else None
    what = f"reduces your {hazard} risk" if hazard else "cuts your home's carbon emissions"
    return (
        f"{m.name} {what} and adds about {r.score_uplift} points "
        f"for £{m.cost_low_gbp:,}–£{m.cost_high_gbp:,}."
    )


def llm_facts(ranked: list[Ranked], risk: RiskProfile, prop: PropertyFacts, score) -> dict:
    """The whole prompt: property facts, hazard levels, score components, top measures.
    Nothing from the household, the address or the account (CONTRACT §6 rule 2)."""
    return {
        "property": prop.model_dump(mode="json", exclude={"source"}),
        "hazards": [
            {"hazard": lv.hazard, "today": lv.today, "in_2050": lv.y2050} for lv in risk.levels
        ],
        "score_components": [
            {"name": c.name, "points": c.points, "max_points": c.max_points}
            for c in score.components
        ],
        "measures": [
            {
                "id": r.measure.id,
                "name": r.measure.name,
                "category": r.measure.category,
                "hazards_reduced": r.measure.hazards_reduced,
                "cost_low_gbp": r.measure.cost_low_gbp,
                "cost_high_gbp": r.measure.cost_high_gbp,
                "annual_bill_saving_gbp": r.measure.annual_bill_saving_gbp,
                "co2_saved_kg_per_year": r.measure.co2_saved_kg_per_year,
                "score_uplift": r.score_uplift,
            }
            for r in ranked[:EXPLAINED_MEASURES]
        ],
    }


async def build_plan(
    session: AsyncSession,
    measures: list[Measure],
    risk: RiskProfile,
    prop: PropertyFacts,
    household: Household,
    completed: list[Measure],
    budget_gbp: int | None = None,
    selected_ids: list[str] | None = None,
) -> Plan:
    ranked = rank(measures, risk, prop, household, completed)
    current = compute_score(risk, prop, completed)
    texts = await llm.explanations(llm_facts(ranked, risk, prop, current), session) or {}

    main = [r for r in ranked if not r.landlord]
    if selected_ids is not None:
        chosen = set(selected_ids) & {r.measure.id for r in main}
    else:  # spec §7 rule 4: highest-ranked measures that fit the budget (low cost)
        budget = household.budget_gbp if budget_gbp is None else budget_gbp
        chosen, spent = set(), 0
        for r in main:
            if spent + r.measure.cost_low_gbp <= budget:
                chosen.add(r.measure.id)
                spent += r.measure.cost_low_gbp

    items = [
        PlanItem(
            measure=r.measure,
            rank=i,
            score_uplift=r.score_uplift,
            payback_years=_payback(r.measure),
            explanation=texts.get(r.measure.id) or template(r),
            selected=r.measure.id in chosen,
        )
        for i, r in enumerate(ranked, start=1)
    ]
    picked = [r.measure for r in ranked if r.measure.id in chosen]
    return Plan(
        items=items,
        total_cost_low_gbp=sum(m.cost_low_gbp for m in picked),
        total_cost_high_gbp=sum(m.cost_high_gbp for m in picked),
        projected_score=compute_score(risk, prop, [*completed, *picked]),
        explanation_source="llm" if any(i.measure.id in texts for i in items) else "template",
    )


def _payback(m: Measure) -> float | None:
    if m.annual_bill_saving_gbp <= 0:
        return None
    return round(((m.cost_low_gbp + m.cost_high_gbp) / 2) / m.annual_bill_saving_gbp, 1)


async def load_measures(session: AsyncSession) -> list[Measure]:
    """A's `measures.csv`, loaded into Postgres by `make seed`."""
    rows = (await session.scalars(select(db.Measure).order_by(db.Measure.id))).all()
    return [Measure.model_validate(r, from_attributes=True) for r in rows]


async def load_funding_options(session: AsyncSession) -> list[FundingOption]:
    """A's `funding.csv`, loaded into Postgres by `make seed` (L6's `match_funding` input)."""
    rows = (await session.scalars(select(db.FundingOption).order_by(db.FundingOption.id))).all()
    return [FundingOption.model_validate(r, from_attributes=True) for r in rows]
