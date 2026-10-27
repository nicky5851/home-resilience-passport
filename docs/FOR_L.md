# For L: things to do or know

Newest first. Tick an item (`[x]`) when it is done or read, in any PR. N adds an item in every
step that affects L, with the PR or branch it came from. Branches without a PR are stacked on
the one below and get their PR once that merges.

## To do

- [ ] **Show the "Ask your landlord" group (L11) from `items`.** For renters (`private_renter`, `social_renter`) the plan puts measures with `measure.needs_landlord: true` after all the others, never selected (even if you send their ids in `selected_ids`). Split the list on that flag; owners and landlords get them in the main list. *(branch `n/N11-planner`)*
- [ ] **Handle `404` from `POST /homes/{id}/plan` before the home is assessed** ("This home has not been assessed yet."): run the assessment first. *(branch `n/N11-planner`)*
- [ ] **Build the reset-password page at `/reset-password?token=…`.** The link the back end makes (written to the API log in M1) opens that path. The page posts `{"token", "password"}` to `/api/v1/auth/reset-password`: `200` = done, `400 validation` = show `detail` (bad or expired token: "This reset link is not valid. Please ask for a new one."; weak password: the rule). Tokens last 1 hour. *(branch `n/N10-auth`)*
- [ ] **Register again on your machine.** Real accounts replaced the stub: old `stub-…` cookies get `401`. Passwords need at least 10 characters and can't be your email. *(branch `n/N10-auth`)*
- [ ] **Review PR #16: optional household subsidence answer (contract).** It needs your approval. Choose between the yes/no/unknown answer in the PR (a `yes` always shows your "new cracks in the walls" `why` text, even when the user meant clay) or a four-option answer (`clay` / `cracks` / `no` / `unknown`). The household form needs the new optional question either way. *(#16)*
- [ ] **Review PR #15: decision-log entries cite the PR number instead of a commit hash.** Process change to spec §13 and CLAUDE.md; needs your approval. *(#15)*
- [ ] **Review PR #14: N8 climate projections.** Merges on green after 24 h without a review (spec §8), but comments are welcome any time. *(#14)*
- [ ] **Run `make flood-data` once.** Downloads the EA flood-risk file (about 5 MB, into git-ignored `data/raw/`) and loads 164,033 postcodes. Without it every flood band is unknown (`null`). *(#13)*
- [ ] **Add `EPC_API_BASE_URL=` to your `.env`** (empty = the live register). *(#12)*
- [ ] **Get your own EPC token** at https://get-energy-performance-data.communities.gov.uk ("My Bearer token") and put it in `.env` as `EPC_API_TOKEN=…`. Never commit or paste it. Integration-site tokens are for tests only. *(#12, README "EPC API token")*
- [ ] **Set up your laptop (L0):** Git, Node 22 LTS, `pnpm`, Python 3.12, `uv`, Docker Desktop, Claude Code; clone, `make dev`, and check `curl localhost:8000/api/v1/health`. *(spec §10 L0)*

## To know

- [ ] **Score uplifts show "about 0 points" until your L5 merges**: the planner takes each measure's uplift from `compute_score`, which is still the stub. Nothing to change in the planner when L5 lands. *(branch `n/N11-planner`)*
- [ ] **`explanation_source: "llm"` can still contain template sentences**: only the top 8 measures go to the LLM, and any sentence over 30 words or 200 characters is replaced by the template. Without `ANTHROPIC_API_KEY` every plan is `"template"`. *(branch `n/N11-planner`)*
- [ ] **Re-posting `/plan` for the budget slider is cheap**: explanations are cached by home and measures, never by budget or selection, so only the first call can wait for the LLM (up to 8 s). Only the latest plan is stored. Demo homes keep their fixture plan. *(branch `n/N11-planner`)*
- [ ] **Priorities boost measures by 20%**: `lower_bills` = bill saving; `comfort` = heat; `flood_safety` = flood; `lower_carbon` = CO2 saving; `home_value` = measures that raise the EPC (bill or CO2 saving). Vulnerable households get heat and flood measures first. *(branch `n/N11-planner`)*
- [ ] **Certificates of users' own homes are lost when the API restarts** until N14 moves them to storage. Homes, assessments, events and share links are stored in Postgres. *(branch `n/N10-auth`)*
- [ ] **Plans and funding still come from the demo fixture matched by postcode** (flood-terrace for any other postcode) until N11 and your L6. *(branch `n/N10-auth`)*
- [ ] **API tests need Postgres** (`make db`); locally they skip if it is down, CI always runs them. *(branch `n/N10-auth`)*
- [ ] **`POST /homes` returns `400 validation` with `detail` starting `property_override:`** when the address has no EPC and no property details were sent (also when the register is down). Show the property form then. *(branch `n/N9-assessment`)*
- [ ] **`subsidence_signal` is always `unknown` for real homes** until #16 is decided. *(branch `n/N9-assessment`)*
- [ ] **Assessments use real data** (flood band, live warnings, climate). Live warnings get 3 s, then count as 0. A cold assessment takes 1–3 s. *(branch `n/N9-assessment`)*
- [ ] **A `fixtures: real data` PR is coming** with real flood bands and climate figures for the demo homes. It needs your approval, and your `backend/tests/scoring/expected/` files may need updating. Scores refreshed by `make fixtures` stay the stub's 50 until your L5 merges; run `make fixtures` after L5. *(#14, `make fixtures`)*
- [ ] **"2050" climate figures are the 2041–2049 mean**: the model has no 2050. Your `why` text saying "by 2050" is fine. *(#14)*
- [ ] **Open-Meteo's free tier limits calls per minute and per hour.** When it refuses, the app uses regional defaults. *(#14)*
- [ ] **Response types are named `*-Output`** in `schema.d.ts` for models that appear in both requests and responses: `Address-Output`, `Household-Output`, `PropertyFacts-Output` (requests use `*-Input`). That's how FastAPI names them; use the `-Output` ones for what the API returns.
- [ ] **Two spec questions for you and N:** the spec text says an invalid postcode is `422`, but the contract (which wins) says `400`; and the spec §5 heat bump mentions "no shading noted", but there is no such field. Agree a spec text fix at the next sync.
