# N_20_function.md — Resilience Studio (20 new functions for N)

Version 1.0 · written 28 Oct 2026 · owner **N** · for N's Claude Code (cc)

This file specifies **20 new, independent functions** for the Home Resilience Passport (HRP), grouped into one product area called **Resilience Studio**. Each function is built end to end (back end + front end) by N's cc alone, without any work from L or A.

None of the 20 repeats the 20 features already planned (address risk profile, multi-source flood card, surface-water diagnostic, live flood alert mode, observed heat history, UKCP18 panel, EPC reality check, estimated EPC, fabric-first planner, overheating planner, storm checklist, subsidence indicator, no-regrets ranker, budget ladder, funding concierge, renters' mode, vulnerability mode, verified works passport, shareable report, community dashboard). Where a Studio function sits near one of those, its section says how it differs.

---

## 0. How cc uses this file

1. Read `CLAUDE.md`, `docs/CODING_SPEC.md`, `docs/CONTRACT.md`, then this file. All their rules still apply: one step at a time, run the checks, **stop and wait for "approved"**, then commit, log decisions in `docs/decisions/N.md`, push, open or update the PR.
2. Steps are named **S00** to **S20**. **S00 (Studio foundation) must be built and merged first.** After that, S01–S20 are independent of each other: build them in any order. The recommended order is in §5.
3. Branch per step: `n/S00-studio-foundation`, `n/S01-retrofit-sandbox`, and so on. One PR per step. PR title: `S01 · Retrofit Sandbox`.
4. Commit message per step: `feat(studio): S01 retrofit sandbox` (S00: `feat(studio): S00 studio foundation`).
5. If a data source's URL, parameter or field name in this file no longer matches the live service, **read the provider's current docs first**, use what is live, and log the difference in `docs/decisions/N.md` (spec §13 rules). Every external figure that this file marks **"verify"** (prices, grant amounts, research percentages) must be read from the linked source at build time and stored in config with its URL and the date read. Never invent a number.
6. Code freeze for M1 is **Tue 10 Nov**. Anything not merged by then waits until after submission. Studio must never break the demo path (start → risk → score → plan → funding → passport for the 5 demo homes).

---

## 1. Ground rules: how Studio stays inside the contract

Studio is **purely additive**. It adds new files, new routes and new tables. It changes no existing route, schema, field, cookie, CSV column or page.

### 1.1 What Studio never touches

| Never edit                                                                                                                                              | Why                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/CONTRACT.md`, `docs/openapi.json`, `backend/app/schemas/`, `backend/tests/fixtures/`, `.env.example` (except adding new names, allowed) | Shared contract files                                                                                                                                         |
| `backend/app/scoring/`, `backend/tests/scoring/`                                                                                                    | L's pure functions. Studio **calls** `assess_risk`, `compute_score`, `match_funding` read-only, exactly as N's services already do                |
| Any existing file under `frontend/`                                                                                                                   | L's front end. Studio only **adds new files** in two N-owned folders (S00 charter)                                                                      |
| `data/reference/*.csv` values                                                                                                                         | A's data. Studio reads the `measures` and `funding_options` tables through the existing loader                                                            |
| `frontend/package.json` dependencies                                                                                                                  | No new front-end packages. Studio uses what L1 installed: Next.js 15, React, Tailwind, shadcn/ui, Recharts, React-Leaflet. Motion is CSS + Web Animations API |

### 1.2 Where Studio code lives (all N-owned)

```
backend/app/studio/
├── __init__.py
├── router.py              # mounts every feature router under /api/v1/studio (auto-discovery)
├── common/
│   ├── schemas.py         # Evidence, StudioHome, FeatureMeta, error helpers
│   ├── home_ref.py        # resolve_home(): UUID (owner, login) or "demo-<slug>" (public)
│   ├── cache.py           # thin wrapper over the existing api_cache table
│   ├── http.py            # shared httpx.AsyncClient factory, 10 s timeout, retries=1
│   ├── geo.py             # haversine, point-in-polygon, Douglas-Peucker, bbox
│   └── fallback.py        # load_fallback(feature, slug) from fallbacks/
├── features/
│   ├── s01_retrofit_sandbox/   {__init__.py, meta.py, router.py, schemas.py, service.py, config.py}
│   ├── s02_street_proof/        …
│   └── … one folder per feature
├── data/                  # small committed reference tables N owns (CSV/JSON, each with a source_url column)
└── fallbacks/<feature>/<slug>.json   # recorded responses for the 5 demo homes (offline demo)
backend/alembic/versions/   # studio_* tables, one migration per feature that needs one
backend/tests/studio/       # test_s01_*.py … test_s20_*.py, plus recorded upstream responses for respx
backend/scripts/export_openapi_studio.py
docs/openapi-studio.json    # Studio's own OpenAPI snapshot (NOT the shared docs/openapi.json)
docs/studio/                # this file, plus any Studio notes

frontend/src/app/studio/                 # N-owned route tree (new files only)
├── layout.tsx                            # Studio shell: fonts, tokens, sub-nav
├── page.tsx                              # Studio hub (20 tiles, demo-home picker)
└── [ref]/
    ├── page.tsx                          # per-home Studio hub
    └── s01-retrofit-sandbox/page.tsx … s20 (one folder per feature)
frontend/src/features/studio/            # N-owned components, hooks, styles, API client
├── api/{client.ts,schema.d.ts}           # generated from docs/openapi-studio.json
├── design/{tokens.css,studio.css}        # design system (§2)
├── components/                           # EvidenceBadge, SourceNote, StatTile, NumberTicker, Reveal, …
├── lib/                                  # pure TS helpers + vitest tests
└── s01/ … s20/                           # feature components
```

### 1.3 Routes, auth and errors

- Every Studio route is under **`/api/v1/studio/...`**. No existing path is reused or shadowed.
- Per-home routes take a path parameter **`{ref}`**:
  - a home UUID → login required (existing `hrp_auth` cookie and current-user dependency), owner only, otherwise `404 not_found` (same rule as `/homes/{id}`);
  - `demo-<slug>` (e.g. `demo-flood-terrace`) → public, read-only, served from the demo-home data that `GET /demo/homes` already uses. This makes every feature work logged-out for the video.
- Errors use the contract format and codes exactly (`{"detail", "code"}`, CONTRACT.md §3). Studio adds **no new error codes**.
- The existing Origin check middleware already covers every `POST/PUT/PATCH/DELETE`, including Studio's.
- Rate limits use the existing in-memory limiter (`backend/app/core/ratelimit.py`) with Studio's own keys and limits in each feature's `config.py`.
- Data rules are the contract's: `snake_case`, every field present (`null` for unknown, `[]` for empty lists), money in integer pounds `_gbp`, carbon in kg CO2e per year, dates `YYYY-MM-DD`, timestamps ISO 8601 UTC with `Z`, user-facing text ≤ 140 characters (≤ 200 for explanations). England and Wales only (`unsupported_region` as in §1 rule 9).

### 1.4 How Studio keeps the OpenAPI contract untouched

FastAPI would normally add new routes to `docs/openapi.json`, which is a shared file. Studio avoids that:

1. Studio routers are mounted with `include_in_schema=False` on the main app, so `make openapi` output and the shared `docs/openapi.json` stay byte-identical.
2. `backend/scripts/export_openapi_studio.py` builds a throwaway `FastAPI()` that includes **only** the Studio routers and writes **`docs/openapi-studio.json`**.
3. `make studio-openapi` runs it; `make studio-types` runs `pnpm exec openapi-typescript ../docs/openapi-studio.json -o src/features/studio/api/schema.d.ts` (openapi-typescript is already a dev dependency from L2).
4. N adds a CI step (N owns `.github/`): fail if `docs/openapi-studio.json` or `frontend/src/features/studio/api/schema.d.ts` differ from what the commands produce. Same safety as the main contract, separate file.

The Studio front end never hand-writes API types; it imports from its own `schema.d.ts` and uses `openapi-fetch` (already installed).

### 1.5 Evidence classes (applies to every number Studio shows)

Every Studio response carries an `evidence: list[Evidence]` and every chart, tile and sentence in the UI shows an **EvidenceBadge**:

| Class             | Value                 | Meaning                                                       | Examples                                                                                                                                                     |
| ----------------- | --------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Observed          | `observed`          | Measured or recorded fact                                     | ERA5 reanalysis weather, EA recorded flood outlines, Land Registry sales, user's meter readings, planning designations                                       |
| Official modelled | `official_modelled` | Output of an official or recognised model, shown as published | EPC/SAP ratings, NCERM erosion projections, PVGIS solar yield, NESO carbon-intensity forecast, Met Office UKV forecast, DESNZ grid factors, CAMS air quality |
| Estimated by HRP  | `estimated`         | Anything **we** calculate                               | Score changes, heat-pump simulation, damp risk, value uplift, inferred upgrades                                                                              |

```python
# backend/app/studio/common/schemas.py
EvidenceClass = Literal["observed", "official_modelled", "estimated"]

class Evidence(BaseModel):
    label: str                 # what this evidence covers, e.g. "Annual solar yield" (≤ 60 chars)
    evidence: EvidenceClass
    source: str                # e.g. "PVGIS 5.3, EU Joint Research Centre"
    source_url: str
    retrieved_at: datetime     # UTC, Z
    note: str | None           # ≤ 140 chars, e.g. "Not a valuation."
```

Rule: never present an `estimated` value with an official source name, and never call a projection a prediction. Each response also has `fallback_used: bool`; when `true` the UI shows a quiet "Sample data · live source unavailable" chip.

### 1.6 Personal data (CONTRACT.md §6 applies unchanged)

- Nothing personal in LLM prompts (S19 has its own test), logs, or public responses.
- Studio never stores raw uploaded meter data (S03), never stores health-related answers (S12 sends them in a POST body, used once, not persisted), and never exposes addresses or house numbers of other people's homes (S02, S14, S20 return distances and postcode districts only, with k ≥ 5 anonymity).
- Every `studio_*` table that hangs off a home has `ON DELETE CASCADE` to `homes`, so the existing account deletion (`DELETE /users/me`) and home deletion still remove everything. N adds each new table to the export in `GET /users/me/export` **only if** it holds user-entered data (S11 answers, S17 calendar token); add a test that counts rows before and after account deletion.

### 1.7 Offline and fallbacks

Each feature that calls an external API:

- uses `studio/common/http.py` (10 s timeout, one retry on connect error) and caches in `api_cache` with the TTL in its `config.py`;
- has recorded responses for the 5 demo homes in `backend/app/studio/fallbacks/<feature>/<slug>.json`, captured by `make studio-record` (one script, `backend/scripts/record_studio_fallbacks.py`, that calls each live API once per demo home);
- when live fails and a fallback exists → serve it with `fallback_used: true`; when neither exists → `502 upstream_unavailable` (contract).
- Tests never touch the network (`respx` with recorded responses).

**Wi-Fi-off check for every step:** with the network off, the feature still works for all 5 demo homes.

---

## 2. Studio design system (Lloyds-inspired, classy, calm)

Studio should feel like a private-banking statement crossed with a modern climate lab: deep green, warm paper, fine serif numerals, hairline rules, and motion that is slow and deliberate.

**Brand rule:** the palette is *inspired by* Lloyds' green. Studio never uses the Lloyds name in its own product name, the black horse, a logo, or any copy that implies it is an official Lloyds product. Anything bank-branded is labelled "illustrative", exactly as the funding rules already require.

### 2.1 Colour tokens (`frontend/src/features/studio/design/tokens.css`)

All tokens are CSS variables scoped to `.studio` (set on the Studio layout's root `div`) so nothing leaks into L's pages.

| Token                                   | Hex                                                         | Use                                                                      |
| --------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| `--s-forest-950`                      | `#00261B`                                                 | Hero and "stage" backgrounds (S07, S20)                                  |
| `--s-forest-800`                      | `#003B2B`                                                 | Hero gradient end, dark cards                                            |
| `--s-green-700`                       | `#006A4D`                                                 | Primary: buttons, links, active states, key numerals                     |
| `--s-green-500`                       | `#11B67A`                                                 | Bright accent: progress, highlights, "after" states                      |
| `--s-green-100`                       | `#E5F3EC`                                                 | Tinted surfaces, selected rows                                           |
| `--s-paper`                           | `#FAF8F3`                                                 | Page background (warm off-white)                                         |
| `--s-card`                            | `#FFFFFF`                                                 | Cards                                                                    |
| `--s-stone-200`                       | `#E7E2D8`                                                 | Hairline borders, dividers                                               |
| `--s-stone-500`                       | `#8C857A`                                                 | Secondary text, axis labels                                              |
| `--s-ink`                             | `#0E1F18`                                                 | Body text                                                                |
| `--s-brass`                           | `#B08D57`                                                 | Sparing luxury accent: "your home" marker ring, passport stamp           |
| `--s-observed`                        | `#1F5F8B`                                                 | Evidence: Observed (solid dot)                                           |
| `--s-official`                        | `#006A4D`                                                 | Evidence: Official modelled (half-filled dot)                            |
| `--s-estimated`                       | `#A86200`                                                 | Evidence: Estimated (dashed outline)                                     |
| `--s-risk-low` / `-med` / `-high` | `#2F8F5B` / `#C98A0B` / `#B3261E`                     | Hazard levels only                                                       |
| EPC band colours A→G                   | `#008054 #19B459 #8DCE46 #FFD500 #FCAA65 #EF8023 #E9153B` | Only where an EPC band is shown, matching the familiar certificate scale |

Contrast: body text on paper ≥ 7:1, secondary ≥ 4.5:1. Never rely on colour alone: every risk level and evidence class also has a word and a shape.

Dark stage sections (`.s-stage`) invert to forest background with paper text; they are used for at most one band per page.

### 2.2 Typography

Loaded in `frontend/src/app/studio/layout.tsx` with `next/font/google` (self-hosted at build time, so it works offline and sets no third-party cookies):

| Role                       | Font                          | Settings                                                                                       |
| -------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------- |
| Display and big numerals   | **Fraunces** (variable) | `opsz` auto, weight 400–600, `font-variant-numeric: lining-nums tabular-nums` for figures |
| UI and body                | **Inter**               | 400/500/600, 16 px base, line-height 1.55                                                      |
| Sources, codes, timestamps | **JetBrains Mono**      | 12–13 px, `--s-stone-500`                                                                   |

Type scale (rem): 0.75 · 0.875 · 1 · 1.125 · 1.375 · 1.75 · 2.25 · 3 · 4.5 (hero numerals only). Headings in Fraunces, sentence case, never all-caps except tiny eyebrow labels (Inter 600, 0.75 rem, letter-spacing 0.08em).

### 2.3 Layout and surfaces

- Max width 1200 px, 12-column grid, 24 px gutters (16 px on mobile), generous vertical rhythm (64–96 px between sections).
- Cards: white, 1 px `--s-stone-200` border, radius 20 px, shadow `0 1px 2px rgb(14 31 24 / .04), 0 8px 24px rgb(14 31 24 / .06)`.
- Signature motif: a **fine topographic contour pattern** (SVG, generated once in `components/Contours.tsx`, 6% opacity) behind hero sections, and a circular **passport stamp** (brass ring + feature number "S07") on each feature's header.
- Every feature page has the same frame: **Hero** (eyebrow "Resilience Studio · S07", Fraunces title, one-sentence promise, home chip) → **Answer** (the one headline number or sentence) → **Explore** (the interactive visual) → **Act** (what to do next, links into the existing plan/passport pages) → **Sources** (numbered footnotes with evidence badges, retrieved dates, licences).
- Responsive at 375, 768 and 1280 px. No horizontal scroll at 375 px.

### 2.4 Motion

| Token               | Value                              | Use                           |
| ------------------- | ---------------------------------- | ----------------------------- |
| `--s-ease-out`    | `cubic-bezier(0.22, 1, 0.36, 1)` | Everything entering           |
| `--s-ease-inout`  | `cubic-bezier(0.65, 0, 0.35, 1)` | Morphs, scrubbing             |
| `--s-dur-1/2/3/4` | 160 / 320 / 640 / 1200 ms          | Hover / state / reveal / hero |

Patterns (all in `features/studio/components/`):

- `Reveal`: fade + 12 px rise on scroll into view (IntersectionObserver), children staggered 40 ms.
- `NumberTicker`: counts to a new value over 640 ms with `requestAnimationFrame`, tabular numerals so width never jumps.
- `DrawPath`: SVG line drawing via `stroke-dashoffset` for chart lines and maps.
- `Dial`: semicircle score dial with needle easing and band letter cross-fade.
- `prefers-reduced-motion: reduce` → all of the above render the final state instantly; canvas particle effects (S07) are replaced with a static frame. Test this.

### 2.5 Components every feature uses

`EvidenceBadge` (shape + word + tooltip with source, date, link) · `SourceNotes` (numbered footnotes) · `StatTile` (eyebrow, Fraunces numeral, unit, delta, badge) · `StudioCard` · `Segmented` (pill segmented control) · `RangeBar` (low–high band with point) · `HomeChip` (address line1 + postcode district for owner homes; "Demo · Flood-zone terrace" for demos) · `EmptyState` (illustrated, kind wording) · `ErrorState` (contract code → message, same wording as L's pages) · `SkeletonBlock` (shimmer in `--s-green-100`) · `FallbackChip` · `StudioNav` (chapter tabs). Build them with shadcn/ui primitives that L already installed (Tooltip, Dialog, Slider, Tabs) and Studio tokens.

### 2.6 Charts and maps

- Recharts with Studio defaults (`features/studio/lib/chartTheme.ts`): no vertical gridlines, horizontal gridlines `--s-stone-200` at 50% opacity, axis text Inter 12 px `--s-stone-500`, tooltips as white cards with mono timestamp, series colours from the tokens (primary `--s-green-700`, comparison `--s-stone-500`, "after" `--s-green-500`).
- Maps: React-Leaflet with OpenStreetMap tiles (attribution visible), a muted CSS filter on tiles (`grayscale(.6) contrast(.95)`) inside `.studio` only, home pin in brass, overlays in green/blue with 35% fill.

### 2.7 Voice

Plain, warm and exact. Lead with the answer ("Your home loses about 180 watts for every degree colder it gets outside"). No jargon without a one-line explainer tooltip. No fear language. Every estimate says it is an estimate. Every page ends with something the person can do.

### 2.8 Accessibility

Keyboard path through every interaction (drag-and-drop in S01 and S15 has an "Add"/"Move" button alternative), visible focus ring (`2px --s-green-500` offset 2 px), `aria-live="polite"` on animated headline numbers, charts have a "View as table" toggle, Lighthouse accessibility ≥ 90 on every Studio page.

---

## 3. S00 · Studio foundation (build first)

- **Goal:** Everything the 20 functions share: the charter, back-end package and resolver, the separate OpenAPI pipeline, the design system and the hub page.
- **Charter (one small shared-file change, the only one Studio ever needs):** add two lines to `CLAUDE.md` under "Who is working":
  - "N also owns `backend/app/studio/`, `backend/tests/studio/`, `docs/studio/`, `docs/openapi-studio.json`, `frontend/src/app/studio/` and `frontend/src/features/studio/` (Resilience Studio, additive only; see `docs/studio/N_20_function.md`)."
  - Put this in its own PR titled `docs: Studio ownership charter`, ask L to approve (CLAUDE.md is shared). Per spec §8, if L has not reviewed within 24 h and CI is green, N may merge and mention it at the next meeting. Log it in `docs/DECISIONS.md` (date, N, what, why).
  - Optional, L's call: one "Studio" link in L's main nav. Studio does not depend on it (the hub is reachable at `/studio`, and every Studio page links back).
- **Files:** everything in §1.2's `common/`, `router.py`, `scripts/export_openapi_studio.py`, `scripts/record_studio_fallbacks.py`, Makefile targets (`studio-openapi`, `studio-types`, `studio-record`, `studio-test`), CI step (§1.4), `frontend/src/app/studio/{layout.tsx,page.tsx,[ref]/page.tsx}`, `frontend/src/features/studio/{design,components,api,lib}`, copy this file to `docs/studio/N_20_function.md`.
- **Do:**
  1. `resolve_home(ref, user)` → `StudioHome` with `ref`, `is_demo`, `address`, `property`, `inputs: HazardInputs`, `risk`, `score`, `household | None` (owner homes only; **never** put it in a response unless a feature section says so), `completed_measure_ids`. Demo refs read from the same source as `GET /demo/homes`. Unknown ref → `404 not_found`.
  2. Auto-discovery in `studio/router.py`: iterate `app.studio.features.*`, import each `router.py` and `meta.py`, include routers under `/api/v1/studio` with `include_in_schema=False` on the main app. A feature listed in env `STUDIO_DISABLED` (comma-separated ids, default empty) is skipped. Add `STUDIO_DISABLED` to `.env.example` (adding names is allowed).
  3. `GET /api/v1/studio/features` (public) → `list[FeatureMeta]` where `FeatureMeta = {id: "s01", slug: "retrofit-sandbox", title, chapter: "understand"|"measure"|"plan"|"live"|"money"|"ask", pitch (≤ 140), needs_login: bool, demo_ok: bool}`. The hub renders tiles from this, so adding a feature never edits a shared front-end list.
  4. `GET /api/v1/studio/homes/{ref}` → `StudioHomeSummary` (`ref`, `is_demo`, `line1` (owner) or demo label, `postcode_district`, `lat`, `lon`, `property`, `score`) for the HomeChip.
  5. Design tokens, fonts, Studio layout (`.studio` root, `StudioNav`, footer with "Resilience Studio · estimates are labelled · sources on every page" and the existing OGL/Open-Meteo attribution), all §2.5 components with vitest tests for the pure helpers (ticker easing, number formatting `£1,234`, date formatting).
  6. Hub page `/studio`: dark forest hero ("Resilience Studio. Twenty ways to see your home's future, clearly."), demo-home picker (5 cards) and "My homes" (calls existing `GET /homes` when logged in), then tiles grouped by chapter with staggered reveal. Per-home hub `/studio/[ref]` shows the same tiles linked to that home.
- **Tests:** resolver (owner ok, other user 404, demo ok logged-out, bad ref 404); discovery skips `STUDIO_DISABLED`; `docs/openapi.json` unchanged after mounting Studio (snapshot test); `docs/openapi-studio.json` contains `/api/v1/studio/features`; front-end build passes.
- **Check:** `make test`, `make lint`, `pnpm lint && pnpm typecheck && pnpm build` (frontend), `/studio` renders logged-out with 5 demo cards; `git diff docs/openapi.json` is empty.
- **Commit:** `feat(studio): S00 studio foundation`

### 3.1 The per-feature template (every S01–S20 step follows it)

Each step below lists: **Wow**, **User story**, **How it differs from the taken 20**, **Data sources**, **API** (routes + Pydantic schemas, in `features/sNN_*/schemas.py`), **Algorithm**, **UI**, **Build plan**, **Tests**, **Acceptance**, **Contract note**. In every step cc also:

1. adds `meta.py` (FeatureMeta) and `config.py` (every number, TTL, URL and verified figure with source URL and date read);
2. records fallbacks for the 5 demo homes (`make studio-record`), if the feature calls an external API;
3. runs `make studio-openapi && make studio-types`;
4. builds the page at `frontend/src/app/studio/[ref]/sNN-<slug>/page.tsx` with the §2.3 frame (S18 and S20 are not tied to one home: they live at `frontend/src/app/studio/compare/page.tsx` and `frontend/src/app/studio/portfolio/page.tsx`);
5. checks Wi-Fi off, 375 px layout, reduced motion, keyboard path, Lighthouse a11y ≥ 90.

---

## 4. The 20 functions at a glance

| #   | Name                      | One-line wow                                                                                    | Main data                                            | Evidence                      | Chapter    | Size |
| --- | ------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------- | ---------- | ---- |
| S01 | Retrofit Sandbox          | Drag measures onto a living isometric model of your home and watch score, bills and carbon move | measures, EPC, L's `compute_score`                 | Estimated                     | Plan       | L    |
| S02 | Street Proof              | "11 homes like yours near you went from D to B. Here's what they did."                          | EPC register, postcodes.io                           | Official modelled + Estimated | Understand | L    |
| S03 | Meter Fingerprint         | Your home's real heat loss in watts per degree, measured from your own meter data               | User meter CSV, Open-Meteo ERA5                      | Observed + Estimated          | Measure    | M    |
| S04 | Heat Pump Year            | A full year of a heat pump in your home, hour by hour, on last year's real weather              | Open-Meteo ERA5 hourly, Ofgem cap, BUS               | Estimated                     | Plan       | M    |
| S05 | Solar Roof Studio         | Rotate your roof under a moving sun and see kWh, savings and payback                            | PVGIS (EU JRC), Ofgem SEG, MCS                       | Official modelled + Estimated | Plan       | M    |
| S06 | Grid Carbon Clock         | A 24-hour clock of your region's grid; the greenest time for each appliance                     | NESO Carbon Intensity API                            | Official modelled             | Live       | S    |
| S07 | Storm Replay              | Relive Eunice, Babet or the 2022 heatwave as they hit your exact location                       | Open-Meteo ERA5 hourly, Met Office storm list        | Observed + Estimated          | Understand | L    |
| S08 | Flood Memory              | Every recorded flood near your home since 1946, decade by decade                                | EA Recorded Flood Outlines                           | Observed                      | Understand | M    |
| S09 | Shoreline Watch           | Where the coastline is projected to be in 2055 and 2105, near you                               | EA NCERM 2024, NRW NCERM                             | Official modelled             | Understand | M    |
| S10 | Permission Radar          | Which upgrades need planning permission at your address                                         | planning.data.gov.uk, Planning Portal rules          | Observed + Estimated          | Plan       | M    |
| S11 | Damp & Mould Lab          | Physics-based condensation risk for your walls, corners and windows last winter                 | EPC fabric, Open-Meteo ERA5, BS EN ISO 13788         | Estimated                     | Measure    | M    |
| S12 | Breathe Easy              | The best hours to open your windows in the next 3 days                                          | Open-Meteo Air Quality (CAMS), DEFRA DAQI            | Official modelled + Estimated | Live       | S    |
| S13 | Affordability Stress Test | Your energy bill under four price scenarios, before and after your plan                         | EPC energy fields, Ofgem price cap                   | Estimated                     | Money      | M    |
| S14 | Green Value Lens          | Local sales, indexed to today, and the potential value of a better EPC                          | HM Land Registry PPD + UK HPI, green-premium studies | Observed + Estimated          | Money      | M    |
| S15 | Net Zero Road             | Your home's carbon road to 2050 with each upgrade as a signpost                                 | DESNZ grid factors, CCC 7th budget                   | Official modelled + Estimated | Plan       | M    |
| S16 | Week Ahead                | Seven days of Met Office forecast turned into home actions                                      | Open-Meteo UKMO forecast                             | Official modelled             | Live       | S    |
| S17 | Home Care Calendar        | A 12-month care plan tuned to your local frost and rain, in your calendar                       | Open-Meteo ERA5 climatology                          | Observed + Estimated          | Live       | S    |
| S18 | Home Compare              | Compare up to 3 homes before you buy, side by side                                              | Existing adapters + L's scoring                      | As per pipeline               | Money      | M    |
| S19 | Passport Concierge        | Ask your home anything; answers grounded in its own data, with sources                          | Claude via `llm.py`, Studio tools                  | Estimated                     | Ask        | M    |
| S20 | Lender Portfolio Lens     | A bank's-eye view of 500 real EPC homes: exposure, transition cost, scenarios                   | EPC bulk data, RoFRS table, climate defaults         | Official modelled + Estimated | Money      | L    |

Size: S ≈ half a day with cc, M ≈ one day, L ≈ 1.5–2 days.

---

## S01 · Retrofit Sandbox

**Wow.** A cut-away isometric model of *this* home type (terrace, semi, detached, bungalow or flat) sits on the page. You drag measures from a tray onto the roof, walls, windows, door, garden or services. The house visibly changes (insulation glows in the loft, panels tile onto the roof, a flood door slides into place, an awning unfolds over the window) while the score dial, bills, carbon and the five hazard bars animate in real time.

**User story.** As a homeowner, I want to try upgrades on my home and see what each one does before I commit, so that I understand trade-offs without reading a table.

**Differs from the taken 20.** The no-regrets ranker and budget ladder produce ranked lists; the Sandbox is a free-play, visual what-if on a model of the home. It ranks nothing.

**Data sources.**

- `measures` table (A's `measures.csv`, already loaded) and the home's `PropertyFacts`.
- L's `compute_score(risk, prop, completed_measures)` (pure function; N already calls it in the planner).
- No external API.

**API.**

- `GET /api/v1/studio/homes/{ref}/sandbox` → `SandboxInit`
  - `home: StudioHomeSummary`, `baseline: SandboxState`, `hotspots: list[Hotspot]`, `measures: list[SandboxMeasure]`, `evidence: list[Evidence]`, `fallback_used: bool`
  - `Hotspot = {id: Literal["roof","walls","windows","door","ground","services"], label: str, measure_ids: list[str]}`
  - `SandboxMeasure = {measure: Measure, hotspot: <id>, already_done: bool}` (filtered by `property_types`; for renters, `needs_landlord` measures are included but flagged `needs_landlord: true` in the measure as in the CSV)
- `POST /api/v1/studio/homes/{ref}/sandbox/simulate` body `{measure_ids: list[str]}` (≤ 30, unique, must be in this home's list, else `400 validation`) → `SandboxState`
  - `score: ResilienceScore`, `delta_points: int`, `cost_low_gbp: int`, `cost_high_gbp: int`, `bill_saving_gbp_per_year: int`, `co2_saved_kg_per_year: int`, `components: list[{name, before, after, max_points}]`, `payback_years: float | None`
- "Save as my plan" uses the **existing** `POST /homes/{id}/plan` with `selected_ids` (owner homes only). No new route.

**Algorithm.**

1. Hotspot mapping in `config.py`: ordered keyword rules on measure `id` and `name` (e.g. `loft|roof|solar|pv` → roof; `wall|cladding|render` → walls; `glaz|window|shading|shutter|blind|awning` → windows; `flood-door|barrier|air-brick|door` → door; `paving|garden|drain|butt|soakaway|tree` → ground; anything else → services). Unit-test that every row in the current `measures.csv` maps to exactly one hotspot.
2. Simulate: load the home's latest risk and property, build `completed = already_done + selected`, call `compute_score`. Sum costs, savings, CO2 over selected only. Payback = mid cost / saving if saving > 0.
3. Pure and fast (< 50 ms); no cache needed.

**UI.**

- Left 7/12: `HouseIso` SVG component (5 templates drawn in code from polygons: walls, roof planes, windows, door, ground plate, attic void, service box). Hotspots pulse softly (brass ring) when the tray is open.
- Applied measures add visual layers: `loft` → warm yellow fibre texture in the attic; `solar` → panel grid on the south roof plane; `shading` → awning; `flood-door` → barrier at the door; `heat-pump` → unit beside the house; `permeable` → speckled drive; `water-butt` → barrel at the downpipe; `raised-sockets` → small plug icons lift. Unknown measures get a generic badge on their hotspot.
- Right 5/12: score `Dial` (0–100, band letter cross-fades), three `StatTile`s (cost range, £/yr, kg CO2/yr), five component bars animating from before to after.
- Bottom tray: measure chips by hotspot (HTML5 drag-and-drop, plus an "Add" button on each chip for keyboard and touch). "Before / after" toggle swipes the house. "Reset" and "Save as my plan".
- Debounce simulate calls 150 ms; optimistic animation.

**Build plan.**

1. Schemas + hotspot rules + tests over the real CSV.
2. `GET /sandbox` and `POST /simulate` with resolver; tests against demo homes.
3. `HouseIso` with 5 templates and a storybook-style dev page `/studio/dev/house` (N-owned, hidden from nav).
4. Visual layers for the 8 named measure families.
5. Dial, tiles, bars, tray, drag/drop + keyboard path.
6. Save-as-plan wiring; logged-out demo shows "Sign in to save".

**Tests.** simulate equals a direct `compute_score` call; a measure outside the home's list → 400; > 30 ids → 400; demo ref works logged-out; another user's home → 404; vitest for hotspot-to-layer mapping on the front end.

**Acceptance.** On `demo-flood-terrace`, dragging the flood door onto the door raises the flood component and the dial within 300 ms, the door visibly changes, and the uplift equals that measure's `score_uplift` in the existing `/plan` response.

**Contract note.** Read-only use of `measures`, `compute_score` and the existing plan route; two new Studio routes.

---

## S02 · Street Proof

**Wow.** "38 homes like yours within 1 km. 11 have improved their EPC. Most went from D to B by adding loft insulation and a heat pump." Real neighbours' certificates, anonymised, turned into proof that change is possible.

**User story.** As a homeowner, I want to see what similar homes nearby actually did, so that I trust that the upgrades work on homes like mine.

**Differs from the taken 20.** The community dashboard aggregates *our users'* outcomes for councils. Street Proof mines the public EPC register for *any* nearby home with two or more certificates and shows the user peer evidence. It is not an EPC reality check of their own certificate.

**Data sources.**

- postcodes.io nearest postcodes: `GET https://api.postcodes.io/postcodes?lon={lon}&lat={lat}&radius=1000&limit=50` (docs: https://postcodes.io/docs/api/api-reference-postcodes-io/). Free, no key.
- EPC register via N6's existing client (MHCLG "Get energy performance of buildings data", https://get-energy-performance-data.communities.gov.uk/). Search by each postcode; all certificates per address, not just the latest.

**API.**

- `GET /api/v1/studio/homes/{ref}/street-proof?radius_m=1000` (`radius_m` 250–2000, default 1000) → `StreetProof`
  - `peer_definition: str` (e.g. "Mid-terrace houses built 1900–1949, gas heated, within 1 km")
  - `peers_count: int`, `band_distribution: list[{band, count}]`, `your_sap: int | None`, `your_percentile: int | None`
  - `improvers_count: int`, `median_sap_gain: int | None`
  - `top_upgrades: list[{label, share_pct, median_sap_gain}]` (≤ 6)
  - `stories: list[{distance_m, from_band, to_band, from_sap, to_sap, year_from, year_to, upgrades: list[str]}]` (≤ 6, distance rounded to 100 m, no address, no house number, no UPRN)
  - `partial: bool`, `evidence`, `fallback_used`

**Algorithm.**

1. Nearest postcodes (≤ 50). For each, EPC search through the existing adapter (cache 30 days), concurrency 5 with `asyncio.Semaphore`, overall budget 12 s; anything not done in time → `partial: true`.
2. Group certificates by UPRN (fallback: normalised address + postcode). Peers: same `property_type` and built form, age band within ±1 band, same main fuel family (mains gas / electric / oil / other).
3. Improvers: peers whose latest certificate's SAP is ≥ 5 points above their earliest.
4. Upgrade inference (Estimated): compare earliest vs latest descriptions with keyword rules in `config.py`: walls "no insulation" → "insulated" = *wall insulation*; roof loft thickness increased = *loft insulation*; windows "single" → "double/triple" = *glazing*; main heating text gains "heat pump" = *heat pump*; "photovoltaic" appears = *solar PV*; low-energy lighting % up ≥ 50 points = *LED lighting*; boiler older → "condensing" = *boiler upgrade*.
5. Privacy: if `peers_count < 5`, return no `stories` and no percentile (k-anonymity), message "Not enough similar homes nearby yet".

**UI.**

- Answer: Fraunces sentence with `NumberTicker` counts.
- Explore: horizontal **beeswarm** of peer SAP scores (dots coloured by EPC band), the user's home as a brass ring with a label; band histogram beneath.
- Story cards carousel: each card animates a band arrow D → B, lists upgrades as chips, shows "about 400 m away · 2019 → 2024".
- Upgrade bars ("Loft insulation, 64% of improvers"), each linking to the measure in S01 or the existing plan page.
- Evidence: EPC ratings = Official modelled ("EPC register (SAP assessment)"); upgrades = Estimated ("Inferred by HRP from certificate changes").

**Build plan.** (1) postcodes.io nearest adapter in Studio; (2) multi-certificate EPC fetch reusing N6 client (add a Studio helper, do not change N6's public function signatures); (3) grouping, peers, improvers, inference with unit tests; (4) route + fallbacks; (5) UI.

**Tests.** Inference rules on hand-written certificate pairs; k < 5 hides stories; responses never contain `uprn`, `address`, or a house number (regex test on the JSON); budget timeout sets `partial`.

**Acceptance.** On a demo home, the page shows a peer count, a beeswarm with the home highlighted, at least one story, and works offline from fallback.

**Contract note.** Reuses N's EPC client read-only; adds one Studio route.

---

## S03 · Meter Fingerprint

**Wow.** Upload the CSV your energy supplier lets you download, and Studio measures your home's **real heat-transfer coefficient**: "Your home loses about 182 W for every degree colder it gets outside. That's better than 60% of homes your age." It is the same idea as the smart-meter "SMETER" methods DESNZ trialled, done in seconds.

**User story.** As a homeowner with a smart meter, I want to know how leaky my home really is, so that I can prove improvements with data rather than a model.

**Differs from the taken 20.** Nothing in the list uses consumption data. This is measured (Observed + Estimated), not an EPC.

**Data sources.**

- The user's daily or half-hourly consumption CSV (any supplier export, e.g. Octopus, British Gas, EDF, or the Bright/Glowmarkt app).
- Open-Meteo Historical Weather API (ERA5): `https://archive-api.open-meteo.com/v1/archive?latitude=..&longitude=..&start_date=..&end_date=..&daily=temperature_2m_mean&timezone=Europe/London` (docs: https://open-meteo.com/en/docs/historical-weather-api; CC BY 4.0, free non-commercial).
- 1991–2020 heating degree days for weather normalisation, from the same API (cache 365 days).

**API.**

- `POST /api/v1/studio/homes/{ref}/meter-fingerprint` multipart: `file` (CSV, ≤ 2 MB), `fuel: Literal["gas","electric_heat_pump","electric_direct"]`, `unit: Literal["kwh","m3"]` → `Fingerprint`
  - `days_used: int`, `period_start: date`, `period_end: date`, `base_temp_c: float`, `baseload_kwh_per_day: float`, `slope_kwh_per_degree_day: float`
  - `htc_w_per_k: int`, `htc_ci_low: int`, `htc_ci_high: int`, `hlp_w_per_m2k: float | None`, `r2: float`
  - `rating: Literal["excellent","good","average","poor"]`, `normalised_annual_heating_kwh: int`
  - `scatter: list[{t_mean_c, kwh}]` (≤ 400 points), `fit: list[{t_mean_c, kwh}]`, `evidence`, `fallback_used`
- `GET /api/v1/studio/homes/{ref}/meter-fingerprint/sample.csv` → a synthetic sample file for demo homes (header comment "SAMPLE DATA"), plus `GET .../meter-fingerprint/sample` → the `Fingerprint` computed from it.
- Validation: not UTF-8 text or no parsable date + number columns → `415 unsupported_file`; > 2 MB → `413 file_too_large`; fewer than 60 days with mean temperature below 12 °C → `400 validation` "We need at least 60 days of winter readings".

**Algorithm.**

1. Parse: sniff delimiter (`,` or `;`), strip BOM, find the timestamp column (first column parsing as date/datetime) and consumption column (first numeric column named like `consumption|kwh|usage|value`). Half-hourly → sum to daily (Europe/London days). `m3` → kWh × 11.1868 (volume correction 1.02264 × calorific value 39.5 MJ/m³ ÷ 3.6; constants in config with source: https://www.gov.uk/guidance/gas-meter-readings-and-bill-calculation, **verify**).
2. Join to ERA5 daily mean temperature.
3. Change-point fit: for `Tb` in 12.0–18.0 step 0.5, least squares `E = a + b·max(0, Tb − T)`. Choose lowest SSE. `b` = kWh per degree day.
4. HTC (W/K) = `b × 1000 / 24 × η`, with η = 0.85 for gas, SCOP 3.0 for heat pump (η = 3.0), 1.0 for direct electric (config). Internal and solar gains are absorbed into `Tb` (standard degree-day practice; say so in the tooltip).
5. 95% interval: 200 bootstrap resamples of days (seeded), 2.5th–97.5th percentile.
6. HLP = HTC / floor area (if known). Rating bands (config, label Estimated): < 1.0 excellent, 1.0–2.0 good, 2.0–3.0 average, > 3.0 poor (W/m²K).
7. Normalised annual heating = `b × HDD_1991–2020(Tb)` ÷ η-adjusted.
8. **Privacy:** the raw file is processed in memory and discarded. Owner homes store only the result in `studio_meter_fingerprints` (`home_id` FK cascade, result JSON, created_at). Demo uploads are never stored.

**UI.**

- Answer: huge Fraunces "182 W/K" with plain sentence and an analogy ("like a 1.8 kW heater running whenever it's 10° colder outside").
- Explore: scatter (temperature vs daily kWh), the fit line drawing itself in with `DrawPath`, the base-temperature knee marked; interval as a soft band.
- A horizontal HLP gauge with the four rating zones and the home's marker; CI as a whisker.
- Drop-zone card: "Download your data from your supplier's app (usually Account → Usage → Export)". Helper links per supplier in config. "Try with sample data" button on demo homes.
- Privacy note under the upload: "We read your file once to measure your home and then delete it."

**Build plan.** (1) parser with fixtures of 4 real-looking formats; (2) ERA5 fetch + cache; (3) fit, bootstrap, HTC; (4) routes, sample generator (synthetic data from a known HTC + noise, seeded); (5) table + migration; (6) UI.

**Tests.** Synthetic data with HTC 200 W/K recovers 190–210; m³ conversion; semicolon + BOM file parses; PNG renamed to `.csv` → 415; < 60 winter days → 400; the raw upload is not written to disk or DB (assert no file created, table holds only result keys).

**Acceptance.** On a demo home, "Try with sample data" shows the scatter, the fitted line and an HTC within the sample's known value ± 5%, offline.

**Contract note.** New Studio upload with its own rules; existing upload rules for certificates are unchanged.

---

## S04 · Heat Pump Year

**Wow.** A full year of a heat pump in this home, simulated hour by hour on last year's real local weather. A 365-day radial calendar sweeps round like a clock, each day coloured by the heat pump's efficiency, and the coldest morning of the year pops out: "On 9 January it was −4 °C at 7 am. Your 8 kW heat pump would have coped."

**User story.** As a homeowner thinking about a heat pump, I want to know what size I'd need, what it would cost to run and whether it would cope in a cold snap, so that I can decide with confidence.

**Differs from the taken 20.** The fabric and overheating planners sequence measures; no listed feature simulates a heating system.

**Data sources.**

- Open-Meteo Historical Weather API, hourly `temperature_2m` for the last full calendar year (https://open-meteo.com/en/docs/historical-weather-api).
- Ofgem energy price cap unit rates and standing charges, current quarter (https://www.ofgem.gov.uk/energy-price-cap, **verify**, store with date).
- Boiler Upgrade Scheme grant amount (https://www.gov.uk/apply-boiler-upgrade-scheme, **verify**).
- DESNZ greenhouse gas conversion factors, gas and grid electricity (https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting, **verify**, latest year).
- Install cost: the heat-pump row of `measures.csv` if present, else a config range with source (MCS data dashboard https://datadashboard.mcscertified.com/, **verify**).

**API.**

- `POST /api/v1/studio/homes/{ref}/heat-pump-year` body `{htc_w_per_k: int | None, flow_temp_c: Literal[35,45,55] = 45, keep_gas_standing_charge: bool = False}` → `HeatPumpYear`
  - `year: int`, `htc_used_w_per_k: int`, `htc_source: Literal["user","estimated_from_age_band"]`
  - `recommended_kw: int`, `scop: float`
  - `annual: {heat_kwh, hp_electricity_kwh, gas_kwh_equivalent, hp_cost_gbp, gas_cost_gbp, saving_gbp, co2_hp_kg, co2_gas_kg}`
  - `monthly: list[{month, heat_kwh, hp_cost_gbp, gas_cost_gbp, cop_mean}]` (12)
  - `daily: list[{date, t_mean_c, heat_kwh, cop_mean}]` (365/366)
  - `coldest_hour: {at, temp_c, demand_kw, hp_capacity_kw, coped: bool}`
  - `bus_grant_gbp: int`, `install_cost_low_gbp: int`, `install_cost_high_gbp: int`, `net_cost_low_gbp: int`, `net_cost_high_gbp: int`
  - `prices: {gas_p_per_kwh, elec_p_per_kwh, gas_standing_p_per_day, elec_standing_p_per_day, as_of: date}`, `evidence`, `fallback_used`

**Algorithm.**

1. HTC: user value (e.g. from S03, typed in) or estimate = HLP(age band) × floor area × form factor. HLP table (W/m²K, config, Estimated, sourced to RdSAP age-band defaults as a rough guide): pre-1900 3.0, 1900–29 2.8, 1930–49 2.6, 1950–66 2.4, 1967–75 2.1, 1976–82 1.8, 1983–90 1.6, 1991–95 1.4, 1996–2002 1.2, 2003–06 1.0, 2007–11 0.9, 2012+ 0.8. Form factor: detached 1.0, semi 0.9, end-terrace 0.9, mid-terrace 0.8, bungalow 1.05, flat 0.7.
2. Hourly demand `Q = HTC × max(0, T_set − T_out − 2)` / 1000 kW, with `T_set` 20 °C 07:00–22:00, 17 °C otherwise (2 K internal gains).
3. COP per hour = `0.45 × T_flow_K / (T_flow_K − T_out_K)`, clipped to [1.5, 5.5]; −10% defrost penalty for −2 °C ≤ T_out ≤ 5 °C.
4. Size: `HTC × (21 − (−2)) / 1000` kW (design outdoor −2 °C, config), round up to [4, 5, 6, 8, 10, 12, 14, 16]. Coldest hour "coped" if demand ≤ capacity.
5. Costs: electricity kWh × elec rate; gas = Q / 0.9 boiler efficiency × gas rate; standing charges per day; gas standing charge saved unless kept. CO2 with DESNZ factors.
6. Cache ERA5 year per rounded lat/lon (0.1°), 365 days.

**UI.**

- Answer: "An 8 kW heat pump would heat your home for about £X a year, £Y less than gas" (or "£Y more" — honesty), with SCOP tile.
- Explore: **radial year** (SVG, 365 wedges around a circle, colour scale from `--s-stone-500` (COP 2) to `--s-green-500` (COP 4.5)); a sweep animation draws it in over 1.2 s; hover a wedge for that day. Coldest hour as a brass callout.
- `Segmented` flow temperature 35/45/55 re-runs the simulation (< 300 ms server); explain "Lower flow temperature = bigger radiators, higher efficiency".
- Monthly bars heat pump vs gas cost; grant and net cost card ("illustrative"); link to the existing plan page.

**Build plan.** (1) ERA5 hourly fetch + cache + fallback for demo coords (gzipped JSON); (2) HTC estimator; (3) simulation core as pure functions with tests; (4) route; (5) radial year component; (6) page.

**Tests.** COP bounds and defrost penalty; constant −2 °C year gives demand = HTC × 21 K exactly; size rounding; price switch; flats get form factor 0.7; offline demo works.

**Acceptance.** For `demo-rural-cottage`, the page shows a size, SCOP between 2.5 and 4, the radial year and the coldest-hour callout, offline.

**Contract note.** One Studio route; reads `measures` read-only.

---

## S05 · Solar Roof Studio

**Wow.** A top-down roof sits under an animated sun path that changes with the season slider. Rotate the compass to match your roof, slide the system size and panels tile onto the roof; an orientation rose shows how much each direction would generate, and a payback line crosses zero in a highlighted year.

**User story.** As a homeowner, I want to see whether solar panels make sense on my roof and when they'd pay back, so that I can decide whether to get quotes.

**Differs from the taken 20.** None of the taken features covers generation.

**Data sources.**

- **PVGIS 5.3** (EU Joint Research Centre) `GET https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=..&lon=..&peakpower=..&loss=14&angle=..&aspect=..&outputformat=json` (docs: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en). Free, no key; aspect 0 = south, 90 = west, −90 = east.
- Smart Export Guarantee guide rate (https://www.ofgem.gov.uk/environmental-and-social-schemes/smart-export-guarantee-seg, **verify**, user can override), import price from Ofgem price cap (**verify**).
- Installed cost per kWp (MCS data dashboard https://datadashboard.mcscertified.com/, **verify**), and the solar row of `measures.csv` if present.
- Self-consumption fractions with and without battery (Energy Saving Trust solar guidance https://energysavingtrust.org.uk/advice/solar-panels/, **verify**).

**API.**

- `POST /api/v1/studio/homes/{ref}/solar` body `{aspect_deg: int (−180..180), pitch_deg: int (0..60), kwp: float | None (0.5..12), battery_kwh: Literal[0,5,10] = 0, export_p_per_kwh: float | None}` → `SolarResult`
  - `kwp: float`, `kwp_source: Literal["user","estimated_from_roof"]`, `annual_kwh: int`, `monthly_kwh: list[int]` (12)
  - `self_use_kwh: int`, `export_kwh: int`, `annual_saving_gbp: int`
  - `install_cost_low_gbp: int`, `install_cost_high_gbp: int`, `payback_years: float | None`, `breakeven_year: int | None`, `lifetime_saving_gbp: int` (25 years, 0.5%/yr degradation)
  - `co2_saved_kg_per_year: int`
  - `orientation_rose: list[{aspect_deg, annual_kwh}]` (8 directions at this pitch and size)
  - `suitability: Literal["good","fair","poor","freeholder_needed"]`, `suitability_note: str`, `evidence`, `fallback_used`

**Algorithm.**

1. Roof estimate when `kwp` is null: footprint = floor area ÷ storeys (2 for houses, 1 for bungalows); one slope = footprint ÷ cos(pitch) ÷ 2; usable 70%; 0.2 kWp/m²; cap 6 kWp. Flats → `freeholder_needed` (no estimate unless the user enters kWp).
2. PVGIS PVcalc for the chosen setup, plus 8 calls for the rose (parallel, cached 365 days by rounded lat/lon + pitch + aspect + 1 kWp, then scaled linearly by kWp).
3. Self-use = annual × fraction (config: 0 kWh battery 0.40, 5 kWh 0.65, 10 kWh 0.75, **verify**). Saving = self-use × import price + export × SEG.
4. Payback = mid cost ÷ saving; breakeven year = current year + ceil(payback).
5. Suitability: annual kWh per kWp ≥ 900 good, 750–900 fair, < 750 poor.

**UI.**

- Roof plan SVG with draggable compass ring; a sun arc (computed client-side with the NOAA solar-position approximation in `features/studio/lib/sun.ts`, vitest-tested) animates across for the selected month.
- kWp slider tiles panels onto the roof (each panel ≈ 0.43 kWp).
- Orientation rose (Recharts RadarChart) with the current aspect highlighted.
- Monthly bars with small sun glyphs; a 25-year cumulative cash line that crosses zero at the breakeven year (brass dot, label "Pays back in 2034").
- Permission hint links to S10 if built, otherwise to Planning Portal solar guidance.

**Build plan.** (1) PVGIS adapter + cache + fallbacks; (2) roof estimator; (3) savings maths; (4) route; (5) sun-path lib with tests; (6) UI.

**Tests.** Aspect conversion and bounds; PVGIS response parsing from a recorded file; flats suitability; rose scaling; payback with zero saving → `null`.

**Acceptance.** On `demo-city-top-flat` the page explains freeholder permission; on `demo-clay-semi` it shows annual kWh, rose and breakeven year, offline.

**Contract note.** One Studio route; reads `measures` read-only.

---

## S06 · Grid Carbon Clock

**Wow.** A 24-hour clock face made of 48 half-hour segments, coloured from deep green (clean) to charcoal (dirty) by your region's live grid forecast. Appliance icons sit on their greenest slot round the ring, and the centre donut shows tonight's generation mix morphing as you hover. "Run your washing machine at 02:30: 64% less carbon than now."

**User story.** As a householder, I want to know when my electricity is cleanest, so that I can cut my carbon by shifting when I use appliances, at no cost.

**Differs from the taken 20.** None of the taken features uses grid data.

**Data sources.**

- **Carbon Intensity API** (NESO with University of Oxford, Environmental Defense Fund), regional 48-hour forecast by outward postcode: `GET https://api.carbonintensity.org.uk/regional/intensity/{from_iso}/fw48h/postcode/{outcode}` and current mix `GET https://api.carbonintensity.org.uk/regional/postcode/{outcode}` (docs: https://carbon-intensity.github.io/api-definitions/). Free, no key, CC BY 4.0.

**API.**

- `GET /api/v1/studio/homes/{ref}/grid-carbon` → `GridCarbon`
  - `region_name: str`, `now: {intensity_g_per_kwh, index: Literal["very low","low","moderate","high","very high"], mix: list[{fuel, percent}]}`
  - `forecast: list[{from_at, to_at, intensity_g_per_kwh, index}]` (96)
  - `best_windows: list[{appliance_id, label, start_at, end_at, avg_intensity_g_per_kwh, saving_pct_vs_now, saving_g}]`
  - `greenest_slot: {from_at, intensity_g_per_kwh}`, `dirtiest_slot: {...}`, `evidence`, `fallback_used`

**Algorithm.**

1. Outcode from the home's postcode. Fetch forecast (cache 15 minutes) and current mix.
2. Appliances in config with energy and duration: washing machine 1.0 kWh / 2 h, dishwasher 1.2 kWh / 2 h, tumble dryer 2.5 kWh / 1.5 h, EV charge 28 kWh / 4 h, immersion 3 kWh / 1 h, heat-pump pre-heat 3 kWh / 2 h.
3. For each, slide a window over the next 24 h of slots, minimise mean intensity; saving vs starting now = (now_mean − best_mean) × kWh.
4. Rounded to half-hours, Europe/London display time.

**UI.**

- The **clock**: SVG ring, 48 arcs, hour ticks, a hand at "now" that moves in real time; arcs fade in clockwise on load.
- Appliance chips orbit to their slot positions with a spring-like ease; tapping a chip shows its window card and an "Add to calendar" button (client-side single-event `.ics`).
- Centre: generation-mix donut (wind, solar, nuclear, gas, imports, biomass, hydro, coal, other) with the current intensity in Fraunces.
- Auto-refresh every 15 minutes while the page is open.
- Evidence: Official modelled ("NESO Carbon Intensity forecast").

**Build plan.** (1) adapter + cache + fallback; (2) window search (pure, tested); (3) route; (4) clock component; (5) page.

**Tests.** Window search on a hand-made series; outcode extraction ("SW1A 1AA" → "SW1A"); Welsh postcode maps to a Wales region in a recorded response; API down → fallback with chip.

**Acceptance.** Any demo home shows the ring, now-hand, mix donut and at least four appliance windows, offline from fallback.

**Contract note.** One Studio route.

---

## S07 · Storm Replay

**Wow.** A cinematic, full-bleed dark stage. Pick a real named event (Storm Eunice, Storm Babet, the July 2022 heatwave) and press play: hour by hour, the weather that actually hit *this location* replays. Wind particles stream at the real gust speed, rain falls at the real rate, a heat shimmer rises with the real temperature, and big Fraunces readouts tick. For heatwaves, a second line shows the estimated temperature inside the home, with and without shading and night ventilation. Studio also ranks the events: "Of the last eight big events, Storm Eunice hit your home hardest."

**User story.** As a homeowner, I want to see how real recent storms and heatwaves affected my exact location, so that climate risk feels real and specific to me.

**Differs from the taken 20.** Observed heat history shows yearly statistics; the storm checklist is a static list. Replay is event-specific, hour-by-hour, with an indoor estimate.

**Data sources.**

- Open-Meteo Historical Weather API (ERA5/ERA5-Land, hourly `temperature_2m`, `wind_gusts_10m`, `wind_speed_10m`, `precipitation`) for each event window ± 1 day (https://open-meteo.com/en/docs/historical-weather-api).
- Event catalogue in `config.py`, each with its Met Office page (https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-storm-centre/index), **verify every date**: Storm Dennis (15–16 Feb 2020), Storm Arwen (26–27 Nov 2021), Storm Eunice (18 Feb 2022), heatwave (18–19 Jul 2022), Storm Babet (18–21 Oct 2023), Storm Ciarán (1–2 Nov 2023), Storm Darragh (6–7 Dec 2024), Storm Éowyn (24 Jan 2025). Add newer named events if the Met Office lists them.

**API.**

- `GET /api/v1/studio/homes/{ref}/storm-replay` → `{events: list[{id, name, kind: Literal["wind","rain","heat"], start_date, end_date, local_peak: {value, unit, at}, severity: float (0–1), headline}], hardest_event_id, evidence, fallback_used}`
- `GET /api/v1/studio/homes/{ref}/storm-replay/{event_id}` → `Replay`
  - `event`, `hourly: list[{at, temp_c, gust_kmh, wind_kmh, rain_mm, indoor_now_c: float | None, indoor_with_measures_c: float | None}]`
  - `peak_moments: list[{at, label}]` (≤ 4), `lessons: list[{text, measure_id: str | None}]` (≤ 4), `evidence`, `fallback_used`

**Algorithm.**

1. Fetch each event window (cache forever; past data does not change).
2. Severity per kind: wind = peak gust ÷ 120 km/h; rain = max 24 h rolling total ÷ 60 mm; heat = (peak temp − 25) ÷ 15; clip 0–1. Hardest = max.
3. Indoor estimate for heat events (Estimated): one-node model `T_in(t+1) = T_in + (Δt/τ)(T_out − T_in) + G(t)`, τ by construction (config: solid masonry 30 h, cavity 18 h, timber/flat 10 h), solar gain `G` 0.6 K/h 10:00–18:00 (×1.5 if top-floor flat). With measures: shading halves `G`; night ventilation (22:00–07:00 when `T_out < T_in`) uses τ/3.
4. Lessons: per kind, map to measure ids present in `measures.csv` by category (`storm`, `flood`, `heat`).

**UI.**

- Event "film strip" of cards with severity bars; the hardest event has a brass "Hit you hardest" stamp.
- Replay stage (`.s-stage`): canvas layer for particles (wind streaks, rain), SVG house silhouette (tree sways with gust, gutter overflows above 4 mm/h), play/pause, scrubber, speed 1×/4×; readouts tick; peak moments appear as timeline flags with captions.
- Heat events: line chart outside vs inside now vs inside with measures, with a 26 °C comfort line.
- After playback: "What would have helped" cards linking to the existing plan page.
- Reduced motion: static peak frame with the chart.

**Build plan.** (1) catalogue + verification log; (2) ERA5 fetch + fallbacks for the 5 demo homes × 8 events; (3) severity + indoor model (pure, tested); (4) routes; (5) stage component with canvas + reduced-motion path; (6) page.

**Tests.** Severity ranking on synthetic series; indoor model step response converges to `T_out` with τ; shading reduces peak; event id not in catalogue → 404; fallback works offline.

**Acceptance.** On `demo-rural-cottage`, the hardest event is a wind event and its replay plays smoothly at 60 fps on a laptop; on `demo-city-top-flat` the July 2022 replay shows indoor with measures below indoor now.

**Contract note.** Two Studio routes.

---

## S08 · Flood Memory

**Wow.** A map where every recorded flood near the home since 1946 appears decade by decade as you press play: pale outlines for the 1940s, deepening to strong blue for recent years. A timeline ribbon below lights up named events. "The nearest recorded flood was 240 m away, in November 2000, from the River Ouse."

**User story.** As a homeowner or buyer, I want to know whether my area has actually flooded before, so that I understand the risk from history, not only from models.

**Differs from the taken 20.** The flood risk card shows modelled zones and live alerts. Flood Memory shows **recorded historical outlines** (Observed).

**Data sources.**

- **EA Recorded Flood Outlines** (Open Government Licence): every recorded flood outline in England since 1946, with name, start and end dates, source and cause. The dataset page lists an **OGC API – Features** resource (https://ckan.publishing.service.gov.uk/dataset/recorded-flood-outlines1; also on https://www.data.gov.uk, search "Recorded Flood Outlines"). Step 1 of the build reads that page, records the live collection URL and attribute names in `docs/decisions/N.md`, and queries with `bbox` (WGS84) and `limit`.
- Wales: Natural Resources Wales "Recorded Flood Extents" (https://datamap.gov.wales/, search "Recorded Flood Extents", OGL). If the service is not reachable, Welsh homes show "Historic records for Wales are coming soon".

**API.**

- `GET /api/v1/studio/homes/{ref}/flood-memory?radius_m=1500` (500–3000) → `FloodMemory`
  - `inside_any_outline: bool`, `nearest_m: int | None`
  - `events: list[{name: str | None, start_date: date | None, end_date: date | None, source: str | None, cause: str | None, distance_m: int, contains_home: bool, decade: int}]` (≤ 50, newest first)
  - `by_decade: list[{decade, count}]`
  - `outlines: dict` (GeoJSON FeatureCollection, ≤ 30 features, each simplified to ≤ 500 vertices, properties `{event_index}`)
  - `caveat: str` ("Not every flood is recorded. No record does not mean no risk.")
  - `evidence`, `fallback_used`

**Algorithm.**

1. bbox from home ± radius (degrees from metres at that latitude). Fetch features (cache 30 days).
2. Point-in-polygon (`studio/common/geo.py`, ray casting, holes and MultiPolygons supported) → `contains_home`.
3. Distance: 0 if inside, else minimum haversine distance to polygon edges (point-to-segment on an equirectangular projection around the home; accurate to metres at these scales).
4. Simplify with Douglas–Peucker (tolerance from config) keeping rings closed.
5. Merge outlines that share the same event name and dates.

**UI.**

- Answer card with a calm headline and the caveat in the same card (never hidden).
- Map (React-Leaflet): home pin in brass, outlines coloured by decade (sequential blue ramp), a decade slider with a play button that reveals them in order (`DrawPath` on outlines).
- Timeline ribbon 1946 → today with event dots; hover links to the outline on the map.
- "What to do" links to the existing plan's flood measures and the EA "Sign up for flood warnings" page (https://www.gov.uk/sign-up-for-flood-warnings).

**Build plan.** (1) read dataset page, log URL and fields; (2) geo helpers with tests; (3) adapter + cache + fallbacks; (4) route; (5) map + timeline UI.

**Tests.** Point-in-polygon with holes and MultiPolygon; distance zero inside; simplification keeps first = last; decade grouping; empty result → `events: []`, `inside_any_outline: false`; fallback offline.

**Acceptance.** `demo-flood-terrace` shows at least one recorded event with distance, animated decades and the caveat, offline.

**Contract note.** One Studio route; does not change the RoFRS-based `rofrs_band` or the risk card.

---

## S09 · Shoreline Watch

**Wow.** For coastal homes, a map with a soft animated "tide line" that moves inland from today to 2055 to 2105 as you drag the slider, with toggles for the shoreline management scenario and climate allowance. Inland homes get a graceful answer in one line: "You're 41 km from the coast. Coastal erosion isn't a factor for your home."

**User story.** As a coastal homeowner or buyer, I want to see how far the coastline is projected to retreat near my home, so that I can plan long term and know where to get advice.

**Differs from the taken 20.** None of the taken features covers coastal erosion (it is in the spec's M2 backlog, item 4).

**Data sources.**

- **EA National Coastal Erosion Risk Mapping (NCERM) – National (2024)**, OGL: https://www.data.gov.uk/dataset/national-coastal-erosion-risk-mapping-ncerm-national-2024 . Projections for 2055 and 2105, with and without shoreline management plan (SMP) policy, and climate change allowances. Step 1 reads the dataset page and metadata, records the service URL (OGC API/WFS) and attribute meanings in `docs/decisions/N.md`.
- Wales: NRW NCERM (https://metadata.naturalresources.wales/geonetwork/srv/api/records/NRW_DS121852).
- Signposting: GOV.UK "Check coastal erosion management in your area" (https://www.gov.uk/check-coastal-erosion-management-in-your-area, **verify** URL).

**API.**

- `GET /api/v1/studio/homes/{ref}/shoreline` → `Shoreline`
  - `coastal: bool` (any NCERM feature within 5 km), `nearest_coast_m: int | None`
  - `projections: list[{epoch: Literal[2055, 2105], scenario: Literal["with_smp","no_active_intervention"], climate: str, home_inside_zone: bool, distance_m: int | None}]`
  - `smp_policy: str | None`, `features: dict` (GeoJSON, simplified, ≤ 40 features, properties `{epoch, scenario, climate}`)
  - `advice_links: list[{label, url}]`, `evidence` (Official modelled, "EA NCERM 2024"), `fallback_used`

**Algorithm.** bbox query 5 km; if empty → `coastal: false` and the inland distance from a precomputed coarse coastline (Natural Earth 1:10m coastline, public domain, committed as a small simplified GeoJSON in `studio/data/`, https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-coastline/). Otherwise point-in-polygon per projection zone and distance as in S08. Cache 90 days.

**UI.**

- Coastal: map with zones per epoch, a slider `Today → 2055 → 2105` that cross-fades zones and moves a wave-pattern edge; segmented toggles for scenario and climate; a calm "What this means" card (insurance note: erosion is generally not covered by standard home insurance or Flood Re, **verify** wording with Flood Re's site https://www.floodre.co.uk/); advice links.
- Inland: elegant empty state with a small UK silhouette and the distance.

**Build plan.** (1) dataset reading + log; (2) coastline file + distance; (3) adapter + fallbacks (the `coastal-bungalow` demo home is the hero case); (4) route; (5) UI.

**Tests.** Inland home returns `coastal: false` with a distance; recorded coastal response parses into projections; GeoJSON simplification; offline.

**Acceptance.** `demo-coastal-bungalow` shows zones and the slider; `demo-city-top-flat` shows the inland state, both offline.

**Contract note.** One Studio route.

---

## S10 · Permission Radar

**Wow.** A radar sweep rotates over the home; as it passes, "blips" appear for each planning constraint found at the address (conservation area, listed building, Article 4 direction, tree preservation order, national landscape). Then a traffic-light matrix tells you, for each upgrade in your plan, whether it is likely permitted development, needs a check with the council, or needs consent, with the reason and the official link.

**User story.** As a homeowner, I want to know which upgrades need planning permission at my address before I get quotes, so that I don't waste money or break rules.

**Differs from the taken 20.** Renters' mode deals with landlord permission. Permission Radar deals with **planning law** constraints on the property.

**Data sources.**

- **Planning Data platform** (MHCLG), API docs https://www.planning.data.gov.uk/docs : `GET https://www.planning.data.gov.uk/entity.json?latitude=..&longitude=..&dataset=<name>&limit=..` for area datasets (`conservation-area`, `article-4-direction-area`, `listed-building-outline`, `tree-preservation-zone`, `world-heritage-site`, `area-of-outstanding-natural-beauty`, `national-park`), and a 25 m geometry query for `listed-building` points (read the docs for the geometry parameter). Free, no key. Coverage depends on which councils have published; step 1 finds how the API signals coverage (dataset/organisation provision endpoints) and logs it.
- Permitted development rules summarised from the Planning Portal (https://www.planningportal.co.uk/permission/common-projects) and the GPDO 2015 Schedule 2 (https://www.legislation.gov.uk/uksi/2015/596/schedule/2). **Verify** the heat-pump rules, which changed in 2025, and log the date read.

**API.**

- `GET /api/v1/studio/homes/{ref}/permission-radar` → `PermissionRadar`
  - `local_planning_authority: str | None`
  - `constraints: list[{dataset, label, name: str | None, reference: str | None, entity_url: str | None, applies: bool | None}]` (`null` = council hasn't published this dataset)
  - `measures: list[{measure_id, name, verdict: Literal["likely_permitted","check_council","consent_needed","not_applicable"], reasons: list[str], guidance_url}]`
  - `disclaimer: str` ("Indicative only, not legal advice. Check with your council before work starts.")
  - `evidence` (constraints Observed: "Planning Data platform"; verdicts Estimated: "HRP rules based on Planning Portal guidance"), `fallback_used`

**Algorithm.** A rules table in `config.py`, one rule per measure family (matched by measure id keywords as in S01), evaluated top-down, first match wins:

1. Flat → no householder permitted development rights for external works: external measures `check_council` ("Flats don't have householder permitted development rights; also ask your freeholder"). Internal measures `likely_permitted`.
2. Listed building → any external change and most internal works `consent_needed` ("Listed building consent").
3. Article 4 direction present → windows, doors, roofing, solar on front elevation `check_council`.
4. Conservation area (article 2(3) land) → external wall insulation/cladding `check_council`; solar on a wall fronting a highway `check_council`; roof solar `likely_permitted`; heat pump on a wall fronting a highway `check_council`.
5. Tree preservation (order or zone) → measures involving tree works `consent_needed`.
6. Front-garden hard surfaces over 5 m² must be permeable or drain to a permeable area (Class F) → permeable paving `likely_permitted`, impermeable replacement `check_council`.
7. Otherwise `likely_permitted` with the PD conditions in `reasons` (≤ 3 short lines).

- If the constraints call fails, every `applies` is `null` and external measures default to `check_council` (safe default, spec §13 rule 5).

**UI.**

- Radar: SVG concentric rings and a rotating conic-gradient sweep (2.4 s); blips fade in at fixed angles with labels; a mini map shows any conservation area outline.
- Matrix: rows = measures, a single coloured pill with icon + word ("Likely fine", "Check with council", "Consent needed"); rows expand to reasons and the official link; council name with a link to its planning page (from `postcodes.io` admin district → GOV.UK "Find your local council" https://www.gov.uk/find-local-council).
- Disclaimer always visible under the matrix.

**Build plan.** (1) read API docs, log params and coverage method; (2) adapter for each dataset in parallel + cache 30 days + fallbacks; (3) rules engine (pure, table-driven, tested); (4) route; (5) radar + matrix UI.

**Tests.** Rule table: listed → windows `consent_needed`; conservation → wall insulation `check_council`; flat → external `check_council`; API down → all `null` + safe defaults; every measure in `measures.csv` gets a verdict.

**Acceptance.** On every demo home the radar animates, the matrix lists every plan measure with a verdict, reasons and link, offline from fallback.

**Contract note.** One Studio route.

---

## S11 · Damp & Mould Lab

**Wow.** A wall cross-section diagram glows from warm inside to cold outside, with a dew-point line that crosses into the wall when condensation is likely. Studio replays last winter hour by hour on the home's real weather and fabric, then shows how many hours the wall, the cold corner and the window glass sat in the mould zone. Toggle "extractor fans", "dry clothes outside", "insulate walls" and watch the risk fall.

**User story.** As a household (especially renters and social tenants), I want to understand why my home gets damp and what fixes it, so that I can act and, if needed, show my landlord evidence.

**Differs from the taken 20.** The fabric-first planner says "check moisture before insulating"; this lab quantifies condensation risk with building physics. It does not write a landlord letter (that is renters' mode).

**Data sources.**

- The home's EPC fabric descriptions (walls, windows, construction age) via existing `PropertyFacts` and the EPC adapter's raw record where available.
- Open-Meteo Historical Weather API, hourly `temperature_2m` and `relative_humidity_2m` for last winter (1 Nov–31 Mar).
- Method: BS EN ISO 13788 surface-humidity criterion (mould when surface RH ≥ 80%) and internal humidity classes; BRE IP 1/06 temperature factor fRsi (summaries: https://www.bregroup.com/ and https://www.thenbs.com/ , **verify** constants). U-value defaults from RdSAP 10 tables (https://bregroup.com/sap/sap10, **verify**).
- Social housing context: Awaab's Law guidance on GOV.UK (https://www.gov.uk/government/collections/awaabs-law, **verify** current URL and dates).

**API.**

- `POST /api/v1/studio/homes/{ref}/damp-lab` body `{occupants: int (1–10), dries_clothes_indoors: bool, kitchen_extractor: bool, bathroom_extractor: bool, trickle_vents: bool, heating_setpoint_c: float = 18}` → `DampLab`
  - `winter: str` ("2025–26"), `wall_u: float`, `window_u: float`, `wall_u_source: Literal["epc_description","age_band_default"]`
  - `moisture_class: Literal[1,2,3,4]`
  - `surfaces: list[{surface: Literal["wall","corner","window"], risk_hours_pct: float, level: Level}]`
  - `monthly: list[{month, corner_risk_pct}]`
  - `interventions: list[{id, label, corner_risk_pct_after, delta_pct}]` (sorted by impact)
  - `landlord_note: str | None` (only when the owner home's tenure is `social_renter` or `private_renter`; plain duty summary and link; never shows tenure in a public response)
  - `evidence` (Estimated), `fallback_used`
- Owner homes: the last answers are saved in `studio_damp_answers` (`home_id` FK cascade). They are not sensitive, but include them in the user export.

**Algorithm.**

1. U-values from EPC description keywords (config): solid brick uninsulated 2.1, cavity unfilled 1.5, cavity filled 0.55, timber frame 0.45, "insulated" solid/system 0.35; windows single 4.8, double 2.8, triple 1.6; else age-band defaults.
2. fRsi = 1 − U × Rsi, Rsi = 0.25 m²K/W (ISO 13788 for mould); corner fRsi = wall fRsi − 0.10 (thermal bridge, config); window surface uses Rsi 0.13 and condensation at 100% RH.
3. Surface temp θsi = θe + fRsi × (θi − θe), θi = setpoint.
4. Moisture class: base 2; +1 if occupants ≥ 4 or dries clothes indoors; +1 if no bathroom or kitchen extractor; −1 if both extractors and trickle vents; clip 1–4. Excess vapour pressure Δp at θe ≤ 0 °C: class 1 270, 2 540, 3 810, 4 1080 Pa, falling linearly to 0 at θe = 20 °C.
5. p_e = RH_e × p_sat(θe) (Magnus formula), p_i = p_e + Δp, surface RH = p_i ÷ p_sat(θsi). Risk hour if ≥ 0.80 (window ≥ 1.0).
6. Levels: < 5% low, 5–20% medium, > 20% high. Interventions re-run with one change each: extractors (class −1), dry outside (class −1), +1 °C heating, wall insulation (U 0.3), double glazing (if single).

**UI.**

- Cross-section SVG: inside → plaster → wall → outside, a temperature gradient fill and a dashed dew-point line; condensation droplets appear on the inner surface when risk is high; animates as toggles change.
- Three surface gauges (wall, corner, window) with words and colours; monthly bars for the corner.
- Intervention ladder with checkboxes; each toggle re-POSTs (fast) and shows the new numbers with `NumberTicker`.
- Supportive tone: "Damp is common and fixable. Most of it comes from moisture we make inside." Landlord note only on owner homes with a renter tenure.

**Build plan.** (1) physics core (pure, tested: Magnus, fRsi, classes); (2) U-value parser over real EPC descriptions; (3) ERA5 winter fetch + cache + fallbacks; (4) route + table + export; (5) UI.

**Tests.** Magnus p_sat(0 °C) ≈ 611 Pa and p_sat(20 °C) ≈ 2339 Pa; U 2.1 solid wall, class 3, a 0 °C / 90% RH hour → corner risk true; double glazing reduces window risk; landlord note absent on demo and owner-occupier homes.

**Acceptance.** `demo-flood-terrace` (older solid wall) shows medium or high corner risk and at least three interventions that reduce it, offline.

**Contract note.** One Studio route, one table; `household.tenure` is read server-side only to decide whether to show a note and never returned.

---

## S12 · Breathe Easy

**Wow.** A flowing 72-hour "air ribbon" that breathes slowly on the page: green when outdoor air is clean, cool and dry; plum when it's polluted or full of pollen. Little window icons open and close along it. "Best time to air the house today: 06:00–09:00. Keep windows shut 16:00–19:00 (high pollen)."

**User story.** As a household, I want to know when to open the windows for fresh air or cooling without letting in pollution or pollen, so that my home stays healthy.

**Differs from the taken 20.** The overheating planner mentions night ventilation in general; Breathe Easy uses live air-quality and pollen forecasts to time it.

**Data sources.**

- **Open-Meteo Air Quality API** (Copernicus CAMS European model), hourly `pm2_5`, `pm10`, `nitrogen_dioxide`, `ozone`, `grass_pollen`, `birch_pollen`, `alder_pollen`: `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=..&longitude=..&hourly=..&forecast_days=3&timezone=Europe/London` (docs https://open-meteo.com/en/docs/air-quality-api). Pollen is seasonal and may be `null`.
- Open-Meteo Forecast API, hourly `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `wind_speed_10m` (https://open-meteo.com/en/docs).
- DEFRA Daily Air Quality Index bands (https://uk-air.defra.gov.uk/air-pollution/daqi?view=more-info, **verify** thresholds).

**API.**

- `POST /api/v1/studio/homes/{ref}/breathe-easy` body `{pollen_sensitive: bool = False, pollution_sensitive: bool = False}` (sent as a body so it never appears in URLs or logs; **not stored**) → `BreatheEasy`
  - `hours: list[{at, daqi: int | None, daqi_band: Literal["low","moderate","high","very_high"] | None, pm2_5, no2, o3, pollen_level: Literal["none","low","moderate","high"] | None, temp_c, rh_pct, score: int (0–100), advice: Literal["open","brief_airing","keep_closed"]}]` (72)
  - `best_windows: list[{start_at, end_at, reason}]`, `avoid_windows: list[{start_at, end_at, reason}]`
  - `today_summary: str`, `evidence` (Official modelled for AQ and weather; Estimated for scores), `fallback_used`

**Algorithm.**

1. DAQI per hour: banding of each pollutant per the DEFRA table (hourly concentrations as a proxy; say so in the tooltip), DAQI = max sub-index.
2. Score 100, minus: DAQI 4–6 −30, 7–9 −60, 10 −90 (doubled weight if `pollution_sensitive`); pollen moderate −20 / high −40 (doubled if `pollen_sensitive`); in summer months, + up to 20 when outdoor temp is ≥ 2 °C below 22 °C after 18:00 (cooling benefit); in winter, + 10 for a midday hour with outdoor dew point below 5 °C (drying air, brief airing only).
3. Advice: ≥ 70 open (summer) / brief airing (winter), 40–69 brief airing, < 40 keep closed. Windows = contiguous runs ≥ 2 h.
4. Cache 1 hour.

**UI.**

- The ribbon: an SVG path whose fill gradient is built from hourly scores (green → stone → plum), with a slow 6 s "breathing" scale animation (disabled with reduced motion); day dividers; window glyphs at best and avoid windows.
- Two sensitivity toggles (explained as "only used to tune advice right now, never saved").
- Cards: today's summary, pollutant mini sparklines, pollen petals.

**Build plan.** (1) two adapters + cache + fallbacks; (2) DAQI + scoring (pure, tested); (3) route; (4) ribbon UI.

**Tests.** DAQI banding against the DEFRA table; null pollen → none; sensitivity changes scores; request body not logged (log capture test); offline.

**Acceptance.** Any demo home shows the 72-hour ribbon with at least one best window, offline.

**Contract note.** One Studio route; health-related flags are used once and never stored or logged (CONTRACT.md §6 spirit).

---

## S13 · Affordability Stress Test

**Wow.** Banks stress-test mortgages; Studio stress-tests the home's energy bill. Four elegant horizontal "thermometers" show the annual bill under today's price cap, a return of the winter 2022–23 peak, a +30% shock, and pre-crisis prices, with a line at 10% of household income. Toggle "with my plan" and every bar shrinks.

**User story.** As a household on a budget, I want to see how exposed my bills are to price shocks and how much my plan would protect me, so that I can prioritise measures that make my home affordable to run.

**Differs from the taken 20.** Funding concierge finds money for measures; the budget ladder groups measures by cost. Neither tests bill resilience.

**Data sources.**

- EPC certificate energy fields via the existing adapter: `energy-consumption-current` (kWh/m²/yr), `heating-cost-current`, `hot-water-cost-current`, `lighting-cost-current` and their `-potential` values (field names **verify** in the current API).
- Ofgem price cap: current and historical unit rates and standing charges (https://www.ofgem.gov.uk/energy-price-cap, **verify**, stored in `studio/data/price_cap.csv` with `period_start, gas_p_per_kwh, elec_p_per_kwh, gas_standing_p_per_day, elec_standing_p_per_day, source_url`). The 2022–23 peak uses the Energy Price Guarantee rates actually paid (https://www.gov.uk/government/publications/energy-bills-support/energy-bills-support-factsheet-8-september-2022, **verify**).
- Fuel poverty context: England LILEE definition (https://www.gov.uk/government/collections/fuel-poverty-statistics) and the 10% definition used in Wales (https://www.gov.wales/fuel-poverty, **verify**).
- Measures' `annual_bill_saving_gbp` from `measures.csv`.

**API.**

- `GET /api/v1/studio/homes/{ref}/affordability?measure_ids=a,b,c` → `Affordability`
  - `kwh: {heating_fuel: int, electricity: int}`, `kwh_source: Literal["epc_certificate","estimated"]`, `heating_fuel: Literal["gas","electric","oil","lpg","other"]`
  - `scenarios: list[{id: Literal["today","peak_2022","shock_30","pre_crisis_2021"], label, annual_cost_gbp, annual_cost_after_gbp, pct_income: float | None, pct_income_after: float | None, above_10pct: bool | None, above_10pct_after: bool | None}]`
  - `lilee_indicator: bool | None` (EPC band D–G **and** income band `under_20k`; owner homes only)
  - `help_links: list[{label, url}]` (Citizens Advice energy, Warm Home Discount, Simple Energy Advice, Lloyds-style "talk to us if you're worried" marked illustrative)
  - `evidence`, `fallback_used`
- `pct_income*` and `lilee_indicator` are computed from the household income band midpoint (config) **only for owner homes**, are `null` for demo and public use, and income is never logged.

**Algorithm.**

1. kWh: `energy-consumption-current × floor area`; split into heating fuel vs electricity by main fuel (electric heating → all electricity); else estimated from age band and floor area (config), `kwh_source: "estimated"`.
2. Cost per scenario = Σ kWh × unit rate + 365 × standing charges; `shock_30` = today × 1.3. Oil/LPG use a config price with source (**verify**, e.g. DESNZ quarterly energy prices).
3. After plan = cost − Σ `annual_bill_saving_gbp` scaled by the scenario's price ratio to today (savings grow with prices), floor at standing charges.

**UI.**

- Four thermometers (horizontal bars in `--s-green-700`, a dashed brass line at 10% of income when known), each with Fraunces £ figure and a delta chip when "with my plan" is on (bars animate shorter).
- Measure picker defaults to the user's saved plan selection if there is one (existing `GET /homes/{id}/passport` plan), otherwise the top 3 plan items.
- Reassuring help card with links. Never shows a judgement word like "unaffordable"; says "Above 10% of income: help may be available".

**Build plan.** (1) price-cap CSV with sources; (2) EPC energy-field mapping (reuse adapter raw record); (3) scenario maths (pure, tested); (4) route; (5) UI.

**Tests.** Scenario maths on known numbers; savings scaling; income fields `null` for demo refs; income band never in logs (log capture); offline.

**Acceptance.** `demo-coastal-bungalow` shows four scenarios and shrinking bars with the plan toggled, offline.

**Contract note.** One Studio route; reads `household` server-side for owner homes only and returns only derived percentages to the owner.

---

## S14 · Green Value Lens

**Wow.** Every sale of a similar home nearby in the last five years appears as a dot on a timeline; press "Index to today" and the dots glide up to today's prices using the official House Price Index, settling into a confident range. Then a waterfall shows the potential value of moving from EPC D to B, sourced to published research and set against the plan's cost.

**User story.** As a homeowner, I want to understand what homes like mine sell for and whether upgrades could add value, so that I can see improvements as an investment.

**Differs from the taken 20.** None covers property value. This is not a valuation and never shows a "climate discount" (fairness: no climate penalty).

**Data sources.**

- **HM Land Registry Price Paid Data** (OGL, linked data API): `https://landregistry.data.gov.uk/data/ppi/transaction-record.json?propertyAddress.postcode=<POSTCODE>&_pageSize=200` (docs https://landregistry.data.gov.uk/app/doc/ppd ; SPARQL console https://landregistry.data.gov.uk/app/qonsole). **Verify** query params.
- **UK House Price Index** by local authority and property type (https://landregistry.data.gov.uk/app/ukhpi ; data downloads https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads, **verify**).
- Nearest postcodes via postcodes.io (as S02).
- Green premium research, stored in `studio/data/green_premium.csv` with `study, url, year, pct_per_band_step_low, pct_per_band_step_high`: e.g. Nationwide's EPC price analysis (https://www.nationwidehousepriceindex.co.uk/, search "energy efficiency"), Knight Frank and Rightmove green homes reports. cc reads each source and enters only the figures it actually states (**verify**); at least two sources.

**API.**

- `GET /api/v1/studio/homes/{ref}/green-value?target_band=B` → `GreenValue`
  - `comparables_count: int`, `method: Literal["comparables","hpi_average"]`
  - `indexed_median_gbp: int`, `range_low_gbp: int`, `range_high_gbp: int` (interquartile range, rounded to £1,000)
  - `comps: list[{month: "YYYY-MM", price_gbp, indexed_gbp, property_type, distance_m}]` (≤ 60; no address, no house number, no full postcode)
  - `current_band: str | None`, `target_band: str`, `uplift_low_gbp: int | None`, `uplift_high_gbp: int | None`, `plan_cost_low_gbp: int | None`, `plan_cost_high_gbp: int | None`
  - `premium_sources: list[{study, url, year, pct_low, pct_high}]`
  - `disclaimer: str` ("Not a valuation. Lenders use a professional valuation.")
  - `evidence` (sales Observed, HPI Official statistics → `official_modelled`, uplift Estimated), `fallback_used`

**Algorithm.**

1. Nearest ~30 postcodes within 1 km; fetch PPD per postcode (cache 30 days), last 5 years, same PPD property type (D/S/T/F mapped from `property_type`), standard price paid category A only.
2. Index each price: `price × HPI(LA, type, latest) / HPI(LA, type, sale month)`.
3. If ≥ 5 comps → median and IQR; else LA average price for the type from HPI, `method: "hpi_average"`.
4. Uplift: band steps from current to target (0 if target ≤ current) × [min low, max high] premium per step across sources × indexed median. Never compute a negative.
5. Plan cost: from the existing plan for owner homes, or the top plan items for demos.

**UI.**

- Dot plot over time (Recharts ScatterChart), "Index to today" button animates each dot to its indexed value (Web Animations on SVG circles), then a soft band for the range.
- EPC arrow selector A–G in certificate colours for the target band.
- Waterfall: today's range → potential uplift (range bar) next to plan cost; a "value-to-cost" sentence when uplift ≥ cost, otherwise "Upgrades pay back mainly through lower bills" (honest).
- Disclaimer and sources always visible.

**Build plan.** (1) PPD adapter (verify params) + cache + fallbacks; (2) HPI series loader (cache 30 days); (3) indexing and range maths (pure, tested); (4) premium CSV with verified sources; (5) route; (6) UI.

**Tests.** Indexing maths; < 5 comps → HPI method; response JSON contains no house numbers or full postcodes (regex); uplift never negative; target ≤ current → 0.

**Acceptance.** `demo-clay-semi` shows dots, indexing animation, range and an uplift with at least two cited studies, offline.

**Contract note.** One Studio route.

---

## S15 · Net Zero Road

**Wow.** The home's carbon from 2025 to 2050 drawn as a winding road. Each upgrade is a signpost you drag to the year you plan to do it (loft 2026, heat pump 2030, solar 2032). The area chart beneath reshapes as you move them, a small home icon travels the road as you scroll, and the moment the home reaches near-zero gets a brass milestone: "Near zero by 2033. 41 tonnes saved by 2050."

**User story.** As a homeowner, I want to see how my home's emissions fall over time as the grid gets cleaner and as I make upgrades, so that I can plan a realistic path to net zero.

**Differs from the taken 20.** The planners rank and cost measures today; nothing shows a year-by-year emissions path with grid decarbonisation.

**Data sources.**

- **DESNZ "Valuation of energy use and greenhouse gas emissions for appraisal"** data tables: projected long-run grid electricity emission factors by year (https://www.gov.uk/government/publications/valuation-of-energy-use-and-greenhouse-gas-emissions-for-appraisal, **verify** table and series name: domestic, consumption-based). cc extracts year → kg CO2e/kWh into `studio/data/grid_factors.csv` with source URL.
- DESNZ GHG conversion factors for natural gas, oil and LPG (https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting, **verify**).
- Climate Change Committee, Seventh Carbon Budget (Feb 2025), residential buildings pathway (https://www.theccc.org.uk/publication/the-seventh-carbon-budget/, **verify**): an index of residential emissions vs 2025, stored in `studio/data/ccc_pathway.csv`.
- EPC energy fields (as S13) and `measures.csv` (`co2_saved_kg_per_year`, category).

**API.**

- `POST /api/v1/studio/homes/{ref}/net-zero-road` body `{steps: list[{measure_id: str, year: int (2025–2050)}]}` (≤ 12) → `NetZeroRoad`
  - `years: list[{year, co2_kg_do_nothing, co2_kg_with_plan, pathway_kg}]` (2025–2050)
  - `cumulative_saved_kg: int`, `near_zero_year: int | None` (first year < 500 kg), `default_steps: list[{measure_id, year}]` (suggested spacing of the top plan items), `evidence`, `fallback_used`

**Algorithm.**

1. Base kWh by fuel (as S13). Do nothing: fuel kWh × fuel factor (constant) + electricity kWh × grid factor(year).
2. With plan: apply each measure from its year. Heat-pump measures convert heating fuel kWh to electricity at SCOP 3.0 (config). Solar measures reduce electricity kWh by an estimate (config: 850 kWh per kWp × 3 kWp default, self-use 40%). Other measures subtract their `co2_saved_kg_per_year`, scaled by the fuel/grid factor ratio for electricity-saving measures.
3. Pathway: base-year emissions × CCC residential index.

**UI.**

- The road: an SVG path that winds across the page, with year markers; measure signposts are draggable along it (snap to years), with a keyboard alternative (select + arrow keys).
- Area chart under the road (do nothing in `--s-stone-500`, with plan in `--s-green-500`, CCC pathway dashed).
- Scroll-linked home icon (CSS `animation-timeline: view()` where supported, IntersectionObserver fallback).
- Milestone stamp at the near-zero year; totals with `NumberTicker`.

**Build plan.** (1) extract and commit the two CSVs with sources; (2) pathway maths (pure, tested); (3) route with default steps; (4) road + drag UI; (5) chart.

**Tests.** Grid-factor interpolation between published years; heat-pump conversion lowers emissions once grid factor < gas factor ÷ SCOP; years outside 2025–2050 → 400; unknown measure → 400.

**Acceptance.** `demo-rural-cottage` (oil) shows a steep fall when the heat pump signpost is placed, and moving it later delays the near-zero year.

**Contract note.** One Studio route.

---

## S16 · Week Ahead

**Wow.** Seven beautifully drawn day cards in a horizontal rail, each with a thin-line weather glyph that moves gently (rain lines fall, the sun turns slowly). Days that matter for *this* home carry a badge: "Thursday: gusts 75 km/h. Tie down the trampoline, park away from the oak." Tap a day to get a tick-off checklist; add the actions to your calendar.

**User story.** As a householder, I want this week's forecast turned into simple jobs for my home, so that I'm ready before the weather arrives.

**Differs from the taken 20.** Live flood alert mode reacts to EA warnings; the storm checklist is static. Week Ahead turns the next seven days of the Met Office model into home-specific actions across frost, heat, wind and rain.

**Data sources.**

- **Open-Meteo Forecast API with the UK Met Office model** (`models=ukmo_seamless`): daily `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `wind_gusts_10m_max`, `uv_index_max`, hourly `temperature_2m` (https://open-meteo.com/en/docs/ukmo-api, **verify** model name and available variables; fall back to `best_match` if a variable is missing).
- The home's `PropertyFacts` and latest `RiskProfile` (existing).

**API.**

- `GET /api/v1/studio/homes/{ref}/week-ahead` → `WeekAhead`
  - `issued_at`, `model: str`, `headline: str`
  - `days: list[{date, t_max_c, t_min_c, rain_mm, gust_kmh, uv_index, glyph: Literal["sun","cloud","rain","heavy_rain","wind","frost","snow","storm"], alerts: list[{kind: Literal["frost","hard_frost","heat","wind","strong_wind","heavy_rain"], level: Level, title, actions: list[str], when: str}]}]` (7)
  - `evidence` (Official modelled: "Met Office UKV via Open-Meteo"), `fallback_used`

**Algorithm.** Rules in `config.py`, each with thresholds and actions, tailored by property and risk:

- frost (min ≤ 0 °C): lag outside taps, frost setting on heating; hard frost (≤ −3 °C): also open loft hatch for pipes, check elderly neighbours (generic, no profiling).
- heat (max ≥ 27 °C; ≥ 30 °C high): close blinds on sunny sides by 10:00, open windows after 21:00 when cooler; top-floor flats get high level at ≥ 27 °C.
- wind (gust ≥ 60 km/h; ≥ 80 high): secure bins, trampoline, garden furniture; rural or storm-high homes get high level at ≥ 60.
- heavy rain (≥ 15 mm; ≥ 30 high): clear gutters and drains; homes with `river_sea_flood` medium/high add "check EA flood warnings" link and move valuables upstairs only if a warning is issued.
- Cache 1 hour.

**UI.**

- Rail of 7 cards (scroll-snap on mobile), custom SVG glyphs with subtle CSS animation; alert badges with level colours and words.
- Day sheet (shadcn Dialog): actions as checkboxes (state in `localStorage`, keyed by home + date), "Add to calendar" (client `.ics` with one event per alert).
- Headline sentence for the week.

**Build plan.** (1) adapter + cache + fallbacks; (2) rules engine (pure, tested); (3) route; (4) glyph set; (5) UI.

**Tests.** Thresholds at boundaries; tailoring for top-floor flat and flood-risk home; missing variable → `null` and rule skipped; offline.

**Acceptance.** All demo homes show 7 days; a recorded windy week gives `demo-rural-cottage` a high wind alert.

**Contract note.** One Studio route.

---

## S17 · Home Care Calendar

**Wow.** A seasonal wheel of the year with care tasks placed around it, timed to *your* local climate: "Your average first frost is 9 November, so lag the outside tap by 26 October." One tap subscribes your phone's calendar to a private feed that updates itself when you record new work.

**User story.** As a homeowner, I want a simple yearly maintenance plan that matches my home and local weather, so that small jobs prevent big repairs.

**Differs from the taken 20.** The storm checklist is a one-off list for storms. This is a year-round, climate-timed schedule with a calendar feed.

**Data sources.**

- Open-Meteo Historical Weather API, daily `temperature_2m_min`, `precipitation_sum`, `wind_gusts_10m_max`, 1991–2020, for local climatology (cache 365 days).
- Home facts: heating fuel and system (boiler, heat pump, oil tank), property type, hazards, and completed measures from passport work records (existing).
- Task library in `studio/data/care_tasks.json` with a guidance URL per task (e.g. gutters and drains: https://www.gov.uk/government/publications/prepare-your-property-for-flooding ; boiler service: https://www.gassaferegister.co.uk/ ; heat pump care: https://energysavingtrust.org.uk/advice/air-source-heat-pumps/ ; **verify** each).

**API.**

- `GET /api/v1/studio/homes/{ref}/care-calendar` → `CareCalendar`
  - `climate: {first_frost_avg: "MM-DD" | None, last_frost_avg: "MM-DD" | None, wettest_month: int, windiest_month: int}`
  - `months: list[{month: int, tasks: list[{id, title, why, effort_minutes, hazard: str | None, guidance_url}]}]` (12, starting next month)
  - `evidence`, `fallback_used`
- `GET /api/v1/studio/homes/{ref}/care-calendar.ics` → `text/calendar` download (yearly recurring all-day events with a reminder)
- `POST /api/v1/studio/homes/{ref}/care-calendar/subscribe` (owner only) → `{url}`; `DELETE` same path → `204` (revokes)
- `GET /api/v1/studio/ical/{token}.ics` (public, token = `secrets.token_urlsafe(24)`) → feed. **The feed contains no address, postcode or name**, only task titles. Table `studio_calendar_tokens` (`home_id` FK cascade, token, created_at); include in user export.

**Algorithm.**

1. Climatology: for each year 1991–2020, first day after 1 Aug with min ≤ 0 °C and last day before 1 Jul with min ≤ 0 °C; take the median day-of-year. Wettest month = highest mean monthly rainfall; windiest = highest mean monthly max gust.
2. Tasks have rules: fixed month, or relative ("14 days before first frost"), and conditions (fuel, property type, hazard level, measure present). Examples: lag taps (frost −14 d), clear gutters (after leaf fall: November; and the month before the wettest month), boiler/heat-pump service (September), oil tank check (September, oil only), test flood kit and door seals (October, if a flood measure is recorded or flood risk ≥ medium), check roof after windiest month, bleed radiators (October), clean solar panels (April, if solar recorded), check trees near house (February, if storm risk ≥ medium).
3. ICS: hand-written RFC 5545 (CRLF line ends, 75-octet folding, stable `UID` = `<task_id>-<home hash>@hrp`, `RRULE:FREQ=YEARLY`, `VALARM` 1 day before). No new dependency.

**UI.**

- The **wheel**: SVG ring of 12 months with season tints; task dots placed on dates; the current month highlighted; tasks cascade in.
- Month list cards below; each task with effort ("10 min"), why, and guidance link.
- Climate facts strip ("First frost ~9 Nov · Wettest month: October").
- Buttons: "Download (.ics)", "Subscribe on this phone" (`webcal://` link), "Stop the feed".

**Build plan.** (1) climatology (pure, tested on synthetic years); (2) task library + rules; (3) ICS writer with tests; (4) routes + token table + export + revoke; (5) wheel UI.

**Tests.** First-frost computation; rules include oil tank only for oil; ICS lines ≤ 75 octets and CRLF; revoked token → 404; feed contains no postcode (regex); offline.

**Acceptance.** Any demo home shows the wheel and a valid `.ics` that imports into Google Calendar and Apple Calendar (manual check, note it in the PR).

**Contract note.** Studio routes and one table; the public feed follows the same "no personal data" rule as the public passport.

---

## S18 · Home Compare

**Wow.** Thinking of buying? Enter two or three addresses and three tall passport cards flip in side by side, each with its score dial, five hazards today and in 2050, EPC, and the cost to make it future-ready. A layered radar chart overlays all three, and each row crowns a winner. "Home B is £9,000 cheaper to make resilient."

**User story.** As a buyer, I want to compare the climate resilience of homes I'm considering, so that I can factor future costs into my decision.

**Differs from the taken 20.** The shareable report shows one home's passport. Compare runs the pipeline on homes the user doesn't own yet, with nothing saved.

**Data sources.** The existing N adapters (postcodes.io, EPC, EA flood, Open-Meteo climate) and L's `assess_risk`, `compute_score`, N's planner, all called read-only. No new external source.

**API.**

- `POST /api/v1/studio/compare` (login required) body `{candidates: list[{postcode: str, line1: str, uprn: str | None}]}` (2–3) → `Compare`
  - `homes: list[{label: Literal["A","B","C"], line1, postcode, property: PropertyFacts, risk: RiskProfile, score: ResilienceScore, top_measures: list[{measure_id, name, cost_low_gbp, cost_high_gbp, score_uplift}], cost_to_70_low_gbp: int | None, cost_to_70_high_gbp: int | None}]`
  - `winners: {flood: label, heat: label, storm: label, subsidence: label, carbon: label, overall: label}`
  - `summary: str`, `evidence`, `fallback_used`
- `GET /api/v1/studio/compare/demo?slugs=flood-terrace,clay-semi,rural-cottage` (public) → same shape from demo data.
- Rate limit: 10 compares per hour per user (Studio key). Scottish/NI postcodes → `400 unsupported_region`.

**Algorithm.**

1. For each candidate, build `HazardInputs` with the same adapter calls as the assessment service (`asyncio.gather`), `subsidence_signal="unknown"`; property from EPC (or our model, labelled). Do **not** create `homes` rows.
2. Risk and score via L's functions. Plan via N's planner with a neutral household (owner-occupier, no budget, no priorities, `vulnerable=None`).
3. Cost to 70: add ranked measures greedily until projected score ≥ 70; sum low/high costs; `null` if unreachable.
4. Winners: highest component points per row; overall = highest score, tie → lower cost to 70.

**UI.**

- Address entry: up to three compact postcode + address pickers (re-use the existing public `/lookup/postcode/{postcode}` route for the address list).
- Three cards flip in with a CSS 3D transform (staggered 120 ms); each card: dial, EPC arrow, hazards grid (today / 2050), cost to 70.
- Layered RadarChart (A green, B brass, C blue) over the five components; crown icons on winners; summary sentence.
- Mobile: cards become a swipeable carousel with the radar on top.

**Build plan.** (1) ephemeral assessment helper in Studio that reuses adapters (no changes to the assessment service's public functions); (2) cost-to-70 greedy; (3) routes + rate limit; (4) demo route; (5) UI.

**Tests.** 1 or 4 candidates → 400; region rule; no rows created in `homes` or `assessments` (row counts); demo compare offline; winners logic.

**Acceptance.** Demo compare of three demo homes renders offline; a logged-in compare of two real postcodes returns in under 10 s cold.

**Contract note.** Read-only use of adapters, scoring and planner; one public lookup route reused as-is.

---

## S19 · Passport Concierge

**Wow.** A refined side sheet, "Ask your Passport". Ask "Why is my flood score low?" or "What's the cheapest way to cut my bills?" and get a short, warm answer built only from this home's data, with small green citation pills ("From: EPC register", "From: Environment Agency") and follow-up chips. It never invents a number.

**User story.** As a homeowner who isn't confident with data, I want to ask questions in my own words and get clear answers about my home, so that I understand what to do next.

**Differs from the taken 20.** The planner's AI writes fixed one-sentence explanations. The Concierge is a conversation with tool use over the home's data.

**Data sources.** Claude through N's existing `llm.py` (model from `ANTHROPIC_MODEL`, timeout, daily cap `LLM_DAILY_CALL_LIMIT`, `llm_cache`), using the Anthropic Messages API with tools. Studio tools read the home's existing data only.

**API.**

- `POST /api/v1/studio/homes/{ref}/concierge` body `{messages: list[{role: Literal["user","assistant"], content: str (≤ 1000)}]}` (≤ 12, last must be `user`) → `ConciergeReply`
  - `answer: str` (≤ 1200), `citations: list[{tool: str, label: str}]`, `suggested: list[str]` (≤ 3), `source: Literal["llm","template"]`
- Rate limit 20 messages per hour per user, 10 per hour per IP for demo refs. Conversations are **not stored** on the server (kept in the browser session only).

**Algorithm.**

1. Tools (server-side, read-only, each returns JSON with **no personal fields**): `get_property_facts`, `get_risk_levels`, `get_score_breakdown`, `list_measures(category?, renter_ok?)`, `get_measure(id)`, `list_funding(kind?)` (catalogue only, no eligibility because that needs income), `explain_term(term)` (glossary in config).
2. System prompt: plain English, ≤ 120 words, cite tools used, only state numbers that appear in tool results, say "illustrative" for any bank product, suggest a qualified adviser for financial or structural decisions, refuse anything off-topic politely. Max 4 tool rounds.
3. **Number guard:** after the answer, extract every number with `£`, `%`, `kWh`, `kg` or `points`; if any does not appear in the tool outputs of this turn, discard and return the template answer.
4. **Template fallback** (no key, cap reached, timeout, guard failure): an intent router (keywords → 8 intents: biggest risk, explain score, cheapest bill saving, flood, heat, funding, renters, what next) filling sentences from the same tools. `source: "template"`.
5. Personal data: the prompt and tool outputs never contain email, address, postcode, house number, income band, budget, tenure or `vulnerable` (CONTRACT.md §6 rule 2). Messages typed by the user are passed through, so the UI warns "Don't include personal details", and a scrubber removes UK postcodes and email addresses from user messages before sending.

**UI.**

- Side sheet from the right (shadcn Sheet), Fraunces greeting "Ask about your home", three suggestion chips.
- Messages as paper cards; the reply reveals with a soft typewriter effect (instant with reduced motion); citations as green pills with evidence badges; "Template mode" chip when `source="template"`.
- The sheet is opened from a floating "Ask" button on every Studio page (Studio layout only, not L's pages).

**Build plan.** (1) tools with tests that assert no personal keys; (2) `llm.py` tool-use call path (add a function, do not change existing ones); (3) number guard; (4) template router; (5) route + rate limits; (6) UI.

**Tests.** `test_concierge_prompt_has_no_personal_data` (demo home with a household); number guard rejects an invented "£999"; postcode scrubber; template answers for all 8 intents with no key; rate limit 429.

**Acceptance.** With no `ANTHROPIC_API_KEY`, "What's my biggest risk?" on `demo-flood-terrace` answers from the template with a citation; with a key, the answer cites at least one tool and passes the guard.

**Contract note.** One Studio route; follows the LLM rules in spec §2 and CONTRACT.md §6.

---

## S20 · Lender Portfolio Lens

**Wow.** A boardroom-grade dark-green dashboard for a bank: 500 real (anonymised) homes from the public EPC register, as if they were a mortgage book. KPI tiles tick up: share below EPC C, share in medium or high flood risk, homes at high overheating risk by 2050, total transition finance opportunity, financed emissions. A bubble map by postcode district, and a scenario slider: "If 25% of D–G homes take up their plan by 2030, financed emissions fall 18% and 1 in 5 homes moves to EPC C or better."

**User story.** As a lender (Lloyds' point of view in the challenge), I want to see the climate exposure and retrofit opportunity across a portfolio, so that I can design fair green finance products and target support.

**Differs from the taken 20.** The community dashboard aggregates our users' outcomes for councils. The Lens is a bank-facing view over a sample of public EPC records, with transition-finance scenarios. It is clearly labelled illustrative.

**Data sources.**

- EPC bulk data already downloaded for N12 (`data/raw/`, OGL for non-address fields; **address fields are not used or stored**, see the EPC data licensing page linked from https://get-energy-performance-data.communities.gov.uk/, **verify**).
- The `flood_postcodes` table (EA RoFRS, already loaded) and `climate_defaults.py` (regional, already filled).
- L's `assess_risk` and `compute_score`; `measures.csv` for transition costs.
- EPC C 2030 context: government proposals for private rented homes (https://www.gov.uk/government/consultations , search "minimum energy efficiency standards private rented 2030", **verify** status and wording).
- Financed emissions method reference: PCAF Global GHG Accounting Standard, mortgages (https://carbonaccountingfinancials.com/standard, **verify**).

**API.**

- `GET /api/v1/studio/portfolio` (public, illustrative) → `Portfolio`
  - `sample_size: int`, `generated_on: date`, `sample_note: str`
  - `by_epc_band: list[{band, count}]`, `by_score_band: list[{band, count}]`
  - `flood_exposure: list[{level, count}]`, `heat_2050: list[{level, count}]`
  - `below_c_share_pct: float`, `transition_cost_low_gbp: int`, `transition_cost_high_gbp: int`
  - `financed_emissions_t: float`, `attribution_note: str` (illustrative loan-to-value 0.6)
  - `districts: list[{outcode, lat, lon, count, avg_score, below_c_share_pct}]` (only districts with ≥ 5 homes)
  - `fairness_note: str` ("Scores are never used to raise prices or rates."), `evidence`, `fallback_used: false`
- `POST /api/v1/studio/portfolio/scenario` body `{uptake_pct: int (0–100), by_year: int (2026–2035)}` → `{emissions_before_t, emissions_after_t, reduction_pct, below_c_share_after_pct, homes_upgraded, finance_needed_low_gbp, finance_needed_high_gbp}`

**Algorithm.**

1. `make studio-portfolio` (script `backend/scripts/build_studio_portfolio.py`, seeded): sample 500 certificates across the N12 regions, keep only non-address fields plus **outward code**; map to `PropertyFacts`; flood band from `flood_postcodes` by full postcode at build time, then drop the full postcode; climate from regional defaults; risk + score via L's functions; per home: cheapest set of plan measures (planner with a neutral household) that reaches EPC C or better (approximate: carbon measures' points until carbon component ≥ C midpoint), with cost low/high and CO2 saved. Write `backend/app/studio/data/portfolio_sample.json` (committed, a few hundred KB).
2. Route reads the JSON (no external calls; always works offline).
3. Financed emissions = Σ CO2 t/yr × 0.6 (illustrative attribution).
4. Scenario: deterministic selection of the first `uptake_pct`% of D–G homes by seeded order; apply their upgrade set; recompute.

**UI.**

- `.s-stage` hero with KPI tiles (ticker numerals) and "Illustrative · 500 public EPC records" stamp.
- Stacked EPC band bar in certificate colours; score band bar; flood and heat donuts.
- React-Leaflet bubble map of districts (radius by count, colour by average score), hover cards.
- Scenario panel: uptake slider and year segmented control, before/after bars animating, sentence summary.
- Fairness panel with the no-climate-penalty rule; print stylesheet for a one-page export (browser print to PDF).

**Build plan.** (1) build script with anonymisation and a test; (2) committed sample JSON; (3) routes; (4) scenario maths (pure, tested); (5) dashboard UI.

**Tests.** Sample JSON has no address, house number, UPRN or full postcode (regex); districts below 5 homes dropped; scenario 0% = baseline; 100% reduces emissions; script deterministic with the seed.

**Acceptance.** `/studio/portfolio` renders logged-out offline with all tiles, map and a working scenario slider.

**Contract note.** Two Studio routes; reads existing tables and L's functions read-only.

---

## 5. Build order and the demo video

**Recommended order** (biggest wow per hour first, so the best ones are safe before the Tue 10 Nov freeze):

| Order | Step                                                            | Why                                           |
| ----- | --------------------------------------------------------------- | --------------------------------------------- |
| 1     | S00                                                             | Required base                                 |
| 2     | S01 Retrofit Sandbox                                            | The video's hero moment                       |
| 3     | S07 Storm Replay                                                | Cinematic, emotional, real data               |
| 4     | S20 Lender Portfolio Lens                                       | Speaks directly to Lloyds' "ecosystem" ask    |
| 5     | S03 Meter Fingerprint                                           | Technically impressive, measured not modelled |
| 6     | S10 Permission Radar                                            | Practical, novel, fast                        |
| 7     | S06 Grid Carbon Clock                                           | Small and live                                |
| 8     | S13 Affordability Stress Test                                   | Bank language, fairness                       |
| 9+    | S02, S04, S05, S08, S09, S11, S12, S14, S15, S16, S17, S18, S19 | Any order                                     |

Realistic target before the freeze: S00 plus 6–8 functions. The rest continue after submission (M2), following the same file.

**60–90 s video beats** (suggestion for A's script): S01 drag a flood door and loft insulation on the flood-terrace demo → S07 replay Storm Babet at that home → S03 the fitted line drawing in → S20 the portfolio slider.

---

## 6. Definition of done (every step)

- [ ] Only N-owned paths changed (§1.2); `git diff --stat` shows no shared or L-owned file (S00's charter PR is the single exception).
- [ ] `docs/openapi.json` unchanged; `docs/openapi-studio.json` and Studio `schema.d.ts` regenerated and committed.
- [ ] Every number in the UI has an EvidenceBadge and a source note; verified figures have URL + date read in `config.py`.
- [ ] Works logged-out for all 5 demo homes, and with Wi-Fi off.
- [ ] Owner-only data returns 404 to other users; nothing personal in logs, LLM prompts or public responses.
- [ ] `make test`, `make lint`, `pnpm lint`, `pnpm typecheck`, `pnpm build` green; Lighthouse accessibility ≥ 90; checked at 375 / 768 / 1280 px and with reduced motion.
- [ ] Decision log entries added for anything this file didn't answer.

---

## 7. Prompt to give cc

Paste this at the start of each session (change the step id):

> I'm N. Read `CLAUDE.md`, `docs/CODING_SPEC.md`, `docs/CONTRACT.md` and `docs/studio/N_20_function.md`. We are doing step **S00** only. Follow §1 (contract rules) and §2 (design system) of the Studio file. Restate the goal and the files you will touch, build it, run the checks in the step and §6, then stop and wait for "approved".

---

## 8. Source index

postcodes.io https://postcodes.io/docs/api/api-reference-postcodes-io/ · EPC register https://get-energy-performance-data.communities.gov.uk/ · Open-Meteo Historical https://open-meteo.com/en/docs/historical-weather-api · Open-Meteo Forecast https://open-meteo.com/en/docs · Open-Meteo UKMO https://open-meteo.com/en/docs/ukmo-api · Open-Meteo Air Quality https://open-meteo.com/en/docs/air-quality-api · PVGIS https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en · Carbon Intensity API https://carbon-intensity.github.io/api-definitions/ · EA Recorded Flood Outlines https://ckan.publishing.service.gov.uk/dataset/recorded-flood-outlines1 · EA NCERM 2024 https://www.data.gov.uk/dataset/national-coastal-erosion-risk-mapping-ncerm-national-2024 · NRW NCERM https://metadata.naturalresources.wales/geonetwork/srv/api/records/NRW_DS121852 · Planning Data https://www.planning.data.gov.uk/docs · Planning Portal https://www.planningportal.co.uk/permission/common-projects · GPDO 2015 https://www.legislation.gov.uk/uksi/2015/596/schedule/2 · Ofgem price cap https://www.ofgem.gov.uk/energy-price-cap · Ofgem SEG https://www.ofgem.gov.uk/environmental-and-social-schemes/smart-export-guarantee-seg · Boiler Upgrade Scheme https://www.gov.uk/apply-boiler-upgrade-scheme · DESNZ conversion factors https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting · DESNZ appraisal values https://www.gov.uk/government/publications/valuation-of-energy-use-and-greenhouse-gas-emissions-for-appraisal · CCC Seventh Carbon Budget https://www.theccc.org.uk/publication/the-seventh-carbon-budget/ · MCS data dashboard https://datadashboard.mcscertified.com/ · HM Land Registry PPD https://landregistry.data.gov.uk/app/doc/ppd · UK HPI https://landregistry.data.gov.uk/app/ukhpi · DEFRA DAQI https://uk-air.defra.gov.uk/air-pollution/daqi · Met Office storm centre https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-storm-centre/index · Natural Earth coastline https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-coastline/ · PCAF standard https://carbonaccountingfinancials.com/standard

Every URL marked **verify** in the steps above is checked by cc at build time; if it has moved, cc uses the live page and logs the change.
