"""Clean the EPC bulk extract into a training table (spec step N12).

One row per home (the latest certificate per UPRN), the seven features from `ml.features`,
the two targets (band A–G, CO2 tonnes/yr) and the postcode area used to split train and test.
Rows without a target are dropped; rare categories become "other".
"""

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from ml.download import OUT as RAW
from ml.features import BANDS, CATEGORICAL, OTHER, from_bulk

MIN_SHARE = 0.002  # categories rarer than 0.2% of homes are grouped as "other"
FLOOR_AREA_RANGE = (10.0, 1000.0)  # m²; outside is a typing error, treated as unknown
CO2_RANGE = (0.0, 50.0)  # tonnes/yr; outside is dropped


def postcode_area(postcode: str) -> str:
    """Postcode area ("YO" for YO1 9TJ): the split unit, so test homes come from unseen areas."""
    outward = postcode.strip().upper().split(" ")[0]
    return "".join(ch for ch in outward[:2] if ch.isalpha())


def read_raw(path: Path = RAW) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"{path} is missing: run `make epc-data` first.")
    records = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rec = from_bulk(row)
            rec["band"] = row["current_energy_rating"].strip().upper()
            rec["co2"] = row["co2_emissions_current"]
            rec["uprn"] = row["uprn"].strip()
            rec["lodged"] = row["lodgement_date"]
            rec["area"] = postcode_area(row["postcode"])
            records.append(rec)
    return pd.DataFrame.from_records(records)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """The training table and the categories kept per column (saved with the model)."""
    df = df.copy()
    df["co2"] = pd.to_numeric(df["co2"], errors="coerce")
    df = df[df["band"].isin(BANDS) & df["co2"].between(*CO2_RANGE) & (df["area"] != "")]
    # Latest certificate per home; rows without a UPRN are kept as they are.
    with_uprn = df[df["uprn"] != ""].sort_values("lodged").drop_duplicates("uprn", keep="last")
    df = pd.concat([with_uprn, df[df["uprn"] == ""]], ignore_index=True)

    area = pd.to_numeric(df["floor_area_m2"], errors="coerce")
    df["floor_area_m2"] = area.where(area.between(*FLOOR_AREA_RANGE), np.nan)

    kept: dict[str, list[str]] = {}
    for col in CATEGORICAL:
        shares = df[col].value_counts(normalize=True)
        keep = sorted(str(v) for v in shares[shares >= MIN_SHARE].index if v != OTHER)
        kept[col] = [*keep, OTHER]
        df[col] = df[col].where(df[col].isna() | df[col].isin(keep), OTHER)
    return df.reset_index(drop=True), kept


def as_model_input(df: pd.DataFrame, kept: dict[str, list[str]]) -> pd.DataFrame:
    """Feature columns with fixed categorical dtypes; unseen values become "other"."""
    from ml.features import FEATURES

    out = pd.DataFrame(index=df.index)
    for col in FEATURES:
        if col in kept:
            values = df[col].where(df[col].isna() | df[col].isin(kept[col]), OTHER)
            out[col] = pd.Categorical(values, categories=kept[col])
        else:
            out[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    return out
