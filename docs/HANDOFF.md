# Handoff after the Foundation

The Foundation (N0–N4, L0–L3) is merged into `main` and tagged `contract-v1`. All five seams in
[`CONTRACT.md`](CONTRACT.md) are built and checked by CI. Read [`CODING_SPEC.md`](CODING_SPEC.md)
and `CONTRACT.md` first; this page only says where each person starts.

Rules for everyone: work on a branch (`n/<step>-<slug>` or `l/<step>-<slug>`), one PR per step.
PRs into `main` need green `backend` and `frontend` checks, and are squash-merged. Merge at least
once a day, and by 9 pm the night before a sync meeting. Next meeting: **Merge 1, Tue 3 Nov**.

## N: back end, data, AI

**Set up.** Install Git, Docker Desktop, Python 3.12, `uv`, Node 22 (`nvm use`) and `pnpm`, then:

```bash
git clone https://github.com/nicky5851/home-resilience-passport.git && cd home-resilience-passport
cp .env.example .env      # add EPC_API_TOKEN when you have it
make install && make seed # Postgres, migrations, reference data
make dev                  # API :8000, front end :3000; open /dev/contract, all 19 green
make test && make lint
```

**Start on N5** (postcode adapter), then N6 → N7 → N8 → N9. Merge N8 and N9 before Merge 1.

**You own** `backend/` (except `app/scoring/` and `tests/scoring/`), `backend/ml/`, `infra/`,
`.github/`, `Makefile`, `README.md`, `docs/model_card.md`, `docs/decisions/N.md`, and loading
`data/reference/` (A owns the values).

**Good to know.**
- The stub in `backend/app/api/stub_store.py` is replaced route by route (N9 assess, N10 auth, N11 plan, N14 passport).
- Call scoring only through `from app.scoring import assess_risk, compute_score, match_funding`.
- After any API change, run `make openapi` and `make types` and commit both files. CI fails otherwise.
- The tables are ready in `backend/app/db/models.py`. Add new columns with an Alembic migration.

## L: front end, scoring

**Set up.** Use the same tools and clone as N, then:

```bash
make install && make dev                      # or, without the back end:
cd frontend && NEXT_PUBLIC_API_MOCK=1 pnpm dev # fixtures only
```

Open http://localhost:3000/dev/contract. All 19 checks should be green in both modes.

**Start on L4** (risk engine in `backend/app/scoring/risk.py`), then L5 → L6. L7 → L8 → L9
(journey pages) can run in parallel. Merge L5 and L9 before Merge 1.

**You own** `frontend/`, `backend/app/scoring/` (risk, score, funding), `backend/tests/scoring/`
(put expected values in `expected/`), `docs/scoring.md`, `docs/decisions/L.md`.

**Good to know.**
- Every §6/§7 number is already in `backend/app/scoring/config.py`. Overheating counts days at **28 °C**.
- Make API calls with `api` and `unwrap` from `@/lib/api/client`. Take types from `@/lib/api/types`. Response models are the `-Output` variants. Never hand-write API types.
- `/login` and `/homes` are minimal placeholders until L13.
- Mock mode does not cover work uploads yet.
- Read the "Affects the other coder? yes" entries in `docs/decisions/N.md` first.

## A: data, research, deck

**Set up.** No code is needed. Accept the GitHub invite to read the repo. To see the app, ask N or L
for a demo, or follow L's setup in mock mode.

**Start on the three reference sheets.** Today they hold placeholders: 8 measures with
`example.com` sources, 5 illustrative funding rows, and 5 demo homes.
1. Fill `measures.csv`, `funding.csv` and `demo_homes.csv` in Google Sheets with **exactly** the columns in `CONTRACT.md` §5.
2. Export as CSV and send the files to N. N commits them in a PR, and CI runs `make validate-data`, which names the file, row and column of every problem.
3. Every measure needs a real `source_url`. Lloyds rows must have `is_mock = true`. The five demo homes need at least one renter, one `under_20k` household and one vulnerable household.

**You own** the values in `data/reference/*.csv`. Coders never change a value, they only report
problems. You also review the scoring thresholds in `docs/scoring.md` at Merge 1 (Tue 3 Nov).
