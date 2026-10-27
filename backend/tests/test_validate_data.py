"""N4: `make validate-data` checks every rule in CONTRACT.md §5 and says where the problem is."""

import shutil
from pathlib import Path

import pytest

from app.db.reference import REFERENCE_DIR, load_reference
from scripts.validate_data import main as validate_main

PLACEHOLDER = "https://example.com/placeholder-source"


@pytest.fixture
def ref_dir(tmp_path: Path) -> Path:
    for p in REFERENCE_DIR.glob("*.csv"):
        shutil.copy(p, tmp_path / p.name)
    return tmp_path


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def _errors(directory: Path) -> list[str]:
    return [str(p) for p in load_reference(directory).errors]


def test_committed_csvs_are_valid() -> None:
    assert _errors(REFERENCE_DIR) == []


def test_wrong_column_name_fails_with_clear_message(ref_dir: Path, capsys) -> None:
    _edit(ref_dir / "measures.csv", "id,name,category,", "id,name,categry,")
    assert validate_main([str(ref_dir)]) == 1
    out = capsys.readouterr().out
    assert "error: measures.csv row 1: header must be exactly:" in out
    assert "column 3 is 'categry' but should be 'category'" in out
    assert "FAILED" in out


@pytest.mark.parametrize(
    ("file", "old", "new", "expected"),
    [
        ("measures.csv", ",1500,3500,", ",£1500,3500,", "row 2, column cost_low_gbp"),
        ("measures.csv", ",1500,3500,", ",3600,3500,", "must not be more than cost_high_gbp"),
        ("measures.csv", "river_sea_flood;surface_water", "river_sea_flood; surface_water",
         "no spaces"),
        ("measures.csv", ",false,true,", ",no,true,", "column renter_ok"),
        ("measures.csv", "flood-door,", "Flood_Door,", "kebab-case"),
        ("measures.csv", "flood-plan-kit,", "flood-door,", "already used on row 2"),
        ("measures.csv", ",8,,false", ",16,,false", "column resilience_points"),
        ("measures.csv", f"{PLACEHOLDER}\nflood-plan-kit", "\nflood-plan-kit",
         "row 2, column source_url: is required"),
        ("funding.csv", "Lloyds (illustrative),cashback,500,,,owner_occupier,,true",
         "Lloyds (illustrative),cashback,500,,,owner_occupier,,false", "must have is_mock = true"),
        ("funding.csv", ",grant,7500,,", ",grant,7500,2.5,", "only for loans"),
        ("funding.csv", "under_20k,,carbon,false,https://www.gov.uk/energy-company-obligation",
         "under_20k,,carbon,false,", "is required unless is_mock is true"),
        ("demo_homes.csv", "YO1 9TJ", "NOT A POSTCODE", "column postcode"),
        ("demo_homes.csv", "private_renter", "owner_occupier", "need at least a renter"),
        ("demo_homes.csv", ",5000,", ",100001,", "column budget_gbp"),
        ("demo_homes.csv", "flood_safety;lower_bills,true", "flood_safety;lower_bills,yes",
         "column vulnerable"),
    ],
)  # fmt: skip
def test_rule_violations_are_reported(ref_dir, file, old, new, expected) -> None:
    _edit(ref_dir / file, old, new)
    errors = _errors(ref_dir)
    assert any(expected in e for e in errors), errors
    assert any(e.startswith(f"error: {file}") for e in errors)


def test_placeholder_url_is_only_a_warning() -> None:
    ref = load_reference(REFERENCE_DIR)
    assert all(p.warning for p in ref.problems if p.column == "source_url")
