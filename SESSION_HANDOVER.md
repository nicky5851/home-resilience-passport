# Session Handover — L track (L5 → L10)

Generated 2026-10-28. Everything below is committed/saved — nothing is lost if you restart.

## Paste this to start the new session

```
I'm L. Read SESSION_HANDOVER.md at the repo root first, then continue exactly where it says to
continue. Don't re-ask the questions it already answers. Follow CLAUDE.md's "don't stop between
steps" override noted in the handover — keep going through L7, L8, L9, L10 without pausing for
approval after each one, and only stop to ask for approval once L10 is done.
```

## Where things stand

- **Branch:** `l/L5-resilience-score` (checked out, working tree clean — `git status` confirms
  nothing uncommitted).
- **Commits on this branch:**
  - `ff9cc36` — `feat(scoring): resilience score v1` (L5) — **pushed**, PR open:
    https://github.com/nicky5851/home-resilience-passport/pull/19
  - `6387824` — `feat(scoring): funding matcher` (L6) — **committed locally only, not pushed yet**
    (`git log origin/l/L5-resilience-score..HEAD` shows this one commit ahead).
- **Strategy for L6–L10:** keep committing all of L6/L7/L8/L9/L10 onto this same branch instead
  of opening a new branch/PR per step. Don't push again and don't update PR #19 until the human
  gives final approval at L10 — then push everything in one go and update PR #19's title/body to
  list all the steps it now covers.

## Standing instructions from the human (do not re-ask)

1. "Pull main locally and start L5" — done.
2. "keep on coding and doing all the tak and leave for review at the end, dont stop or ask for
   permisioon in bettween take all acces rn" — override of the normal CLAUDE.md "pause after every
   step" loop. Implement fully, run lint/test, but don't stop to ask after each step.
3. "approved and move to next l and ask for approval when hvae reached l 10" — L5 is approved
   (commit/push/PR done for it). Continue through L6 → L7 → L8 → L9 → L10 without stopping for
   intermediate approval. Only ask for approval once **L10** is fully implemented, tested, and
   linted.

