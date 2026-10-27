# L's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · L1 · pnpm 12 build-script allowlist
- Decision: `frontend/pnpm-workspace.yaml` allows install scripts only for `sharp` and `unrs-resolver`
- Alternatives: allow all build scripts
- Why: pnpm 12 blocks dependency install scripts by default and fails the install; allowing only what Next.js and ESLint need keeps the supply-chain check on (rule 3)
- Files: frontend/pnpm-workspace.yaml
- Commit: a2ca8be
- Affects the other coder? no

### 2026-10-27 · L1 · shadcn/ui "Nova" preset on Radix, brand colours on top
- Decision: `shadcn init -b radix -p nova`; the shadcn colour variables are set from the spec palette (primary = deep green, secondary/muted = mint, destructive = risk red, ring = green), plus named tokens `deep`, `green`, `mint`, `warning`, `risk`, `level-low/medium/high`
- Alternatives: hand-written Tailwind config without shadcn variables
- Why: shadcn components pick up the brand automatically; level colours live in one place for cards, charts and maps (rule 6)
- Files: frontend/src/app/globals.css, frontend/src/lib/theme.ts, frontend/components.json
- Commit: a2ca8be
- Affects the other coder? no

### 2026-10-27 · L1 · No dark theme in M1
- Decision: removed shadcn's `.dark` colour block
- Alternatives: keep an unused dark palette
- Why: no toggle is planned and an untested palette could fail contrast checks in L14 (rule 3)
- Files: frontend/src/app/globals.css
- Commit: a2ca8be
- Affects the other coder? no

### 2026-10-27 · L1 · Prettier style and lint gates
- Decision: Prettier (no semicolons, width 100, Tailwind class sorting) with `eslint-config-prettier`; CI runs `pnpm lint && pnpm format:check`, `pnpm typecheck`, `pnpm test` (vitest), `pnpm build`
- Alternatives: ESLint only
- Why: spec §2 lists eslint, prettier, tsc and vitest; width 100 matches the back end's ruff setting (rule 6)
- Files: frontend/.prettierrc.json, frontend/eslint.config.mjs, frontend/vitest.config.ts, .github/workflows/ci.yml
- Commit: a2ca8be
- Affects the other coder? no

### 2026-10-27 · L1 · Footer links to `/privacy` before the page exists
- Decision: the footer has the attribution text and a `/privacy` link now; the page arrives in L13
- Alternatives: add the link in L13
- Why: CONTRACT §6 rule 3 requires the footer link; the shell is its natural home (rule 6)
- Files: frontend/src/components/app-shell/site-footer.tsx
- Commit: a2ca8be
- Affects the other coder? no

### 2026-10-27 · L3 · `completed_measures` defaults to `()` not `[]`
- Decision: `compute_score(risk, prop, completed_measures: Sequence[Measure] = ())`; `match_funding` takes `Sequence[FundingOption]`
- Alternatives: `list[Measure] = []` exactly as written in spec §4.3
- Why: a mutable default is a classic Python bug (ruff B006); callers passing a list or nothing work the same (rule 3)
- Files: backend/app/scoring/score.py, backend/app/scoring/funding.py
- Commit: 82bbc89
- Affects the other coder? no (call sites are unchanged)

### 2026-10-27 · L3 · All §6/§7 numbers are in `scoring/config.py` from the start
- Decision: thresholds, weights, band floors, EPC band midpoints and the 60-month loan term are named constants now, even though the stub does not use them yet; overheating uses the 28 °C hot-day count (CONTRACT §2)
- Alternatives: add them in L4–L6
- Why: one place to review at Merge 1 with A; tests import the same constants (spec §2 Config)
- Files: backend/app/scoring/config.py
- Commit: 82bbc89
- Affects the other coder? no

