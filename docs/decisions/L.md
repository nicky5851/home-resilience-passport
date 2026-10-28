# L's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · L1 · pnpm 12 build-script allowlist
- Decision: `frontend/pnpm-workspace.yaml` allows install scripts only for `sharp` and `unrs-resolver`
- Alternatives: allow all build scripts
- Why: pnpm 12 blocks dependency install scripts by default and fails the install; allowing only what Next.js and ESLint need keeps the supply-chain check on (rule 3)
- Files: frontend/pnpm-workspace.yaml
- Commit: 6c6f30f
- Affects the other coder? no

### 2026-10-27 · L1 · shadcn/ui "Nova" preset on Radix, brand colours on top
- Decision: `shadcn init -b radix -p nova`; the shadcn colour variables are set from the spec palette (primary = deep green, secondary/muted = mint, destructive = risk red, ring = green), plus named tokens `deep`, `green`, `mint`, `warning`, `risk`, `level-low/medium/high`
- Alternatives: hand-written Tailwind config without shadcn variables
- Why: shadcn components pick up the brand automatically; level colours live in one place for cards, charts and maps (rule 6)
- Files: frontend/src/app/globals.css, frontend/src/lib/theme.ts, frontend/components.json
- Commit: 6c6f30f
- Affects the other coder? no

### 2026-10-27 · L1 · No dark theme in M1
- Decision: removed shadcn's `.dark` colour block
- Alternatives: keep an unused dark palette
- Why: no toggle is planned and an untested palette could fail contrast checks in L14 (rule 3)
- Files: frontend/src/app/globals.css
- Commit: 6c6f30f
- Affects the other coder? no

### 2026-10-27 · L1 · Prettier style and lint gates
- Decision: Prettier (no semicolons, width 100, Tailwind class sorting) with `eslint-config-prettier`; CI runs `pnpm lint && pnpm format:check`, `pnpm typecheck`, `pnpm test` (vitest), `pnpm build`
- Alternatives: ESLint only
- Why: spec §2 lists eslint, prettier, tsc and vitest; width 100 matches the back end's ruff setting (rule 6)
- Files: frontend/.prettierrc.json, frontend/eslint.config.mjs, frontend/vitest.config.ts, .github/workflows/ci.yml
- Commit: 6c6f30f
- Affects the other coder? no

### 2026-10-27 · L1 · Footer links to `/privacy` before the page exists
- Decision: the footer has the attribution text and a `/privacy` link now; the page arrives in L13
- Alternatives: add the link in L13
- Why: CONTRACT §6 rule 3 requires the footer link; the shell is its natural home (rule 6)
- Files: frontend/src/components/app-shell/site-footer.tsx
- Commit: 6c6f30f
- Affects the other coder? no

### 2026-10-27 · L3 · `completed_measures` defaults to `()` not `[]`
- Decision: `compute_score(risk, prop, completed_measures: Sequence[Measure] = ())`; `match_funding` takes `Sequence[FundingOption]`
- Alternatives: `list[Measure] = []` exactly as written in spec §4.3
- Why: a mutable default is a classic Python bug (ruff B006); callers passing a list or nothing work the same (rule 3)
- Files: backend/app/scoring/score.py, backend/app/scoring/funding.py
- Commit: 5adec19
- Affects the other coder? no (call sites are unchanged)

### 2026-10-27 · L3 · All §6/§7 numbers are in `scoring/config.py` from the start
- Decision: thresholds, weights, band floors, EPC band midpoints and the 60-month loan term are named constants now, even though the stub does not use them yet; overheating uses the 28 °C hot-day count (CONTRACT §2)
- Alternatives: add them in L4–L6
- Why: one place to review at Merge 1 with A; tests import the same constants (spec §2 Config)
- Files: backend/app/scoring/config.py
- Commit: 5adec19
- Affects the other coder? no

### 2026-10-27 · L3 · Stub values
- Decision: every hazard `medium`, every component at half points (score 50, band D), funding with no lines and the whole cost as the gap; fixed `generated_at`
- Alternatives: copy the fixture outputs
- Why: obviously placeholder on screen, schema-valid, deterministic; N9 can wire the pipeline before L4 (rule 1)
- Files: backend/app/scoring/risk.py, backend/app/scoring/score.py, backend/app/scoring/funding.py
- Commit: 5adec19
- Affects the other coder? yes (the stub ignores inputs until L4/L5/L6 merge)

### 2026-10-27 · L2 · Mock mode swaps `fetch`, not the client
- Decision: with `NEXT_PUBLIC_API_MOCK=1`, `openapi-fetch` gets a mock `fetch` (`src/mocks/handler.ts`) that answers `/api/v1/...` from the fixtures, following the stub API's rules (cookie-less login kept in `sessionStorage`, 401/404/400 codes, share/revoke). Work uploads and certificate downloads are not mocked yet
- Alternatives: `if (MOCK) return fixture` branches in every call; MSW (new dependency)
- Why: page code is identical in both modes, so `/dev/contract` proves the same code against both; no new dependency (rule 3, rule 6)
- Files: frontend/src/mocks/handler.ts, frontend/src/lib/api/client.ts
- Commit: 038b0d5
- Affects the other coder? no

