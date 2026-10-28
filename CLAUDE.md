# CLAUDE.md — Home Resilience Passport

Read `docs/CODING_SPEC.md` and `docs/CONTRACT.md` before doing anything. It is the single source of truth: stack, folder
ownership, shared contract, data sources, and the numbered steps for N and L.

L: read docs/FOR_L.md first and tick items off.

## Who is working

Ask the human at the start of the session: "Are you N or L, and which step?" Then work only on
that person's step and only inside the paths they own (spec §3).

- **N** owns `backend/` (except `backend/app/scoring/` and `backend/tests/scoring/`), `backend/ml/`, `infra/`, `.github/`, `Makefile`, `README.md`, `docs/model_card.md`, `docs/decisions/N.md`, and committing/loading `data/reference/` (A owns the values in those CSVs: never change one, only report problems).
- **N** also owns Resilience Studio (docs/studio/N_20_function.md): `backend/app/studio/`, `backend/tests/studio/`, `docs/studio/`, `docs/openapi-studio.json`, `frontend/src/app/studio/`, `frontend/src/features/studio/`. Studio is purely additive and never touches the shared contract, L's scoring, or any other existing file.
- **L** owns `frontend/`, `backend/app/scoring/` (risk, score, funding), `backend/tests/scoring/`, `docs/scoring.md`, `docs/decisions/L.md`.
- **Shared** (do not edit without the human confirming the other coder agreed): `docs/CONTRACT.md`, `docs/openapi.json`, `backend/app/schemas/`, `backend/tests/fixtures/` (except the output parts, spec §3.3), `docs/CODING_SPEC.md`, `docs/DECISIONS.md`, `docs/privacy.md`, `CLAUDE.md`, `.env.example`.

## Start of every session

1. `git checkout main && git pull origin main`.
2. Switch to the person's branch (`n/<step>-<slug>` or `l/<step>-<slug>`); create it if needed, or `git rebase main` if it exists.
3. Run `make test` to confirm a clean start. Report any failure before doing anything else.

## One step at a time — always pause

1. Restate the step's Goal and list the files you will touch.
2. Do the step.
3. Run the step's **Check** commands and report the results (pass/fail with output).
4. Also run `make lint` and `make test` (or the `pnpm` equivalents in `frontend/`).
5. **STOP.** Print: "Step <id> done. Please review the diff and run the check yourself. Say 'approved' to commit and push." Wait.

## When the human says "approved"

1. Add any decisions you made that the spec did not cover to the person's log (`docs/decisions/N.md` or `docs/decisions/L.md`) using the format in spec §13. Mark "Affects the other coder? yes" when it touches a seam.
2. `git add` only the files you changed, then `git commit` with the step's commit message from the spec. Leave `PR: #?` in the new decision-log entries.
3. `git push -u origin <branch>`.
4. Open the pull request if none exists (`gh pr create`), or update it (`gh pr edit`), listing the steps it contains and linking new decision-log entries.
5. Replace `PR: #?` with the pull request's number, commit (`docs: decision-log PR number`) and push. No amend, no force-push: the squash merge folds it in.
6. Remind the human: merge to `main` at least once a day, and by 9 pm the evening before a sync meeting, when CI is green.

Never start the next step on your own. Never push to `main` directly. Never force-push.

## Rules

- Follow the spec's locked decisions (§2). Do not swap libraries or patterns.
- Never put secrets in code or git. Read them from env; add new variable names to `.env.example`.
- External APIs: 10 s timeout, cache, and a fallback so the app keeps working (§5).
- Keep the 5 demo homes working end to end at all times.
- Treat user data as real (CONTRACT.md §6): nothing personal in LLM prompts or logs, no tracking, uploads checked by content and size.
- Follow `docs/CONTRACT.md` exactly for field names, units, nulls, errors, auth and CSV formats. Never change it outside a `contract:` PR.
- If the spec does not answer a question, apply §13 Decision rules and log the choice in the person's decision log.
- If a task needs a change to a shared file, stop and tell the human what change is needed and why.
- Refer to team members only as N, L and A.

## Commands

- `make dev` — Postgres + API (:8000) + front end (:3000)
- `make test` / `make lint` — all checks
- `make openapi` — write `docs/openapi.json` from the back-end app (no server needed)
- `make types` — regenerate `frontend/src/lib/api/schema.d.ts` from `docs/openapi.json`
- `make seed` — load `data/reference/*.csv` and the demo homes
- `make validate-data` — check A's CSVs against CONTRACT.md §5
- `make fixtures` — rebuild the output parts of the demo fixtures from the real pipeline (after N8)
- `make train` — prepare data and train the EPC model (N)
