# N's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · N1 · Async Postgres driver from the start
- Decision: `DATABASE_URL` uses `postgresql+asyncpg://`
- Alternatives: sync `psycopg` now, switch in N10
- Why: fastapi-users' SQLAlchemy adapter needs an async session; avoids a driver change mid-build (rule 3)
- Files: backend/app/config.py, .env.example, .github/workflows/ci.yml
- Commit: 6c95cd4
- Affects the other coder? no

### 2026-10-27 · N1 · Makefile targets for later steps are placeholders
- Decision: `openapi`, `types`, `seed`, `validate-data`, `fixtures`, `train` exist now but print the step that adds them and exit 1
- Alternatives: leave them out until their step
- Why: CLAUDE.md lists them; a clear message beats "No rule to make target" (rule 5)
- Files: Makefile
- Commit: 6c95cd4
- Affects the other coder? no

### 2026-10-27 · N1 · Node version pinned in `.nvmrc`
- Decision: `.nvmrc` = `22`; `backend/.python-version` = `3.12`
- Alternatives: rely on the README only
- Why: `nvm use` / `uv` pick the right runtimes automatically (spec §2)
- Files: .nvmrc, backend/.python-version
- Commit: 6c95cd4
- Affects the other coder? no
