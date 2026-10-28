"""Resilience score from a RiskProfile (spec CODING_SPEC.md §6, docs/scoring.md).

0-100 points: flood 30, heat 20, storm 10, subsidence 10 (resilience = 70%), carbon 30. Hazard
points use the **2050** level (forward-looking); carbon points come from the EPC score, or the
band midpoint if only the rating is known, or a flat 15 if both are unknown. Completed (or
candidate) measures add their `resilience_points` to the component named by their `category`,
capped at that component's max.
"""

from collections.abc import Sequence

from app.schemas import Measure, PropertyFacts, ResilienceScore, RiskProfile, ScoreComponent
from app.scoring.config import (
    CARBON_POINTS_PER_EPC_POINT,
    CARBON_POINTS_UNKNOWN,
    EPC_BAND_MIDPOINT,
    HAZARD_COMPONENT,
    LEVEL_FRACTION,
    MAX_POINTS,
    SCORE_BANDS,
    SCORING_VERSION,
)

_COMPONENT_HAZARD = {component: hazard for hazard, component in HAZARD_COMPONENT.items()}


def band_for(value: int) -> str:
    for band, floor in SCORE_BANDS:
        if value >= floor:
            return band
    return "G"


def _carbon_points_and_reason(prop: PropertyFacts) -> tuple[float, str]:
    if prop.epc_score is not None:
        return prop.epc_score * CARBON_POINTS_PER_EPC_POINT, (
            f"Based on your EPC score of {prop.epc_score}."
        )
    if prop.epc_rating is not None:
        return EPC_BAND_MIDPOINT[prop.epc_rating] * CARBON_POINTS_PER_EPC_POINT, (
            f"Estimated from your EPC rating of {prop.epc_rating} (no exact score yet)."
        )
    return CARBON_POINTS_UNKNOWN, "Your EPC rating is unknown, so this is a flat estimate."


def compute_score(
    risk: RiskProfile, prop: PropertyFacts, completed_measures: Sequence[Measure] = ()
) -> ResilienceScore:
    by_hazard = {lv.hazard: lv.y2050 for lv in risk.levels}
    base_points = {
        component: MAX_POINTS[component] * LEVEL_FRACTION[by_hazard[hazard]]
        for hazard, component in HAZARD_COMPONENT.items()
    }
    carbon_points, carbon_reason = _carbon_points_and_reason(prop)
    base_points["carbon"] = carbon_points

    bonus: dict[str, float] = {}
    for measure in completed_measures:
        bonus[measure.category] = bonus.get(measure.category, 0) + measure.resilience_points

    components = []
    for name, max_points in MAX_POINTS.items():
        pts = round(min(base_points[name] + bonus.get(name, 0), max_points), 1)
        if name == "carbon":
            reason = carbon_reason
        else:
            level = by_hazard[_COMPONENT_HAZARD[name]]
            reason = f"Your {name} risk is {level} by 2050, worth {pts:g} of {max_points:g} points."
        if bonus.get(name):
            reason += f" Completed measures add {bonus[name]:g} points."
        components.append(
            ScoreComponent(name=name, points=pts, max_points=max_points, reason=reason)
        )

    value = max(0, min(100, round(sum(c.points for c in components))))
    return ResilienceScore(
        value=value, band=band_for(value), components=components, version=SCORING_VERSION
    )
