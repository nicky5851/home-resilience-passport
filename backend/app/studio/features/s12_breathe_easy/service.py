from datetime import datetime

from app.studio.features.s12_breathe_easy.config import MIN_WINDOW_HOURS, SUMMER_MONTHS
from app.studio.features.s12_breathe_easy.open_meteo import AirQualityHour, WeatherHour
from app.studio.features.s12_breathe_easy.schemas import BreatheEasyRequest, HourReading, Window
from app.studio.features.s12_breathe_easy.scoring import (
    advice_for,
    daqi_band,
    daqi_for,
    pollen_level,
    score_for,
)


def build_hours(
    aq: list[AirQualityHour], wx: list[WeatherHour], request: BreatheEasyRequest
) -> list[HourReading]:
    wx_by_time = {w.at: w for w in wx}
    hours = []
    for a in aq:
        w = wx_by_time.get(a.at)
        index = daqi_for(a.pm2_5, a.pm10, a.no2, a.o3)
        band = daqi_band(index)
        pollen_grains = max(
            (v for v in (a.grass_pollen, a.birch_pollen, a.alder_pollen) if v is not None),
            default=None,
        )
        level = pollen_level(pollen_grains)
        temp_c = w.temp_c if w else None
        dew_point_c = w.dew_point_c if w else None
        score = score_for(
            at=a.at,
            daqi_band_value=band,
            pollen_level_value=level,
            temp_c=temp_c,
            dew_point_c=dew_point_c,
            pollution_sensitive=request.pollution_sensitive,
            pollen_sensitive=request.pollen_sensitive,
        )
        advice = advice_for(score, a.at.month in SUMMER_MONTHS)
        hours.append(
            HourReading(
                at=a.at,
                daqi=index,
                daqi_band=band,
                pm2_5=a.pm2_5,
                no2=a.no2,
                o3=a.o3,
                pollen_level=level,
                temp_c=temp_c,
                rh_pct=w.rh_pct if w else None,
                score=score,
                advice=advice,
            )
        )
    return hours


def _windows_for(hours: list[HourReading], predicate, reason: str) -> list[Window]:
    windows: list[Window] = []
    run_start: datetime | None = None
    for h in hours:
        if predicate(h):
            if run_start is None:
                run_start = h.at
        elif run_start is not None:
            _append_window(windows, run_start, h.at, reason)
            run_start = None
    if run_start is not None and hours:
        _append_window(windows, run_start, hours[-1].at, reason)
    return windows


def _append_window(windows: list[Window], start: datetime, end: datetime, reason: str) -> None:
    hours_long = (end - start).total_seconds() / 3600
    if hours_long >= MIN_WINDOW_HOURS:
        windows.append(Window(start_at=start, end_at=end, reason=reason))


def best_windows(hours: list[HourReading]) -> list[Window]:
    reason = "Clean, cool air - good time to open up."
    return _windows_for(hours, lambda h: h.advice == "open", reason)


def avoid_windows(hours: list[HourReading]) -> list[Window]:
    reason = "Poor air quality or heavy pollen."
    return _windows_for(hours, lambda h: h.advice == "keep_closed", reason)


def today_summary(hours: list[HourReading], best: list[Window], avoid: list[Window]) -> str:
    if not hours:
        return "No air quality data available right now."
    if best:
        w = best[0]
        best_text = f"Best time to air the house today: {w.start_at:%H:%M}–{w.end_at:%H:%M}."
    else:
        best_text = "No clear best window for airing the house today."
    if avoid:
        w = avoid[0]
        avoid_reason = w.reason.lower().rstrip(".")
        avoid_text = f" Keep windows shut {w.start_at:%H:%M}–{w.end_at:%H:%M} ({avoid_reason})."
    else:
        avoid_text = ""
    return best_text + avoid_text
