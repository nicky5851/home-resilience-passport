"""Read and check A's reference CSVs against CONTRACT.md §5.

`load_reference()` returns typed rows plus every problem found, each with the file, the
spreadsheet row (header = row 1) and the column, so A can fix the sheet directly.
Used by `make validate-data` (scripts/validate_data.py) and `make seed` (app/db/seed.py).
"""

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

from app.config import REPO_ROOT
from app.schemas import normalise_postcode
from app.schemas.base import (
    HazardName,
    IncomeBand,
    MeasureCategory,
    Priority,
    PropertyType,
    Tenure,
)
from app.schemas.demo import DemoSlug

REFERENCE_DIR = REPO_ROOT / "data" / "reference"
PLACEHOLDER_HOSTS = ("example.com", "example.org")

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
INT = re.compile(r"^-?[0-9]+$")
FLOAT = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
URL = re.compile(r"^https?://[^\s/$.?#][^\s]*$")


@dataclass
class Problem:
    file: str
    row: int
    column: str | None
    message: str
    warning: bool = False

    def __str__(self) -> str:
        where = f"{self.file} row {self.row}" + (f", column {self.column}" if self.column else "")
        return f"{'warning' if self.warning else 'error'}: {where}: {self.message}"


class CellError(ValueError):
    pass


# --- Cell parsers: raw text -> typed value, or CellError with a plain-English reason ---------

Parser = Callable[[str], Any]


def text(max_len: int | None = None, required: bool = True) -> Parser:
    def parse(v: str) -> str:
        if required and not v:
            raise CellError("is empty but is required")
        if max_len and len(v) > max_len:
            raise CellError(f"is {len(v)} characters; the limit is {max_len}")
        return v

    return parse


def kebab_id(v: str) -> str:
    if not KEBAB.match(v):
        raise CellError(f"'{v}' must be lowercase kebab-case, e.g. flood-door")
    return v


def enum(values: tuple[str, ...]) -> Parser:
    def parse(v: str) -> str:
        if v not in values:
            raise CellError(f"'{v}' is not one of: {', '.join(values)}")
        return v

    return parse


def str_list(values: tuple[str, ...]) -> Parser:
    def parse(v: str) -> list[str]:
        if not v:
            return []
        items = v.split(";")
        for item in items:
            if item != item.strip() or not item:
                raise CellError(f"'{v}' must be separated by ';' with no spaces")
            if item not in values:
                raise CellError(f"'{item}' is not one of: {', '.join(values)}")
        return items

    return parse


def integer(lo: int | None = None, hi: int | None = None, empty_ok: bool = False) -> Parser:
    def parse(v: str) -> int | None:
        if not v:
            if empty_ok:
                return None
            raise CellError("is empty but is required")
        if not INT.match(v):
            raise CellError(f"'{v}' must be a whole number with no £, commas or units")
        n = int(v)
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            raise CellError(f"{n} is outside the allowed range {lo}–{hi}")
        return n

    return parse


def decimal(empty_ok: bool = True) -> Parser:
    def parse(v: str) -> float | None:
        if not v and empty_ok:
            return None
        if not FLOAT.match(v):
            raise CellError(f"'{v}' must be a number with no %, commas or units")
        return float(v)

    return parse


def boolean(empty_ok: bool = False) -> Parser:
    def parse(v: str) -> bool | None:
        if not v and empty_ok:
            return None
        if v not in ("true", "false"):
            allowed = "true, false or empty" if empty_ok else "true or false"
            raise CellError(f"'{v}' must be {allowed}")
        return v == "true"

    return parse


def url(v: str) -> str:
    if v and not URL.match(v):
        raise CellError(f"'{v}' is not a web address starting with http:// or https://")
    return v


def postcode(v: str) -> str:
    try:
        return normalise_postcode(v)
    except ValueError as e:
        raise CellError(f"'{v}' is not a full UK postcode") from e


# --- The three files (CONTRACT §5) --------------------------------------------------------

SUBSIDENCE = ("clay_reported", "cracks_reported", "none_reported", "unknown")
HAZARD_SHOWN = ("river_sea_flood", "overheating", "storm", "subsidence", "low_risk")
FUNDING_KINDS = ("grant", "loan", "mortgage_further_advance", "insurance_discount", "cashback")
LOAN_KINDS = ("loan", "mortgage_further_advance")

COLUMNS: dict[str, dict[str, Parser]] = {
    "demo_homes.csv": {
        "slug": enum(get_args(DemoSlug)),
        "postcode": postcode,
        "house_number": text(),
        "hazard_shown": enum(HAZARD_SHOWN),
        "tenure": enum(get_args(Tenure)),
        "income_band": enum(get_args(IncomeBand)),
        "budget_gbp": integer(0, 100_000),
        "priorities": str_list(get_args(Priority)),
        "vulnerable": boolean(empty_ok=True),
        "subsidence_signal": enum(SUBSIDENCE),
        "notes": text(required=False),
    },
    "measures.csv": {
        "id": kebab_id,
        "name": text(40),
        "category": enum(get_args(MeasureCategory)),
        "hazards_reduced": str_list(get_args(HazardName)),
        "cost_low_gbp": integer(0),
        "cost_high_gbp": integer(0),
        "annual_bill_saving_gbp": integer(0),
        "co2_saved_kg_per_year": integer(0),
        "resilience_points": integer(0, 15),
        "property_types": str_list(get_args(PropertyType)),
        "renter_ok": boolean(),
        "needs_landlord": boolean(),
        "source_url": url,
    },
    "funding.csv": {
        "id": kebab_id,
        "name": text(50),
        "provider": text(),
        "kind": enum(FUNDING_KINDS),
        "max_amount_gbp": integer(0, empty_ok=True),
        "apr_percent": decimal(),
        "income_bands": str_list(get_args(IncomeBand)),
        "tenures": str_list(get_args(Tenure)),
        "categories": str_list(get_args(MeasureCategory)),
        "is_mock": boolean(),
        "source_url": url,
    },
}


