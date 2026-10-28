"""Permitted-development rules engine (docs/studio/N_20_function.md §S10 Algorithm, rules 1-7),
pure and table-driven."""

from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.studio.features.s10_permission_radar.config import (
    DEFAULT_FAMILY,
    GPDO_URL,
    MEASURE_FAMILY_RULES,
    PLANNING_PORTAL_URL,
)
from app.studio.features.s10_permission_radar.schemas import Constraint, MeasureVerdict

EXTERNAL_FAMILIES = {"windows", "doors", "roofing", "solar", "heat_pump", "wall_insulation"}


def family_for(measure_id: str, measure_name: str) -> str:
    text = f"{measure_id} {measure_name}".lower()
    for family, keywords in MEASURE_FAMILY_RULES:
        if any(k in text for k in keywords):
            return family
    return DEFAULT_FAMILY


def _applies(constraints: dict[str, bool | None], dataset: str) -> bool:
    return constraints.get(dataset) is True


def _unknown(constraints: dict[str, bool | None], dataset: str) -> bool:
    return constraints.get(dataset) is None


def verdict_for(
    measure: Measure, family: str, prop: PropertyFacts, constraints: dict[str, bool | None]
) -> MeasureVerdict:
    is_flat = prop.property_type == "flat"
    is_external = family in EXTERNAL_FAMILIES
    reasons: list[str] = []

    # 1. Flats: no householder PD rights for external works.
    if is_flat and is_external:
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="check_council",
            reasons=[
                "Flats don't have householder permitted development rights; also ask your "
                "freeholder."
            ],
            guidance_url=PLANNING_PORTAL_URL,
        )
    if is_flat and not is_external:
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="likely_permitted",
            reasons=["Internal-only work is generally not development requiring permission."],
            guidance_url=PLANNING_PORTAL_URL,
        )

    # Unknown coverage (API down) -> safe default for external measures.
    unreachable = any(_unknown(constraints, d) for d in constraints)

    # 2. Listed building.
    if _applies(constraints, "listed-building-outline"):
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="consent_needed",
            reasons=["Listed building consent is needed for most external and internal works."],
            guidance_url=GPDO_URL,
        )

    # 3. Article 4 direction.
    if _applies(constraints, "article-4-direction-area") and family in (
        "windows",
        "doors",
        "roofing",
        "solar",
    ):
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="check_council",
            reasons=["An Article 4 direction removes permitted development rights here."],
            guidance_url=PLANNING_PORTAL_URL,
        )

    # 4. Conservation area.
    if _applies(constraints, "conservation-area"):
        if family == "wall_insulation":
            return MeasureVerdict(
                measure_id=measure.id,
                name=measure.name,
                verdict="check_council",
                reasons=["External wall insulation/cladding needs a check in a conservation area."],
                guidance_url=PLANNING_PORTAL_URL,
            )
        if family == "solar":
            return MeasureVerdict(
                measure_id=measure.id,
                name=measure.name,
                verdict="likely_permitted",
                reasons=[
                    "Roof solar is usually permitted development, even in a conservation area.",
                    "A wall-mounted panel fronting a highway would need a council check instead.",
                ],
                guidance_url=PLANNING_PORTAL_URL,
            )
        if family == "heat_pump":
            return MeasureVerdict(
                measure_id=measure.id,
                name=measure.name,
                verdict="check_council",
                reasons=[
                    "A heat pump on a wall fronting a highway needs a council check in a "
                    "conservation area.",
                    "The 1 m boundary-distance rule was removed in England from 29 May 2025 "
                    "(S.I. 2025/560); noise limits (MCS 020) still apply.",
                ],
                guidance_url=PLANNING_PORTAL_URL,
            )

    # 5. Tree preservation.
    if family == "tree_works" and (_applies(constraints, "tree-preservation-zone")):
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="consent_needed",
            reasons=["Tree works need consent under a tree preservation order/zone."],
            guidance_url=PLANNING_PORTAL_URL,
        )

    # 6. Hard surfacing (Class F).
    if family == "hard_surfacing":
        permeable = "permeable" in measure.id.lower() or "permeable" in measure.name.lower()
        if permeable:
            return MeasureVerdict(
                measure_id=measure.id,
                name=measure.name,
                verdict="likely_permitted",
                reasons=["Permeable surfacing over 5 sqm is permitted development (Class F)."],
                guidance_url=GPDO_URL,
            )
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="check_council",
            reasons=[
                "An impermeable front-garden surface over 5 sqm needs planning permission "
                "unless it drains to a permeable area (Class F)."
            ],
            guidance_url=GPDO_URL,
        )

    # Safe default when the constraints API is unreachable.
    if unreachable and is_external:
        return MeasureVerdict(
            measure_id=measure.id,
            name=measure.name,
            verdict="check_council",
            reasons=[
                "Planning constraint data was unreachable; check with your council to be safe."
            ],
            guidance_url=PLANNING_PORTAL_URL,
        )

    # 7. Otherwise likely permitted.
    if family == "heat_pump":
        reasons = [
            "Likely permitted development, subject to noise limits (MCS 020 sound calculation).",
            "The 1 m boundary-distance rule was removed in England from 29 May 2025 "
            "(S.I. 2025/560).",
        ]
    elif not is_external:
        reasons = ["Internal-only work is generally not development requiring permission."]
    else:
        reasons = ["Likely permitted development, subject to the usual size/position limits."]

    return MeasureVerdict(
        measure_id=measure.id,
        name=measure.name,
        verdict="likely_permitted",
        reasons=reasons[:3],
        guidance_url=PLANNING_PORTAL_URL,
    )


def entity_label(dataset: str, entity: dict) -> Constraint:
    from app.studio.features.s10_permission_radar.config import DATASETS

    reference = entity.get("reference")
    entity_id = entity.get("entity")
    return Constraint(
        dataset=dataset,
        label=DATASETS[dataset],
        name=entity.get("name"),
        reference=reference,
        entity_url=f"https://www.planning.data.gov.uk/entity/{entity_id}" if entity_id else None,
        applies=True,
    )
