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