### 2026-10-27 · L2 · Contract checks are one shared list
- Decision: `src/lib/api/contract-checks.ts` holds the 19 checks; the `/dev/contract` page renders them, and vitest runs them in mock mode on every CI run and against a live API when `CONTRACT_API_URL` is set
- Alternatives: page-only checks
- Why: CI catches mock/contract drift without a browser; the page and tests can never disagree (rule 3)
- Files: frontend/src/lib/api/contract-checks.ts, frontend/src/lib/api/contract-checks.test.ts, frontend/src/app/dev/contract/
- Commit: 038b0d5
- Affects the other coder? no

### 2026-10-27 · L2 · `mocks:sync` writes an index and runs before dev, build, typecheck and test
- Decision: the sync script copies the fixture JSON and generates `src/mocks/fixtures/index.ts` (git-ignored); `pnpm dev`, `build`, `typecheck` and `test` run it first
- Alternatives: run it only before `dev` and `build` as spec §4.4 says
- Why: the mock handler imports the fixtures, so `tsc` and vitest need them too, including in CI (rule 1)
- Files: frontend/scripts/mocks-sync.mjs, frontend/package.json
- Commit: 038b0d5
- Affects the other coder? no

### 2026-10-27 · L2 · Minimal `/login` and `/homes` pages now
- Decision: a bare log-in form (redirects to a same-site `next` only) and a protected "My homes" list, so the `RequireUser` redirect has a real target; L13 replaces both with the full account pages
- Alternatives: redirect to a page that does not exist yet
- Why: the L2 check needs a protected page that redirects to a working `/login` (rule 1)
- Files: frontend/src/app/login/, frontend/src/app/homes/, frontend/src/components/auth/require-user.tsx, frontend/src/lib/auth/use-user.ts
- Commit: 038b0d5
- Affects the other coder? no

### 2026-10-27 · L2 · CI fails on stale `schema.d.ts`
- Decision: the front-end CI job runs `pnpm types` and `git diff --exit-code src/lib/api/schema.d.ts`; `schema.d.ts` is excluded from Prettier and ESLint so the generated file is committed as generated
- Alternatives: format the generated file
- Why: CONTRACT §3 (b); formatting would make the drift check depend on Prettier's version
- Files: .github/workflows/ci.yml, Makefile, frontend/.prettierignore, frontend/eslint.config.mjs
- Commit: 038b0d5
- Affects the other coder? yes (after any API change N runs `make openapi` and `make types` and commits both)

### 2026-10-27 · L2 · New dependencies `openapi-fetch`, `openapi-typescript`
- Decision: added to the front end
- Alternatives: none; spec §2 locks both
- Why: required by L2
- Files: frontend/package.json, frontend/pnpm-lock.yaml
- Commit: 038b0d5
- Affects the other coder? no

