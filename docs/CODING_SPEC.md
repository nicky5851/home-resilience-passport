# Home Resilience Passport — Coding Specification

Version 1.3 · 26 Oct 2026 · Owners: N and L · v1.3 = review fixes + Milestone 2 hosting and real user data (§14); full list in §15
Submission: **Sun 15 Nov 2026** (TCS Sustainathon UK&I, Lloyds Banking Group challenge)

This file is the single source of truth for the build. Claude Code reads it through `CLAUDE.md`.
How N's and L's code connect (the five seams) is fixed in **`docs/CONTRACT.md`**; read it with this file.
Every decision that could be made in advance is made here. If something is not covered, follow
**§13 Decision rules** and log the choice in `docs/DECISIONS.md`.

---

## 0. How to use this spec

1. Open Claude Code in the repo root. It loads `CLAUDE.md`, which points here.
2. Tell it: **"Do step N5"** (or L5, etc.). One step at a time.
3. Claude Code does the step, runs the step's **Check**, then **stops** and reports.
4. You (the human) read the diff, run the check yourself, and test it in the browser or terminal.
5. If it passes, say **"approved"**. Claude Code then commits with the step's commit message, appends to your decision log, pushes your branch and opens or updates your pull request (§8). Then say **"do step N6"**.
6. If it fails: tell Claude Code what is wrong. Do not move on until the check passes.

Rules that apply to every step:

- Only touch the paths you own (§3). Shared files change only as in §3.3.
- Every step ends green: tests pass, lint passes, app still starts.
- No secrets in git. Keys go in `.env` (git-ignored); add the variable name to `.env.example`.
- Each step lists its **Goal**, **Files**, **Do**, **Check**, and **Commit**.
- Any decision Claude Code makes that this spec does not cover goes into **your own decision log**: `docs/decisions/N.md` or `docs/decisions/L.md` (§13).

### Phases

| Phase | When | Steps | Result |
| --- | --- | --- | --- |
| **F – Foundation** | Mon 26 Oct, merged by 9 pm | N0–N4, L0–L3 (marked **[F]**) | All five seams built and checked by CI; tag `contract-v1` |
| **B1 – Build, part 1** | Tue 27 Oct → Tue 3 Nov | N5–N9, L4–L9 | Real data and scoring on screen; merge meeting Tue 3 Nov |
| **B2 – Build, part 2** | Wed 4 Nov → Tue 10 Nov | N10–N15, L10–L14 | Full journey, login, model, passport; merge meeting and code freeze Tue 10 Nov |
| **M2a – Go live** | From Mon 16 Nov, after submission | N16–N19, L15–L16 (§14) | Live link with real accounts, once the go-live checklist passes |

Foundation order on Monday (arrows = "must be merged first"):

```
N0 → N1 ─┬─→ N2 ─┬─→ N3 ─→ L2
         │       └─→ L3
         ├─→ L0 → L1 ─────→ L2
         └─→ N4
```

After the foundation, N and L build independently. The contract can only change through a `contract:` PR that both approve (CONTRACT.md, last section). Steps marked **⚑** are checked at the next merge meeting, so finish and merge them before it.

---

## 1. What we are building

A web app where a UK homeowner enters a postcode and a few household details and gets:

1. Their home's climate risks (river and sea flooding, overheating, storms, subsidence) **today and in 2050**, from real public data.
2. A **Resilience Score** (0–100, band A–G) that sits next to their EPC rating.
3. A ranked, costed **improvement plan** with plain-English AI explanations.
4. A **funding bundle**: grants they qualify for first, then (mock) Lloyds finance, plus an insurance-discount estimate.
5. A **Passport**: the home's saved record of score history and work done, shareable read-only with a buyer, lender or insurer.

Fairness is built in: a low score never raises the price, grants are shown first for low-income households, renters see measures they can do without the landlord.

### Milestones

| Milestone | Date | Scope |
| --- | --- | --- |
| **M1 – Submission build** | Code freeze **Tue 10 Nov**, video **Fri 13 Nov**, submit by **Sat 14 Nov** | Everything in steps N0–N15 and L0–L14, running locally with real data, login, 5 demo homes, recorded video |
| **M2a – Live and real users** | Steps N16–N19, L15–L16 (§14). Starts Mon 16 Nov, after submission (owner decision 27 Oct). The submission is video-only | Hosted on Vercel + Render + Neon Postgres + private file storage; real accounts with privacy notice, data export and account deletion; rate limits |
| **M2b – Full version** | After 15 Nov | Surface-water flood data, licensed subsidence data, installer marketplace, live alerts, landlord view (§12) |

---

## 2. Locked decisions

| Area | Decision |
| --- | --- |
| Repo | One GitHub monorepo: `backend/`, `frontend/`, `data/`, `docs/`, `infra/` |
| Front end | **Next.js 15 (App Router) + TypeScript (strict)**, Tailwind CSS, shadcn/ui components, Recharts for charts, React-Leaflet + OpenStreetMap tiles for the map |
| Back end | **Python 3.12 + FastAPI**, Pydantic v2, SQLAlchemy 2.0, Alembic migrations, httpx for outbound calls |
| Database | **PostgreSQL 16** via Docker Compose (`infra/docker-compose.yml`) |
| Auth (M1) | `fastapi-users` with email + password, JWT in an **httpOnly cookie**. The front end proxies `/api/*` to the back end through Next.js rewrites so the cookie is first-party |
| API contract | FastAPI's OpenAPI schema is the contract. Front-end types are **generated** with `openapi-typescript` into `frontend/src/lib/api/schema.d.ts`; requests use `openapi-fetch` |
| AI: explanations | Anthropic Python SDK, used lightly (one call per home and measure set, cached). Model from env `ANTHROPIC_MODEL` (default `claude-sonnet-5-5`). Timeout 8 s. Daily cap `LLM_DAILY_CALL_LIMIT` (default 300) after which the template is used. If `ANTHROPIC_API_KEY` is missing, fall back to template text, so the app always works. No personal data in prompts (CONTRACT.md §6) |
| AI: our own model | **N trains a model on the public EPC bulk dataset** that predicts a home's EPC band and CO2 per year from its features (type, built form, age band, floor area, region, heating, fuel). scikit-learn `HistGradientBoostingClassifier` / `Regressor`, saved with `joblib` to `backend/ml/artifacts/` (commit if under 25 MB, otherwise Git LFS). Used when a home has no EPC certificate. Documented in `docs/model_card.md` |
| Package managers | Backend: `uv` (`pyproject.toml`). Front end: `pnpm`. Runtimes: **Python 3.12, Node 22 LTS** (Node 20 reached end of life in April 2026) |
| Config | Every number lives in a config file, never inline: `backend/app/config.py` (N: timeouts, cache TTLs, limits, env settings via `pydantic-settings`) and `backend/app/scoring/config.py` (L: thresholds, weights, bands, funding term). Tests import the same constants |
| Quality | Backend: `ruff` (lint + format), `pytest`. Front end: `eslint`, `prettier`, `tsc --noEmit`, `vitest` for logic, Playwright smoke test (joint session) |
| CI | GitHub Actions on every PR: backend lint + tests, front-end lint + typecheck + build |
| Hosting | M1: local only, demo recorded as video. M2: Vercel (front end) + Render (API, Docker, Frankfurt) + Neon Postgres (London) + Cloudflare R2 for certificates (EU bucket). Details and the go-live checklist: §14 |
| Personal data | Treated as real from M2. Rules in CONTRACT.md §6; hosting, retention and privacy notice in §14 |
| Money and units | GBP as integers in pounds (`cost_low_gbp`). Carbon in kg CO2e per year. Dates ISO 8601 UTC |
| Naming | Python `snake_case`; TypeScript `camelCase` for variables, `PascalCase` for components; API JSON fields `snake_case` |
| Branches | `main` is protected. Work on `n/<step-id>-<slug>` or `l/<step-id>-<slug>`. Squash-merge PRs |
| Commits | Conventional: `feat(backend): …`, `feat(frontend): …`, `chore: …`, `fix: …`, `docs: …` |

---

## 3. Repo layout and ownership

