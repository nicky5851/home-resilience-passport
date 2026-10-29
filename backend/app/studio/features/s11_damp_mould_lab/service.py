from collections import defaultdict

from app.schemas.property import PropertyFacts
from app.studio.features.s11_damp_mould_lab.config import (
    AGE_BAND_WALL_U,
    AGE_BAND_WINDOW_U,
    DEFAULT_WALL_U,
    DEFAULT_WINDOW_U,
    DOUBLE_GLAZING_U,
    LEVEL_LOW_MAX_PCT,
    LEVEL_MEDIUM_MAX_PCT,
    RSI_WALL,
    RSI_WINDOW,
    WALL_INSULATION_U,
    WINDOW_CONDENSATION_RH,
)
from app.studio.features.s11_damp_mould_lab.era5_winter import HourlyWeather
from app.studio.features.s11_damp_mould_lab.physics import (
    corner_f_rsi,
    f_rsi,
    level_for,
    moisture_class_for,
    surface_rh,
)
from app.studio.features.s11_damp_mould_lab.schemas import (
    DampLabRequest,
    Intervention,
    MonthlyCornerRisk,
    SurfaceRisk,
)

MONTH_NAMES = {11: "Nov", 12: "Dec", 1: "Jan", 2: "Feb", 3: "Mar"}


def wall_u_for(prop: PropertyFacts) -> float:
    return AGE_BAND_WALL_U.get(prop.construction_age_band or "", DEFAULT_WALL_U)


def window_u_for(prop: PropertyFacts) -> float:
    return AGE_BAND_WINDOW_U.get(prop.construction_age_band or "", DEFAULT_WINDOW_U)


def _risk_hours_pct(
    hourly: list[HourlyWeather],
    wall_u: float,
    window_u: float,
    heating_setpoint_c: float,
    moisture_class: int,
) -> tuple[float, float, float, dict[str, dict[str, int]]]:
    """Returns (wall_pct, corner_pct, window_pct, monthly counts)."""
    wall_f = f_rsi(wall_u, RSI_WALL)
    corner_f = corner_f_rsi(wall_f)
    window_f = f_rsi(window_u, RSI_WINDOW)

    total = len(hourly) or 1
    wall_hits = corner_hits = window_hits = 0
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"risk": 0, "total": 0})

    for h in hourly:
        wall_rh = surface_rh(h.temp_c, h.rh, heating_setpoint_c, wall_f, moisture_class)
        corner_rh = surface_rh(h.temp_c, h.rh, heating_setpoint_c, corner_f, moisture_class)
        window_rh = surface_rh(h.temp_c, h.rh, heating_setpoint_c, window_f, moisture_class)

        wall_hits += wall_rh >= 0.80
        corner_at_risk = corner_rh >= 0.80
        corner_hits += corner_at_risk
        window_hits += window_rh >= WINDOW_CONDENSATION_RH

        key = MONTH_NAMES.get(h.at.month, str(h.at.month))
        monthly[key]["total"] += 1
        monthly[key]["risk"] += int(corner_at_risk)

    return (
        100 * wall_hits / total,
        100 * corner_hits / total,
        100 * window_hits / total,
        dict(monthly),
    )


def build_monthly(monthly_counts: dict[str, dict[str, int]]) -> list[MonthlyCornerRisk]:
    order = ["Nov", "Dec", "Jan", "Feb", "Mar"]
    out = []
    for month in order:
        counts = monthly_counts.get(month)
        if not counts or counts["total"] == 0:
            continue
        out.append(
            MonthlyCornerRisk(
                month=month, corner_risk_pct=round(100 * counts["risk"] / counts["total"], 1)
            )
        )
    return out


def build_interventions(
    hourly: list[HourlyWeather],
    wall_u: float,
    window_u: float,
    heating_setpoint_c: float,
    moisture_class: int,
    base_corner_pct: float,
    kitchen_extractor: bool,
    bathroom_extractor: bool,
    trickle_vents: bool,
) -> list[Intervention]:
    candidates: list[tuple[str, str, int, float, float]] = []

    if not (kitchen_extractor and bathroom_extractor):
        candidates.append(
            ("extractors", "Fit kitchen and bathroom extractor fans", -1, wall_u, window_u)
        )
    candidates.append(
        ("dry-outside", "Dry clothes outside or in a vented room", -1, wall_u, window_u)
    )
    candidates.append(("heating", "Turn the heating up by 1°C", 0, wall_u, window_u))
    if wall_u > WALL_INSULATION_U:
        candidates.append(("wall-insulation", "Insulate the walls", 0, WALL_INSULATION_U, window_u))
    if window_u > DOUBLE_GLAZING_U:
        candidates.append(
            ("double-glazing", "Upgrade to double glazing", 0, wall_u, DOUBLE_GLAZING_U)
        )

    results = []
    for intervention_id, label, class_delta, new_wall_u, new_window_u in candidates:
        new_setpoint = heating_setpoint_c + (1.0 if intervention_id == "heating" else 0.0)
        new_class = max(1, min(4, moisture_class + class_delta))
        _, corner_pct, _, _ = _risk_hours_pct(
            hourly, new_wall_u, new_window_u, new_setpoint, new_class
        )
        results.append(
            Intervention(
                id=intervention_id,
                label=label,
                corner_risk_pct_after=round(corner_pct, 1),
                delta_pct=round(base_corner_pct - corner_pct, 1),
            )
        )
    return sorted(results, key=lambda i: i.delta_pct, reverse=True)


def build_damp_lab(
    prop: PropertyFacts, hourly: list[HourlyWeather], request: DampLabRequest, winter_label: str
) -> tuple[list[SurfaceRisk], list[MonthlyCornerRisk], list[Intervention], float, float, int]:
    wall_u = wall_u_for(prop)
    window_u = window_u_for(prop)
    moisture_class = moisture_class_for(
        request.occupants,
        request.dries_clothes_indoors,
        request.kitchen_extractor,
        request.bathroom_extractor,
        request.trickle_vents,
    )

    wall_pct, corner_pct, window_pct, monthly_counts = _risk_hours_pct(
        hourly, wall_u, window_u, request.heating_setpoint_c, moisture_class
    )

    surfaces = [
        SurfaceRisk(
            surface="wall",
            risk_hours_pct=round(wall_pct, 1),
            level=level_for(wall_pct, LEVEL_LOW_MAX_PCT, LEVEL_MEDIUM_MAX_PCT),
        ),
        SurfaceRisk(
            surface="corner",
            risk_hours_pct=round(corner_pct, 1),
            level=level_for(corner_pct, LEVEL_LOW_MAX_PCT, LEVEL_MEDIUM_MAX_PCT),
        ),
        SurfaceRisk(
            surface="window",
            risk_hours_pct=round(window_pct, 1),
            level=level_for(window_pct, LEVEL_LOW_MAX_PCT, LEVEL_MEDIUM_MAX_PCT),
        ),
    ]
    monthly = build_monthly(monthly_counts)
    interventions = build_interventions(
        hourly,
        wall_u,
        window_u,
        request.heating_setpoint_c,
        moisture_class,
        corner_pct,
        request.kitchen_extractor,
        request.bathroom_extractor,
        request.trickle_vents,
    )
    return surfaces, monthly, interventions, wall_u, window_u, moisture_class
