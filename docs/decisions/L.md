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
- Commit: <hash>
- Affects the other coder? no (call sites are unchanged)

### 2026-10-27 · L3 · All §6/§7 numbers are in `scoring/config.py` from the start
- Decision: thresholds, weights, band floors, EPC band midpoints and the 60-month loan term are named constants now, even though the stub does not use them yet; overheating uses the 28 °C hot-day count (CONTRACT §2)
- Alternatives: add them in L4–L6
- Why: one place to review at Merge 1 with A; tests import the same constants (spec §2 Config)
- Files: backend/app/scoring/config.py
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · L3 · Stub values
- Decision: every hazard `medium`, every component at half points (score 50, band D), funding with no lines and the whole cost as the gap; fixed `generated_at`
- Alternatives: copy the fixture outputs
- Why: obviously placeholder on screen, schema-valid, deterministic; N9 can wire the pipeline before L4 (rule 1)
- Files: backend/app/scoring/risk.py, backend/app/scoring/score.py, backend/app/scoring/funding.py
- Commit: <hash>
- Affects the other coder? yes (the stub ignores inputs until L4/L5/L6 merge)
