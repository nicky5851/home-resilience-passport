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
- Commit: d441770
- Affects the other coder? yes (output parts are placeholders, not L's scoring; measures/funding rows are placeholders until A's CSVs)

### 2026-10-27 · N2 · Contract models reject unknown keys
- Decision: every schema model uses `extra="forbid"`
- Alternatives: Pydantic's default (ignore extra keys)
- Why: a misspelt field in a fixture or request fails loudly instead of silently becoming `null` (rule 3)
- Files: backend/app/schemas/base.py
- Commit: d441770
- Affects the other coder? yes (a request body with an extra key gets `400 validation`)

### 2026-10-27 · N2 · `HazardLevel.data_source` stays `str`
- Decision: typed `str` exactly as spec §4.1; the five allowed strings are `DATA_SOURCES` and checked in `test_schemas.py`
- Alternatives: a `Literal` of the five strings
- Why: follow §4.1 to the letter; the test still catches a wrong string (rule 2)
- Files: backend/app/schemas/hazards.py, backend/tests/test_schemas.py
- Commit: d441770
- Affects the other coder? no

### 2026-10-27 · N2 · `Passport` extends `PublicPassport`
- Decision: `PublicPassport` is the base class; `Passport` adds `household` and `share_token`
- Alternatives: two independent classes
- Why: the public model cannot gain household data by accident; FastAPI's response model strips the extra fields (rule 5)
- Files: backend/app/schemas/passport.py
- Commit: d441770
- Affects the other coder? no

### 2026-10-27 · N3 · Route bodies live in `schemas/api.py`
- Decision: the §4.2 shorthand shapes (`PostcodeLookup`, `HomeCreate`, `HomeCreated`, `HomeSummary`, `Assessment`, `PlanRequest`, `FundingRequest`, `ShareLink`, `ModelInfo`, `ErrorBody`, `ForgotPassword`, `ResetPassword`) are Pydantic models in the shared schemas package
- Alternatives: define them inside N's routers
- Why: they are contract (the front end's types come from them); keeping them with §4.1 makes every contract change one place (rule 2, rule 6)
- Files: backend/app/schemas/api.py
- Commit: <hash>
- Affects the other coder? yes (new type names in `schema.d.ts`)

### 2026-10-27 · N3 · `HomeSummary.score` is a full `ResilienceScore | null`
- Decision: `GET /homes` returns the whole latest score object, not just the number
- Alternatives: `score: int | null`
- Why: §4.2 writes `score?` without a type; the "My homes" list can show the band without another call (rule 1)
- Files: backend/app/schemas/api.py
- Commit: <hash>
- Affects the other coder? yes

### 2026-10-27 · N3 · Response fields are required in OpenAPI
- Decision: `json_schema_serialization_defaults_required=True` on every contract model
- Alternatives: leave defaults optional in the schema
- Why: CONTRACT §1 rule 2 says every field is always present; otherwise the generated TS types mark nullable fields optional. Side effect: `Address`, `Household`, `PropertyFacts` appear as `-Input` / `-Output` in OpenAPI
- Files: backend/app/schemas/base.py, docs/openapi.json
- Commit: <hash>
- Affects the other coder? yes (use `components["schemas"]["PropertyFacts-Output"]` etc. for responses)

### 2026-10-27 · N3 · Stub state is in memory
- Decision: `app/api/stub_store.py` keeps homes, events, certificates and share links in a process-local dict; demo homes are readable by any logged-in user
- Alternatives: write the stub against the database now
- Why: N4 builds the tables, N9/N10/N14 replace the stub piece by piece; memory keeps N3 small (rule 3)
- Files: backend/app/api/stub_store.py
- Commit: <hash>
- Affects the other coder? no (restarting the API forgets stub homes)

### 2026-10-27 · N3 · `POST /homes/{id}/work` returns 200
- Decision: 200 with the `PassportEvent`
- Alternatives: 201
- Why: the contract names 201 only for `POST /homes`; keep FastAPI's default elsewhere (rule 2)
- Files: backend/app/api/homes.py
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · N3 · Unlisted 4xx statuses map to `validation`
- Decision: e.g. 405 returns `code="validation"`; 422 never appears (converted to 400 and removed from OpenAPI)
- Alternatives: invent new codes
- Why: CONTRACT §3 lists a closed set of codes (rule 2)
- Files: backend/app/api/errors.py, backend/app/main.py
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · N3 · New dependency `python-multipart`
- Decision: added to the back end
- Alternatives: none; FastAPI needs it for form-encoded login and multipart uploads
- Why: required by CONTRACT §4 and §6
- Files: backend/pyproject.toml, backend/uv.lock
- Commit: <hash>
- Affects the other coder? no
