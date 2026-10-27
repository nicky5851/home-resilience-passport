"""Seam 1: the fixtures follow the data-format rules in CONTRACT.md §1–§2."""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas import (
    DATA_SOURCES,
    HAZARD_ORDER,
    Address,
    DemoHome,
    HazardInputs,
    HazardLevel,
    Household,
    Passport,
    PublicPassport,
    normalise_postcode,
)
from tests.conftest import DEMO_SLUGS, FIXTURES_DIR, load_fixture

PARTS: dict[str, type[BaseModel]] = {
    "inputs": HazardInputs,
    "passport": Passport,
}


def _walk(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def test_exactly_five_fixtures() -> None:
    assert sorted(p.stem for p in FIXTURES_DIR.glob("*.json")) == sorted(DEMO_SLUGS)


def test_fixture_validates(demo_fixture: dict) -> None:
    DemoHome.model_validate({k: demo_fixture[k] for k in DemoHome.model_fields})
    for key, model in PARTS.items():
        model.model_validate(demo_fixture[key])


def test_every_field_present(demo_fixture: dict) -> None:
    """Rule 2: re-serialising adds nothing, so no field was missing from the file."""
    demo = DemoHome.model_validate({k: demo_fixture[k] for k in DemoHome.model_fields})
    for key, value in demo.model_dump(mode="json").items():
        assert demo_fixture[key] == value, key
    for key, model in PARTS.items():
        assert (
            model.model_validate(demo_fixture[key]).model_dump(mode="json") == (demo_fixture[key])
        ), key


def test_snake_case_keys(demo_fixture: dict) -> None:
    for path, value in _walk(demo_fixture):
        if isinstance(value, dict):
            for k in value:
                if path.endswith(".detail"):
                    continue
                assert k == k.lower() and " " not in k and "-" not in k, f"{path}.{k}"


def test_inputs_property_matches_property(demo_fixture: dict) -> None:
    assert demo_fixture["inputs"]["property"] == demo_fixture["property"]


def test_levels_order_and_sources(demo_fixture: dict) -> None:
    levels = [HazardLevel.model_validate(lv) for lv in demo_fixture["risk"]["levels"]]
    assert tuple(lv.hazard for lv in levels) == HAZARD_ORDER
    assert all(lv.data_source in DATA_SOURCES for lv in levels)
    sw = levels[-1]
    assert (sw.today, sw.y2050, sw.why) == (
        "medium",
        "medium",
        "Surface-water data is coming in a later version",
    )


def test_timestamps_are_utc_z(demo_fixture: dict) -> None:
    assert demo_fixture["risk"]["generated_at"].endswith("Z")
    for ev in demo_fixture["passport"]["events"]:
        assert ev["at"].endswith("Z")


def test_funding_adds_up(demo_fixture: dict) -> None:
    f, p = demo_fixture["funding"], demo_fixture["plan"]
    assert f["covered_gbp"] + f["gap_gbp"] == p["total_cost_low_gbp"]


def test_coverage_rule() -> None:
    """CONTRACT §5: a renter, a low-income and a vulnerable household across the five."""
    hh = [Household.model_validate(load_fixture(s)["household"]) for s in DEMO_SLUGS]
    assert any(h.tenure in ("private_renter", "social_renter") for h in hh)
    assert any(h.income_band == "under_20k" for h in hh)
    assert any(h.vulnerable is True for h in hh)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sw1a1aa", "SW1A 1AA"),
        (" SW1A   1AA ", "SW1A 1AA"),
        ("e18ng", "E1 8NG"),
        ("YO1 9TJ", "YO1 9TJ"),
    ],
)
def test_postcode_normalised(raw: str, expected: str) -> None:
    assert normalise_postcode(raw) == expected


def test_bad_postcode_rejected() -> None:
    with pytest.raises(ValidationError):
        Address(line1="x", postcode="NOTAPOSTCODE", lat=0, lon=0, country="england")


def test_text_limits() -> None:
    with pytest.raises(ValidationError):
        HazardLevel(
            hazard="storm", today="low", y2050="low", why="x" * 141, data_source="Your answer"
        )


def test_household_rules() -> None:
    base = dict(tenure="owner_occupier", income_band="under_20k", budget_gbp=0)
    h = Household(**base)
    assert h.vulnerable is None and h.priorities == [] and h.consent_lloyds_data is False
    with pytest.raises(ValidationError):
        Household(**base | {"priorities": ["comfort", "lower_bills", "home_value", "lower_carbon"]})
    with pytest.raises(ValidationError):
        Household(**base | {"budget_gbp": 100_001})


def test_unknown_keys_rejected() -> None:
    with pytest.raises(ValidationError):
        Household(tenure="owner_occupier", income_band="under_20k", budget_gbp=0, typo=1)


def test_public_passport_has_no_household(demo_fixture: dict) -> None:
    assert "household" not in PublicPassport.model_fields
    assert "share_token" not in PublicPassport.model_fields
    full = Passport.model_validate(demo_fixture["passport"])
    public = PublicPassport.model_validate(full.model_dump(exclude={"household", "share_token"}))
    assert "household" not in public.model_dump()
