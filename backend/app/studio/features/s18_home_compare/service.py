"""Cost-to-70 and winners maths (docs/studio/N_20_function.md §S18 Algorithm 3-4), pure and
tested."""

from app.schemas.hazards import RiskProfile
from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.schemas.score import ResilienceScore
from app.scoring import compute_score
from app.services.planner import Ranked
from app.studio.features.s18_home_compare.config import SCORE_TARGET, TOP_MEASURES_LIMIT
from app.studio.features.s18_home_compare.schemas import Label, TopMeasure


def top_measures(ranked: list[Ranked]) -> list[TopMeasure]:
    return [
        TopMeasure(
            measure_id=r.measure.id,
            name=r.measure.name,
            cost_low_gbp=r.measure.cost_low_gbp,
            cost_high_gbp=r.measure.cost_high_gbp,
            score_uplift=r.score_uplift,
        )
        for r in ranked[:TOP_MEASURES_LIMIT]
    ]


def cost_to_70(
    ranked: list[Ranked], risk: RiskProfile, prop: PropertyFacts
) -> tuple[int | None, int | None]:
    completed: list[Measure] = []
    low = 0
    high = 0
    for r in ranked:
        completed.append(r.measure)
        low += r.measure.cost_low_gbp
        high += r.measure.cost_high_gbp
        if compute_score(risk, prop, completed).value >= SCORE_TARGET:
            return low, high
    return None, None


def winner_for_component(scores: list[ResilienceScore], labels: list[Label], name: str) -> Label:
    def points(score: ResilienceScore) -> float:
        return next((c.points for c in score.components if c.name == name), 0.0)

    best = max(range(len(scores)), key=lambda i: points(scores[i]))
    return labels[best]


def overall_winner(
    scores: list[ResilienceScore], costs_low: list[int | None], labels: list[Label]
) -> Label:
    def key(i: int) -> tuple[int, int]:
        cost = costs_low[i]
        return (-scores[i].value, cost if cost is not None else 10**9)

    best = min(range(len(scores)), key=key)
    return labels[best]
