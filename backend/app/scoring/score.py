"""Resilience score from a RiskProfile. L3 stub: half points everywhere; real rules in L5."""

from collections.abc import Sequence

from app.schemas import Measure, PropertyFacts, ResilienceScore, RiskProfile, ScoreComponent
from app.scoring.config import MAX_POINTS, SCORE_BANDS, SCORING_VERSION

STUB_REASON = "Placeholder points until the score engine is ready."


def band_for(value: int) -> str:
    for band, floor in SCORE_BANDS:
        if value >= floor:
            return band
    return "G"


def compute_score(
    risk: RiskProfile, prop: PropertyFacts, completed_measures: Sequence[Measure] = ()
) -> ResilienceScore:
    components = [
        ScoreComponent(name=name, points=mx / 2, max_points=mx, reason=STUB_REASON)
        for name, mx in MAX_POINTS.items()
    ]
    value = round(sum(c.points for c in components))
    return ResilienceScore(
        value=value, band=band_for(value), components=components, version=SCORING_VERSION
    )
