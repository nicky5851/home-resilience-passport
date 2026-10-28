# N's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · N1 · Async Postgres driver from the start
- Decision: `DATABASE_URL` uses `postgresql+asyncpg://`
- Alternatives: sync `psycopg` now, switch in N10
- Why: fastapi-users' SQLAlchemy adapter needs an async session; avoids a driver change mid-build (rule 3)
- Files: backend/app/config.py, .env.example, .github/workflows/ci.yml
- Commit: c2e0e00
- Affects the other coder? no

### 2026-10-27 · N1 · Makefile targets for later steps are placeholders
- Decision: `openapi`, `types`, `seed`, `validate-data`, `fixtures`, `train` exist now but print the step that adds them and exit 1
- Alternatives: leave them out until their step
- Why: CLAUDE.md lists them; a clear message beats "No rule to make target" (rule 5)
- Files: Makefile
- Commit: c2e0e00
- Affects the other coder? no

### 2026-10-27 · N1 · Node version pinned in `.nvmrc`
- Decision: `.nvmrc` = `22`; `backend/.python-version` = `3.12`
- Alternatives: rely on the README only
- Why: `nvm use` / `uv` pick the right runtimes automatically (spec §2)
- Files: .nvmrc, backend/.python-version
- Commit: c2e0e00
- Affects the other coder? no

### 2026-10-27 · N2 · Fixtures written by a generator script
- Decision: `backend/scripts/placeholder_fixtures.py` writes the 5 fixtures; outputs use a rough copy of spec §6/§7 so they add up
- Alternatives: hand-written JSON
- Why: five large files stay consistent and schema-valid; rerun after any schema change until `make fixtures` (N8) replaces it (rule 3)
- Files: backend/scripts/placeholder_fixtures.py, backend/tests/fixtures/demo_homes/
- Commit: 11b2fb9
- Affects the other coder? yes (output parts are placeholders, not L's scoring; measures/funding rows are placeholders until A's CSVs)

### 2026-10-27 · N2 · Contract models reject unknown keys
- Decision: every schema model uses `extra="forbid"`
- Alternatives: Pydantic's default (ignore extra keys)
- Why: a misspelt field in a fixture or request fails loudly instead of silently becoming `null` (rule 3)
- Files: backend/app/schemas/base.py
- Commit: 11b2fb9
- Affects the other coder? yes (a request body with an extra key gets `400 validation`)

### 2026-10-27 · N2 · `HazardLevel.data_source` stays `str`
- Decision: typed `str` exactly as spec §4.1; the five allowed strings are `DATA_SOURCES` and checked in `test_schemas.py`
- Alternatives: a `Literal` of the five strings
- Why: follow §4.1 to the letter; the test still catches a wrong string (rule 2)
- Files: backend/app/schemas/hazards.py, backend/tests/test_schemas.py
- Commit: 11b2fb9
- Affects the other coder? no

### 2026-10-27 · N2 · `Passport` extends `PublicPassport`
- Decision: `PublicPassport` is the base class; `Passport` adds `household` and `share_token`
- Alternatives: two independent classes
- Why: the public model cannot gain household data by accident; FastAPI's response model strips the extra fields (rule 5)
- Files: backend/app/schemas/passport.py
- Commit: 11b2fb9
- Affects the other coder? no

