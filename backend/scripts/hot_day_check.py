"""Hot-day threshold check (CONTRACT.md §2, spec N2).

Counts mean days/yr with daily max >= 30 °C and >= 28 °C in central London,
1991–2020, from Open-Meteo's climate API. If the 30 °C figure is below 1.0, the contract
threshold becomes 28 °C.

    uv run python -m scripts.hot_day_check
"""

import httpx

from app.config import CLIMATE_BASELINE_YEARS, CLIMATE_MODEL, EXTERNAL_TIMEOUT_S

URL = "https://climate-api.open-meteo.com/v1/climate"
LONDON = (51.51, -0.13)


def main() -> None:
    start, end = CLIMATE_BASELINE_YEARS
    res = httpx.get(
        URL,
        params={
            "latitude": LONDON[0],
            "longitude": LONDON[1],
            "start_date": f"{start}-01-01",
            "end_date": f"{end}-12-31",
            "models": CLIMATE_MODEL,
            "daily": "temperature_2m_max",
        },
        timeout=EXTERNAL_TIMEOUT_S * 3,  # one-off 30-year pull, not an app call
    )
    res.raise_for_status()
    temps = [t for t in res.json()["daily"]["temperature_2m_max"] if t is not None]
    years = end - start + 1
    at30 = sum(t >= 30 for t in temps) / years
    at28 = sum(t >= 28 for t in temps) / years
    print(f"Model {CLIMATE_MODEL}, London {LONDON}, {start}-{end}, {len(temps)} days")
    print(f"Mean hot days/yr at >=30 °C: {at30:.2f}")
    print(f"Mean hot days/yr at >=28 °C: {at28:.2f}")
    print("Result: keep 30 °C" if at30 >= 1.0 else "Result: switch the contract to 28 °C")


if __name__ == "__main__":
    main()
