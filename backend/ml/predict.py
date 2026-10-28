"""Serve the EPC model (spec step N13): band and CO2 for homes without a certificate.

The artefact from `make train` is loaded once (at start-up, `app.main`). If it is missing or
cannot be loaded the app keeps working without estimates: `estimate` returns None and
`/model/info` says the model is unavailable.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from ml.features import from_facts
from ml.prepare import as_model_input

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).with_name("artifacts") / "epc_model.joblib"
CO2_DECIMALS = 1  # certificates give CO2 to 0.1 t/yr


@dataclass(frozen=True)
class Estimate:
    band: str
    co2_tonnes_per_year: float


@lru_cache(maxsize=1)
def model() -> dict[str, Any] | None:
    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception:  # noqa: BLE001 — any load failure means "no estimates", never a crash
        log.exception("EPC model could not be loaded from %s; estimates are off", MODEL_PATH)
        return None
    # The API predicts one home at a time, which is 3x faster on one OpenMP thread (starting
    # threads cost 5–10 ms per call). Set once for the process: the API has no other OpenMP work.
    threadpool_limits(limits=1, user_api="openmp")
    log.info("EPC model %s loaded", artifact["version"])
    return artifact


def estimate(facts: Any, region: str | None) -> Estimate | None:
    """Band and CO2 for `PropertyFacts` in `region` (postcodes.io name); None without a model."""
    artifact = model()
    if artifact is None:
        return None
    x = as_model_input(pd.DataFrame([from_facts(facts, region)]), artifact["categories"])
    band = str(artifact["classifier"].predict(x)[0])
    co2 = max(0.0, round(float(artifact["regressor"].predict(x)[0]), CO2_DECIMALS))
    return Estimate(band=band, co2_tonnes_per_year=co2)


def info() -> dict[str, Any]:
    """Version, training data and flat metrics (`by_region.London.accuracy`) for `/model/info`."""
    artifact = model()
    if artifact is None:
        return {"version": "unavailable", "trained_on": "model file missing", "metrics": {}}
    metrics: dict[str, float] = {}
    for key, value in artifact["metrics"].items():
        if isinstance(value, dict):  # by_property_type / by_region → {group: {metric: value}}
            for group, values in value.items():
                for name, v in values.items():
                    metrics[f"{key}.{group}.{name}"] = float(v)
        else:
            metrics[key] = float(value)
    return {
        "version": artifact["version"],
        "trained_on": artifact["trained_on"],
        "metrics": metrics,
    }
