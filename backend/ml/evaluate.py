"""Model metrics (spec step N12): accuracy, within-one-band accuracy, macro F1, CO2 MAE, the
same per property type and region (fairness check), and a confusion matrix image."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error

from ml.features import BANDS

MIN_GROUP_SIZE = 200  # groups smaller than this are not reported (too noisy)


def within_one_band(y_true, y_pred) -> float:  # type: ignore[no-untyped-def]
    idx = {b: i for i, b in enumerate(BANDS)}
    t = np.array([idx[b] for b in y_true])
    p = np.array([idx[b] for b in y_pred])
    return float(np.mean(np.abs(t - p) <= 1))


def band_metrics(y_true, y_pred) -> dict[str, float]:  # type: ignore[no-untyped-def]
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "within_one_band": round(within_one_band(y_true, y_pred), 3),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", labels=list(BANDS))), 3),
    }


def evaluate(test: pd.DataFrame, band_pred, co2_pred) -> dict:  # type: ignore[no-untyped-def]
    test = test.assign(band_pred=list(band_pred), co2_pred=list(co2_pred))
    metrics: dict = {
        **band_metrics(test["band"], test["band_pred"]),
        "co2_mae_tonnes": round(float(mean_absolute_error(test["co2"], test["co2_pred"])), 2),
        "test_homes": len(test),
    }
    for col in ("property_type", "region"):
        groups = {}
        for value, g in test.groupby(col, observed=True):
            if len(g) >= MIN_GROUP_SIZE:
                groups[str(value)] = {**band_metrics(g["band"], g["band_pred"]), "homes": len(g)}
        metrics[f"by_{col}"] = groups
    return metrics


def confusion_png(y_true, y_pred, path: Path) -> None:  # type: ignore[no-untyped-def]
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = confusion_matrix(y_true, y_pred, labels=list(BANDS), normalize="true")
    fig, ax = plt.subplots(figsize=(5.5, 4.8), dpi=120)
    im = ax.imshow(m, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(BANDS)), BANDS)
    ax.set_yticks(range(len(BANDS)), BANDS)
    ax.set_xlabel("Predicted band")
    ax.set_ylabel("Actual band")
    ax.set_title("EPC band: share of each actual band")
    for i in range(len(BANDS)):
        for j in range(len(BANDS)):
            if m[i, j] >= 0.01:
                colour = "white" if m[i, j] > 0.5 else "black"
                ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", color=colour, fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
