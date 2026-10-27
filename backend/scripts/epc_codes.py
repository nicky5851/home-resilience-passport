"""Build `app/adapters/epc_codes.json` from the EPC register's code tables (step N6).

uv run python -m scripts.epc_codes [path/to/codes.csv]

Download the CSV first (no login needed) into data/raw/ (git-ignored):
    curl -L -o data/raw/epc_codes.csv \
        https://get-energy-performance-data.communities.gov.uk/download/codes

Certificates store some answers as numeric codes whose meaning depends on the certificate's
`schema_type` (for example `main_fuel` 10 is electricity in RdSAP-17 but dual fuel in SAP-17),
so the table is kept per schema. Northern Ireland schemas are dropped (CONTRACT §1 rule 9).
"""

import csv
import json
import sys
from pathlib import Path

from app.config import REPO_ROOT

DEFAULT_CSV = REPO_ROOT / "data" / "raw" / "epc_codes.csv"
OUT = Path(__file__).resolve().parents[1] / "app" / "adapters" / "epc_codes.json"
CODES = ("property_type", "built_form", "construction_age_band", "main_fuel")


def build(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    """{schema_type: {code: {key: value}}}"""
    out: dict[str, dict[str, dict[str, str]]] = {}
    for r in rows:
        schema, code = r["schema_version"], r["code"]
        if code not in CODES or "-NI-" in schema:
            continue
        out.setdefault(schema, {}).setdefault(code, {})[r["key"]] = r["value"].strip()
    return dict(sorted(out.items()))


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else DEFAULT_CSV
    with path.open(newline="", encoding="utf-8") as f:
        table = build(list(csv.DictReader(f)))
    OUT.write_text(json.dumps(table, indent=1, sort_keys=True) + "\n")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}: {len(table)} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