```
hrp/
├── CLAUDE.md                     # shared · rules for Claude Code
├── README.md                     # N
├── Makefile                      # N · dev, test, lint, types, seed
├── .env.example                  # shared (add names only)
├── .github/workflows/ci.yml      # N
├── infra/docker-compose.yml      # N
├── docs/
│   ├── CODING_SPEC.md            # shared (joint sessions only)
│   ├── DECISIONS.md              # shared · team-level decisions (append-only)
│   ├── decisions/
│   │   ├── N.md                  # N · N's Claude Code decision log
│   │   └── L.md                  # L · L's Claude Code decision log
│   ├── model_card.md             # N · what the EPC model does, data, accuracy, limits
│   ├── privacy.md                # shared · privacy notice text (§14.5), rendered at /privacy
│   └── scoring.md                # L · how risk, score and funding are computed
├── data/
│   ├── reference/                # A provides, N commits/loads
│   │   ├── measures.csv
│   │   ├── funding.csv
│   │   └── demo_homes.csv
│   └── raw/                      # git-ignored downloads (RoFRS ZIP, EPC bulk CSVs)
├── backend/
│   ├── pyproject.toml            # N
│   ├── alembic/                  # N
│   ├── app/
│   │   ├── main.py               # N
│   │   ├── config.py             # N
│   │   ├── schemas/              # SHARED CONTRACT (§3.3)
│   │   ├── api/                  # N · routers
│   │   ├── db/                   # N · models, session, seed
│   │   ├── auth/                 # N
│   │   ├── adapters/             # N · postcodes, epc, flood, climate
│   │   ├── services/             # N · assessment, planner, passport, llm, storage (calls L's scoring and funding)
│   │   └── scoring/              # L · pure functions, no I/O: risk.py, score.py, funding.py, config.py
│   ├── scripts/                  # N · export_openapi.py, validate_data.py
│   ├── uploads/                  # git-ignored · M1 certificate files
│   ├── ml/                       # N · EPC model: prepare.py, train.py, predict.py, artifacts/
│   └── tests/
│       ├── fixtures/             # shared · demo_homes JSON fixtures
│       ├── scoring/              # L
│       └── (everything else)     # N
└── frontend/                     # L (all of it)
    ├── package.json
    ├── src/app/                  # pages (App Router)
    ├── src/components/
    ├── src/lib/api/              # generated types + client
    └── src/mocks/                # fixture-backed mock mode (fixtures copied in by `pnpm mocks:sync`, git-ignored)
```

### 3.1 N owns
`backend/` except `backend/app/scoring/` and `backend/tests/scoring/`; `backend/ml/`; `infra/`; `.github/`; `Makefile`; `README.md`; `docs/model_card.md`; `docs/decisions/N.md`; committing and loading `data/reference/` (A owns the content: N's Claude Code never edits a value in A's CSVs, it only reports problems).

### 3.2 L owns
`frontend/`; `backend/app/scoring/` (risk, score **and funding**); `backend/tests/scoring/`; `docs/scoring.md`; `docs/decisions/L.md`.

### 3.3 Shared files (change carefully)
`docs/CONTRACT.md`, `docs/openapi.json`, `backend/app/schemas/`, `backend/tests/fixtures/`, `docs/CODING_SPEC.md`, `docs/privacy.md`, `CLAUDE.md`, `.env.example`.

Exception for fixtures: the **input** parts of each demo fixture (`address`, `household`, `property`, `inputs`) are contract. The **output** parts (`risk`, `score`, `plan`, `funding`, `passport`) are examples for mock mode and tests; either coder may refresh them in their own PR (regenerated with `make fixtures`, N8 hand-off) as long as CI shows they still validate against the schemas. L's scoring tests keep their expected values in `backend/tests/scoring/expected/` (L owns), so L never needs a shared-file PR to change a threshold.

- Change these **only** in a joint session, or in a PR that the other coder approves.
- Every change gets a line in `docs/DECISIONS.md` (date, who, what, why).
- After any schema change, N runs `make types` and L pulls before continuing.

### 3.4 How N and L avoid conflicts
- N's code calls L's scoring through exactly three functions (§4.3). Until L delivers them, N uses the stub that ships in step L3.
- L's front end calls N's API through generated types. Until N's real endpoints exist, L runs in **mock mode** (`NEXT_PUBLIC_API_MOCK=1`) backed by `backend/tests/fixtures/`.
- Pull `main` into your branch at the start of every work session (`git pull origin main`).

---

## 4. Shared contract

### 4.1 Pydantic models (`backend/app/schemas/`)

Field lists below are the contract. Types are Pydantic v2. `Level = Literal["low","medium","high"]`.

**property.py**
- `Address`: `uprn: str | None`, `line1: str`, `postcode: str`, `lat: float`, `lon: float`, `local_authority: str | None`, `country: Literal["england","wales","scotland","northern_ireland"]`
- `PropertyFacts`: `property_type: Literal["detached","semi_detached","terraced","flat","bungalow","other"]`, `built_form: str | None`, `construction_age_band: str | None`, `floor_area_m2: float | None`, `floor_level: int | None` (0 = ground), `top_floor: bool | None`, `main_heating: str | None`, `main_fuel: str | None`, `epc_rating: Literal["A","B","C","D","E","F","G"] | None`, `epc_score: int | None`, `co2_tonnes_per_year: float | None`, `source: Literal["epc_api","model","user","demo"]`

**household.py**
- `Household`: `tenure: Literal["owner_occupier","landlord","private_renter","social_renter"]`, `income_band: Literal["under_20k","20k_40k","40k_60k","60k_100k","over_100k"]`, `budget_gbp: int` (0–100000), `priorities: list[Literal["lower_bills","comfort","flood_safety","lower_carbon","home_value"]]` (at most 3), `vulnerable: bool | None` (any of: over 75, disability, long-term illness, young children; `None` = prefer not to say; special category data, CONTRACT.md §6), `consent_lloyds_data: bool` (default `false`; stored only, nothing is ever sent to Lloyds in M1 or M2), `subsidence_signal: Literal["yes","no","unknown"]` (default `"unknown"`; optional question "Have you noticed new cracks in the walls, or been told the ground is clay?"; mapped to `HazardInputs.subsidence_signal` as in CONTRACT.md §2)

**hazards.py**
- `HazardInputs` (raw facts from adapters, produced by N):
  `rofrs_band: Literal["high","medium","low","very_low","none"] | None` (river/sea, from EA RoFRS postcode data),
  `active_flood_warnings: int`,
  `hot_days_baseline: float | None`, `hot_days_2050: float | None`,
  `heavy_rain_days_baseline: float | None`, `heavy_rain_days_2050: float | None`,
  `max_wind_baseline_kmh: float | None`, `max_wind_2050_kmh: float | None`
  (exact definitions, units and valid ranges: CONTRACT.md §2),
  `subsidence_signal: Literal["clay_reported","cracks_reported","none_reported","unknown"]` (M1: from user answer; M2: BGS data),
  `property: PropertyFacts`
- `HazardLevel`: `hazard: Literal["river_sea_flood","overheating","storm","subsidence","surface_water"]`, `today: Level`, `y2050: Level`, `why: str` (≤ 140 chars), `data_source: str`
- `RiskProfile`: `levels: list[HazardLevel]`, `generated_at: datetime`

**score.py**
- `ScoreComponent`: `name: Literal["flood","heat","storm","subsidence","carbon"]`, `points: float`, `max_points: float`, `reason: str`
- `ResilienceScore`: `value: int` (0–100), `band: Literal["A","B","C","D","E","F","G"]`, `components: list[ScoreComponent]`, `version: str` (e.g. `"v1"`)

**plan.py**
- `Measure` (row of `measures.csv`): `id: str`, `name: str`, `category: Literal["flood","heat","storm","subsidence","carbon"]`, `hazards_reduced: list[str]`, `cost_low_gbp: int`, `cost_high_gbp: int`, `annual_bill_saving_gbp: int`, `co2_saved_kg_per_year: int`, `resilience_points: int`, `property_types: list[str]` (empty = all), `renter_ok: bool`, `needs_landlord: bool`, `source_url: str`
- `PlanItem`: `measure: Measure`, `rank: int`, `score_uplift: int`, `payback_years: float | None`, `explanation: str`, `selected: bool`
- `Plan`: `items: list[PlanItem]`, `total_cost_low_gbp: int`, `total_cost_high_gbp: int`, `projected_score: ResilienceScore`, `explanation_source: Literal["llm","template"]`

**funding.py**
- `FundingOption` (row of `funding.csv`): `id`, `name`, `provider`, `kind: Literal["grant","loan","mortgage_further_advance","insurance_discount","cashback"]`, `max_amount_gbp: int | None`, `apr_percent: float | None`, `income_bands: list[str]` (empty = all), `tenures: list[str]` (empty = all), `categories: list[str]`, `is_mock: bool`, `source_url: str`
- `FundingLine`: `option: FundingOption`, `amount_gbp: int`, `note: str`
- `FundingBundle`: `lines: list[FundingLine]` (grants first), `covered_gbp: int`, `gap_gbp: int`, `monthly_cost_gbp: int | None`