### 2026-10-27 · L4 · `RiskProfile.generated_at` is a fixed constant, not the system clock
- Decision: `assess_risk` returns a hardcoded `RISK_GENERATED_AT` (2026-10-27T09:00:00Z) instead of `datetime.now(UTC)`
- Alternatives: read the system clock inside `assess_risk`
- Why: `test_assess_risk_contract` calls `assess_risk` twice and asserts equality, and `test_functions_are_pure` requires no I/O; reading the clock would make two calls with the same input differ (rule 2 — contract test, not just convention)
- Files: backend/app/scoring/risk.py
- Commit: d26b0cf
- Affects the other coder? yes (N9's assessment pipeline must overwrite `generated_at` with the real time before storing/returning the assessment — the value coming out of `assess_risk` is not the real timestamp)

### 2026-10-27 · L4 · Subsidence and flood `why` text goes beyond the demo fixtures
- Decision: `why` varies per `subsidence_signal` value and mentions the active flood warning count, rather than the single constant sentence N's placeholder-fixture generator used
- Alternatives: match the placeholder fixtures' text exactly for continuity
- Why: CODING_SPEC.md's L4 step requires "every `HazardLevel.why` is a human sentence"; output parts of fixtures are not contract and L's own expected values live in `backend/tests/scoring/expected/` (spec §3.3), so divergence here is expected and does not break anything N owns
- Files: backend/app/scoring/risk.py, backend/tests/scoring/expected/*.json
- Commit: d26b0cf
- Affects the other coder? no

### 2026-10-28 · L5 · `surface_water` has no score component

- Decision: `compute_score` only scores `flood`, `heat`, `storm`, `subsidence`, `carbon`; `surface_water` is left out even though it is one of the 5 `HAZARD_ORDER` hazards
- Alternatives: fold it into `flood`'s points, or add a 6th component
- Why: spec §6's score table only lists 4 hazard components totalling 70%, plus carbon 30%; `HAZARD_COMPONENT` in `config.py` (written at L3) already excludes `surface_water`, so this just follows the existing constant
- Files: backend/app/scoring/score.py
- Commit: 7427591
- Affects the other coder? no

### 2026-10-28 · L5 · 0–100 clamp on `ResilienceScore.value` is a safeguard, not a real limiter

- Decision: `compute_score` clamps the summed value to `[0, 100]` even though each component is already bounded `[0, max_points]` by construction, so the sum is always in range
- Alternatives: no clamp, relying on the per-component bounds
- Why: CODING_SPEC.md's L5 Check explicitly requires "the score never goes above 100 or below 0"; a defensive clamp costs nothing and keeps that check true even if a future change to `LEVEL_FRACTION` or the carbon formula breaks the per-component bound
- Files: backend/app/scoring/score.py
- Commit: 7427591
- Affects the other coder? no

### 2026-10-28 · L7 · `country` for a picked address is guessed client-side from the postcode area
- Decision: `PostcodeLookup` (the lookup response) does not return `country`, even though `lookup_postcode` computes it server-side and `Address-Input` (needed for `POST /homes`) requires it. Rather than change the shared schema, `frontend/src/lib/journey/postcode.ts` guesses `england` vs `wales` from a short list of mostly-Welsh postcode areas (`CF`, `LD`, `LL`, `NP`, `SA`, `SY`)
- Alternatives: add `country` to `PostcodeLookup` (shared schema/contract change, needs N's sign-off); always send `england` and let the backend overwrite it later
- Why: rule 2 of §13 ("do not change the shared contract; work around it in your own paths") — this is cosmetic (it only affects the stored `Address.country` label, nothing in scoring or risk, which recompute hazard data from the postcode itself), so a client guess is an acceptable approximation. `SY` is genuinely split between England (Shropshire) and Wales (Ceredigion) and will sometimes guess wrong
- Files: frontend/src/lib/journey/postcode.ts
- Commit: de67480
- Affects the other coder? yes — N could close this properly by adding `country` to `PostcodeLookup` in a future `contract:` PR; flagging for the next sync meeting rather than blocking on it now

### 2026-10-28 · L13 · Wrote a placeholder `docs/privacy.md` (shared file) since none existed
- Decision: L13's `/privacy` page needs `docs/privacy.md` content to copy in at build time, but the file didn't exist yet (it's presumably A's or the team's to write properly). Wrote a draft from the facts already in CONTRACT.md §6 so the page isn't empty, with a visible "Draft — not yet reviewed" banner at the top of the rendered page and the file itself
- Alternatives: leave `/privacy` broken/empty until the file exists; stop and wait for a human to write it
- Why: `docs/privacy.md` is listed as a shared file in CLAUDE.md, so this is flagged rather than treated as settled; §13 rule 1 ("keep the demo path working") favours a real, working page over a blocked one, and the content is grounded only in what CONTRACT.md already commits to, not invented policy
- Files: docs/privacy.md, frontend/scripts/privacy-sync.mjs, frontend/src/app/privacy/page.tsx
- Commit: 993592e
- Affects the other coder? yes — needs A/N sign-off on the actual wording before this is real; flag at the next sync meeting

### 2026-10-28 · integration · `POST /homes/{id}/funding` never called `match_funding` for real homes
- Decision: found via local end-to-end smoke testing (real postcode → assess → plan → funding) that `backend/app/api/homes.py`'s `funding` endpoint always returned `store.funding(home)` — the matched demo fixture's static bundle — for every home, real or demo, ignoring `selected_ids` and the home's actual plan entirely. `covered_gbp + gap_gbp` didn't equal the plan's `total_cost_low_gbp`, violating my own L6 test invariant. Fixed it to mirror the already-correct `plan` endpoint: for a real (`home.stored`) home, load measures + funding options, call `planner.build_plan` with the given `selected_ids` to get a consistent `Plan`, then call my `match_funding(plan, household, options)`. Added `planner.load_funding_options` next to the existing `load_measures`
- Alternatives: leave it until N9/N11's own follow-up noticed it; write a separate funding-service module instead of extending `planner.py`
- Why: §13 rule 1 ("keep the demo path working" extends to the real path once it exists) — this blocked the real (non-demo) journey end to end, discovered only by actually running the app locally rather than trusting unit tests alone; mirroring the existing `plan` endpoint's pattern is the smallest correct fix and needed no new design decisions, both pieces (`match_funding`, `build_plan`) already existed and were already approved
- Files: backend/app/api/homes.py, backend/app/services/planner.py (both N-owned; flagging since I edited outside my usual paths)
- PR: #27
- Affects the other coder? yes — N should sanity-check this wiring, it touches `homes.py` and `planner.py` which are N's files
