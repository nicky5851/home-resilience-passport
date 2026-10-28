from datetime import datetime

from app.studio.features.s06_grid_carbon_clock.config import APPLIANCES, MIX_FUELS
from app.studio.features.s06_grid_carbon_clock.schemas import (
    BestWindow,
    CurrentIntensity,
    ForecastSlot,
    MixShare,
    Slot,
)


def parse_mix(generationmix: list[dict]) -> list[MixShare]:
    by_fuel = {m["fuel"]: m["perc"] for m in generationmix}
    return [MixShare(fuel=f, percent=by_fuel.get(f, 0.0)) for f in MIX_FUELS]


def parse_current(period: dict) -> CurrentIntensity:
    return CurrentIntensity(
        intensity_g_per_kwh=round(period["intensity"]["forecast"]),
        index=period["intensity"]["index"],
        mix=parse_mix(period["generationmix"]),
    )


def parse_forecast(periods: list[dict]) -> list[ForecastSlot]:
    return [
        ForecastSlot(
            from_at=datetime.fromisoformat(p["from"].replace("Z", "+00:00")),
            to_at=datetime.fromisoformat(p["to"].replace("Z", "+00:00")),
            intensity_g_per_kwh=round(p["intensity"]["forecast"]),
            index=p["intensity"]["index"],
        )
        for p in periods
    ]


def best_window(
    forecast: list[ForecastSlot], appliance_id: str, now_intensity: float
) -> BestWindow | None:
    label, kwh, slots_needed = APPLIANCES[appliance_id]
    if len(forecast) < slots_needed:
        return None

    best_start = 0
    best_mean = None
    for start in range(len(forecast) - slots_needed + 1):
        window = forecast[start : start + slots_needed]
        mean = sum(s.intensity_g_per_kwh for s in window) / slots_needed
        if best_mean is None or mean < best_mean:
            best_mean, best_start = mean, start

    assert best_mean is not None
    window = forecast[best_start : best_start + slots_needed]
    saving_pct = (
        round((now_intensity - best_mean) / now_intensity * 100, 1) if now_intensity > 0 else 0.0
    )
    saving_g = round((now_intensity - best_mean) * kwh, 1)
    return BestWindow(
        appliance_id=appliance_id,
        label=label,
        start_at=window[0].from_at,
        end_at=window[-1].to_at,
        avg_intensity_g_per_kwh=round(best_mean, 1),
        saving_pct_vs_now=saving_pct,
        saving_g=saving_g,
    )


def best_windows_for_all(forecast: list[ForecastSlot], now_intensity: float) -> list[BestWindow]:
    windows = []
    for appliance_id in APPLIANCES:
        w = best_window(forecast, appliance_id, now_intensity)
        if w is not None:
            windows.append(w)
    return windows


def greenest_and_dirtiest(forecast: list[ForecastSlot]) -> tuple[Slot, Slot]:
    greenest = min(forecast, key=lambda s: s.intensity_g_per_kwh)
    dirtiest = max(forecast, key=lambda s: s.intensity_g_per_kwh)
    return (
        Slot(from_at=greenest.from_at, intensity_g_per_kwh=greenest.intensity_g_per_kwh),
        Slot(from_at=dirtiest.from_at, intensity_g_per_kwh=dirtiest.intensity_g_per_kwh),
    )
