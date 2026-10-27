"""Train the EPC band and CO2 models (spec step N12).

uv run --group ml python -m ml.train      # `make train`

Reads `data/raw/epc_bulk.csv` (`make epc-data`), cleans it (`ml.prepare`), splits 80/20 by
postcode area with a fixed seed so test homes come from areas the model never saw, trains a
HistGradientBoostingClassifier (band A–G) and a HistGradientBoostingRegressor (CO2 t/yr), then
writes `ml/artifacts/epc_model.joblib`, `metrics.json` and `confusion_matrix.png`.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit

from ml.download import REGIONS, YEARS
from ml.evaluate import confusion_png, evaluate
from ml.features import FEATURES
from ml.features import REGIONS as REGION_NAMES
from ml.prepare import as_model_input, clean, read_raw

ARTIFACTS = Path(__file__).with_name("artifacts")
MODEL_PATH = ARTIFACTS / "epc_model.joblib"
METRICS_PATH = ARTIFACTS / "metrics.json"
CONFUSION_PATH = ARTIFACTS / "confusion_matrix.png"
SEED = 42
TEST_SHARE = 0.2
# Early stopping with 30 rounds of patience beat 10 (the default) and 300 fixed rounds on a
# validation split of the training areas (docs/model_card.md).
PARAMS = {
    "max_iter": 300,
    "learning_rate": 0.1,
    "early_stopping": True,
    "n_iter_no_change": 30,
    "random_state": SEED,
}


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SHARE, random_state=SEED)
    train_idx, test_idx = next(gss.split(df, groups=df["area"]))
    return df.iloc[train_idx], df.iloc[test_idx]


def fit(train: pd.DataFrame, kept: dict[str, list[str]]):  # type: ignore[no-untyped-def]
    x = as_model_input(train, kept)
    clf = HistGradientBoostingClassifier(categorical_features="from_dtype", **PARAMS)
    reg = HistGradientBoostingRegressor(categorical_features="from_dtype", **PARAMS)
    return clf.fit(x, train["band"]), reg.fit(x, train["co2"])


def main() -> int:
    df, kept = clean(read_raw())
    train, test = split(df)
    print(f"{len(df):,} homes: {len(train):,} train, {len(test):,} test "
          f"({test['area'].nunique()} unseen postcode areas)", flush=True)  # fmt: skip
    clf, reg = fit(train, kept)
    x_test = as_model_input(test, kept)
    band_pred, co2_pred = clf.predict(x_test), reg.predict(x_test)
    metrics = evaluate(test, band_pred, co2_pred)
    metrics["train_homes"] = len(train)

    now = datetime.now(UTC)
    regions = ", ".join(REGION_NAMES[r] for r in REGIONS)
    ARTIFACTS.mkdir(exist_ok=True)
    artifact = {
        "version": f"epc-{now:%Y%m%d}",
        "trained_on": f"EPC register bulk data, {'/'.join(map(str, YEARS))} certificates, "
        f"{regions} ({len(df):,} homes)",
        "trained_at": now.isoformat(timespec="seconds"),
        "features": list(FEATURES),
        "categories": kept,
        "classifier": clf,
        "regressor": reg,
        "metrics": metrics,
    }
    joblib.dump(artifact, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    confusion_png(test["band"], band_pred, CONFUSION_PATH)
    size_mb = MODEL_PATH.stat().st_size / 1e6
    print(json.dumps({k: v for k, v in metrics.items() if not k.startswith("by_")}, indent=2))
    print(f"Wrote {MODEL_PATH.name} ({size_mb:.1f} MB), {METRICS_PATH.name}, {CONFUSION_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
