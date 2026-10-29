"""Indexing and uplift maths (docs/studio/N_20_function.md §S14 Algorithm), pure and tested."""

import statistics

from app.studio.features.s14_green_value_lens.config import EPC_BAND_ORDER


def indexed_price(price_gbp: int, index_at_sale: float, index_latest: float) -> int:
    if index_at_sale <= 0:
        return price_gbp
    return round(price_gbp * index_latest / index_at_sale)


def median_and_iqr(values: list[int]) -> tuple[int, int, int]:
    """(median, q1, q3), each rounded to the nearest £1,000."""
    ordered = sorted(values)
    median = statistics.median(ordered)
    q1 = statistics.median(ordered[: len(ordered) // 2]) if len(ordered) >= 2 else median
    upper_half = ordered[(len(ordered) + 1) // 2 :]
    q3 = statistics.median(upper_half) if upper_half else median

    def round_1000(v: float) -> int:
        return round(v / 1000) * 1000

    return round_1000(median), round_1000(q1), round_1000(q3)


def band_steps(current_band: str | None, target_band: str) -> int:
    if (
        current_band is None
        or current_band not in EPC_BAND_ORDER
        or target_band not in EPC_BAND_ORDER
    ):
        return 0
    steps = EPC_BAND_ORDER.index(current_band) - EPC_BAND_ORDER.index(target_band)
    return max(0, steps)


def uplift_gbp(
    current_band: str | None,
    target_band: str,
    indexed_median_gbp: int,
    premium_pct_low: float,
    premium_pct_high: float,
) -> tuple[int | None, int | None]:
    steps = band_steps(current_band, target_band)
    if steps == 0:
        return (0, 0) if current_band is not None else (None, None)
    low = round(indexed_median_gbp * (premium_pct_low / 100) * steps)
    high = round(indexed_median_gbp * (premium_pct_high / 100) * steps)
    return max(0, low), max(0, high)
