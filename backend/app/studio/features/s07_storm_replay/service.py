from app.schemas.plan import Measure
from app.schemas.property import PropertyFacts
from app.studio.features.s07_storm_replay.config import (
    EVENTS,
    GUTTER_OVERFLOW_RAIN_MM_PER_H,
    LESSON_CATEGORY_BY_KIND,
    MAX_LESSONS,
    MAX_PEAK_MOMENTS,
    TAU_DEFAULT,
    TAU_HOURS_BY_CONSTRUCTION,
)
from app.studio.features.s07_storm_replay.era5_event import HourlyWeather
from app.studio.features.s07_storm_replay.schemas import (
    EventSummary,
    HourlyReplayPoint,
    Lesson,
    LocalPeak,
    PeakMoment,
)
from app.studio.features.s07_storm_replay.sim import (
    heat_severity,
    max_24h_rolling_rain,
    rain_severity,
    simulate_indoor,
    wind_severity,
)


def event_by_id(event_id: str) -> dict | None:
    return next((e for e in EVENTS if e["id"] == event_id), None)


def tau_for(prop: PropertyFacts) -> float:
    if prop.property_type == "flat":
        return TAU_HOURS_BY_CONSTRUCTION["timber_or_flat"]
    age_band = prop.construction_age_band or ""
    if age_band in ("before 1900", "1900-1929"):
        return TAU_HOURS_BY_CONSTRUCTION["solid_masonry"]
    return TAU_HOURS_BY_CONSTRUCTION.get("cavity", TAU_DEFAULT)


def summarise_event(event: dict, hourly: list[HourlyWeather]) -> EventSummary:
    kind = event["kind"]
    if kind == "wind":
        peak = max(hourly, key=lambda h: h.gust_kmh)
        severity = wind_severity(peak.gust_kmh)
        local_peak = LocalPeak(value=peak.gust_kmh, unit="km/h", at=peak.at)
        headline = f"Gusts of {round(peak.gust_kmh)} km/h at your home"
    elif kind == "rain":
        rolling = max_24h_rolling_rain(hourly)
        peak = max(hourly, key=lambda h: h.rain_mm)
        severity = rain_severity(rolling)
        local_peak = LocalPeak(value=round(rolling, 1), unit="mm/24h", at=peak.at)
        headline = f"{round(rolling)} mm of rain in 24 hours at your home"
    else:
        peak = max(hourly, key=lambda h: h.temp_c)
        severity = heat_severity(peak.temp_c)
        local_peak = LocalPeak(value=peak.temp_c, unit="°C", at=peak.at)
        headline = f"{peak.temp_c}°C at your home"

    return EventSummary(
        id=event["id"],
        name=event["name"],
        kind=kind,
        start_date=event["start_date"],
        end_date=event["end_date"],
        local_peak=local_peak,
        severity=round(severity, 2),
        headline=headline,
    )


def build_replay(
    event: dict, hourly: list[HourlyWeather], prop: PropertyFacts, measures: list[Measure]
) -> tuple[EventSummary, list[HourlyReplayPoint], list[PeakMoment], list[Lesson]]:
    summary = summarise_event(event, hourly)
    kind = event["kind"]

    indoor_now = indoor_measures = None
    if kind == "heat":
        is_top_floor_flat = bool(prop.top_floor) and prop.property_type == "flat"
        tau = tau_for(prop)
        indoor_now = simulate_indoor(
            hourly, tau, is_top_floor_flat, shading=False, night_vent=False
        )
        indoor_measures = simulate_indoor(
            hourly, tau, is_top_floor_flat, shading=True, night_vent=True
        )

    points = [
        HourlyReplayPoint(
            at=h.at,
            temp_c=h.temp_c,
            gust_kmh=h.gust_kmh,
            wind_kmh=h.wind_kmh,
            rain_mm=h.rain_mm,
            indoor_now_c=indoor_now[i] if indoor_now else None,
            indoor_with_measures_c=indoor_measures[i] if indoor_measures else None,
        )
        for i, h in enumerate(hourly)
    ]

    peak_moments = [PeakMoment(at=summary.local_peak.at, label=summary.headline)]
    if kind == "rain":
        overflow = next((h for h in hourly if h.rain_mm >= GUTTER_OVERFLOW_RAIN_MM_PER_H), None)
        if overflow:
            peak_moments.append(PeakMoment(at=overflow.at, label="Gutters likely overflowing"))
    peak_moments = peak_moments[:MAX_PEAK_MOMENTS]

    category = LESSON_CATEGORY_BY_KIND[kind]
    relevant = [m for m in measures if m.category == category][:MAX_LESSONS]
    lessons = [Lesson(text=f"Consider: {m.name}", measure_id=m.id) for m in relevant]
    if not lessons:
        lessons = [Lesson(text="No specific measures logged for this hazard yet.", measure_id=None)]

    return summary, points, peak_moments, lessons