**passport.py**
- `PassportEvent`: `id`, `kind: Literal["assessed","plan_saved","work_recorded","shared"]`, `at: datetime`, `score_after: int | None`, `detail: dict`
- `Passport`: `home_id`, `address: Address`, `property: PropertyFacts`, `household: Household`, `latest_risk: RiskProfile`, `latest_score: ResilienceScore`, `plan: Plan | None`, `events: list[PassportEvent]`, `share_token: str | None`
- `PublicPassport`: same as `Passport` without `household` and without `share_token` (used by `/public/passport/{token}`); `work_recorded` events show `has_certificate` but no `certificate_name`

**demo.py**
- `DemoHome`: `slug`, `hazard_shown`, `address: Address`, `household: Household`, `property: PropertyFacts`, `risk: RiskProfile`, `score: ResilienceScore`, `plan: Plan`, `funding: FundingBundle` (built from the fixtures by `make seed`; served by `GET /demo/homes`)

**user.py**
- `UserRead`: `id: UUID`, `email: str`, `is_active: bool`, `is_superuser: bool`, `is_verified: bool` (fastapi-users default)
- `UserCreate`: `email: str`, `password: str`, `accept_privacy: bool` (must be `true`)

### 4.2 API routes (all under `/api/v1`)

| Method | Path | Body → Response | Auth |
| --- | --- | --- | --- |
| GET | `/health` | → `{status:"ok"}` | no |
| POST | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`; GET `/users/me` | fastapi-users defaults, shapes in CONTRACT.md §4 | – |
| GET | `/users/me/export` | → JSON download of everything the user owns | yes |
| DELETE | `/users/me` | → `204`, deletes the account and all its data | yes |
| GET | `/lookup/postcode/{postcode}` | → `{postcode, lat, lon, local_authority, addresses: [{line1, uprn?, epc_rating?}]}` | no |
| POST | `/homes` | `{address: Address, household: Household, property_override?: PropertyFacts}` → `{home_id}` | yes |
| GET | `/homes` | → `[{home_id, line1, postcode, score?}]` | yes |
| DELETE | `/homes/{id}` | → `204`, deletes the home, its events, files and share link | yes |
| POST | `/homes/{id}/assess` | → `{risk: RiskProfile, score: ResilienceScore, inputs: HazardInputs}` | yes |
| GET | `/homes/{id}/risk` | → `{risk, score, inputs}` (latest) | yes |
| POST | `/homes/{id}/plan` | `{budget_gbp?, selected_ids?: list[str]}` → `Plan` | yes |
| POST | `/homes/{id}/funding` | `{selected_ids: list[str]}` → `FundingBundle` | yes |
| GET | `/homes/{id}/passport` | → `Passport` | yes |
| POST | `/homes/{id}/work` | multipart: `measure_id`, `completed_on`, optional `cost_gbp`, optional `certificate` file (rules: CONTRACT.md §6) → `PassportEvent` | yes |
| GET | `/homes/{id}/work/{event_id}/certificate` | → the file | yes (owner) |
| POST | `/homes/{id}/share` | → `{share_token, url}` (a new token replaces any old one) | yes |
| DELETE | `/homes/{id}/share` | → `204`, the old link stops working | yes |
| GET | `/public/passport/{share_token}` | → `PublicPassport` | no |
| GET | `/model/info` | → `{version, trained_on, metrics}` | no |
| GET | `/demo/homes` | → `list[DemoHome]` (works without external APIs) | no |

Errors, status codes, timing, auth and cookie rules: **CONTRACT.md §3–§4**.

### 4.3 Scoring interface (L implements, N calls)

```python
# backend/app/scoring/__init__.py
def assess_risk(inputs: HazardInputs) -> RiskProfile: ...
def compute_score(risk: RiskProfile, prop: PropertyFacts,
                  completed_measures: list[Measure] = []) -> ResilienceScore: ...
def match_funding(plan: Plan, household: Household,
                  options: list[FundingOption]) -> FundingBundle: ...
