"""N12: EPC model data, features, training and the committed artefact (offline)."""

import csv
import io
import json
import random
import time
import zipfile

import httpx
import joblib
import pandas as pd
import pytest

from app.schemas import PropertyFacts
from ml import download, prepare, train
from ml.features import BANDS, FEATURES, from_bulk, from_facts, simplify_heating

BULK_ROW = {
    "certificate_number": "0000-0000-0000-0000-0001", "uprn": "34092565", "postcode": "SW6 3ST",
    "region": "E12000007", "lodgement_date": "2024-07-21", "property_type": "Flat",
    "built_form": "End-Terrace", "construction_age_band": "England and Wales: before 1900",
    "total_floor_area": "84", "mainheat_description": "Boiler and radiators, mains gas",
    "main_fuel": "mains gas (not community)", "current_energy_rating": "C",
    "co2_emissions_current": "2.2",
}  # fmt: skip


# --- Features ---------------------------------------------------------------------------------


def test_features_from_a_bulk_row() -> None:
    assert from_bulk(BULK_ROW) == {
        "property_type": "flat",
        "built_form": "End-Terrace",
        "age_band": "before 1900",
        "region": "London",
        "heating": "boiler",
        "fuel": "mains gas",
        "floor_area_m2": 84.0,
    }


def test_features_from_property_facts_match_training() -> None:
    """The app's PropertyFacts (EPC adapter or user) give the same values as the bulk data."""
    facts = PropertyFacts(
        property_type="flat", built_form="End-Terrace", construction_age_band="before 1900",
        floor_area_m2=84, main_heating="Boiler and radiators, mains gas", main_fuel="mains gas",
        source="epc_api",
    )  # fmt: skip
    assert from_facts(facts, "London") == from_bulk(BULK_ROW)


@pytest.mark.parametrize(
    ("description", "heating"),
    [
        ("Air source heat pump, radiators, electric", "heat pump"),
        ("Electric storage heaters", "storage heaters"),
        ("Community scheme", "community"),
        ("Room heaters, electric", "room heaters"),
        ("Boiler and underfloor heating, oil", "boiler"),
        ("Something new", "other"),
        (None, None),
    ],
)
def test_simplify_heating(description, heating) -> None:
    assert simplify_heating(description) == heating


@pytest.mark.parametrize(
    ("value", "expected"), [("NO DATA!", None), ("", None), ("  Detached ", "Detached")]
)
def test_not_recorded_values_are_missing(value, expected) -> None:
    assert from_bulk(BULK_ROW | {"built_form": value})["built_form"] == expected


# --- Download ---------------------------------------------------------------------------------


def test_keep_filters_regions_and_columns() -> None:
    rows = [BULK_ROW | {"extra": "x"}, BULK_ROW | {"region": "E12000001"}]
    kept = list(download.keep(rows))
    assert kept == [[BULK_ROW[c] for c in download.COLUMNS]]