@dataclass
class Reference:
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    problems: list[Problem] = field(default_factory=list)

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if not p.warning]


def _read_file(path: Path, ref: Reference) -> list[tuple[int, dict[str, Any]]]:
    name, spec = path.name, COLUMNS[path.name]
    if not path.exists():
        ref.problems.append(Problem(name, 0, None, "file is missing"))
        return []
    try:
        content = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        ref.problems.append(Problem(name, 0, None, "file is not UTF-8; export it again as CSV"))
        return []

    reader = csv.reader(io.StringIO(content))
    header = next(reader, [])
    expected = list(spec)
    if header != expected:
        diffs = [
            f"column {i + 1} is '{got}' but should be '{want}'"
            for i, (got, want) in enumerate(zip(header, expected, strict=False))
            if got != want
        ]
        if len(header) != len(expected):
            diffs.append(f"found {len(header)} columns, expected {len(expected)}")
        msg = "header must be exactly: " + ",".join(expected) + " (" + "; ".join(diffs) + ")"
        ref.problems.append(Problem(name, 1, None, msg))
        return []

    rows: list[tuple[int, dict[str, Any]]] = []
    for line_no, cells in enumerate(reader, start=2):
        if not any(c.strip() for c in cells):
            continue
        if len(cells) != len(expected):
            msg = f"has {len(cells)} cells, expected {len(expected)} (check for stray commas)"
            ref.problems.append(Problem(name, line_no, None, msg))
            continue
        row: dict[str, Any] = {}
        ok = True
        for col, raw in zip(expected, cells, strict=True):
            try:
                row[col] = spec[col](raw)
            except CellError as e:
                ref.problems.append(Problem(name, line_no, col, str(e)))
                ok = False
        if ok:
            rows.append((line_no, row))
    return rows


def _check_unique(name: str, rows: list[tuple[int, dict]], col: str, ref: Reference) -> None:
    seen: dict[Any, int] = {}
    for line_no, row in rows:
        if row[col] in seen:
            msg = f"'{row[col]}' is already used on row {seen[row[col]]}"
            ref.problems.append(Problem(name, line_no, col, msg))
        seen.setdefault(row[col], line_no)


def _check_source_url(name: str, line_no: int, row: dict, ref: Reference) -> None:
    if not row["source_url"] and not row.get("is_mock", False):
        msg = "is required" + (" unless is_mock is true" if "is_mock" in row else "")
        ref.problems.append(Problem(name, line_no, "source_url", msg))
    elif any(host in row["source_url"] for host in PLACEHOLDER_HOSTS):
        msg = "is a placeholder address; replace it with the real source"
        ref.problems.append(Problem(name, line_no, "source_url", msg, warning=True))


def load_reference(directory: Path = REFERENCE_DIR) -> Reference:
    ref = Reference()

    demo = _read_file(directory / "demo_homes.csv", ref)
    _check_unique("demo_homes.csv", demo, "slug", ref)
    for line_no, row in demo:
        if len(row["priorities"]) > 3:
            ref.problems.append(
                Problem("demo_homes.csv", line_no, "priorities", "choose at most 3 priorities")
            )
    if demo:
        slugs = {row["slug"] for _, row in demo}
        missing = sorted(set(get_args(DemoSlug)) - slugs)
        if missing:
            msg = f"missing demo home(s): {', '.join(missing)}"
            ref.problems.append(Problem("demo_homes.csv", 0, "slug", msg))
        rows = [row for _, row in demo]
        for ok, what in (
            (any(r["tenure"] in ("private_renter", "social_renter") for r in rows), "a renter"),
            (any(r["income_band"] == "under_20k" for r in rows), "an under_20k household"),
            (any(r["vulnerable"] is True for r in rows), "a vulnerable household"),
        ):
            if not ok:
                msg = f"coverage rule: the five homes need at least {what}"
                ref.problems.append(Problem("demo_homes.csv", 0, None, msg))

    measures = _read_file(directory / "measures.csv", ref)
    _check_unique("measures.csv", measures, "id", ref)
    for line_no, row in measures:
        if row["cost_low_gbp"] > row["cost_high_gbp"]:
            msg = "cost_low_gbp must not be more than cost_high_gbp"
            ref.problems.append(Problem("measures.csv", line_no, "cost_low_gbp", msg))
        _check_source_url("measures.csv", line_no, row, ref)

    funding = _read_file(directory / "funding.csv", ref)
    _check_unique("funding.csv", funding, "id", ref)
    for line_no, row in funding:
        if row["apr_percent"] is not None and row["kind"] not in LOAN_KINDS:
            msg = "apr_percent is only for loans; leave it empty"
            ref.problems.append(Problem("funding.csv", line_no, "apr_percent", msg))
        if "lloyds" in row["provider"].lower() and not row["is_mock"]:
            msg = "Lloyds-branded rows must have is_mock = true"
            ref.problems.append(Problem("funding.csv", line_no, "is_mock", msg))
        _check_source_url("funding.csv", line_no, row, ref)

    ref.rows = {
        "demo_homes.csv": [r for _, r in demo],
        "measures.csv": [r for _, r in measures],
        "funding.csv": [r for _, r in funding],
    }
    return ref
