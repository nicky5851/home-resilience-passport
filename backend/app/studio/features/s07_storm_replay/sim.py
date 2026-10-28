"""Pure severity scoring and the one-node indoor-temperature model
(docs/studio/N_20_function.md §S07 algorithm 2-3)."""

from datetime import datetime

from app.studio.features.s07_storm_replay.config import (
    HEAT_SEVERITY_BASE_C,
    HEAT_SEVERITY_DIVISOR_C,
    NIGHT_VENT_END_HOUR,
    NIGHT_VENT_START_HOUR,
    NIGHT_VENT_TAU_DIVISOR,
    RAIN_SEVERITY_DIVISOR_MM,
    SHADING_GAIN_MULTIPLIER,
    SOLAR_GAIN_END_HOUR,
    SOLAR_GAIN_K_PER_HOUR,
    SOLAR_GAIN_START_HOUR,
    TOP_FLOOR_FLAT_GAIN_MULTIPLIER,
    WIND_SEVERITY_DIVISOR_KMH,
)
from app.studio.features.s07_storm_replay.era5_event import HourlyWeather


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def wind_severity(peak_gust_kmh: float) -> float:
    return _clip01(peak_gust_kmh / WIND_SEVERITY_DIVISOR_KMH)


def rain_severity(max_24h_rolling_mm: float) -> float:
    return _clip01(max_24h_rolling_mm / RAIN_SEVERITY_DIVISOR_MM)


def heat_severity(peak_temp_c: float) -> float:
    return _clip01((peak_temp_c - HEAT_SEVERITY_BASE_C) / HEAT_SEVERITY_DIVISOR_C)


def max_24h_rolling_rain(hourly: list[HourlyWeather]) -> float:
    if len(hourly) < 24:
        return sum(h.rain_mm for h in hourly)
    window = sum(h.rain_mm for h in hourly[:24])
    best = window
    for i in range(24, len(hourly)):
        window += hourly[i].rain_mm - hourly[i - 24].rain_mm
        best = max(best, window)
    return best


def solar_gain(at: datetime, is_top_floor_flat: bool, shading: bool) -> float:
    if not (SOLAR_GAIN_START_HOUR <= at.hour < SOLAR_GAIN_END_HOUR):
        return 0.0
    gain = SOLAR_GAIN_K_PER_HOUR
    if is_top_floor_flat:
        gain *= TOP_FLOOR_FLAT_GAIN_MULTIPLIER
    if shading:
        gain *= SHADING_GAIN_MULTIPLIER
    return gain


def simulate_indoor(
    hourly: list[HourlyWeather],
    tau_hours: float,
    is_top_floor_flat: bool,
    shading: bool,
    night_vent: bool,
    start_indoor_c: float = 22.0,
) -> list[float]:
    """One-node model: `T_in(t+1) = T_in + (dt/tau)(T_out - T_in) + G(t)`, dt=1h."""
    indoor = []
    t_in = start_indoor_c
    for h in hourly:
        tau = tau_hours
        is_night = h.at.hour >= NIGHT_VENT_START_HOUR or h.at.hour < NIGHT_VENT_END_HOUR
        if night_vent and is_night and h.temp_c < t_in:
            tau = tau_hours / NIGHT_VENT_TAU_DIVISOR
        t_in = t_in + (1.0 / tau) * (h.temp_c - t_in) + solar_gain(h.at, is_top_floor_flat, shading)
        indoor.append(round(t_in, 2))
    return indoor
