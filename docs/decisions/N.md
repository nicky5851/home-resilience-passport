# N's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · N1 · Async Postgres driver from the start
- Decision: `DATABASE_URL` uses `postgresql+asyncpg://`
- Alternatives: sync `psycopg` now, switch in N10
- Why: fastapi-users' SQLAlchemy adapter needs an async session; avoids a driver change mid-build (rule 3)
- Files: backend/app/config.py, .env.example, .github/workflows/ci.yml
- Commit: 5427e2a
- Affects the other coder? no

### 2026-10-27 · N1 · Makefile targets for later steps are placeholders
- Decision: `openapi`, `types`, `seed`, `validate-data`, `fixtures`, `train` exist now but print the step that adds them and exit 1
- Alternatives: leave them out until their step
- Why: CLAUDE.md lists them; a clear message beats "No rule to make target" (rule 5)
- Files: Makefile
- Commit: 5427e2a
- Affects the other coder? no

### 2026-10-27 · N1 · Node version pinned in `.nvmrc`
- Decision: `.nvmrc` = `22`; `backend/.python-version` = `3.12`
- Alternatives: rely on the README only
- Why: `nvm use` / `uv` pick the right runtimes automatically (spec §2)
- Files: .nvmrc, backend/.python-version
- Commit: 5427e2a
- Affects the other coder? no

### 2026-10-27 · N2 · Fixtures written by a generator script
- Decision: `backend/scripts/placeholder_fixtures.py` writes the 5 fixtures; outputs use a rough copy of spec §6/§7 so they add up
- Alternatives: hand-written JSON
- Why: five large files stay consistent and schema-valid; rerun after any schema change until `make fixtures` (N8) replaces it (rule 3)
- Files: backend/scripts/placeholder_fixtures.py, backend/tests/fixtures/demo_homes/
- Commit: ac223ac
- Affects the other coder? yes (output parts are placeholders, not L's scoring; measures/funding rows are placeholders until A's CSVs)

### 2026-10-27 · N2 · Contract models reject unknown keys
- Decision: every schema model uses `extra="forbid"`
- Alternatives: Pydantic's default (ignore extra keys)
- Why: a misspelt field in a fixture or request fails loudly instead of silently becoming `null` (rule 3)
- Files: backend/app/schemas/base.py
- Commit: ac223ac
- Affects the other coder? yes (a request body with an extra key gets `400 validation`)

### 2026-10-27 · N2 · `HazardLevel.data_source` stays `str`
- Decision: typed `str` exactly as spec §4.1; the five allowed strings are `DATA_SOURCES` and checked in `test_schemas.py`
- Alternatives: a `Literal` of the five strings
- Why: follow §4.1 to the letter; the test still catches a wrong string (rule 2)
- Files: backend/app/schemas/hazards.py, backend/tests/test_schemas.py
- Commit: ac223ac
- Affects the other coder? no

### 2026-10-27 · N2 · `Passport` extends `PublicPassport`
- Decision: `PublicPassport` is the base class; `Passport` adds `household` and `share_token`
- Alternatives: two independent classes
- Why: the public model cannot gain household data by accident; FastAPI's response model strips the extra fields (rule 5)
- Files: backend/app/schemas/passport.py
- Commit: ac223ac
- Affects the other coder? no
