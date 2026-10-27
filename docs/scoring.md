# Scoring v1

L owns this file and `backend/app/scoring/`. The contract (field names, ranges, hazard order)
is fixed in `docs/CONTRACT.md`; everything below is the implementation of CODING_SPEC.md §6 and
may be tuned without a contract change (thresholds are first-version, reviewed with A at Merge 1).

Every threshold and weight is a named constant in `backend/app/scoring/config.py`. Nothing in this
document should disagree with that file; if it does, `config.py` is right and this file is stale.

## Risk engine (`app/scoring/risk.py`, step L4)

`assess_risk` is a pure function: given the same `HazardInputs` it always returns the same
`RiskProfile`. `today` is computed from the baseline inputs, `y2050` from the 2041–2050 inputs.
A missing (`null`) numeric input is scored `medium` and `why` says the data is unavailable
(CONTRACT.md §2 rule 52).

| Hazard | Low | Medium | High |
| --- | --- | --- | --- |
| River/sea flood | `rofrs_band` is `none` or `very_low` | `low` | `medium` or `high`; **+1 level** if `active_flood_warnings > 0` (capped at high) |
| Overheating | hot days < 5 | 5–15 | > 15; **+1 level** if `top_floor` is true or `epc_rating` is A/B (capped at high) |
| Storm | max sustained wind < 50 km/h | 50–65 | > 65 |
| Subsidence | `none_reported` | `unknown` | `clay_reported` or `cracks_reported` |
| Surface water | — fixed at `medium`/`medium` for M1 (no data source yet, CONTRACT.md §2) | | |

Notes:
- `rofrs_band` has no 2050 variant, so `today` and `y2050` are the same value for flood and
  subsidence (the EA band and the user's subsidence answer do not change with the climate
  projection).
- The flood warning bump and the heat bump each apply at most once; both cap at `high` rather
  than overflowing.
- `why` is a plain-English sentence (CONTRACT.md §1 rule 8, ≤140 characters), naming the data
  source where it exists ("The Environment Agency rates flood risk here as high.") or saying so
  plainly when a figure is missing ("Hot-day data for your postcode is unavailable, so this is
  scored as medium risk.").
- `RiskProfile.generated_at` is a fixed constant inside `risk.py`, not the system clock. A pure
  function cannot read "now" and stay deterministic (`test_functions_are_pure`,
  `test_assess_risk_contract`'s determinism check). The real timestamp is set by the assessment
  service (N9) when it stores the result — see `docs/decisions/L.md`.

## Resilience score (`app/scoring/score.py`, step L5)

Not yet implemented (still the L3 stub). Will follow CODING_SPEC.md §6:

- 100 points total: flood 30, heat 20, storm 10, subsidence 10 (resilience = 70%), carbon 30.
- Hazard points use the **2050** level: low = full marks, medium = half, high = 10%.
- Carbon points = `epc_score × 0.3`; if only `epc_rating` is known, use the band midpoint
  (A 96 … G 10); if both are unknown, 15 points flat.
- Measures (completed or candidate) add their `resilience_points` to the component named by
  their `category`, capped at that component's max.
- Bands: A ≥ 85, B 70–84, C 55–69, D 40–54, E 25–39, F 10–24, G < 10.

## Funding matcher (`app/scoring/funding.py`, step L6)

Not yet implemented (still the L3 stub). Will follow CODING_SPEC.md §7 Funding.