SCORING_VERSION = "v1"
```
All three are pure functions: no network, no database, deterministic. N's code loads the inputs (from the database) and passes them in. Every threshold and weight they use lives in `backend/app/scoring/config.py`.

### 4.4 Fixtures
`backend/tests/fixtures/demo_homes/<slug>.json` — one file per demo home, holding `address`, `household`, `property`, `inputs` (HazardInputs), and the expected `risk`, `score`, `plan`, `funding`, `passport`. Used by N's tests, L's scoring tests, and the front-end mock mode. Created in N2 with placeholder values; real-data values replace them after N8 (see N8 hand-off). Which parts are contract and which may be refreshed freely: §3.3. The front end cannot import files outside `frontend/`, so `pnpm mocks:sync` (runs before `pnpm dev` and `pnpm build`) copies them into `frontend/src/mocks/fixtures/` (git-ignored).

---

## 5. Real data sources

Each source has an adapter in `backend/app/adapters/` with: a typed function, a 10-second timeout, a DB cache table (TTL in brackets), and a fallback. **The app must keep working when any source is down.**

| Source | Used for | Access | Adapter | Fallback |
| --- | --- | --- | --- | --- |
| postcodes.io | Postcode → lat/lon, local authority | Free, no key | `postcodes.py` (30 days) | `422 validation` |
| EPC register (MHCLG "Get energy performance of buildings data", developer API) | Property type, age, floor area, heating, EPC rating, CO2 | Free; register for API access. **Step N6 starts by reading the current API guide** linked from get-energy-performance-data.communities.gov.uk (the old epc.opendatacommunities.org now redirects there) | `epc.py` (30 days) | User fills `PropertyFacts` manually |
| EA "Risk of Flooding from Rivers and Sea – Postcodes in Areas at Risk" | River/sea flood band per postcode | Open Government Licence, ZIP download (updated Jul 2026), loaded into Postgres table `flood_postcodes` | `flood.py` | `rofrs_band = None` → shown as "unknown" |
| EA real-time flood-monitoring API | Active warnings near the home | Free, no key | `flood.py` (15 min) | `active_flood_warnings = 0` |
| Open-Meteo Climate API (CMIP6 models, to 2050) | Hot days, heavy-rain days, wind, now vs 2050 | Free for non-commercial use, no key; must credit CMIP6 and Open-Meteo | `climate.py` (90 days, keyed by lat/lon rounded to 0.1°). Two requests in parallel (1991–2020 and 2041–2050) so each stays well under the 10 s timeout | Regional defaults table (`backend/app/adapters/climate_defaults.py`: one row per English region and Wales, filled from the first real calls in N8) |
| EPC bulk data (same service, bulk download) | Training data for N's EPC model | Free; sign in with GOV.UK One Login to download. Use a subset (for example 3 regions, about 500k certificates) | `backend/ml/prepare.py` | – (training only) |
| User answers | Subsidence signal (M1) | – | – | `unknown` |

Coverage: England and Wales (CONTRACT.md §1 rule 9). Wales has no RoFRS data, so its flood card shows "unknown".

Not in M1 (see §12): surface-water flooding (licence check needed), BGS GeoSure subsidence (paid licence), coastal erosion.

Attribution footer in the UI (L14): "Contains public sector information licensed under the Open Government Licence v3.0. Climate data: Open-Meteo, CMIP6."

---

## 6. Scoring v1 (L owns; may tune in `docs/scoring.md`, contract stays)

Risk levels (today uses baseline values, 2050 uses 2041–2050 values):

| Hazard | Low | Medium | High |
| --- | --- | --- | --- |
| River/sea flood | `none` or `very_low` | `low` | `medium` or `high`; +1 level if `active_flood_warnings > 0` (cap high) |
| Overheating | hot days < 5 | 5–15 | > 15; +1 level if top-floor flat or `epc_rating` is A/B with no shading noted (cap high) |
| Storm | max wind < 50 km/h | 50–65 | > 65 (sustained 10 m wind, not gusts; L and A recheck at Merge 1 on real values) |
| Subsidence | `none_reported` | `unknown` | `clay_reported` or `cracks_reported` |

Score (0–100): flood 30, heat 20, storm 10, subsidence 10 (resilience = 70%) plus carbon 30.
- Hazard points: low = full, medium = half, high = 10% of max. Use the **2050** level (forward-looking).
- Carbon points = `epc_score` (1–100) × 0.3. If `epc_score` is `null` but `epc_rating` is known (for example predicted by our model), use the band's midpoint: A 96, B 86, C 75, D 61, E 47, F 30, G 10. If both are unknown, 15 points.
- Completed (or candidate) measures add their `resilience_points` to the component named by the measure's `category` (a `carbon` measure adds to carbon), each component capped at its max. `hazards_reduced` does not move points.
- Bands: A ≥ 85, B 70–84, C 55–69, D 40–54, E 25–39, F 10–24, G < 10.

The thresholds are a first version; A reviews them against research at Merge 1 (Tue 3 Nov).

---

## 7. Planner rules (N owns) and funding rules (L owns)

**Planner**
1. Candidate measures: those whose `property_types` match (or empty), excluding `needs_landlord` for renters (show them in a separate "ask your landlord" group).
2. For each, compute `score_uplift` = `compute_score(...)` with the measure added minus the current score.
3. Rank by `score_uplift / cost_mid` descending, where `cost_mid = max(50, (cost_low_gbp + cost_high_gbp) / 2)` so free measures do not divide by zero; then by the household's priorities (+20% weight to matching categories). If `vulnerable` is `true`: heat and flood measures first. Ties: lower `cost_low_gbp` first, then `id`.
4. Default selection: highest-ranked measures that fit `budget_gbp` (using `cost_low_gbp`).
5. Explanations: one LLM call per plan (not per measure). Prompt includes the home's property facts, hazard levels, score components, and the top 8 measures, and **nothing personal** (CONTRACT.md §6 rule 2); asks for one sentence per measure, ≤ 30 words, plain English, no made-up numbers. Cache key = hash of (property facts, hazard levels, measure ids, `SCORING_VERSION`, model name); budget and selection are not in the key, so moving the budget slider never calls the LLM again. Timeout 8 s. On error, timeout, daily cap reached or missing key, use the template: "`{name}` reduces your `{hazard}` risk and adds about `{score_uplift}` points for £`{low}`–£`{high}`."

**Funding** (L implements as `match_funding`, step L6)
1. Filter `funding.csv` by income band, tenure, and selected measure categories.
2. Order: grants → cashback → insurance discount → loans/further advance.
3. Allocate grants up to cost; the remaining `gap_gbp` goes to the lowest-APR loan; compute `monthly_cost_gbp` over 5 years.
4. **Fairness rule:** never show a higher price or rate because of a worse score. Mock Lloyds rows are labelled "illustrative" in the UI.

---

## 8. Workflow

- **Start of every work session** (Claude Code does this first): `git checkout main && git pull origin main`, then create or update your branch (`git checkout -b n/N7-flood`, or `git rebase main` on an existing one).
- **After every approved step** (Claude Code does this when you say "approved"): commit with the step's commit message, append any new entries to your decision log, `git push -u origin <branch>`, and open or update the pull request with `gh pr create` / `gh pr edit`. The PR description lists the steps it contains and links the decision-log entries.
- **Merge to `main` at least once a day** you code, and always by **9 pm the evening before a sync meeting**. Merge only when CI is green. The other coder gives a quick review within 24 h; if they have not, merge anyway when CI is green and mention it at the next meeting.
- One PR can hold several steps from the same day. Title = step ids + goal.
- Never commit to `main` directly. Never force-push `main`.
- `make dev` runs everything: Postgres (Docker), API on :8000, front end on :3000.
- `make test`, `make lint`, `make openapi` (writes `docs/openapi.json` from the app), `make types` (regenerates front-end types from `docs/openapi.json`), `make seed` (loads reference CSVs and demo homes), `make fixtures` (after N8: rebuilds the output parts of the demo fixtures from the real pipeline), `make validate-data`.

---

## 9. N's steps (back end, data, AI, integration)

Targets: **N0–N4 merged Mon 26 Oct 9 pm (Foundation)**, **N5–N9 by Tue 3 Nov (Merge 1)**, **N10–N15 by Tue 10 Nov (Merge 2, freeze)**.

### [F] N0 · Setup
- **Goal:** Tools and accounts ready.
- **Do:** Install Git, Docker Desktop, Python 3.12, `uv`, Node 22 LTS, `pnpm`, Claude Code. Create the GitHub repo `hrp` (private), add L and A as collaborators. Branch protection on a **private** repo needs GitHub Pro: claim it free with the GitHub Student Developer Pack (education.github.com) before N1, or N1 cannot protect `main`. Register for EPC API access. Create an Anthropic API key (optional for now).
- **Check:** `docker --version`, `uv --version`, `node -v` (v22.x), `pnpm -v` all print versions. L and A have accepted the repo invite. Settings → Branches shows rule options (Pro active).
- **Commit:** none.

### [F] N1 · Monorepo scaffold
- **Goal:** Anyone can clone and run the skeleton with one command.
- **Files:** `README.md`, `Makefile`, `.env.example`, `.gitignore`, `infra/docker-compose.yml`, `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/config.py`, `backend/tests/test_health.py`, `.github/workflows/ci.yml`, `docs/DECISIONS.md`, copy this spec to `docs/CODING_SPEC.md` and `CLAUDE.md` to the root.
- **Do:** FastAPI app with `/api/v1/health`; settings via `pydantic-settings` in `backend/app/config.py` (every timeout, TTL and limit from this spec as a named constant); Postgres 16 container; CI running ruff + pytest for backend with a `postgres:16` service container (front-end job added by L1). `.gitignore` covers `.env`, `data/raw/`, `backend/uploads/`, `frontend/src/mocks/fixtures/`. Turn on branch protection for `main` (PR + green CI).
- **Check:** `make dev` starts Postgres and API; `curl localhost:8000/api/v1/health` → `{"status":"ok"}`; `make test` passes; CI green on the PR.
- **Commit:** `chore: scaffold monorepo, backend health check, CI`

### [F] N2 · Shared contract
- **Goal:** All Pydantic models from §4.1 exist, plus 5 demo-home fixtures.
- **Files:** `backend/app/schemas/*.py`, `backend/tests/fixtures/demo_homes/*.json`, `backend/tests/test_schemas.py`, `backend/tests/test_contract_ranges.py`.
- **Do:** Write the models exactly as §4.1 and CONTRACT.md §1–§2 (every field present, `null` for unknown, lists default `[]`). Write 5 fixture files using the slugs in CONTRACT.md §5, with realistic placeholder values inside the §2 valid ranges. `test_contract_ranges.py` asserts every fixture's `HazardInputs` is in range. Then run the **hot-day threshold check** in CONTRACT.md §2 (one `curl` to Open-Meteo for London, counted with a short script in `backend/scripts/`) and report the number; the human edits CONTRACT.md if it says to.
- **Check:** `pytest backend/tests/test_schemas.py backend/tests/test_contract_ranges.py` passes; CI green.
- **Commit:** `feat(backend): shared schemas and demo fixtures`

### [F] N3 · Stub API
- **Goal:** Every route in §4.2 exists and returns fixture data, so L can generate types and build screens.
- **Files:** `backend/app/api/*.py`, `backend/tests/test_api_stubs.py`.
- **Do:** Routers for all routes in §4.2 (including export, delete, forgot/reset password, certificate download and share revoke), answering from the fixtures. Error handlers that turn every error into CONTRACT.md §3 format (422 → 400 `validation`, `detail` always a string). The **auth stub** exactly as CONTRACT.md §4 (cookie `hrp_auth`, any credentials accepted, `accept_privacy` required, `/users/me`, `401` on `/homes/*` and `/users/me*` without the cookie). The **Origin check** middleware (CONTRACT.md §4) is real from now on. `backend/scripts/export_openapi.py` + `make openapi` write `docs/openapi.json`; CI fails if the committed file differs from the app's schema. Add `backend/tests/test_auth_flow.py` (register → login → me → logout → 401) and `test_origin_check.py` (POST without `Origin` → 403).
- **Check:** `/docs` shows every route; every route returns schema-valid JSON in tests; error and auth tests pass; changing a field without updating `docs/openapi.json` makes CI fail (try it, then revert).
- **Commit:** `feat(backend): stub API, error format, auth stub, contract CI`

### [F] N4 · Database and seed
- **Goal:** Real tables and reference data loaded.
- **Files:** `backend/app/db/{models.py,session.py,seed.py}`, `backend/alembic/`.
- **Do:** Tables `users` (fastapi-users columns plus `privacy_accepted_at`, `privacy_version`, `created_at`, `last_seen_at`), `homes`, `households`, `assessments` (inputs, risk, score JSONB), `plans`, `passport_events`, `work_files` (`event_id`, `storage_key`, `certificate_name`, `content_type`, `size_bytes`), `share_links`, `measures`, `funding_options`, `flood_postcodes`, `api_cache`, `llm_cache`. Every table hanging off a user or home uses `ON DELETE CASCADE`, so deleting a user removes everything (files are removed by the service in N14). `make seed` loads `data/reference/*.csv` (use A's sample rows, or 3 placeholder rows each). Add `make validate-data`: checks every rule in CONTRACT.md §5 and prints row and column of each problem; add it to CI.
- **Check:** `alembic upgrade head` works on a fresh DB; `make seed` loads rows; a test reads one measure back; a CSV with a wrong column name fails `make validate-data` with a clear message.
- **Commit:** `feat(backend): database models, migrations, seed loader`

### N5 · Postcode adapter
- **Goal:** Real postcode lookup.
- **Files:** `backend/app/adapters/postcodes.py`, tests with recorded responses (`respx`).
- **Do:** Call postcodes.io; normalise postcode; cache 30 days; wire into `/lookup/postcode/{postcode}`.
- **Check:** A real postcode returns lat/lon and local authority; an invalid one returns 422 `validation`; tests pass offline using recorded responses.
- **Commit:** `feat(backend): postcode lookup via postcodes.io`

### N6 · EPC adapter
- **Goal:** Property facts from the real EPC register.
- **Files:** `backend/app/adapters/epc.py`, tests.
- **Do:** First read the current developer API guide (see §5) and note base URL and auth in `docs/DECISIONS.md`. Search certificates by postcode, list addresses with their latest certificate, map fields into `PropertyFacts` (`source="epc_api"`). Cache 30 days. If no certificate: return the address list without EPC data so the user can fill it in.
- **Check:** A real postcode lists addresses with EPC ratings; mapping test covers at least one flat and one house; a missing key degrades gracefully.
- **Commit:** `feat(backend): EPC register adapter`

### N7 · Flood adapter
- **Goal:** River/sea flood band and live warnings.
- **Files:** `backend/app/adapters/flood.py`, `backend/app/db/load_rofrs.py`, tests.
- **Do:** Script downloads the RoFRS "Postcodes in Areas at Risk" ZIP into `data/raw/` (git-ignored), inspects its columns, and loads them into `flood_postcodes` (record the column mapping in `docs/DECISIONS.md`). Lookup returns the highest band present for the postcode. Call the EA real-time flood-monitoring API for warnings within 5 km.
- **Check:** A postcode known to be in a flood area returns `medium` or `high`; a hill-top postcode returns `none`; warnings call degrades to 0 when offline.
- **Commit:** `feat(backend): EA flood risk and live warnings`

### ⚑ N8 · Climate adapter
- **Goal:** Today vs 2050 heat, rain and wind.
- **Files:** `backend/app/adapters/climate.py`, tests.
- **Do:** Call Open-Meteo Climate API for one model (`EC_Earth3P_HR`) with daily `temperature_2m_max`, `precipitation_sum`, `wind_speed_10m_max`, as two parallel requests (1991–2020, 2041–2050); compute the statistics exactly as CONTRACT.md §2 defines them. Cache by rounded lat/lon. Fallback: regional defaults table.
- **Check:** London returns more hot days in 2050 than baseline; second call hits the cache; tests use recorded responses.
- **Hand-off:** once N5–N8 work, add `make fixtures` and record the real `HazardInputs` for the 5 demo homes into `backend/tests/fixtures/demo_homes/` in a PR titled `fixtures: real data` and ask L to approve it (the inputs are contract). L re-runs scoring tests on them (no meeting needed). Also fill `climate_defaults.py` from real calls.
- **Commit:** `feat(backend): climate projections via Open-Meteo`

### ⚑ N9 · Assessment pipeline
- **Goal:** `POST /homes` and `POST /homes/{id}/assess` work end to end with real data.
- **Files:** `backend/app/services/assessment.py`, routers.
- **Do:** Build `HazardInputs` from adapters (in parallel with `asyncio.gather`), call `scoring.assess_risk` and `scoring.compute_score` (L's stub until L5 merges), store the assessment, add a passport event `assessed`.
- **Check:** A real postcode produces a schema-valid risk and score in under 5 s (cold) and under 1 s (cached); the 5 demo homes work with the network off.
- **Commit:** `feat(backend): assessment pipeline`

### ⚑ N10 · Auth
- **Goal:** Real accounts; homes belong to users.
- **Files:** `backend/app/auth/`, routers.
- **Do:** Replace the stub with fastapi-users exactly as CONTRACT.md §4 (same routes, cookie name and responses, so the front end needs no change); users only see their own homes. `UserManager.validate_password` enforces the password rule; `accept_privacy` is stored as `privacy_accepted_at` + `privacy_version`. Map every fastapi-users error code to CONTRACT.md §3. Real `GET /users/me/export` and `DELETE /users/me`. Forgot-password writes the reset link to the log when `RESEND_API_KEY` is unset (M1). Rate limits from CONTRACT.md §3 with a small in-memory fixed-window limiter in `backend/app/core/ratelimit.py` (no new dependency; fine for one API instance). Update `last_seen_at` at most once a day per user.
- **Check:** Register → login → `/users/me` works; another user gets 404 on your home; the 6th login in a minute gets 429; export contains the user's home; delete removes every row for that user (test counts rows per table before and after); tests cover all of these.
- **Commit:** `feat(backend): email/password auth with cookie JWT`

### N11 · Planner and AI explanations
- **Goal:** Ranked, costed plan with plain-English explanations.
- **Files:** `backend/app/services/{planner.py,llm.py}`, tests.
- **Do:** Implement §7 Planner. LLM call through `llm.py` (one place for model, timeout 8 s, cache in `llm_cache`, daily cap). Template fallback.
- **Check:** Plan for each demo home is schema-valid; renters never get `needs_landlord` items in the main list; with no API key the plan still returns with `explanation_source="template"`; `test_llm_prompt_has_no_personal_data` passes (CONTRACT.md §6 rule 2); a second `/plan` with a different budget makes no LLM call (mocked client call count stays 1).
- **Commit:** `feat(backend): planner with AI explanations and template fallback`

### N12 · EPC model: data and training
- **Goal:** Our own trained model that predicts EPC band and CO2 per year.
- **Files:** `backend/ml/{prepare.py,train.py,evaluate.py}`, `backend/ml/artifacts/`, `docs/model_card.md`, tests.
- **Do:** Download EPC bulk data for about 3 regions into `data/raw/` (git-ignored). `prepare.py` cleans it and keeps the features in §2 (drop rows with missing targets; group rare categories). `train.py` trains `HistGradientBoostingClassifier` for the band (A–G) and `HistGradientBoostingRegressor` for CO2, with a fixed random seed and an 80/20 split by postcode area so test homes are unseen. `evaluate.py` reports accuracy, within-one-band accuracy, macro F1, CO2 MAE, and a confusion matrix image. Write `docs/model_card.md`: data, features, metrics, limits, fairness notes (check accuracy is similar across property types and regions).
- **Check:** `make train` runs end to end from raw data; within-one-band accuracy is reported (target ≥ 80%); the artefact loads in a test; model card filled in.
- **Commit:** `feat(ml): EPC band and CO2 model with model card`

### ⚑ N13 · EPC model in the app
- **Goal:** Homes without a certificate get a predicted EPC band and CO2, clearly labelled.
- **Files:** `backend/ml/predict.py`, `backend/app/services/assessment.py`, tests.
- **Do:** Load the model once at start-up. In the assessment, if `epc_rating` is missing, predict it from the known facts and set `PropertyFacts.source="model"`. Add a `GET /api/v1/model/info` route returning model version and metrics for the Technology slide.
- **Check:** A demo home with its EPC removed gets a predicted band; prediction takes under 50 ms; the label "Estimated by our model" reaches the API response.
- **Commit:** `feat(ml): serve EPC predictions in assessment`

### N14 · Passport, work records and sharing
- **Goal:** The passport record, score history and share link.
- **Files:** `backend/app/services/passport.py`, routers.
- **Do:** `GET /passport` assembles everything; `POST /work` validates and stores the certificate exactly as CONTRACT.md §6 through `services/storage.py` (one interface, `LocalStorage` in M1, `R2Storage` added in N17), records the event and recomputes the score with completed measures; certificate download is owner-only; `POST /share` creates a random token with `secrets.token_urlsafe(24)` (32 chars), `DELETE /share` revokes it; `DELETE /homes/{id}` removes the home and its files; public route hides `household`, `share_token` and certificate names.
- **Check:** Recording a measure raises the score and adds an event; a `.exe` renamed to `.pdf` gets 415; a 6 MB PDF gets 413; another user gets 404 on your certificate; the public link works logged-out, shows no household data, and stops working after revoke.
- **Commit:** `feat(backend): passport, work records and share links`

### ⚑ N15 · Hardening for M1
- **Goal:** Demo-proof back end.
- **Do:** Consistent error codes (§4.2); upstream timeouts logged, not crashing; `make seed` loads the 5 demo homes with full data; README "run the demo in 5 commands"; test coverage of every route.
- **Check:** With Wi-Fi off, the 5 demo homes still run end to end; `make test` and CI green.
- **Commit:** `chore(backend): M1 hardening and demo seed`

---

## 10. L's steps (front end, scoring)

Targets: **L0–L3 merged Mon 26 Oct 9 pm (Foundation)**, **L4–L9 by Tue 3 Nov (Merge 1)**, **L10–L14 by Tue 10 Nov (Merge 2, freeze)**.

### [F] L0 · Setup
- **Goal:** Tools ready.
- **Do:** Install Git, Node 22 LTS, `pnpm`, Python 3.12, `uv`, Docker Desktop, Claude Code. Accept the repo invite, clone, run `make dev` once N1 is merged.
- **Check:** `curl localhost:8000/api/v1/health` works on L's machine.
- **Commit:** none.

### [F] L1 · Front-end scaffold
- **Goal:** Next.js app with the design system.
- **Files:** `frontend/` (create with `create-next-app`, TypeScript, App Router, Tailwind, ESLint), shadcn/ui init, `frontend/src/app/layout.tsx`, `next.config.ts` (rewrite `/api/:path*` → `http://localhost:8000/api/:path*`), add the front-end CI job.
- **Do:** Theme tokens: deep green `#0B3D3A`, green `#1E9E6A`, mint `#E6F4EE`, warning `#F2A35E`, risk red `#D9534F`. Font: Inter via `next/font`. App shell with header ("Home Resilience Passport"), footer with data attribution.
- **Check:** `pnpm dev` shows the shell on :3000; `pnpm lint`, `pnpm tsc --noEmit`, `pnpm build` pass; CI green.
- **Commit:** `feat(frontend): Next.js scaffold, theme, app shell`

### [F] L2 · API client and mock mode
- **Goal:** Typed calls to the back end, and a mock mode that works without it.
- **Files:** `frontend/src/lib/api/{schema.d.ts,client.ts}`, `frontend/src/mocks/`.
- **Do:** Generate types with `make types` (after N3 is merged). `client.ts` wraps `openapi-fetch` and turns error bodies into a typed `ApiError {status, code, detail}`. A `useUser()` hook and a `requireUser` guard that redirects to `/login?next=…` on `401` (CONTRACT.md §4). When `NEXT_PUBLIC_API_MOCK=1`, the client returns fixture data instead (`pnpm mocks:sync` copies them in, §4.4). Every mutating request is same-origin, so the browser sends `Origin` automatically (CONTRACT.md §4). Build a **`/dev/contract` page** that exercises every seam: lists demo homes, logs in with the stub, creates a home, runs assess/plan/funding/passport, triggers a `404` and a `400`, and shows a green or red tick per call.
- **Check:** `/dev/contract` is all green against the real stub API and in mock mode; `tsc` passes; logged-out visit to a protected page redirects to `/login`.
- **Commit:** `feat(frontend): typed client, auth guard, mock mode, contract page`

### [F] L3 · Scoring package skeleton
- **Goal:** N can call scoring from day one.
- **Files:** `backend/app/scoring/__init__.py`, `backend/app/scoring/{risk.py,score.py,funding.py,config.py}`, `backend/tests/scoring/test_contract.py`, `backend/tests/scoring/expected/`.
- **Do:** Implement all three §4.3 signatures (`assess_risk`, `compute_score`, `match_funding`) returning fixed placeholder values that validate against the schemas.
- **Check:** `pytest backend/tests/scoring` passes; N's assessment code can import it.
- **Commit:** `feat(scoring): interface stub`

### L4 · Risk engine
- **Goal:** Real hazard levels per §6.
- **Files:** `backend/app/scoring/risk.py`, tests, `docs/scoring.md`.
- **Do:** Implement thresholds; every `HazardLevel.why` is a human sentence ("About 18 hot days a year by 2050, up from 6 today"). Document the rules in `docs/scoring.md`.
- **Check:** Table-driven tests cover every threshold edge; all 5 fixtures give the expected levels.
- **Commit:** `feat(scoring): risk engine v1`

### ⚑ L5 · Resilience score
- **Goal:** 0–100 score, band and reasons per §6.
- **Files:** `backend/app/scoring/score.py`, tests, `docs/scoring.md`.
- **Check:** Tests for band edges, unknown EPC, measure uplift capping; fixtures match expected scores; the score never goes above 100 or below 0.
- **Commit:** `feat(scoring): resilience score v1`

### L6 · Funding matcher
- **Goal:** `match_funding` per §7 Funding, as a pure function.
- **Files:** `backend/app/scoring/funding.py`, `backend/tests/scoring/test_funding.py`, `docs/scoring.md`.
- **Do:** Filter options by income band, tenure and selected categories; order grants → cashback → insurance discount → loans; allocate grants first; put the gap on the lowest-APR loan; compute the 5-year monthly cost. Never vary price or rate by score (fairness rule).
- **Check:** Low-income owner gets grants first; high-income owner gets no means-tested grants; `covered_gbp + gap_gbp` equals plan cost; tests cover every rule.
- **Commit:** `feat(scoring): funding matcher`

### L7 · Start: postcode and address
- **Goal:** Page 1 of the journey.
- **Files:** `frontend/src/app/(journey)/start/page.tsx`, components.
- **Do:** Postcode input with UK format validation → address list (with EPC rating badge if present) → "My address isn't listed" → manual property form. "Try a demo home" button lists the 5 demo homes.
- **Check:** Works in mock and real mode; keyboard-only usable; error state for bad postcode.
- **Commit:** `feat(frontend): postcode and address selection`

### L8 · Household form
- **Goal:** Collect `Household`.
- **Do:** react-hook-form + zod mirroring the schema; plain-English helper text; the optional vulnerability box with the exact wording and "prefer not to say" default from CONTRACT.md §6 rule 1; `consent_lloyds_data` checkbox unticked by default. If the user is logged out, save the form to `sessionStorage` and send them to `/login?next=/start/household` (or sign-up), then restore it (CONTRACT.md §3). On submit → `POST /homes` then `POST /assess`, show a progress state ("Checking flood maps… climate projections… energy certificate…").
- **Check:** Validation messages for each field; successful submit lands on the risk page.
- **Commit:** `feat(frontend): household form and assessment start`

### ⚑ L9 · Risk page
- **Goal:** Show the risks clearly.
- **Do:** Map centred on the home (React-Leaflet, OSM tiles); one card per hazard with level colour and `why`; toggle Today / 2050; data source line on each card.
- **Check:** All 5 demo homes render; toggle changes levels; mobile width 375 px has no horizontal scroll.
- **Commit:** `feat(frontend): risk results with map and 2050 toggle`

### L10 · Score dashboard
- **Goal:** The score is the hero.
- **Do:** Radial gauge (Recharts) with value and band; component bars (flood, heat, storm, subsidence, carbon) with reasons; side-by-side with EPC rating; "What does this mean?" explainer.
- **Check:** Values match API; screen reader reads the score as text.
- **Commit:** `feat(frontend): resilience score dashboard`

### L11 · Plan page
- **Goal:** Interactive plan.
- **Do:** Ranked list with cost range, saving, CO2, score uplift and explanation; checkboxes; budget slider; live totals and projected score (re-POST `/plan` debounced 400 ms); separate "Ask your landlord" group for renters.
- **Check:** Changing selection updates totals and projected score; renter demo home shows the landlord group.
- **Commit:** `feat(frontend): interactive improvement plan`

### L12 · Funding page
- **Goal:** One clear funding bundle.
- **Do:** Stacked bar of how the cost is covered (grants, cashback, discount, loan); cards per line; "Illustrative" tag on mock Lloyds products; monthly cost.
- **Check:** Bundle matches API; low-income demo home shows grants first.
- **Commit:** `feat(frontend): funding bundle`

### ⚑ L13 · Passport, history, sharing, accounts
- **Goal:** The passport and login.
- **Do:** Sign-up page with the required "I have read the privacy notice" checkbox linking to `/privacy` (sends `accept_privacy: true`); log-in / log-out; forgot-password and reset-password pages; `/privacy` page rendering `docs/privacy.md` (copied in at build time like the fixtures); "Account" page with "Download my data" (`/users/me/export`) and "Delete my account" (type `DELETE` to confirm); "My homes" list with "Delete this home"; Passport page with score history line chart, events timeline, "Record completed work" form with certificate upload; "Share" button that copies the public link; public read-only passport page at `/p/[token]`; "Stop sharing" button (`DELETE /share`). Certificate upload accepts PDF/JPEG/PNG up to 5 MB and shows the 413/415 messages.
- **Check:** Full journey works logged-in; public link works in a private window and shows no household data; after "Stop sharing" it shows "This link is no longer active"; delete account logs you out and your homes are gone.
- **Commit:** `feat(frontend): passport, sharing and accounts`

### ⚑ L14 · Polish for M1
- **Goal:** Demo-ready UI.
- **Do:** Loading, empty and error states on every page; accessibility pass (labels, contrast, focus); responsive check at 375, 768, 1280 px; attribution footer; landing page with one-line pitch and "Start" / "Try a demo home".
- **Check:** Lighthouse accessibility ≥ 90 on start, risk and passport pages; `pnpm build` clean; CI green.
- **Commit:** `feat(frontend): M1 polish`

---

## 11. Meetings (90 min, twice a week)

Only three meetings are merge points. The others are optional working sessions or deck time with A.

| Meeting | Date | Must be merged before (by 9 pm the night before) | In the meeting | Done when |
| --- | --- | --- | --- | --- |
| **Foundation check** | Tue 27 Oct | All **[F]** steps: N0–N4, L0–L3 | Everyone clones fresh and runs `make dev`. Open `/dev/contract` (all green). Confirm the hot-day threshold result (CONTRACT.md §2). Walk through CONTRACT.md together so A knows the CSV rules. Tag `contract-v1`. Agree who reviews whose PRs | Tag pushed; all three laptops run the app |
| Optional | Fri 30 Oct | – | Deck kick-off with A; help each other with blockers | – |
| **Merge 1** | Tue 3 Nov | N5–N9, L4–L9 (⚑ N8, N9, L5, L9) | Real postcode end to end. **Sense check:** do the risk levels and scores look right for the 5 demo homes on real data? Read both decision logs. A reviews thresholds in `docs/scoring.md`. Any contract change done here | A real postcode shows real risks and a sensible score |
| Optional | Fri 6 Nov | – | Bug bash: A tests as each persona and logs GitHub Issues | – |
| **Merge 2 + freeze** | Tue 10 Nov | N10–N15, L10–L14 (⚑ N10, N13, N15, L13, L14) | Full journey with real login. Playwright smoke test (`frontend/e2e/journey.spec.ts`). Fix only blockers. Read both decision logs. Tag `v1.0-m1` | All checks green; tag pushed |
| **Video** | Fri 13 Nov | Deck draft complete | Record the 60–90 s demo and screenshots, insert into deck, rehearse | Submit by Sat 14 Nov |

Every merge meeting starts with 10 minutes reading `docs/decisions/N.md` and `L.md`; entries marked "Affects the other coder? yes" are resolved first.

---

## 12. Milestone 2 backlog (after 15 Nov, or earlier if ahead)

1. (Moved to §14, M2a.)
2. Surface-water flood risk (check EA licence terms first).
3. Subsidence from BGS data (licence) instead of the user answer.
4. Coastal erosion (EA National Coastal Erosion Risk Mapping).
5. Live alerts: email when a flood warning covers a saved home.
6. Installer marketplace (TrustMark/MCS search, booking requests).
7. Landlord view (portfolio of homes, tenant safety notes) and branch-adviser mode.
8. Smart-home sensor ingestion (simulated device feed first).
9. Insurer view and pricing API (mock).

---

## 13. Decision rules for anything not covered

When Claude Code meets a question this spec does not answer, choose in this order and log it in **the coder's own log** (`docs/decisions/N.md` or `docs/decisions/L.md`):

1. **Keep the demo path working** (start → risk → score → plan → funding → passport for the 5 demo homes).
2. **Do not change the shared contract.** Work around it inside your own paths; if impossible, stop and ask the human.
3. **Simplest thing that is correct and tested.** No new dependency unless it saves real work; name it in the PR.
4. **Real data with a graceful fallback** beats either one alone.
5. **Fair and plain:** nothing that penalises a high-risk or low-income household; no jargon on screen.
6. **Match existing patterns** in the codebase over introducing new ones.

If two options are still equal, pick one, note the alternative in the log, and move on.

**Decision log entry format** (one per decision, newest at the bottom):

```
### 2026-10-29 · N7 · RoFRS ZIP has one row per postcode and band
- Decision: take the highest band present for the postcode
- Alternatives: weighted average by property count
- Why: simplest, conservative for flood risk (rule 3, rule 5)
- Files: backend/app/adapters/flood.py
- Commit: <short hash, filled in when committed>
- Affects the other coder? no
```

At every sync meeting, N and L read both logs together. Any entry marked "Affects the other coder? yes" is copied into `docs/DECISIONS.md` and, if needed, becomes a contract change.

---

## 14. Milestone 2a: live hosting and real user data

Goal: a public link where a real person can sign up, assess their own home and keep a passport, with their data handled properly. Built after submission (from Mon 16 Nov) on top of M1; no M1 behaviour changes. The submission deck shows the video only. The link goes public once every box in the go-live checklist (§14.6) is ticked.

### 14.1 How it is hosted

```
 browser ──HTTPS──► Vercel (Next.js, frontend/)          one domain: hrp-<team>.vercel.app
                      │ rewrite /api/v1/*  (API_ORIGIN)
                      ▼
                    Render web service (Docker, backend/, Frankfurt)
                      ├──► Neon Postgres 16 (AWS London, TLS required)
                      ├──► Cloudflare R2 bucket "hrp-certificates" (EU jurisdiction, private)
                      ├──► postcodes.io · EPC API · EA · Open-Meteo   (unchanged adapters)
                      └──► Anthropic API (no personal data)
```

| Piece | Choice | Plan and cost | Why |
| --- | --- | --- | --- |
| Front end | Vercel, Git integration on `main` | Hobby, free | Native Next.js; preview deploy per PR |
| API | Render web service from `backend/Dockerfile` | **Starter, about $7/month** (owner decision 27 Oct) | Free tier sleeps after 15 min and takes about a minute to wake, longer than our 20 s front-end timeout |
| Database | Neon, region `aws-eu-west-2` (London) | Free (0.5 GB) | Free tier does not expire (Render's free Postgres is deleted after 30 days); UK data residency |
| Files | Cloudflare R2, EU jurisdiction | Free (10 GB) | S3-compatible, private by default, no egress fees |
| Email (password reset) | Resend, only if we own a domain | Free tier; domain about £10/year | Without a domain, forgot-password shows "Email us at <team address>" and N resets manually |

Render and Neon both run in the UK/EU, so no personal data leaves the UK/EU except prompts to Anthropic, which contain none (CONTRACT.md §6).

### 14.2 Secrets and environment

Never in git, never in logs, never in the front-end bundle. Only `NEXT_PUBLIC_*` variables reach the browser, and none of them are secret.

| Variable | Local `.env` | Render | Vercel | GitHub Actions |
| --- | --- | --- | --- | --- |
| `ENV` | `development` | `production` | – | `test` |
| `DATABASE_URL` | Docker Postgres | Neon URL with `sslmode=require` | – | service container |
| `AUTH_SECRET` | any 32+ chars | `openssl rand -hex 32` | – | test value in workflow |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | the Vercel URL | – | `http://test` |
| `EPC_API_TOKEN` | yours | team token | – | not needed (recorded responses) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `LLM_DAILY_CALL_LIMIT` | optional | set | – | not set (template path) |
| `STORAGE_BACKEND` | `local` | `r2` | – | `local` |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | – | set | – | – |
| `RESEND_API_KEY`, `MAIL_FROM` | – | only with a domain | – | – |
| `API_ORIGIN` | `http://localhost:8000` | – | the Render URL | – |
| `NEXT_PUBLIC_APP_URL` | `http://localhost:3000` | – | the Vercel URL | – |

Rules: N creates the production values and enters them in the Render and Vercel dashboards; they are shared with L only through those dashboards (add L as a team member), never pasted in chat or GitHub. A leaked key is rotated the same day (`AUTH_SECRET` rotation logs everyone out, which is fine). Enable GitHub secret scanning and push protection on the repo if the plan offers it.

### 14.3 Security baseline

- HTTPS everywhere (Vercel and Render provide it). Cookie `Secure` in production (CONTRACT.md §4).
- Security headers from Next.js (`next.config.ts` `headers()`): `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, and a Content-Security-Policy that allows only self, OSM tile servers and inline styles that Tailwind/Recharts need.
- `/docs` and `/openapi.json` on the API are disabled when `ENV=production`; `/dev/contract` (front end) returns 404 in production.
- Passwords hashed by fastapi-users (Argon2 via `pwdlib`). Rate limits per CONTRACT.md §3.
- Dependencies: Dependabot on for `uv` and `pnpm` (security updates only).
- Backups: Neon point-in-time restore (free tier keeps 24 h). Before go-live, test one restore to a branch database.

### 14.4 Retention and user rights

| Data | Kept for | How it is removed |
| --- | --- | --- |
| Account and everything it owns | Until the user deletes it, or 12 months after `last_seen_at` | `DELETE /users/me`; a daily job (`backend/app/jobs/retention.py`, run by Render cron) deletes accounts idle for 12 months after an email warning if email is set up, otherwise without one |
| Share link | Until revoked or the home is deleted | `DELETE /homes/{id}/share` |
| Certificates | With their work record | Deleted with the record, home or account (storage service deletes the object) |
| API logs (contain IPs) | Render keeps 7 days on Starter | Automatic |
| Caches (`api_cache`, `llm_cache`) | TTL in §5 | Contain no personal data |

Rights covered: access (export), erasure (delete), rectification (edit household and home at any time), withdrawing consent for `vulnerable` (set to "prefer not to say"). Requests by email are handled by N within a week.

### 14.5 Privacy notice (`docs/privacy.md`)

N writes `docs/privacy.md` in N19 from this outline, in plain English, at most one screen per section. A reviews it. It is not legal advice; it describes what the app actually does.

1. Who we are: a student team building Home Resilience Passport for the TCS Sustainathon; contact email.
2. What we collect: email and password (stored hashed), the home's address and property facts, household answers, the optional vulnerability answer, uploaded certificates, IP addresses in server logs for 7 days.
3. Why, and the legal basis: to provide the account and passport you asked for (contract); the vulnerability answer only with your explicit consent, to put safety measures first; logs for security (legitimate interests).
4. Who else handles it (processors): Vercel, Render, Neon, Cloudflare, and Anthropic (receives property and hazard facts only, nothing that identifies you). Public data sources receive only a postcode or coordinates.
5. What we never do: sell data, share it with Lloyds or anyone else, use advertising or tracking cookies.
6. How long we keep it (§14.4) and how to download or delete it from the Account page.
7. Your rights and how to complain to the ICO (ico.org.uk).
8. Version and date (this is `privacy_version`, stored when a user accepts).

Before opening sign-ups to people outside the team and judges, check whether the team needs to pay the ICO data protection fee (ico.org.uk "Do I need to pay the fee?" self-assessment); note the answer in `docs/DECISIONS.md`.

### 14.6 Go-live checklist (all ticked before the link goes public)

- [ ] Fresh sign-up, assess a real postcode, save, record work with a PDF, share, open the share link logged-out, stop sharing, export, delete account: all work on the live URL.
- [ ] The 5 demo homes load in under 3 s with the network to external sources blocked (cached seed in Neon).
- [ ] First request after 30 minutes idle answers in under 5 s.
- [ ] `/docs`, `/openapi.json` and `/dev/contract` are 404 in production.
- [ ] Response headers checked (securityheaders.com grade A or B).
- [ ] No secret in the repo (`git log -p | grep -i -E "sk-ant|secret|password="` reviewed), none in the browser bundle.
- [ ] Privacy notice live at `/privacy`, linked from the footer and the sign-up checkbox.
- [ ] Neon restore tested once.

### 14.7 M2a steps

Each follows the same Goal / Do / Check / Commit pattern and the same stop-after-each-step rule.

| Step | Owner | Do | Done when | Commit |
| --- | --- | --- | --- | --- |
| **N16** · Production config | N | `backend/Dockerfile` (python:3.12-slim, `uv sync --frozen`, non-root user, `uvicorn` with `--proxy-headers`), `render.yaml`, `ENV=production` behaviour from §14.3, Neon database created and `alembic upgrade head` + `make seed` run against it | `docker build` and `docker run` work locally against Neon; `/api/v1/health` reports `db: ok` | `chore(infra): production Dockerfile and Render config` |
| **N17** · File storage | N | `R2Storage` in `services/storage.py` (boto3, new dependency named in the PR), selected by `STORAGE_BACKEND`; downloads streamed through the API, never a public bucket URL | Upload, download and delete work against R2; tests still use `LocalStorage` | `feat(backend): R2 storage for certificates` |
| **N18** · Deploy API | N | Create the Render service from the repo (auto-deploy on `main`), set §14.2 variables, add the retention cron job | Live `/api/v1/health` OK; retention job runs once in dry-run mode and logs what it would delete | `chore(infra): deploy API to Render` |
| **N19** · Privacy and go-live | N | Write `docs/privacy.md` (§14.5), password-reset email if a domain exists, run §14.6 with L | Every box in §14.6 ticked; result noted in `docs/DECISIONS.md` | `docs: privacy notice and go-live record` |
| **L15** · Deploy front end | L | Vercel project on `frontend/`, `API_ORIGIN` + `NEXT_PUBLIC_APP_URL` set, security headers and CSP (§14.3), `/dev/contract` hidden in production | Live URL serves the app; login cookie is set on the Vercel domain with `Secure`; headers present | `chore(frontend): Vercel deploy and security headers` |
| **L16** · Real-user polish | L | Footer privacy link; first-visit note "This is a student project; Lloyds products shown are illustrative"; empty states for a brand-new account; check the full journey on a phone | §14.6 journey works on a phone at 375 px | `feat(frontend): real-user polish` |

Order: N16 → N17 → N18 → L15 → (N19 and L16 together). About 1.5 days for N and 1 day for L.

---

## 15. Change log

| Version | Date | What changed | Why |
| --- | --- | --- | --- |
| 1.2 | 26 Oct | Foundation plan, five seams in CONTRACT.md | – |
| 1.3 | 26 Oct | Carbon points use the EPC band midpoint when only a band is known | Otherwise our model's predictions never changed the score |
| 1.3 | 26 Oct | Measure points go to the component named by `category`, including carbon | The rule was ambiguous and carbon measures could never raise the score, so the planner would never rank them |
| 1.3 | 26 Oct | `max_gust_*` renamed `max_wind_*`; storm thresholds lowered to 50/65 km/h | Open-Meteo climate data is sustained wind, not gusts; at 70/90 km/h nearly every home would be "low" |
| 1.3 | 26 Oct | Hot-day threshold check before tagging `contract-v1` | The climate model runs cool; at 30 °C overheating may never show |
| 1.3 | 26 Oct | LLM timeout 8 s (was 20 s), cache key excludes budget and selection, daily call cap | Contract says plan answers within 8 s; the budget slider would otherwise call the LLM on every move |
| 1.3 | 26 Oct | `DemoHome` shape added; logged-out users browse demos read-only; sign-up happens before `POST /homes` | `/demo/homes` had no defined shape, and the journey never said where login happens |
| 1.3 | 26 Oct | `UserRead` matches fastapi-users' default; fastapi-users errors mapped to our error format | Avoids custom serializers in N10 and keeps every error the same shape |
| 1.3 | 26 Oct | England and Wales only, `unsupported_region` error | EPC and EA data do not cover Scotland or Northern Ireland |
| 1.3 | 26 Oct | `make openapi` + `make types` from the committed `docs/openapi.json`, with a CI check on `schema.d.ts` too | Types no longer depend on a running API and cannot go stale |
| 1.3 | 26 Oct | Output parts of fixtures may be refreshed without a joint PR; L's expected values live in L's folder | L would otherwise need a shared-file PR every time a threshold changed |
| 1.3 | 26 Oct | `pnpm mocks:sync` copies fixtures into the front end | Next.js cannot import files from outside `frontend/` |
| 1.3 | 26 Oct | Node 22 LTS; GitHub Pro (Student Pack) for branch protection on a private repo | Node 20 is end of life; free private repos cannot protect `main` |
| 1.3 | 26 Oct | Real-user routes added to the contract now (export, delete account, delete home, forgot/reset password, certificate download, stop sharing), stubbed in N3 | Adding them later would need a contract change in the middle of the build |
| 1.3 | 26 Oct | Privacy and upload rules (CONTRACT.md §6), Origin check, rate limits, `accept_privacy` on register, `vulnerable` can be "prefer not to say" | Real user data in M2; the vulnerability answer can reveal health, which needs explicit consent |
| 1.3 | 26 Oct | New §14: M2a hosting, secrets, security, retention, privacy notice, go-live checklist, steps N16–N19 and L15–L16 | M2 is now in scope with real user data |
| 1.3 | 27 Oct | M2a moves to after submission (from Mon 16 Nov), on Render Starter + Neon + R2; submission is video-only | Owner decision: less pressure in freeze week |

Claude Code adds rows to the end of this table when a step changes something in this spec (with the owner's approval).