### 2026-10-27 · N3 · Route bodies live in `schemas/api.py`
- Decision: the §4.2 shorthand shapes (`PostcodeLookup`, `HomeCreate`, `HomeCreated`, `HomeSummary`, `Assessment`, `PlanRequest`, `FundingRequest`, `ShareLink`, `ModelInfo`, `ErrorBody`, `ForgotPassword`, `ResetPassword`) are Pydantic models in the shared schemas package
- Alternatives: define them inside N's routers
- Why: they are contract (the front end's types come from them); keeping them with §4.1 makes every contract change one place (rule 2, rule 6)
- Files: backend/app/schemas/api.py
- Commit: 010cf6d
- Affects the other coder? yes (new type names in `schema.d.ts`)

### 2026-10-27 · N3 · `HomeSummary.score` is a full `ResilienceScore | null`
- Decision: `GET /homes` returns the whole latest score object, not just the number
- Alternatives: `score: int | null`
- Why: §4.2 writes `score?` without a type; the "My homes" list can show the band without another call (rule 1)
- Files: backend/app/schemas/api.py
- Commit: 010cf6d
- Affects the other coder? yes

### 2026-10-27 · N3 · Response fields are required in OpenAPI
- Decision: `json_schema_serialization_defaults_required=True` on every contract model
- Alternatives: leave defaults optional in the schema
- Why: CONTRACT §1 rule 2 says every field is always present; otherwise the generated TS types mark nullable fields optional. Side effect: `Address`, `Household`, `PropertyFacts` appear as `-Input` / `-Output` in OpenAPI
- Files: backend/app/schemas/base.py, docs/openapi.json
- Commit: 010cf6d
- Affects the other coder? yes (use `components["schemas"]["PropertyFacts-Output"]` etc. for responses)

### 2026-10-27 · N3 · Stub state is in memory
- Decision: `app/api/stub_store.py` keeps homes, events, certificates and share links in a process-local dict; demo homes are readable by any logged-in user
- Alternatives: write the stub against the database now
- Why: N4 builds the tables, N9/N10/N14 replace the stub piece by piece; memory keeps N3 small (rule 3)
- Files: backend/app/api/stub_store.py
- Commit: 010cf6d
- Affects the other coder? no (restarting the API forgets stub homes)

### 2026-10-27 · N3 · `POST /homes/{id}/work` returns 200
- Decision: 200 with the `PassportEvent`
- Alternatives: 201
- Why: the contract names 201 only for `POST /homes`; keep FastAPI's default elsewhere (rule 2)
- Files: backend/app/api/homes.py
- Commit: 010cf6d
- Affects the other coder? no

### 2026-10-27 · N3 · Unlisted 4xx statuses map to `validation`
- Decision: e.g. 405 returns `code="validation"`; 422 never appears (converted to 400 and removed from OpenAPI)
- Alternatives: invent new codes
- Why: CONTRACT §3 lists a closed set of codes (rule 2)
- Files: backend/app/api/errors.py, backend/app/main.py
- Commit: 010cf6d
- Affects the other coder? no

### 2026-10-27 · N3 · New dependency `python-multipart`
- Decision: added to the back end
- Alternatives: none; FastAPI needs it for form-encoded login and multipart uploads
- Why: required by CONTRACT §4 and §6
- Files: backend/pyproject.toml, backend/uv.lock
- Commit: 010cf6d
- Affects the other coder? no

### 2026-10-27 · N4 · `users` table defined by hand with fastapi-users' columns
- Decision: `id`, `email`, `hashed_password`, `is_active`, `is_superuser`, `is_verified` written out in `models.py`, plus our own columns
- Alternatives: `fastapi-users-db-sqlalchemy`'s `SQLAlchemyBaseUserTableUUID` mixin now
- Why: no new dependency until N10; the columns match the mixin, so N10 can switch with no migration (rule 3)
- Files: backend/app/db/models.py
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · Demo homes validated but not stored yet
- Decision: `make seed` loads `measures` and `funding_options`; `demo_homes.csv` is checked by `make validate-data` only. `/demo/homes` keeps serving the fixtures
- Alternatives: create a demo user and five homes now
- Why: there is no `demo_homes` table in N4's list and N15 seeds them "with full data" (rule 1, rule 3)
- Files: backend/app/db/seed.py
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · Seed replaces reference tables wholesale
- Decision: delete all rows then insert, in one transaction
- Alternatives: upsert row by row
- Why: the tables always mirror A's CSVs, including removed rows; plans keep their own JSON copy of measures so nothing references these rows (rule 3)
- Files: backend/app/db/seed.py
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · Placeholder source URLs are warnings
- Decision: `example.com` / `example.org` in `source_url` prints a warning; `make validate-data` still passes
- Alternatives: fail CI on placeholders
- Why: lets the foundation merge before A's sheets arrive while keeping the gap visible on every run (rule 1)
- Files: backend/app/db/reference.py, data/reference/measures.csv
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · Tests use their own `<db>_test` database
- Decision: a session fixture drops and recreates `hrp_test` and migrates it to head; locally DB tests skip with a hint if Postgres is down, in CI (`CI` set) they fail
- Alternatives: run against the dev database; transaction-rollback per test
- Why: never touches dev data, and each run proves migrations work on a fresh DB (rule 3)
- Files: backend/tests/conftest.py, backend/tests/test_db.py
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · `flood_postcodes` is a minimal (postcode, band) table
- Decision: composite primary key, no other columns
- Alternatives: guess the RoFRS ZIP's columns now
- Why: N7 inspects the real file and records the mapping; it adds columns in its own migration (rule 3)
- Files: backend/app/db/models.py
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N4 · New dependencies `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
- Decision: added to the back end
- Alternatives: none; spec §2 locks SQLAlchemy 2.0 + Alembic, asyncpg is the async driver (N1 decision)
- Why: required by N4
- Files: backend/pyproject.toml, backend/uv.lock
- Commit: b6cef8a
- Affects the other coder? no

### 2026-10-27 · N5 · Unknown or invalid postcode returns 400, not 422
- Decision: `GET /lookup/postcode/{postcode}` answers `400` `validation` for a malformed postcode and for one postcodes.io does not know
- Alternatives: `422` as written in spec §5's table and the N5 Check
- Why: CONTRACT.md §3 converts every 422 to 400 `validation`; the contract wins over the spec text (rule 2). The spec wording needs a fix agreed with L
- Files: backend/app/api/lookup.py
- Commit: ff60142
- Affects the other coder? yes (the front end shows `detail` under the postcode box for status 400; the spec text still says 422)

### 2026-10-27 · N5 · Country comes from postcodes.io, not a postcode-area list
- Decision: `unsupported_region` is decided by postcodes.io's `country`; Scotland, Northern Ireland, the Channel Islands and the Isle of Man are unsupported. The stub's area regex is removed
- Alternatives: keep the regex as an offline pre-check
- Why: the regex blocked English border postcodes such as TD15 (Berwick-upon-Tweed, Northumberland); the stub's own comment planned this switch
- Files: backend/app/api/lookup.py, backend/app/adapters/postcodes.py
- Commit: ff60142
- Affects the other coder? no

### 2026-10-27 · N5 · `api_cache` is best-effort; demo postcodes fall back to their fixture
- Decision: if the database cannot be reached, cache reads miss and writes are dropped (only the error type is logged). If postcodes.io is down, a demo postcode answers from its fixture and any other postcode returns `502 upstream_unavailable`
- Alternatives: fail the request when the cache fails; return 502 for demo postcodes too
- Why: the app must keep working when any part is down (spec §5) and the 5 demo homes must work offline (rule 1, N9 check); a non-demo postcode has no fallback, which is exactly CONTRACT §3's 502 case
- Files: backend/app/adapters/cache.py, backend/app/api/lookup.py, backend/app/api/deps.py
- Commit: ff60142
- Affects the other coder? no

### 2026-10-27 · N5 · Shared adapter plumbing and test fixtures
- Decision: `app/adapters/http.py` (client with the 10 s timeout, `UpstreamUnavailable`) and `app/adapters/cache.py` (`Cache` protocol, `DbCache`) are reused by N6–N8. API tests override `get_api_cache` with an in-memory cache and block all outbound HTTP via `respx`; postcodes.io answers are recorded in `backend/tests/adapters/recorded/postcodes/`
- Alternatives: per-adapter clients and caches; API tests against the dev database
- Why: one pattern for every adapter (rule 6); tests stay offline and never touch the dev database
- Files: backend/app/adapters/, backend/tests/conftest.py, backend/tests/adapters/
- Commit: ff60142
- Affects the other coder? no

### 2026-10-27 · N5 · New dev dependency `respx`
- Decision: added to the back end's dev group
- Alternatives: hand-written `httpx.MockTransport`
- Why: spec N5 names `respx` for recorded responses
- Files: backend/pyproject.toml, backend/uv.lock
- Commit: ff60142
- Affects the other coder? no

### 2026-10-27 · N6 · `EPC_API_BASE_URL` setting; cache keys per environment
- Decision: the EPC API base URL is a setting, live by default (an empty value also means live). A token only works on the environment that issued it, so the integration (test) host is set in `.env` when using an integration token. EPC cache keys include the API host
- Alternatives: hard-coded live URL; cache keys without the host
- Why: integration tokens get `403 UNAUTHORISED` on live. During the N6 live check the dev cache served integration test homes after switching to live, for up to 30 days; per-host keys stop that
- Files: backend/app/config.py, backend/app/adapters/epc.py, .env.example, README.md, docs/DECISIONS.md
- Commit: c861041
- Affects the other coder? yes (new variable `EPC_API_BASE_URL` in the shared `.env.example`; each person needs their own token, README "EPC API token")

### 2026-10-27 · N6 · Code tables from the register's codes CSV
- Decision: `scripts/epc_codes.py` turns the register's public codes CSV into `app/adapters/epc_codes.json` ({schema: {code: {key: value}}}, England and Wales schemas only) for `property_type`, `built_form`, `construction_age_band`, `main_fuel`; values use the bulk-data wording the demo fixtures use ("Mid-Terrace", "1900-1929", "mains gas")
- Alternatives: call `/api/codes/info` at runtime
- Why: code meanings change between schema versions (`main_fuel` 10 is electricity in RdSAP-17, dual fuel in SAP-17); a static table needs no extra calls and no token
- Files: backend/scripts/epc_codes.py, backend/app/adapters/epc_codes.json
- Commit: c861041
- Affects the other coder? no

### 2026-10-27 · N6 · Mapping rules for certificates
- Decision: latest certificate per address, ties on the same date broken by certificate number; fuel taken from the main-heating description when it names one, else the coded fuel; flats get `floor_level` from the storey and `top_floor` from the level/top-storey answers, houses get `floor_level=0`, `top_floor=null`
- Alternatives: first row wins; coded fuel only
- Why: the register returns same-day certificates for one UPRN; one recorded certificate codes bottled LPG while describing electric heating, and the description is what users see
- Files: backend/app/adapters/epc.py
- Commit: c861041
- Affects the other coder? no

### 2026-10-27 · N6 · Lookup lists the demo address first; at most 50 addresses
- Decision: for a demo postcode the demo address is listed before the register's addresses; the list is cut at 50 (CONTRACT §3). Without a token, or with the register down, the register part is empty
- Alternatives: demo address only; register addresses only
- Why: keeps the demo path working (rule 1) while showing real data
- Files: backend/app/api/lookup.py
- Commit: c861041
- Affects the other coder? no

### 2026-10-27 · N6 · Test fixtures recorded from the integration API
- Decision: `backend/tests/adapters/recorded/epc/` holds integration-API responses (SW1A 1AA, CF10 1EP and their certificates) plus the register's official RdSAP-17.0 flat sample (integration has no flats). The live check ran against the live API but its answers are not stored
- Alternatives: record live responses
- Why: integration data is the register's test data, so nothing about real homes is committed
- Files: backend/tests/adapters/
- Commit: c861041
- Affects the other coder? no

### 2026-10-27 · N7 · RoFRS: one row per postcode, highest band with properties
- Decision: the ZIP's CSV has one row per postcode with property counts per band; `flood_postcodes` stores the highest band whose `TOT_CNT_*` count is > 0, one row per postcode, in the existing (postcode, band) table. Rows whose `PC` is not a real postcode ("V…" pseudo-postcodes, 106k rows) are skipped. The table is replaced as a whole
- Alternatives: one row per postcode and band (N4's guess); weighted average by property count; a migration adding the counts
- Why: CONTRACT §2 defines `rofrs_band` as the highest band present; no schema change needed (rule 3); conservative for flood risk (rule 5)
- Files: backend/app/db/load_rofrs.py, docs/DECISIONS.md
- Commit: 4ada357
- Affects the other coder? no

### 2026-10-27 · N7 · Empty table or database down means unknown, not `none`
- Decision: `rofrs_band` returns `None` for Wales, when `flood_postcodes` is empty, or when the database cannot be read; `none` only when the data is loaded and the postcode is not in it
- Alternatives: `none` whenever no row is found
- Why: a machine that never ran `make flood-data` must not tell a household it is not at flood risk (rule 5)
- Files: backend/app/adapters/flood.py
- Commit: 4ada357
- Affects the other coder? no

### 2026-10-27 · N7 · Live warnings count severity 1–3 only, capped at 50
- Decision: count EA items with `severityLevel` 1 (severe warning), 2 (warning) or 3 (alert) within 5 km; level 4 ("no longer in force") is ignored. Capped at 50 (CONTRACT §2 range). Cached 15 minutes by lat/lon rounded to 3 decimals; failures return 0 and are not cached
- Alternatives: count every item returned
- Why: CONTRACT §2 counts warnings "currently in force"; the live feed includes expired ones
- Files: backend/app/adapters/flood.py
- Commit: 4ada357
- Affects the other coder? no

### 2026-10-27 · N7 · `make flood-data` downloads the RoFRS ZIP itself
- Decision: the loader downloads the ZIP (no sign-up, OGL) into git-ignored `data/raw/` when missing, or with `--download`; 120 s timeout for this one-off 5 MB download; tests build a tiny ZIP so CI never downloads
- Alternatives: manual download; commit the data
- Why: one command per machine; the big file stays out of git
- Files: backend/app/db/load_rofrs.py, backend/app/config.py, Makefile
- Commit: 4ada357
- Affects the other coder? yes (each machine runs `make flood-data` once, otherwise every flood band is unknown)

### 2026-10-27 · N8 · Climate averages use the years that have data (no 2050 in the model)
- Decision: each statistic is averaged over the years with at least 360 days of data; the request still asks for 2041–2050, but `EC_Earth3P_HR` returns no 2050, so the future figures are 2041–2049 in practice. A period whose numbers fall outside CONTRACT §2's ranges is treated as failed
- Alternatives: divide by the 10 years asked for; request 2041–2049
- Why: dividing by 10 would understate every 2050 figure by about 10%; keeping the contract window means a model that adds 2050 just works
- Files: backend/app/adapters/climate.py
- Commit: 6b5caec
- Affects the other coder? yes (L's `why` text says "by 2050"; the figure is the 2041–2049 mean)

### 2026-10-27 · N8 · Regional defaults: by region name, else nearest point
- Decision: `climate_defaults.py` has one row per English region and Wales, filled by `scripts/climate_defaults.py` from real calls at one city per region. The fallback picks the row by the postcode's region from postcodes.io (`PostcodeInfo.region`, "Wales" for Wales), else the nearest reference point. Each period falls back on its own; defaults are never cached
- Alternatives: nearest point only
- Why: nearest-point alone sends GL54 (rural-cottage demo, South West) to West Midlands
- Files: backend/app/adapters/climate.py, backend/app/adapters/climate_defaults.py, backend/scripts/climate_defaults.py, backend/app/adapters/postcodes.py
- Commit: 6b5caec
- Affects the other coder? no

### 2026-10-27 · N8 · `DbCache` serialises its own session use
- Decision: `DbCache` holds an `asyncio.Lock` so adapters can share one request's cache under `asyncio.gather`
- Alternatives: one session per adapter call
- Why: the live check showed parallel reads failing (`InvalidRequestError`) and silently skipping the cache; N9 gathers every adapter
- Files: backend/app/adapters/cache.py
- Commit: 6b5caec
- Affects the other coder? no

### 2026-10-27 · N8 · `make fixtures` (outputs) and `make fixtures-inputs` (contract)
- Decision: `make fixtures` recomputes `risk`, `score` and the passport copies from each fixture's inputs with `app.scoring`, offline. `make fixtures-inputs` first records `rofrs_band` and the six climate fields from the real adapters (real answers only), keeping `property`, `subsidence_signal` and `active_flood_warnings` (a live value). `plan` and `funding` stay until N11/L6. Fixture changes go in the separate `fixtures: real data` PR, which needs L's approval
- Alternatives: one command doing both; record a live warnings snapshot
- Why: inputs are contract (spec §3.3); outputs may be refreshed by either coder
- Files: backend/scripts/make_fixtures.py, Makefile
- Commit: 6b5caec
- Affects the other coder? yes (until L5 merges, `compute_score` is the stub, so refreshed scores are all 50)

### 2026-10-27 · N9 · Homes and assessments stay in the in-memory store until N10
- Decision: `POST /homes` and `POST /homes/{id}/assess` run the real pipeline, but the home, its real address/property/household and its latest assessment are kept in the stub store (`StubHome.real`, `StubHome.assessment`), not in Postgres. They are lost on restart. N10 moves homes and assessments into the database together with real users
- Alternatives: insert placeholder `users` rows for stub-cookie emails so homes can be stored now
- Why: `homes.user_id` needs a `users` row, which only exists with real accounts (N10); placeholder users would have to be migrated or deleted again
- Files: backend/app/api/homes.py, backend/app/api/stub_store.py
- Commit: c5ce465
- Affects the other coder? yes (assessments vanish when the API restarts until N10)

### 2026-10-27 · N9 · Property facts when creating a home
- Decision: `property_override` wins; else the latest EPC for `address.uprn`; else, for a demo postcode, the demo home's property; else 400 `validation` with detail starting `property_override:` (also when the EPC register is down)
- Alternatives: 502 `upstream_unavailable` when the register is down
- Why: the user can always carry on by entering the details (spec §5: the app keeps working)
- Files: backend/app/services/assessment.py, backend/app/api/homes.py
- Commit: c5ce465
- Affects the other coder? yes (front end shows the property form on that 400)

### 2026-10-27 · N9 · Live warnings have a 3 s budget inside an assessment
- Decision: `active_flood_warnings` is given `ASSESS_WARNINGS_BUDGET_S = 3.0`; slower counts as 0, the same as the feed being down (N7). The flood band is read before the parallel network calls because it uses the request's session directly
- Alternatives: keep the 10 s outbound timeout and miss the < 5 s cold target
- Why: the EA feed took 1.6–5.6 s cold in the N9 check; everything else took under 0.3 s
- Files: backend/app/services/assessment.py, backend/app/config.py
- Commit: c5ce465
- Affects the other coder? no

### 2026-10-27 · N9 · `subsidence_signal` is always `unknown` for now
- Decision: no request field carries the user's subsidence answer, so new homes get the contract default `unknown`; a separate `contract:` PR proposes an optional household field
- Alternatives: none without a contract change
- Why: CONTRACT §2 says the value comes from the household form, but neither `Household` nor `HomeCreate` has it
- Files: backend/app/services/assessment.py
- Commit: c5ce465
- Affects the other coder? yes

### 2026-10-28 · N10 · Our own user store instead of fastapi-users-db-sqlalchemy
- Decision: `app/auth/users.py` has a five-method `UserStore` (get, get_by_email, create, update, delete) over `app.db.models.User`; only the core `fastapi-users` package is installed
- Alternatives: `fastapi-users[sqlalchemy]`
- Why: its SQLAlchemy adapter pins SQLAlchemy below 2.1 and would downgrade 2.1.6 → 2.0.55 for the whole back end; the adapter is ~30 lines
- Files: backend/app/auth/users.py, backend/pyproject.toml, backend/uv.lock
- Commit: 5f0f5e4
- Affects the other coder? no

### 2026-10-28 · N10 · Our routes call fastapi-users; its routers are not mounted
- Decision: register/login/logout/forgot/reset/me keep the stub's route functions and call `UserManager` and `JWTStrategy`; every fastapi-users error is mapped to CONTRACT §3 there (duplicate → 409 `conflict`; bad password rule → 400 with the rule in plain English; bad login → 400 "Email or password is incorrect"; bad reset token → 400). Email lookups ignore case
- Alternatives: mount `fastapi_users.get_auth_router()` etc.
- Why: keeps `docs/openapi.json` byte-identical, so the front end and the contract do not change
- Files: backend/app/api/auth.py, backend/app/api/deps.py
- Commit: 5f0f5e4
- Affects the other coder? no

### 2026-10-28 · N10 · Reset link opens `/reset-password?token=…`
- Decision: with `RESEND_API_KEY` unset (M1), forgot-password logs `Password reset link for user <id>: <NEXT_PUBLIC_APP_URL>/reset-password?token=<token>` (no email address in the log). Tokens last 1 hour (fastapi-users default). With the key set it logs that email arrives in M2 and does not log the link
- Alternatives: `/login/reset?token=`
- Why: the spec names forgot/reset pages but no path
- Files: backend/app/auth/users.py, backend/app/config.py
- Commit: 5f0f5e4
- Affects the other coder? yes (L builds the page at that path; see docs/FOR_L.md)

### 2026-10-28 · N10 · Users' homes in Postgres; demo homes stay in memory
- Decision: homes, households, assessments, passport events and share links are stored (`app/services/homes.py`) and shown to routes as `StubHome` views; the five demo homes still answer from fixtures, readable by every logged-in user. Plans and funding still come from the fixture matched by postcode (N11 / L6); certificate files of stored homes stay in memory (`homes.CERTIFICATES`) until N14. Events are stored to the microsecond for ordering and shown to the second. Replaces the N9 in-memory decision
- Alternatives: store demo homes per user
- Why: demo homes are read-only showcases (CONTRACT §3); the user approved moving homes and assessments into the database in N10
- Files: backend/app/services/homes.py, backend/app/api/homes.py, backend/app/api/public.py, backend/app/api/stub_store.py
- Commit: 5f0f5e4
- Affects the other coder? yes (certificates are lost when the API restarts until N14)

### 2026-10-28 · N10 · Rate limits count every attempt; production needs a real secret
- Decision: login and register limits count every request, successful or not, per client IP (`X-Forwarded-For` first entry only when `ENV=production`); assess counts per user. `Retry-After` is rounded up to whole seconds. Settings refuse to load in production with the dev `AUTH_SECRET` or one under 32 characters
- Alternatives: count only failed logins
- Why: simplest reading of CONTRACT §3; a weak secret lets anyone forge login cookies
- Files: backend/app/core/ratelimit.py, backend/app/api/deps.py, backend/app/config.py
- Commit: 5f0f5e4
- Affects the other coder? no

### 2026-10-28 · N10 · Export shape
- Decision: `/users/me/export` is `{"user": {UserRead + created_at, last_seen_at, privacy_accepted_at, privacy_version}, "homes": [{"passport": Passport, "assessments": [...], "plans": [...]}]}`; never the password hash; certificates by file name only (in passport events)
- Alternatives: one flat list per table
- Why: readable by a person, and contains every row CONTRACT §4 lists
- Files: backend/app/api/auth.py
- Commit: 5f0f5e4
- Affects the other coder? no

### 2026-10-28 · N10 · Risk `generated_at` is the assessment's time
- Decision: the assessment service overwrites `RiskProfile.generated_at` from L's pure `assess_risk` with the current UTC time (to the second)
- Alternatives: pass the time into `assess_risk`
- Why: keeps L's function pure (spec §4.3); missed in N9
- Files: backend/app/services/assessment.py
- Commit: 5f0f5e4
- Affects the other coder? no

### 2026-10-28 · N11 · Household priorities → measures
- Decision: a measure gets the +20% priority weight when it serves one of the household's priorities: `lower_bills` = bill saving > 0; `comfort` = category `heat`; `flood_safety` = category `flood`; `lower_carbon` = CO2 saving > 0; `home_value` = measures that raise the EPC rating, i.e. a bill saving or a CO2 saving > 0 (the EPC rating is set by energy cost and CO2)
- Alternatives: `home_value` matches nothing; `home_value` = every measure
- Why: spec §7 rule 3 names the boost but not the mapping; `home_value` mapping chosen by N (the human)
- Files: backend/app/services/planner.py
- Commit: 0aa9ab8
- Affects the other coder? no

### 2026-10-28 · N11 · Renters' landlord group is part of `items`
- Decision: for renters (`private_renter`, `social_renter`), measures with `needs_landlord` are ranked after every other measure and are never selected (not by default, not through `selected_ids`); the front end shows items with `measure.needs_landlord` as the "Ask your landlord" group. Owners and landlords get them in the main list
- Alternatives: a separate `landlord_items` field in `Plan` (contract change)
- Why: spec §7 rule 1 asks for a separate group but `Plan` has only `items`; no contract change needed
- Files: backend/app/services/planner.py
- Commit: 0aa9ab8
- Affects the other coder? yes (L11 splits the list by `measure.needs_landlord`)

### 2026-10-28 · N11 · LLM explanations: top 8, mixed sources, no server-side fallback
- Decision: one call per plan for the top 8 ranked measures (Messages API, `ANTHROPIC_MODEL`, 8 s timeout, no SDK retries, `effort: low`, JSON schema output); sentences over 30 words or 200 characters are dropped; every other item gets the template. `explanation_source` is `llm` when at least one item's text came from the LLM. Refusals and every error use the template, so Anthropic's server-side fallback model is not enabled
- Alternatives: explain every measure; label mixed plans `template`
- Why: spec §7 rule 5 (top 8, one call); the template already covers every failure
- Files: backend/app/services/llm.py, backend/app/services/planner.py
- Commit: 0aa9ab8
- Affects the other coder? yes (an `llm` plan can still contain template sentences)

### 2026-10-28 · N11 · LLM cache and daily cap
- Decision: `llm_cache` rows never expire (key = sha256 of property facts, hazard levels, measure ids, `SCORING_VERSION`, model); only successful answers are cached. The daily cap (`LLM_DAILY_CALL_LIMIT`) counts call attempts per UTC day in memory, so it resets when the API restarts
- Alternatives: count cache rows created today (would not count failed calls)
- Why: one API instance; failed calls must count towards the cap too
- Files: backend/app/services/llm.py
- Commit: 0aa9ab8
- Affects the other coder? no

### 2026-10-28 · N11 · Plans: latest only, demo homes keep fixtures
- Decision: `POST /homes/{id}/plan` for a stored home stores only the latest plan (`plans`, with the budget actually used); before an assessment it returns 404 `not_found`. Demo homes return their fixture plan. Done measures (`work_recorded` events) leave the plan and count towards the projected score; recording work on a stored home accepts any measure in `measures`
- Alternatives: keep every plan (the slider would add a row per move)
- Why: the slider re-posts `/plan` on every move (CONTRACT §3)
- Files: backend/app/api/homes.py, backend/app/services/homes.py
- Commit: 0aa9ab8
- Affects the other coder? yes (plan before assessment is 404)

### 2026-10-28 · N12 · EPC bulk data read in place with HTTP range requests
- Decision: `ml/download.py` asks the register API for the domestic bulk file (`/api/files/domestic/csv`, bearer token; 302 to a signed S3 link that expires after 30 s), reads the 8.3 GB zip's index and only the chosen year's member through `Range` requests, renewing the link on every 403, and never prints the signed link
- Alternatives: download the whole 8.3 GB zip; sign in to the website and download by hand
- Why: about 270 MB transferred instead of 8.3 GB (20 GB of free disk), no manual step, reproducible from `make epc-data`
- Files: backend/ml/download.py, Makefile
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · Training subset: 2024 certificates in London, Yorkshire and the South West
- Decision: one lodgement year (2024) and three regions (E12000007, E12000003, E12000009): 553,640 certificates, 537,908 homes after cleaning
- Alternatives: several years; other regions
- Why: spec asks for about 3 regions and 500k certificates; these hold the five demo homes and mix city flats, terraces and rural houses
- Files: backend/ml/download.py, docs/model_card.md
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · Seven features built by one module for training and serving
- Decision: `ml/features.py` builds property type (EPC adapter's rule), built form, age band (prefix removed), floor area, region (ONS code → postcodes.io name), heating type (from the description) and fuel (description first, coded fuel second, as the adapter) from both a bulk row and `PropertyFacts`
- Alternatives: separate code for training and serving
- Why: the model must never see a value the app cannot produce
- Files: backend/ml/features.py
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · Cleaning rules
- Decision: latest certificate per UPRN (rows without UPRN kept); drop rows without a valid band A–G or with CO2 outside 0–50 t/yr; floor area outside 10–1000 m² becomes unknown; categories under 0.2% of homes become "other"; split unit = postcode area (letters of the outward code)
- Alternatives: drop rows with any missing feature
- Why: the model handles missing values natively, and the app often lacks some facts
- Files: backend/ml/prepare.py
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · Early stopping with 30 rounds of patience
- Decision: both models use early stopping with `n_iter_no_change=30` (max 300 rounds, learning rate 0.1, seed 42)
- Alternatives: default patience 10 (stopped after 11 rounds); 300 fixed rounds
- Why: on a validation split of the training areas (not the test set) accuracy was 66.0% vs 65.3% (patience 10) and 64.1% (300 rounds)
- Files: backend/ml/train.py
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · Model artefact committed to git
- Decision: `backend/ml/artifacts/epc_model.joblib` (0.7 MB, both models, kept categories, metrics, version) is committed with `metrics.json` and `confusion_matrix.png`
- Alternatives: Git LFS; train on deploy
- Why: spec §2 commits artefacts under 25 MB; the app needs the model without the training data
- Files: backend/ml/artifacts/
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N12 · scikit-learn and pandas are runtime dependencies; matplotlib training-only
- Decision: `scikit-learn` and `pandas` in the back end's main dependencies (N13 predicts inside the API); `matplotlib` in the `ml` dependency group (`uv run --group ml`), used only for the confusion matrix
- Alternatives: everything in the `ml` group
- Why: the API loads the model at start-up; CI and the API image need not install plotting
- Files: backend/pyproject.toml, backend/uv.lock, Makefile
- Commit: 7131404
- Affects the other coder? no

### 2026-10-28 · N13 · Estimates only fill gaps; `source` becomes "model"
- Decision: when `epc_rating` is missing, the model fills the band, and CO2 only if it is missing too; `PropertyFacts.source` is set to `"model"` even when the other facts came from the user; a certificate's band is never replaced
- Alternatives: keep `source="user"` and add a separate flag (needs a contract change); replace every EPC field
- Why: spec N13 says set `source="model"`; the front end needs one field to show "Estimated by our model"
- Files: backend/app/services/assessment.py
- Commit: 2862ef2
- Affects the other coder? yes (front-end label; scoring's "Our EPC model" data source)

### 2026-10-28 · N13 · Estimate region from the postcode lookup
- Decision: the region feature comes from postcodes.io (`PostcodeInfo.region`, cached), the same lookup the climate step uses; unknown region if the lookup fails
- Alternatives: store a region on the home
- Why: no new data or contract field; the training regions use the same names
- Files: backend/app/services/assessment.py, backend/ml/features.py
- Commit: 2862ef2
- Affects the other coder? no

### 2026-10-28 · N13 · The app works without the model file
- Decision: if `ml/artifacts/epc_model.joblib` is missing or fails to load, it is logged once, there are no estimates (scoring handles a missing band) and `/model/info` returns `version: "unavailable"`
- Alternatives: fail start-up
- Why: spec §5 fallback rule: the app keeps working
- Files: backend/ml/predict.py, backend/app/api/public.py
- Commit: 2862ef2
- Affects the other coder? no

### 2026-10-28 · N13 · Predictions on one OpenMP thread
- Decision: on model load the API process limits OpenMP to one thread (`threadpool_limits`)
- Alternatives: default threads (17 ms typical, 46 ms worst); limiting per call (overhead made it slower)
- Why: one home at a time is faster on one thread: 5.4 ms typical, 7.7 ms worst of 200 (spec limit 50 ms); the API has no other OpenMP work
- Files: backend/ml/predict.py
- Commit: 2862ef2
- Affects the other coder? no

### 2026-10-28 · N13 · Model loaded at start-up
- Decision: a FastAPI lifespan in `app/main.py` loads the model once (cached) before the first request; about 1.3 s added to start-up
- Alternatives: load on first use
- Why: spec N13 says load once at start-up; the first assessment doesn't wait
- Files: backend/app/main.py
- Commit: 2862ef2
- Affects the other coder? no

### 2026-10-28 · N13 · `/model/info` metrics as flat dotted names
- Decision: `metrics` holds `accuracy`, `within_one_band`, `macro_f1`, `co2_mae_tonnes`, `test_homes`, `train_homes`, plus `by_property_type.<type>.<metric>` and `by_region.<region>.<metric>` (38 values)
- Alternatives: nested objects (contract says `dict[str, float]`)
- Why: fits the contract unchanged; the Technology slide can pick the keys it needs
- Files: backend/ml/predict.py
- Commit: 2862ef2
- Affects the other coder? yes (key names for the Technology slide)

### 2026-10-28 · N14 · `/passport` is 404 before the first assessment
- Decision: `GET /homes/{id}/passport` (and the public passport of a shared, unassessed home) answers `404 not_found` "This home has not been assessed yet." until the home is assessed
- Alternatives: fall back to a demo fixture's risk and score (the M1 stub did this)
- Why: `Passport.latest_risk` and `latest_score` are required, and a demo home's values are wrong data for a real home; same rule as `/risk` and `/plan`
- Files: backend/app/services/passport.py, backend/app/api/homes.py, backend/app/api/public.py
- Commit: 816970a
- Affects the other coder? yes (front end assesses before showing the passport)

### 2026-10-28 · N14 · Passport property is the assessed property
- Decision: `Passport.property` is the latest assessment's `inputs.property`, so it carries our model's estimate (`source: "model"`) when the home had no EPC band
- Alternatives: the facts as entered (`source: "user"`)
- Why: the passport shows the band and CO2 the score was computed from, with the "Estimated by our model" label
- Files: backend/app/services/passport.py
- Commit: 816970a
- Affects the other coder? yes (`property.source` can be `"model"` on the passport)

### 2026-10-28 · N14 · Recorded work counts at once and in later assessments
- Decision: the current score is `compute_score(latest risk, assessed property, completed measures)`; used for `Passport.latest_score`, the homes list, `score_after` of the work event (with the new measure) and every new assessment
- Alternatives: count work only at the next assessment
- Why: spec N14 "recomputes the score with completed measures"; re-assessing must not drop the uplift
- Files: backend/app/services/passport.py, backend/app/services/assessment.py, backend/app/api/homes.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N14 · Demo homes keep their fixture score until work is recorded
- Decision: with no completed measures a demo home's score is its fixture score; after work it is `compute_score` with the fixture risk and the completed fixture-plan measures
- Alternatives: always recompute (would differ from the fixtures once L5 lands and before `make fixtures`)
- Why: keeps the five demo homes identical to their fixtures
- Files: backend/app/services/passport.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N14 · `score_after` is null for work on an unassessed home
- Decision: work can be recorded before a stored home's first assessment; its event has `score_after: null`
- Alternatives: refuse the work (400); use a fixture score
- Why: there is no score yet; `PassportEvent.score_after` allows null
- Files: backend/app/api/homes.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N14 · File and row order for certificates
- Decision: upload writes the file, then the event and `work_files` rows in one commit (the file is removed if the commit fails); deleting a home or account removes the rows first, then the files, and a file that fails to delete is logged, not raised
- Alternatives: rows first on upload; files first on delete
- Why: a row never points at a missing file; an orphan file is the only possible leftover and is logged
- Files: backend/app/services/homes.py, backend/app/api/auth.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N14 · Storage keys are only `<uuid>.<ext>`
- Decision: `LocalStorage` accepts only keys matching `^[0-9a-f]{32}\.(pdf|jpg|png)$` (made by `new_key`), writes through a temporary file and renames it
- Alternatives: accept any relative path
- Why: a key can never leave the uploads folder, and a half-written file is never served
- Files: backend/app/services/storage.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N14 · Demo homes' certificates stay in memory
- Decision: certificates recorded on the five demo homes are kept in memory, not in storage
- Alternatives: store them like real homes
- Why: demo homes are shared fixtures every logged-in user can open, with no owner or database row to delete them with
- Files: backend/app/api/homes.py
- Commit: 816970a
- Affects the other coder? no

### 2026-10-28 · N15 · "Seed the demo homes with full data" = cache their upstream data
- Decision: `make seed` writes each demo home's postcode details and both climate periods (from its fixture) into `api_cache`; no demo rows in the user tables, and the five demo homes stay fixture-served
- Alternatives: a demo user owning five database homes (needs a shared password)
- Why: meets the N15 check (Wi-Fi off, demo homes end to end) for both the demo list and a typed demo postcode, and never waits on a network timeout
- Files: backend/app/db/seed.py, backend/app/adapters/postcodes.py, backend/app/adapters/climate.py, README.md
- Commit: 60663c7
- Affects the other coder? no

### 2026-10-28 · N15 · Seeded entries use the normal cache lifetimes
- Decision: seeded postcode entries last 30 days and climate entries 90 days, like fetched ones; README says to run `make seed` before a demo
- Alternatives: never-expiring entries
- Why: no special case in the cache; a re-seed refreshes them from the fixtures
- Files: backend/app/db/seed.py, README.md
- Commit: 60663c7
- Affects the other coder? no

### 2026-10-28 · N15 · Seeded region from the nearest regional default
- Decision: a demo home's cached `PostcodeInfo.region` is `default_region(lat, lon).name`
- Alternatives: add a region to the fixtures (shared file)
- Why: the five demo homes sit well inside one region, and the fixtures stay unchanged
- Files: backend/app/db/seed.py
- Commit: 60663c7
- Affects the other coder? no

### 2026-10-28 · N15 · Live flood warnings are never seeded
- Decision: the EA warnings feed is not cached by the seed; offline it counts 0
- Alternatives: seed the fixture's warning count
- Why: a seeded count would hide real warnings when online
- Files: backend/app/db/seed.py
- Commit: 60663c7
- Affects the other coder? no

### 2026-10-28 · N15 · Coverage with greenlet tracing; `pytest-cov` dev dependency
- Decision: `pytest-cov` in the dev group, `[tool.coverage.run] concurrency = ["greenlet", "thread"]`, and `make coverage`
- Alternatives: no coverage tool
- Why: spec N15 "test coverage of every route"; without greenlet tracing, lines after an async database call look untested (homes routes showed 55% instead of 99%)
- Files: backend/pyproject.toml, backend/uv.lock, Makefile
- Commit: 60663c7
- Affects the other coder? no

### 2026-10-28 · S00 · Studio foundation: resolve_home, auto-discovery, dual OpenAPI
- Decision: `resolve_home(ref, session, user)` in `app/studio/common/home_ref.py` accepts either
  a home UUID (owner-only, login required, same 404/401 shape as `/homes/{id}`) or a
  `demo-<slug>` ref (public, no login, same source as `GET /demo/homes`). Every feature calls it
  the same way. `app/studio/router.py` auto-discovers `app/studio/features/<id>_*` packages at
  import time (skipping ids in `STUDIO_DISABLED`) and mounts them on the main app with
  `include_in_schema=False`, so `docs/openapi.json` stays byte-identical — proven by a test that
  diffs the file's own `paths` for a `/studio` prefix. Studio's own schema is snapshotted
  separately by `backend/scripts/export_openapi_studio.py` into `docs/openapi-studio.json` (a
  throwaway `FastAPI()` with only the Studio routers, included normally) and typed into
  `frontend/src/features/studio/api/schema.d.ts` via `make studio-types`.
- Also: demo refs get a human label (`demo_label()`) instead of exposing nothing, matching the
  HomeChip spec ("Demo · Flood-zone terrace"); `completed_measure_ids` reuses `passports.completed`
  for both demo and real homes via `store.homes[...]` rather than re-deriving it.
- Alternatives: a single `GET /studio/homes/{ref}` dependency wired through FastAPI `Depends`
  end-to-end (rejected — `resolve_home` is called directly inside handlers, not just declared on
  routes, so the optional-login dependency (`MaybeUser`) only resolves when a route itself
  declares it, not when a function calling `resolve_home` is invoked manually); including Studio
  in the main `docs/openapi.json` (rejected by spec §1.4 — would force L's generated types to
  carry 20 features' worth of schemas)
- Why: spec §1.1–§1.4, §3; keeps Studio fully isolated from L's contract surface while reusing
  the same auth/ownership rules as the real journey
- Files: backend/app/studio/**, backend/scripts/export_openapi_studio.py,
  backend/scripts/record_studio_fallbacks.py, backend/tests/studio/**, backend/app/main.py,
  backend/app/config.py, .env.example, Makefile, frontend/src/app/studio/**,
  frontend/src/features/studio/**, frontend/package.json
- PR: #29
- Affects the other coder? no — purely additive, verified `make test`/`make lint`/`pnpm build`
  all green and docs/openapi.json unchanged

### 2026-10-28 · S01 · Retrofit Sandbox: one house diagram, not five
- Decision: drew one schematic SVG house with the spec's six hotspot regions
  (roof/walls/windows/door/ground/services) that highlight when a measure there is applied,
  instead of five separate hand-drawn isometric templates (terrace/semi/detached/bungalow/flat)
  with per-measure visual layers. Click-to-toggle measure chips (not HTML5 drag-and-drop) drive
  the sandbox — the spec already asks for an "Add" button alternative for keyboard/touch, so
  that path became the only path.
- Also: `resolve_home`'s home-summary conversion was duplicated in `router.py`'s hub route and
  would have been duplicated again here, so it moved to a shared `summarize()` in
  `common/home_ref.py` (used by both).
- Alternatives: the full five-template, per-measure-layer build as written (explicitly scoped
  down by the human given the 1 am deadline across all 20 features)
- Why: the data/interaction model (hotspot grouping, live score simulation, save-as-plan) is
  what §13 rule 1 and the acceptance test actually check; the illustration fidelity is not
  load-bearing for any test or the contract
- Files: backend/app/studio/features/s01_retrofit_sandbox/**, backend/tests/studio/test_s01_retrofit_sandbox.py,
  backend/app/studio/common/home_ref.py, backend/app/studio/router.py,
  frontend/src/features/studio/s01/**, frontend/src/features/studio/components/Dial.tsx,
  frontend/src/app/studio/[ref]/s01-retrofit-sandbox/page.tsx
- PR: #30
- Affects the other coder? no

### 2026-10-28 · S02 · Street Proof: new adapter primitives, earliest/latest only
- Decision: added `search_postcode_rows`, `certificate_by_number`, `decode_field` and
  `property_type_from_certificate` to N6's `app/adapters/epc.py`, and `nearest_postcodes` to
  N5's `app/adapters/postcodes.py` — new exported functions, no existing signature changed.
  To bound the number of EPC certificate fetches per request (concurrency 5, 12s budget), only
  the earliest and latest certificate per address are fetched in full, not every certificate in
  an address's history — the spec's own algorithm only ever compares earliest vs latest, so
  nothing is lost.
- Also: fixed a real inference bug while testing against hand-written RdSAP wording — `"no
  insulation"` contains the substring `"insulat"`, so a naive `"insulat" in earliest and
  "insulat" in latest"` check never fires; `_newly_insulated()` checks the negative phrase is
  gone instead.
- Alternatives: fetching every certificate in a group's history (rejected — unbounded fetch
  count for a popular street); keyword rules tuned to the SAP-Schema test fixture's U-value
  wording (rejected — real-world homes are almost all on RdSAP, which uses the spec's assumed
  "no insulation (assumed)" / "as built, insulated" wording; the newer SAP schema's numeric
  U-value descriptions aren't matchable by text either way)
- Why: §1.7 (bounded external calls, tests never touch network); the acceptance test needs real
  RdSAP-shaped fixtures, which is how the substring bug was caught
- Files: backend/app/adapters/epc.py, backend/app/adapters/postcodes.py,
  backend/app/studio/features/s02_street_proof/**, backend/tests/studio/test_s02_street_proof.py,
  frontend/src/features/studio/s02/**, frontend/src/app/studio/[ref]/s02-street-proof/page.tsx
- PR: #31
- Affects the other coder? no

### 2026-10-28 · S03 · Meter Fingerprint: no persistence table yet; static UK climatology
- Decision: implemented the full change-point regression, bootstrap CI and HTC pipeline, but
  skipped the `studio_meter_fingerprints` table the spec names (owner homes would store only
  the result JSON, cascade-deleted with the home). Every request recomputes from the upload;
  nothing is written anywhere either way, so the privacy requirement ("never store raw uploaded
  meter data") holds trivially, it's just not yet *saved* for a returning user. Also used a
  static 1991-2020 UK monthly-mean-temperature table (config.py, Met Office averages, flagged
  "verify") for the secondary "normalised annual heating" stat instead of a second 30-year ERA5
  pull per upload — the headline HTC number is unaffected either way.
- Alternatives: add the table + Alembic migration + export-flow wiring now (deferred — time
  budget across 20 features; this is pure persistence, not correctness, and is a cheap follow-up)
- Why: the "wow" and the measured number are both real and tested; the gap is a save-for-later
  convenience, not a privacy or correctness issue
- Files: backend/app/studio/features/s03_meter_fingerprint/**, backend/tests/studio/test_s03_meter_fingerprint.py,
  frontend/src/features/studio/s03/**, frontend/src/app/studio/[ref]/s03-meter-fingerprint/page.tsx
- PR: #32
- Affects the other coder? no

### 2026-10-28 · S04 · Heat Pump Year: radial calendar simplified; sourced figures logged
- Decision: built the full hour-by-hour change-point heat demand + COP simulation over a real
  ERA5 year, sizing, and cost/CO2/grant maths exactly per spec, but replaced the bespoke SVG
  "radial year" clock with two Recharts charts (monthly HP-vs-gas cost bars, daily mean-COP
  line) - same data, same interactivity (flow-temp switch re-simulates), simpler chrome, per the
  frontend-effort calibration agreed for this batch of features.
- Also: looked up and recorded the **verify**-flagged figures live on 2026-10-28 rather than
  inventing them - Ofgem Direct Debit cap Oct-Dec 2026 (26.32p/kWh elec, 7.97p/kWh gas; 54.83p
  and 29.68p standing charges), Boiler Upgrade Scheme £7,500 standard grant, and DESNZ 2026 CO2
  factors (0.13096 kg/kWh elec, 0.18231 kg/kWh gas) via a third-party citation of the official
  workbook cells (not the workbook itself - flagged for re-verification). No heat-pump row exists
  yet in `measures.csv`, so install cost uses a config range (£8,000-£14,000) sourced to the MCS
  dashboard's reported 2025 average and 2026 trade-guide ranges.
- Why: the "wow" the spec describes is the per-home simulation and the coldest-hour callout, not
  the clock widget specifically; a correct, tested simulation with an honest chart beats a
  prettier one that risks shipping late or wrong
- Files: backend/app/studio/features/s04_heat_pump_year/**, backend/tests/studio/test_s04_heat_pump_year.py,
  frontend/src/features/studio/s04/**, frontend/src/app/studio/[ref]/s04-heat-pump-year/page.tsx
- PR: #33
- Affects the other coder? no

### 2026-10-28 · S05 · Solar Roof Studio: no bespoke sun-path UI; sourced figures logged
- Decision: built the roof-area kWp estimator, PVGIS adapter (plus an 8-direction orientation
  rose, scaled linearly by kWp per the spec), self-use/export savings maths, payback/breakeven
  and suitability bands exactly per spec, but used a Recharts RadarChart for the orientation
  rose and bar chart for monthly generation instead of the spec's draggable-compass roof plan
  with an animated NOAA sun-path - same calibration as S01/S04's simplifications.
- Sourced figures read live on 2026-10-28 (logged here rather than invented): Ofgem import rate
  (same 26.32p/kWh as S04), a representative 15p/kWh SEG export rate (no single Ofgem "guide
  rate" exists - suppliers set their own, ranging roughly 4p-30p in late 2026; user can override
  via `export_p_per_kwh`), and an MCS/DESNZ-derived £1,500-£2,000/kWp install cost range (no
  solar row exists yet in `measures.csv`).
- Why: the measured generation estimate, rose and payback are the substance; the sun-path
  animation is presentation on top of the same numbers
- Files: backend/app/studio/features/s05_solar_roof_studio/**, backend/tests/studio/test_s05_solar_roof_studio.py,
  frontend/src/features/studio/s05/**, frontend/src/app/studio/[ref]/s05-solar-roof-studio/page.tsx
- PR: #?
- Affects the other coder? no