So: **do not stop after L7, L8, or L9.** Implement each, run its Check commands + `make lint` +
`make test`, commit locally (message per CODING_SPEC.md's step), and move straight to the next
one. Only print the "Step done, please review" stop-and-wait message after L10.

## What's done

### L5 — Resilience score (`backend/app/scoring/score.py`)
Real `compute_score` implementation per CODING_SPEC.md §6 / docs/scoring.md. 32 tests in
`backend/tests/scoring/test_score.py`, all passing. Decisions logged in `docs/decisions/L.md`.
Demo-home expected scores written into `backend/tests/scoring/expected/*.json`.

### L6 — Funding matcher (`backend/app/scoring/funding.py`)
Real `match_funding` implementation per CODING_SPEC.md §7 / docs/scoring.md. 14 tests in
`backend/tests/scoring/test_funding.py`, all passing. `docs/scoring.md` L6 section updated.
Committed locally as `6387824`, not yet pushed (per the batching strategy above).

Full backend suite at last check: **301 passed, 13 skipped**. `make lint` clean. Frontend
unaffected (7 passed, 1 skipped).

## What's next: L7

**L7 goal (per CODING_SPEC.md):** Start page — postcode and address lookup/selection, frontend.
Research for this is already done (via an Explore agent) so you don't need to re-gather it:

- **API client:** `frontend/src/lib/api/client.ts` (openapi-fetch wrapper), errors in
  `frontend/src/lib/api/errors.ts` (`ApiError`).
- **Relevant generated types** (`frontend/src/lib/api/schema.d.ts` / `types.ts`): `Address`,
  `PropertyFacts`, `DemoHome`, `PostcodeLookup`, `LookupAddress`, `HomeCreate`.
- **Auth guard pattern:** `frontend/src/lib/auth/use-user.ts` (`useUser()` hook) and
  `frontend/src/components/auth/require-user.tsx` (`RequireUser`) — template to follow for any
  page in the new journey that needs a logged-in user.
- **Mock-mode handler:** `frontend/src/mocks/handler.ts` — intercepts `fetch` when
  `NEXT_PUBLIC_API_MOCK=1`. Already implements postcode lookup, demo-homes listing, and
  home-creation endpoints against fixtures in `frontend/src/mocks/fixtures/` (5 demo slugs:
  `flood-terrace`, `coastal-bungalow`, `city-top-flat`, `clay-semi`, `rural-cottage`).
- **shadcn/ui components installed so far:** only `Button`
  (`frontend/src/components/ui/button.tsx`). **Input, Card, Form, Label, RadioGroup, Select are
  NOT yet added** — will need `pnpm dlx shadcn add ...` for whichever L7/L8 actually needs.
- **Dependencies NOT yet installed:** `react-hook-form`, `zod`. Check whether L7 strictly needs
  them (a plain controlled form might suffice for a single postcode input) or whether to install
  them now since L8 (household form) will need them anyway.
- **Existing page templates to copy patterns from:** `frontend/src/app/login/page.tsx` +
  `login-form.tsx` (form submission pattern), `frontend/src/app/homes/page.tsx` + `my-homes.tsx`
  (authenticated list page pattern).
- **Routing:** no route group exists yet for the user journey. CODING_SPEC.md implies a
  `(journey)` route group will be needed for L7 (postcode/address) → L8 (household) → L9 (risk) →
  L10 (score dashboard) pages. Check CODING_SPEC.md's exact step definitions for the expected
  route paths before creating files.
- **Layout/shell:** `frontend/src/app/layout.tsx`, `frontend/src/components/app-shell/
  site-header.tsx` / `site-footer.tsx`.
- **Theme tokens** (`frontend/src/app/globals.css`): `bg-deep`, `text-green`, `bg-mint`,
  `text-warning`, `text-risk`, `level-low/medium/high` etc. — use these, not raw Tailwind colors.
- **CONTRACT.md rules for postcode/address:**
  - Postcode is normalized: uppercase, exactly one space before the inward code.
  - Coverage is England/Wales only — other prefixes (Scotland, NI) get rejected by the API with
    `400 unsupported_region`.
  - Regex used elsewhere in the backend (`app/schemas/property.py`) for reference:
    `^([A-Z]{1,2}[0-9][A-Z0-9]?)([0-9][A-Z]{2})$` (apply after uppercasing + stripping spaces,
    then re-insert the one space).

**Before writing any L7 code:** re-read CODING_SPEC.md's L7 step definition itself (Goal, files,
Check commands) — the research above covers the surrounding frontend patterns, not the exact
acceptance criteria for L7.

## After L7: remaining steps (still to do, same "don't stop" rule)

- **L8** — Household form (tenure, income band, budget, priorities, vulnerable, Lloyds-data
  consent — matches the `Household` schema already read during L6).
- **L9** — Risk page (human flagged this one as important — read CODING_SPEC.md's L9 section
  carefully; it surfaces `RiskProfile` from L4).
- **L10** — Score dashboard (surfaces `ResilienceScore` from L5). **Stop here and ask for
  approval** per the human's instruction — do not push/open PR updates without it.

## Reminders for whoever (re)starts this

- Branch stays `l/L5-resilience-score` for all of L6–L10 (don't create new branches per step).
- Run `make lint && make test` after every step before moving to the next.
- Log any undocumented decisions in `docs/decisions/L.md` (spec §13 format) — but only fill in
  the commit hash / amend once the human has approved at L10, same as the L5/L6 pattern.
- Only L-owned paths: `frontend/`, `backend/app/scoring/`, `backend/tests/scoring/`,
  `docs/scoring.md`, `docs/decisions/L.md`. Anything touching `backend/app/schemas/`,
  `docs/CONTRACT.md`, or other shared files needs the human to confirm with N first.
- Never push to `main` directly, never force-push, never open the PR against anything but `main`.
