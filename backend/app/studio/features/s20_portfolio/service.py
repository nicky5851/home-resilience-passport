"""Aggregation and scenario maths (docs/studio/N_20_function.md §S20 Algorithm 3-4), pure and
tested; the route is a thin wrapper reading the committed sample (`data.load()`)."""

from datetime import UTC, datetime

from app.studio.common.schemas import Evidence
from app.studio.features.s20_portfolio.config import (
    ATTRIBUTION_FACTOR,
    ATTRIBUTION_NOTE,
    EVIDENCE_SOURCE,
    EVIDENCE_URL,
    FAIRNESS_NOTE,
    MIN_HOMES_PER_DISTRICT,
    SAMPLE_NOTE,
)
from app.studio.features.s20_portfolio.data import PortfolioData, PortfolioHome
from app.studio.features.s20_portfolio.schemas import (
    BandCount,
    District,
    LevelCount,
    Portfolio,
    ScenarioResult,
)

BELOW_C_BANDS = ("D", "E", "F", "G")


def _count_by(values: list[str]) -> list[BandCount]:
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return [BandCount(band=k, count=counts[k]) for k in sorted(counts)]


def _level_counts(homes: tuple[PortfolioHome, ...], hazard: str) -> list[LevelCount]:
    counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    for h in homes:
        level = next((lv.y2050 for lv in h.risk.levels if lv.hazard == hazard), None)
        if level in counts:
            counts[level] += 1
    return [LevelCount(level=level, count=counts[level]) for level in ("low", "medium", "high")]  # type: ignore[arg-type]


def _districts(data: PortfolioData) -> list[District]:
    by_outcode: dict[str, list[PortfolioHome]] = {}
    for h in data.homes:
        by_outcode.setdefault(h.outcode, []).append(h)

    out = []
    for outcode, homes in sorted(by_outcode.items()):
        if len(homes) < MIN_HOMES_PER_DISTRICT:
            continue
        centroid = data.district_centroids.get(outcode)
        if centroid is None:
            continue
        below_c = sum(1 for h in homes if h.property.epc_rating in BELOW_C_BANDS)
        out.append(
            District(
                outcode=outcode,
                lat=centroid[0],
                lon=centroid[1],
                count=len(homes),
                avg_score=round(sum(h.score.value for h in homes) / len(homes), 1),
                below_c_share_pct=round(below_c / len(homes) * 100, 1),
            )
        )
    return out


def build_portfolio(data: PortfolioData) -> Portfolio:
    homes = data.homes
    total = len(homes)
    below_c = sum(1 for h in homes if h.property.epc_rating in BELOW_C_BANDS)
    financed_emissions = sum(
        (h.property.co2_tonnes_per_year or 0.0) * ATTRIBUTION_FACTOR for h in homes
    )

    return Portfolio(
        sample_size=total,
        generated_on=data.generated_on,
        sample_note=SAMPLE_NOTE,
        by_epc_band=_count_by([h.property.epc_rating for h in homes if h.property.epc_rating]),
        by_score_band=_count_by([h.score.band for h in homes]),
        flood_exposure=_level_counts(homes, "river_sea_flood"),
        heat_2050=_level_counts(homes, "overheating"),
        below_c_share_pct=round(below_c / total * 100, 1),
        transition_cost_low_gbp=sum(h.transition.cost_low_gbp for h in homes),
        transition_cost_high_gbp=sum(h.transition.cost_high_gbp for h in homes),
        financed_emissions_t=round(financed_emissions, 1),
        attribution_note=ATTRIBUTION_NOTE,
        districts=_districts(data),
        fairness_note=FAIRNESS_NOTE,
        evidence=[
            Evidence(
                label="Portfolio sample",
                evidence="official_modelled",
                source=EVIDENCE_SOURCE,
                source_url=EVIDENCE_URL,
                retrieved_at=datetime.now(UTC),
            )
        ],
        fallback_used=False,
    )


def run_scenario(data: PortfolioData, uptake_pct: int, by_year: int) -> ScenarioResult:
    """Deterministic: the first `uptake_pct`% of D-G homes, in the sample's seeded order, are
    upgraded (spec step 4). `by_year` is accepted and validated (the segmented control's
    label) but the spec gives no formula linking it to adoption speed, so it does not change
    the maths here (scope note)."""
    homes = data.homes
    total = len(homes)
    financed_before = sum(
        (h.property.co2_tonnes_per_year or 0.0) * ATTRIBUTION_FACTOR for h in homes
    )

    below_c_homes = [h for h in homes if h.property.epc_rating in BELOW_C_BANDS]
    homes_upgraded = round(uptake_pct / 100 * len(below_c_homes))
    selected = below_c_homes[:homes_upgraded]

    moved_to_c = sum(1 for h in selected if h.transition.reached_c)
    co2_saved_t = sum(h.transition.co2_saved_kg_per_year / 1000 for h in selected)
    financed_after = max(0.0, financed_before - co2_saved_t * ATTRIBUTION_FACTOR)
    reduction_pct = (
        0.0 if financed_before == 0 else (financed_before - financed_after) / financed_before * 100
    )
    below_c_after_count = len(below_c_homes) - moved_to_c
    below_c_after_pct = below_c_after_count / total * 100 if total else 0.0

    return ScenarioResult(
        emissions_before_t=round(financed_before, 1),
        emissions_after_t=round(financed_after, 1),
        reduction_pct=round(reduction_pct, 1),
        below_c_share_after_pct=round(below_c_after_pct, 1),
        homes_upgraded=homes_upgraded,
        finance_needed_low_gbp=sum(h.transition.cost_low_gbp for h in selected),
        finance_needed_high_gbp=sum(h.transition.cost_high_gbp for h in selected),
    )
