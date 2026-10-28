"""Pure sandbox logic: hotspot grouping and the before/after score simulation."""

from app.schemas import Measure, PropertyFacts, RiskProfile
from app.scoring import compute_score
from app.studio.features.s01_retrofit_sandbox.config import HOTSPOT_LABELS, hotspot_for
from app.studio.features.s01_retrofit_sandbox.schemas import (
    Hotspot,
    HotspotId,
    SandboxMeasure,
    SandboxState,
    ScoreComponentDelta,
)

MAX_SELECTED = 30


def eligible_measures(measures: list[Measure], property_type: str | None) -> list[Measure]:
    return [m for m in measures if not m.property_types or property_type in m.property_types]


def build_sandbox_measures(
    measures: list[Measure], property_type: str | None, already_done_ids: set[str]
) -> list[SandboxMeasure]:
    return [
        SandboxMeasure(
            measure=m, hotspot=hotspot_for(m.id, m.name), already_done=m.id in already_done_ids
        )
        for m in eligible_measures(measures, property_type)
    ]


def build_hotspots(sandbox_measures: list[SandboxMeasure]) -> list[Hotspot]:
    by_hotspot: dict[HotspotId, list[str]] = {hid: [] for hid in HOTSPOT_LABELS}
    for sm in sandbox_measures:
        by_hotspot[sm.hotspot].append(sm.measure.id)
    return [
        Hotspot(id=hid, label=HOTSPOT_LABELS[hid], measure_ids=ids)
        for hid, ids in by_hotspot.items()
    ]


def simulate(
    risk: RiskProfile,
    prop: PropertyFacts,
    all_measures: list[Measure],
    already_done: list[Measure],
    selected_ids: list[str],
) -> SandboxState:
    by_id = {m.id: m for m in all_measures}
    selected = [by_id[mid] for mid in selected_ids]

    before = compute_score(risk, prop, already_done)
    completed = [*already_done, *selected]
    after = compute_score(risk, prop, completed)

    before_by_name = {c.name: c for c in before.components}
    components = [
        ScoreComponentDelta(
            name=c.name,
            before=before_by_name[c.name].points,
            after=c.points,
            max_points=c.max_points,
        )
        for c in after.components
    ]

    cost_low = sum(m.cost_low_gbp for m in selected)
    cost_high = sum(m.cost_high_gbp for m in selected)
    bill_saving = sum(m.annual_bill_saving_gbp for m in selected)
    co2_saved = sum(m.co2_saved_kg_per_year for m in selected)
    mid_cost = (cost_low + cost_high) / 2
    payback = round(mid_cost / bill_saving, 1) if bill_saving > 0 else None

    return SandboxState(
        score=after,
        delta_points=after.value - before.value,
        cost_low_gbp=cost_low,
        cost_high_gbp=cost_high,
        bill_saving_gbp_per_year=bill_saving,
        co2_saved_kg_per_year=co2_saved,
        components=components,
        payback_years=payback,
    )
