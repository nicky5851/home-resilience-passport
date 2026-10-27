# L's decision log

Format: spec §13. Newest at the bottom.

### 2026-10-27 · L1 · pnpm 12 build-script allowlist
- Decision: `frontend/pnpm-workspace.yaml` allows install scripts only for `sharp` and `unrs-resolver`
- Alternatives: allow all build scripts
- Why: pnpm 12 blocks dependency install scripts by default and fails the install; allowing only what Next.js and ESLint need keeps the supply-chain check on (rule 3)
- Files: frontend/pnpm-workspace.yaml
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · L1 · shadcn/ui "Nova" preset on Radix, brand colours on top
- Decision: `shadcn init -b radix -p nova`; the shadcn colour variables are set from the spec palette (primary = deep green, secondary/muted = mint, destructive = risk red, ring = green), plus named tokens `deep`, `green`, `mint`, `warning`, `risk`, `level-low/medium/high`
- Alternatives: hand-written Tailwind config without shadcn variables
- Why: shadcn components pick up the brand automatically; level colours live in one place for cards, charts and maps (rule 6)
- Files: frontend/src/app/globals.css, frontend/src/lib/theme.ts, frontend/components.json
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · L1 · No dark theme in M1
- Decision: removed shadcn's `.dark` colour block
- Alternatives: keep an unused dark palette
- Why: no toggle is planned and an untested palette could fail contrast checks in L14 (rule 3)
- Files: frontend/src/app/globals.css
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · L1 · Prettier style and lint gates
- Decision: Prettier (no semicolons, width 100, Tailwind class sorting) with `eslint-config-prettier`; CI runs `pnpm lint && pnpm format:check`, `pnpm typecheck`, `pnpm test` (vitest), `pnpm build`
- Alternatives: ESLint only
- Why: spec §2 lists eslint, prettier, tsc and vitest; width 100 matches the back end's ruff setting (rule 6)
- Files: frontend/.prettierrc.json, frontend/eslint.config.mjs, frontend/vitest.config.ts, .github/workflows/ci.yml
- Commit: <hash>
- Affects the other coder? no

### 2026-10-27 · L1 · Footer links to `/privacy` before the page exists
- Decision: the footer has the attribution text and a `/privacy` link now; the page arrives in L13
- Alternatives: add the link in L13
- Why: CONTRACT §6 rule 3 requires the footer link; the shell is its natural home (rule 6)
- Files: frontend/src/components/app-shell/site-footer.tsx
- Commit: <hash>
- Affects the other coder? no