def test_range_reader_renews_expired_links(mock_http) -> None:
    """Signed S3 links last 30 s: a 403 asks the API for a new one and carries on."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("certificates-2024.csv", "a,b\n1,2\n" * 1000)
    data = buf.getvalue()

    def serve(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("sig") == "old" and request.headers["range"] != "bytes=0-0":
            return httpx.Response(403)
        start, end = map(int, request.headers["range"].removeprefix("bytes=").split("-"))
        chunk = data[start : end + 1]
        rng = f"bytes {start}-{start + len(chunk) - 1}/{len(data)}"
        return httpx.Response(206, content=chunk, headers={"content-range": rng})

    mock_http.get(url__startswith="https://s3.example/").mock(side_effect=serve)
    links = iter(["https://s3.example/f.zip?sig=old", "https://s3.example/f.zip?sig=new"])
    with httpx.Client() as client:
        remote = download.RangeFile(lambda: next(links), client)
        with zipfile.ZipFile(io.BufferedReader(remote, 64)) as z:
            assert z.read("certificates-2024.csv").count(b"1,2") == 1000


# --- Prepare ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("postcode", "area"), [("YO1 9TJ", "YO"), ("e1 8ng", "E"), ("B90 1QL", "B")]
)
def test_postcode_area(postcode, area) -> None:
    assert prepare.postcode_area(postcode) == area


def _raw(rows: list[dict]) -> pd.DataFrame:
    path = io.StringIO()
    w = csv.DictWriter(path, download.COLUMNS)
    w.writeheader()
    w.writerows(rows)
    records = []
    for row in csv.DictReader(io.StringIO(path.getvalue())):
        rec = from_bulk(row) | {
            "band": row["current_energy_rating"], "co2": row["co2_emissions_current"],
            "uprn": row["uprn"], "lodged": row["lodgement_date"],
            "area": prepare.postcode_area(row["postcode"]),
        }  # fmt: skip
        records.append(rec)
    return pd.DataFrame.from_records(records)


def test_clean_keeps_the_latest_certificate_and_drops_bad_targets() -> None:
    rows = [
        BULK_ROW | {"uprn": "1", "lodgement_date": "2024-01-01", "current_energy_rating": "D"},
        BULK_ROW | {"uprn": "1", "lodgement_date": "2024-06-01", "current_energy_rating": "C"},
        BULK_ROW | {"uprn": "2", "current_energy_rating": "INVALID!"},
        BULK_ROW | {"uprn": "3", "co2_emissions_current": ""},
        BULK_ROW | {"uprn": "4", "co2_emissions_current": "900"},
        BULK_ROW | {"uprn": "5", "total_floor_area": "5"},  # typing error → unknown area
        BULK_ROW | {"uprn": ""},  # no UPRN: kept
    ]
    df, _ = prepare.clean(_raw(rows))
    assert sorted(df["uprn"]) == ["", "1", "5"]
    assert df.loc[df["uprn"] == "1", "band"].item() == "C"
    assert pd.isna(df.loc[df["uprn"] == "5", "floor_area_m2"].item())


def test_rare_categories_become_other() -> None:
    rows = [BULK_ROW | {"uprn": str(i)} for i in range(999)]
    rows.append(BULK_ROW | {"uprn": "999", "mainheat_description": "Warm air, electric"})
    df, kept = prepare.clean(_raw(rows))
    assert kept["heating"] == ["boiler", "other"]  # warm air is 0.1% < 0.2%
    assert df.loc[df["uprn"] == "999", "heating"].item() == "other"
    x = prepare.as_model_input(df, kept)
    assert list(x.columns) == list(FEATURES)


# --- Training end to end (tiny synthetic data) ---------------------------------------------------


def test_train_runs_end_to_end(tmp_path, monkeypatch) -> None:
    rng = random.Random(1)
    ages = ["before 1900", "1950-1966", "1983-1990", "2007-2011", "2012 onwards"]
    areas = ["YO", "LS", "E", "N", "EX", "TR", "BS", "SE", "HU", "PL"]
    rows = []
    for i in range(3000):
        age = rng.randrange(len(ages))
        band = BANDS[min(6, max(0, 5 - age + rng.choice([-1, 0, 0, 1])))]
        rows.append(BULK_ROW | {
            "uprn": str(i), "postcode": f"{rng.choice(areas)}1 1AA",
            "construction_age_band": f"England and Wales: {ages[age]}",
            "region": rng.choice(["E12000003", "E12000007", "E12000009"]),
            "total_floor_area": str(rng.randint(30, 200)), "current_energy_rating": band,
            "co2_emissions_current": str(round(1 + (6 - age) * 0.8 + rng.random(), 1)),
        })  # fmt: skip
    raw = tmp_path / "epc_bulk.csv"
    with raw.open("w", newline="") as fh:
        w = csv.DictWriter(fh, download.COLUMNS)
        w.writeheader()
        w.writerows(rows)

    monkeypatch.setattr(prepare, "RAW", raw)
    monkeypatch.setattr(train, "read_raw", lambda: prepare.read_raw(raw))
    for name in ("MODEL_PATH", "METRICS_PATH", "CONFUSION_PATH"):
        monkeypatch.setattr(train, name, tmp_path / getattr(train, name).name)
    monkeypatch.setattr(train, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(train, "confusion_png", lambda *a: None)  # matplotlib is training-only

    assert train.main() == 0
    metrics = json.loads((tmp_path / "metrics.json").read_text())
    assert metrics["within_one_band"] > 0.8
    assert metrics["test_homes"] + metrics["train_homes"] == 3000
    assert joblib.load(tmp_path / "epc_model.joblib")["features"] == list(FEATURES)


# --- The committed artefact ---------------------------------------------------------------------


def test_committed_artifact_loads_and_predicts() -> None:
    artifact = joblib.load(train.MODEL_PATH)
    assert artifact["version"].startswith("epc-")
    assert artifact["metrics"]["within_one_band"] >= 0.8  # spec N12 target
    facts = PropertyFacts(
        property_type="terraced", built_form="Mid-Terrace", construction_age_band="1900-1929",
        floor_area_m2=85, main_heating="Boiler and radiators, mains gas", main_fuel="mains gas",
        source="user",
    )  # fmt: skip
    x = prepare.as_model_input(pd.DataFrame([from_facts(facts, "London")]), artifact["categories"])
    start = time.perf_counter()
    band = artifact["classifier"].predict(x)[0]
    co2 = float(artifact["regressor"].predict(x)[0])
    assert (time.perf_counter() - start) < 0.5
    assert band in BANDS and 0 < co2 < 50