### 2026-10-27 · L3 · Stub values
- Decision: every hazard `medium`, every component at half points (score 50, band D), funding with no lines and the whole cost as the gap; fixed `generated_at`
- Alternatives: copy the fixture outputs
- Why: obviously placeholder on screen, schema-valid, deterministic; N9 can wire the pipeline before L4 (rule 1)
- Files: backend/app/scoring/risk.py, backend/app/scoring/score.py, backend/app/scoring/funding.py
- Commit: 82bbc89
- Affects the other coder? yes (the stub ignores inputs until L4/L5/L6 merge)

### 2026-10-27 · L2 · Mock mode swaps `fetch`, not the client
- Decision: with `NEXT_PUBLIC_API_MOCK=1`, `openapi-fetch` gets a mock `fetch` (`src/mocks/handler.ts`) that answers `/api/v1/...` from the fixtures, following the stub API's rules (cookie-less login kept in `sessionStorage`, 401/404/400 codes, share/revoke). Work uploads and certificate downloads are not mocked yet
- Alternatives: `if (MOCK) return fixture` branches in every call; MSW (new dependency)
- Why: page code is identical in both modes, so `/dev/contract` proves the same code against both; no new dependency (rule 3, rule 6)
- Files: frontend/src/mocks/handler.ts, frontend/src/lib/api/client.ts
- Commit: 1cc384a
- Affects the other coder? no

### 2026-10-27 · L2 · Contract checks are one shared list
- Decision: `src/lib/api/contract-checks.ts` holds the 19 checks; the `/dev/contract` page renders them, and vitest runs them in mock mode on every CI run and against a live API when `CONTRACT_API_URL` is set
- Alternatives: page-only checks
- Why: CI catches mock/contract drift without a browser; the page and tests can never disagree (rule 3)
- Files: frontend/src/lib/api/contract-checks.ts, frontend/src/lib/api/contract-checks.test.ts, frontend/src/app/dev/contract/
- Commit: 1cc384a
- Affects the other coder? no

### 2026-10-27 · L2 · `mocks:sync` writes an index and runs before dev, build, typecheck and test
- Decision: the sync script copies the fixture JSON and generates `src/mocks/fixtures/index.ts` (git-ignored); `pnpm dev`, `build`, `typecheck` and `test` run it first
- Alternatives: run it only before `dev` and `build` as spec §4.4 says
- Why: the mock handler imports the fixtures, so `tsc` and vitest need them too, including in CI (rule 1)
- Files: frontend/scripts/mocks-sync.mjs, frontend/package.json
- Commit: 1cc384a
- Affects the other coder? no

### 2026-10-27 · L2 · Minimal `/login` and `/homes` pages now
- Decision: a bare log-in form (redirects to a same-site `next` only) and a protected "My homes" list, so the `RequireUser` redirect has a real target; L13 replaces both with the full account pages
- Alternatives: redirect to a page that does not exist yet
- Why: the L2 check needs a protected page that redirects to a working `/login` (rule 1)
- Files: frontend/src/app/login/, frontend/src/app/homes/, frontend/src/components/auth/require-user.tsx, frontend/src/lib/auth/use-user.ts
- Commit: 1cc384a
- Affects the other coder? no

### 2026-10-27 · L2 · CI fails on stale `schema.d.ts`
- Decision: the front-end CI job runs `pnpm types` and `git diff --exit-code src/lib/api/schema.d.ts`; `schema.d.ts` is excluded from Prettier and ESLint so the generated file is committed as generated
- Alternatives: format the generated file
- Why: CONTRACT §3 (b); formatting would make the drift check depend on Prettier's version
- Files: .github/workflows/ci.yml, Makefile, frontend/.prettierignore, frontend/eslint.config.mjs
- Commit: 1cc384a
- Affects the other coder? yes (after any API change N runs `make openapi` and `make types` and commits both)

### 2026-10-27 · L2 · New dependencies `openapi-fetch`, `openapi-typescript`
- Decision: added to the front end
- Alternatives: none; spec §2 locks both
- Why: required by L2
- Files: frontend/package.json, frontend/pnpm-lock.yaml
- Commit: 1cc384a
- Affects the other coder? no
