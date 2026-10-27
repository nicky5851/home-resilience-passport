# Model card: EPC band and CO2 estimator

Version `epc-20261027` · trained 27 Oct 2026 · owner N · code `backend/ml/` · artefact `backend/ml/artifacts/epc_model.joblib` (0.7 MB)

## What it does

For a home with no Energy Performance Certificate, it estimates:

- the **EPC band** (A–G), and
- **CO2 emissions** in tonnes per year,

from seven facts the app already has or asks for. The app labels the result "Estimated by our model" (`PropertyFacts.source = "model"`, step N13). It is used **only** when a home has no certificate. A real certificate always wins.

It is **not** an EPC. It cannot see insulation, glazing, boiler age or anything else an assessor checks. It estimates what homes *like this one* usually score.

## Data

- **Source:** the EPC register's domestic bulk download (Ministry of Housing, Communities and Local Government, via https://get-energy-performance-data.communities.gov.uk), Open Government Licence v3.0.
- **Subset:** certificates lodged in **2024** for homes in **London, Yorkshire and The Humber, and the South West**. These three regions hold the five demo homes and mix city flats, terraces and rural houses. `make epc-data` reads only that year from the register's 8 GB zip, using HTTP range requests, and keeps 13 columns: 553,640 certificates, 98 MB in `data/raw/` (git-ignored).
- **Cleaning** (`ml/prepare.py`):
  - Keep the latest certificate per UPRN.
  - Drop rows with no valid band or with CO2 outside 0–50 t/yr.
  - Treat a floor area outside 10–1000 m² as unknown.
  - Group categories held by fewer than 0.2% of homes as "other".
  - Result: **537,908 homes**.
- **Band mix:**

  | Band | A | B | C | D | E | F | G |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | Share | 1.1% | 15.4% | 44.0% | 31.1% | 6.6% | 1.3% | 0.5% |

- **Property mix:** flats 235k, terraced 128k, semi-detached 91k, detached 52k, bungalows 33k.

## Features

| Feature | From | Notes |
| --- | --- | --- |
| Property type | type + built form | detached, semi_detached, terraced, flat, bungalow, other (same rule as the EPC adapter) |
| Built form | certificate | e.g. "Mid-Terrace" |
| Age band | certificate | "England and Wales: " prefix removed |
| Floor area | certificate | m² |
| Region | ONS region code → postcodes.io name | only the three training regions are known; others count as unknown |
| Heating | main heating description | boiler, heat pump, storage heaters, community, room heaters, warm air, electric other, other |
| Fuel | description first, coded fuel second | mains gas, electricity, oil, LPG, wood, other (missing for 4.7%) |

Training and the app build these features with the same code (`ml/features.py`), so the model never sees a value it could not get in the app. Missing values are allowed: the model handles them natively.

## Model

- **Band:** scikit-learn `HistGradientBoostingClassifier`.
- **CO2:** `HistGradientBoostingRegressor`.
- **Settings:** native categorical features, learning rate 0.1, up to 300 rounds, early stopping with 30 rounds of patience, random seed 42.
- **Why 30 rounds of patience:** on a validation split of the training areas, it beat the default of 10 (accuracy 66.0% vs 65.3%) and 300 fixed rounds (64.1%, which overfits to the training areas).
- **Split:** 80/20 by **postcode area** (`GroupShuffleSplit`, seed 42), so every test home comes from one of 11 areas the model never saw. 448,829 homes train, 89,079 test.

## Results (test areas)

| Metric | Value |
| --- | --- |
| Band accuracy | **65.2%** |
| Within one band | **97.0%** (target ≥ 80%) |
| Macro F1 | 0.476 |
| CO2 mean absolute error | **0.65 t/yr** |

Confusion matrix: `backend/ml/artifacts/confusion_matrix.png`. All numbers are also in `metrics.json`.

The model is good at the common middle bands (B 76%, C 74%, D 59% correct) and pulls the rare ends towards the middle: most A homes are predicted B, and E–G homes are often predicted one band better. That is the main reason macro F1 is lower than accuracy.

## Fairness checks

Accuracy should not depend much on what kind of home someone lives in or where. On the test areas:

| Group | Accuracy | Within one band | Homes |
| --- | --- | --- | --- |
| Flat | 66.7% | 97.3% | 38,413 |
| Terraced | 65.7% | 98.1% | 21,715 |
| Semi-detached | 64.6% | 96.5% | 12,469 |
| Detached | 61.9% | 95.4% | 9,610 |
| Bungalow | 61.5% | 95.3% | 6,823 |
| London | 65.4% | 97.9% | 43,874 |
| Yorkshire and The Humber | 68.9% | 97.9% | 16,888 |
| South West | 62.9% | 95.2% | 28,317 |

Within-one-band accuracy stays between 95% and 98% for every group. Detached homes, bungalows and the South West are a few points worse. They are more varied (oil and LPG heating, older rural stock), and they are often the worst-rated homes, which the model tends to rate one band too well.

**How the app handles this:**

- An estimate never changes a price or rate (spec §7 Funding, fairness rule).
- The app always shows that the band is an estimate.
- Users can override any fact.

## Limits

- **Three regions only.** Homes elsewhere in England and Wales get an estimate with region "unknown". Expect them to be somewhat less accurate than the numbers above, which were not measured there.
- **2024 certificates only.** Certificates are lodged when homes are sold, let or improved, so the data over-represents rented flats and recently sold homes. It under-represents homes that never changed hands.
- **The target is itself a model.** An EPC band comes from RdSAP calculations by an assessor, not from metered energy use.
- **Rare bands (A, F, G) are often missed** by one band; see the results above.
- **No retraining schedule.** Re-run `make train` (with `make epc-data` for new years or regions) and update this card.

## Reproduce

```bash
make epc-data   # once: needs EPC_API_TOKEN in .env, about 45 s
make train      # about 20 s; writes backend/ml/artifacts/
```

`make train` downloads the extract first if `data/raw/epc_bulk.csv` is missing.
