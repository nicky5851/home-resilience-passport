"""Any supplier's consumption export -> one reading per day (docs/studio/N_20_function.md §S03
step 1). Deliberately permissive: sniffs the delimiter, strips a BOM, and finds columns by
name/shape rather than requiring an exact header."""

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime

from app.studio.features.s03_meter_fingerprint.config import M3_TO_KWH

_CONSUMPTION_NAME = re.compile(r"consumption|kwh|usage|value|reading", re.I)
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M")


class UnreadableFile(Exception):
    """Not UTF-8 text, or no column looks like a date + a number."""


@dataclass
class DailyReading:
    day: date
    kwh: float


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        return ","


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_number(value: str) -> float | None:
    value = value.strip().replace(",", "")
    try:
        return float(value)
    except ValueError:
        return None


def parse_consumption_csv(raw: bytes, unit: str) -> list[DailyReading]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise UnreadableFile("Not a text file") from e

    delimiter = _sniff_delimiter(text[:2000])
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if not rows:
        raise UnreadableFile("Empty file")

    header = rows[0]
    date_col = _find_date_column(rows)
    value_col = _find_value_column(header, rows, exclude=date_col)
    if date_col is None or value_col is None:
        raise UnreadableFile("No date and consumption columns found")

    data_rows = rows[1:] if _looks_like_header(header) else rows
    by_day: dict[date, float] = {}
    for row in data_rows:
        if len(row) <= max(date_col, value_col):
            continue
        day_val = _parse_date(row[date_col])
        num = _parse_number(row[value_col])
        if day_val is None or num is None:
            continue
        kwh = num * M3_TO_KWH if unit == "m3" else num
        by_day[day_val] = by_day.get(day_val, 0.0) + kwh

    if not by_day:
        raise UnreadableFile("No parsable rows")
    return [DailyReading(day=d, kwh=kwh) for d, kwh in sorted(by_day.items())]


def _looks_like_header(row: list[str]) -> bool:
    return any(_parse_date(cell) is None and _parse_number(cell) is None for cell in row)


def _find_date_column(rows: list[list[str]]) -> int | None:
    body = rows[1:] if _looks_like_header(rows[0]) else rows
    sample = body[: min(10, len(body))]
    if not sample:
        return None
    n_cols = max(len(r) for r in sample)
    for col in range(n_cols):
        hits = sum(1 for r in sample if len(r) > col and _parse_date(r[col]) is not None)
        if hits >= max(1, len(sample) // 2):
            return col
    return None


def _find_value_column(header: list[str], rows: list[list[str]], exclude: int | None) -> int | None:
    for i, name in enumerate(header):
        if i != exclude and _CONSUMPTION_NAME.search(name):
            return i
    body = rows[1:] if _looks_like_header(header) else rows
    sample = body[: min(10, len(body))]
    if not sample:
        return None
    n_cols = max(len(r) for r in sample)
    for col in range(n_cols):
        if col == exclude:
            continue
        hits = sum(1 for r in sample if len(r) > col and _parse_number(r[col]) is not None)
        if hits >= max(1, len(sample) // 2):
            return col
    return None
