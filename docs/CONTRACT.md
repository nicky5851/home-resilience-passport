# Contract v1 — the five seams

Version `contract-v1` · decided 26 Oct 2026, revised 26 Oct (spec v1.3 review, M2 folded in) · tagged at the Foundation check on Tue 27 Oct · shared file (changes need N and L to approve the PR)

This is everything N's code and L's code agree on. If both sides follow it, the front end and back
end cannot drift apart. The Pydantic models in `backend/app/schemas/` (spec §4.1) are the code form
of this document; where they disagree, fix the code to match this file.

| Seam | Between | Locked in | Checked automatically by |
| --- | --- | --- | --- |
| 1. Data formats | Everyone | §1 | `test_schemas.py`, fixture validation in CI |
| 2. Hazard data → scoring | N's adapters → L's `scoring/` | §2 | `test_contract_ranges.py` (inputs in range), L's scoring tests on fixtures |
| 3. API → screens | N's routes → L's pages | §3 | OpenAPI snapshot diff + front-end typecheck in CI |
| 4. Login and cookies | N's auth → L's pages | §4 | `test_auth_flow.py` (back end), `/dev/contract` page (front end) |
| 5. Spreadsheets → code | A's CSVs → N's loader, L's funding | §5 | `make validate-data` in CI |

§6 (files and personal data) is not a sixth seam; it holds rules both sides must follow for uploads and privacy, so they are fixed here too.

---

## 1. Data formats (general rules)

1. JSON field names are `snake_case`. Enum values are lowercase strings (`"semi_detached"`), except EPC and score bands (`"A"`–`"G"`).
2. **Every field is always present.** Unknown values are `null`, never missing. Lists are never `null`; use `[]`.
3. Money: integer pounds (`1500`), never pence or strings. Field names end in `_gbp`.
4. Carbon: kilograms CO2e per year (`co2_saved_kg_per_year`), except `co2_tonnes_per_year` which comes straight from the EPC.
5. Dates: `YYYY-MM-DD`. Timestamps: ISO 8601 UTC with `Z` (`2026-11-03T14:05:00Z`).
6. IDs: `home_id` and event ids are UUID v4 strings. Measure and funding ids are the CSV `id` (lowercase `kebab-case`, e.g. `flood-door`).
7. Postcodes are stored and returned upper-case with one space (`SW1A 1AA`). Input may be any case and spacing.
8. Text shown to users (`why`, `reason`, `explanation`, `note`) is plain English, no markdown, at most 140 characters (explanations at most 200).
9. Coverage: **England and Wales only.** `GET /lookup/postcode/{postcode}` for a Scottish or Northern Irish postcode returns `400` with `code="unsupported_region"` and `detail="Home Resilience Passport covers England and Wales for now."` In Wales `rofrs_band` is always `null` (the EA dataset is England only) and the flood card says so.

## 2. Hazard data → scoring (the field definitions)

`HazardInputs` is filled by N's adapters and read by L's `assess_risk`. Every number means exactly this:

| Field | Unit | Definition | Source | Valid range | Unknown |
| --- | --- | --- | --- | --- | --- |
| `rofrs_band` | enum | Highest EA Risk of Flooding from Rivers and Sea band present in the postcode: `high` (≥ 3.3%/yr), `medium` (1–3.3%), `low` (0.1–1%), `very_low` (< 0.1%), `none` (postcode not in the dataset) | EA RoFRS postcodes | enum | `null` |
| `active_flood_warnings` | count | EA flood warnings or alerts currently in force within 5 km of the home | EA flood-monitoring API | 0–50 | `0` |
| `hot_days_baseline` | days/yr | Mean number of days per year with daily max temperature ≥ 30 °C, years 1991–2020 | Open-Meteo, model `EC_Earth3P_HR` | 0–60 | `null` |
| `hot_days_2050` | days/yr | Same, years 2041–2050 | same | 0–90 | `null` |
| `heavy_rain_days_baseline` | days/yr | Mean days per year with precipitation ≥ 20 mm, 1991–2020 | same | 0–40 | `null` |
| `heavy_rain_days_2050` | days/yr | Same, 2041–2050 | same | 0–50 | `null` |
| `max_wind_baseline_kmh` | km/h | Mean of each year's highest daily maximum 10 m wind speed, 1991–2020. This is sustained wind from the model, **not gusts** (Open-Meteo's climate API has no gusts), so values are lower than gust figures in the news | same (`wind_speed_10m_max`) | 10–150 | `null` |
| `max_wind_2050_kmh` | km/h | Same, 2041–2050 | same | 10–150 | `null` |
| `subsidence_signal` | enum | User answer: `clay_reported` (knows soil is clay), `cracks_reported` (new cracks in walls), `none_reported`, `unknown` (did not answer) | Household form | enum | `"unknown"` |
| `property` | object | `PropertyFacts` (spec §4.1). `top_floor` is `true` only for flats on the top storey | EPC, our model, or user | – | fields `null` |

Rules:
- **Hot-day threshold check (do once, before the `contract-v1` tag):** N calls Open-Meteo once for central London (51.51, -0.13). If `hot_days_baseline` at 30 °C comes out below 1.0, the threshold in this table becomes **28 °C** (edit this row, no other change). Reason: the climate model runs cooler than weather stations, and at 30 °C almost every home would score "low" for overheating.
- Scoring must accept `null` in any numeric field and treat it as "unknown" (scored as medium risk, `why` says the data was unavailable).
- `HazardLevel.data_source` uses these exact strings: `"Environment Agency"`, `"Open-Meteo (CMIP6)"`, `"EPC register"`, `"Our EPC model"`, `"Your answer"`.
- The five hazards always appear in `RiskProfile.levels` in this order: `river_sea_flood`, `overheating`, `storm`, `subsidence`, `surface_water`. In M1 `surface_water` is always `today="medium"`, `y2050="medium"`, `why="Surface-water data is coming in a later version"`.

## 3. API → screens

**Base path** `/api/v1`. JSON in and out (except login, which is form-encoded, and work uploads, which are multipart). The front end always calls relative `/api/v1/...`; Next.js rewrites it to `${API_ORIGIN}/api/v1/...`, where `API_ORIGIN` is `http://localhost:8000` in dev and the Render URL in production. Because the browser only ever talks to the front-end domain, the cookie is first-party and **no CORS is configured** (the API sends no `Access-Control-Allow-*` headers).

**Status codes and errors.** Every error body is `{"detail": "<plain-English message>", "code": "<code>"}`. `detail` is always a string, never a list or object. This includes errors raised by `fastapi-users` (for example `REGISTER_USER_ALREADY_EXISTS`, `LOGIN_BAD_CREDENTIALS`, `REGISTER_INVALID_PASSWORD`): N's error handler maps them to the codes below.

| Status | `code` | When | Front end does |
| --- | --- | --- | --- |
| 400 | `validation` | Body or path fails validation (FastAPI 422 is converted to 400) | Show `detail` next to the form |
| 401 | `unauthorised` | Not logged in on a protected route | Redirect to `/login?next=<current path>` |
| 403 | `forbidden` | Origin check failed (§4) | Generic error page; in dev, log a hint about `ALLOWED_ORIGINS` |
| 404 | `not_found` | Unknown id, or a home that belongs to someone else | "We couldn't find that home" page |
| 400 | `unsupported_region` | Postcode in Scotland or Northern Ireland (§1 rule 9) | Show `detail` under the postcode box |
| 409 | `conflict` | Email already registered | Show `detail` |
| 413 | `file_too_large` | Upload over 5 MB (§6) | Show `detail` next to the file input |
| 415 | `unsupported_file` | Upload is not PDF, JPEG or PNG (§6) | Show `detail` next to the file input |
| 429 | `rate_limited` | Too many requests (login: 5 per minute per IP; register: 10 per hour per IP; assess: 30 per hour per user). Header `Retry-After` in seconds | Show "Please wait a moment and try again" |
| 502 | `upstream_unavailable` | A data source failed **and** no fallback exists | Toast: "Some data is temporarily unavailable"; keep partial results |
| 500 | `internal` | Anything else | Generic error page with "Try again" |

**Timing.** `POST /homes/{id}/assess` may take up to 10 s on a cold postcode (the front end shows the step-by-step progress screen and times out at 20 s). `POST /homes/{id}/plan` may take up to 8 s when the LLM runs (show a skeleton). Everything else answers in under 1 s.

**Shapes.** Route list and bodies: spec §4.2. Extra rules:
- `GET /lookup/postcode/{postcode}` returns `addresses: []` (not an error) when the EPC register has nothing; the front end then shows "My address isn't listed".
- `POST /homes` returns `201` with `{"home_id": "<uuid>"}`. Assessment is a separate call.
- `GET /homes/{id}/risk` before any assessment returns `404 not_found`.
- `POST /homes/{id}/plan` with no body uses the household budget and default selection.
- `explanation` text in a plan depends only on the home and the measures, **never on the budget or selection**, so re-posting `/plan` while the user moves the budget slider never waits for the LLM (it is served from cache after the first call).
- `GET /demo/homes` returns `list[DemoHome]` (spec §4.1): each demo home with its precomputed `risk`, `score`, `plan` and `funding`, so a logged-out visitor can browse it read-only. "Make this my home" calls `POST /homes` with the demo's `address`, `household` and `property` as `property_override`, which needs login.
- Logged-out users can look up a postcode and pick an address; the household form asks them to sign up or log in **before** `POST /homes`. The front end keeps the half-filled form in `sessionStorage` and restores it after login (`/login?next=/start/household`).
- The public passport (`/public/passport/{token}`) never contains `household` (the field is absent from that response model, `PublicPassport`).
- No pagination in M1. Lists are at most 50 items.

**Types.** The front end never hand-writes API types. `make openapi` writes the back end's schema to `docs/openapi.json` (from the app object, no server needed). `make types` regenerates `frontend/src/lib/api/schema.d.ts` from `docs/openapi.json`. CI fails if (a) the committed `docs/openapi.json` differs from the app's schema, or (b) the committed `schema.d.ts` differs from what `make types` produces, so any API change is visible in the PR and the front end can never be built against stale types.

## 4. Login and cookies

- Library: `fastapi-users`, cookie transport, JWT strategy.
- Cookie: name `hrp_auth`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` only when `ENV=production`, lifetime 7 days. JWT signed with `AUTH_SECRET` (env, at least 32 random bytes); changing it logs everyone out.
- User object (`UserRead`, every response that returns a user): `{"id", "email", "is_active", "is_superuser", "is_verified"}`. This is fastapi-users' default shape, so N10 needs no custom serializer; the stub returns the same keys (`true`, `false`, `false`).
- Routes:
  - `POST /api/v1/auth/register` — JSON `{"email", "password", "accept_privacy": true}` → `201` `UserRead`. Password at least 10 characters and not equal to the email. `accept_privacy` must be `true` (the user ticked "I have read the privacy notice"), otherwise `400 validation`; the back end stores `privacy_accepted_at` and `privacy_version`. Duplicate → `409 conflict`.
  - `POST /api/v1/auth/login` — **form-encoded** `username=<email>&password=<pw>` → `204` and `Set-Cookie: hrp_auth=…`. Wrong details → `400` `{"detail":"Email or password is incorrect","code":"validation"}`.
  - `POST /api/v1/auth/logout` → `204`, cookie cleared.
  - `GET /api/v1/users/me` → `200` `UserRead` or `401`.
  - `GET /api/v1/users/me/export` → `200` JSON file (`Content-Disposition: attachment; filename="hrp-export.json"`) with the user, every home, household, assessment, plan, passport event and share link they own. Certificates are listed by file name, not embedded. (Right of access.)
  - `DELETE /api/v1/users/me` → `204`. Deletes the user, their homes and everything hanging off them, including uploaded files and share links, then clears the cookie. Cannot be undone; the front end asks the user to type `DELETE` first. (Right to erasure.)
  - `POST /api/v1/auth/forgot-password` `{"email"}` → `202` always (never reveals whether the email exists). `POST /api/v1/auth/reset-password` `{"token", "password"}` → `200` or `400 validation`. fastapi-users defaults; the email is sent in M2 only (§6). In M1 the reset token is written to the API log instead.
- Protected routes: everything under `/homes` and `/users/me*`. Public: `/health`, `/lookup/*`, `/demo/*`, `/public/*`, `/auth/*`, `/model/info`.
- **Origin check:** every `POST`, `PUT`, `PATCH` and `DELETE` must carry an `Origin` (or, if absent, `Referer`) header whose origin is in `ALLOWED_ORIGINS` (env, comma-separated; dev `http://localhost:3000`). Otherwise `403` with `code="forbidden"`. This, plus `SameSite=Lax`, is our CSRF protection; there are no CSRF tokens. Tests and `curl` set the header explicitly.
- Rate limits: as in the §3 table, keyed on the client IP from `X-Forwarded-For` (first entry) when `ENV=production`, because every request arrives through the Vercel proxy.
- Front end: a `useUser()` hook calls `/users/me`; protected pages redirect on `401`. Demo homes can be viewed without logging in (read-only), saving needs login.
- **Foundation stub:** until N10, the back end accepts any email and password (register still requires `accept_privacy: true`), sets `hrp_auth=stub-<email>`, and `/users/me` returns `{"id":"00000000-0000-0000-0000-000000000001","email":<email>,"is_active":true,"is_superuser":false,"is_verified":false}`. Export returns a fixture JSON; delete returns `204` and clears the cookie; forgot/reset return their success codes. The Origin check is real from the stub onward. The front end cannot tell the difference, so L builds the real pages against the stub.

## 5. Spreadsheets → code

A edits in Google Sheets and exports CSV. Rules for all three files:
- UTF-8, comma-separated, first row is the header with **exactly** these column names in this order.
- Lists inside a cell are separated by `;` with no spaces (`flood;storm`). Empty list = empty cell.
- Booleans are `true` or `false`. Numbers have no `£`, commas or units.
- `source_url` is required on every row except where `is_mock` is `true`.
- `make validate-data` checks every rule and prints the row and column of each problem. CI runs it on every PR, so a broken sheet cannot be merged.

**`data/reference/demo_homes.csv`**

| Column | Type | Allowed values |
| --- | --- | --- |
| `slug` | text | one of `flood-terrace`, `coastal-bungalow`, `city-top-flat`, `clay-semi`, `rural-cottage` |
| `postcode` | text | a real postcode in England or Wales |
| `house_number` | text | made up, e.g. `12` |
| `hazard_shown` | text | `river_sea_flood`, `overheating`, `storm`, `subsidence`, `low_risk` |
| `tenure` | enum | `owner_occupier`, `landlord`, `private_renter`, `social_renter` |
| `income_band` | enum | `under_20k`, `20k_40k`, `40k_60k`, `60k_100k`, `over_100k` |
| `budget_gbp` | int | 0–100000 |
| `priorities` | list | from `lower_bills`, `comfort`, `flood_safety`, `lower_carbon`, `home_value` |
| `vulnerable` | bool or empty | empty = "prefer not to say" (`null`) |
| `subsidence_signal` | enum | `clay_reported`, `cracks_reported`, `none_reported`, `unknown` |
| `notes` | text | anything |

Coverage rule: at least one renter, one low-income household (`under_20k`) and one vulnerable household across the five.

**`data/reference/measures.csv`**

| Column | Type | Allowed values / unit |
| --- | --- | --- |
| `id` | text | kebab-case, unique |
| `name` | text | ≤ 40 chars |
| `category` | enum | `flood`, `heat`, `storm`, `subsidence`, `carbon` |
| `hazards_reduced` | list | from `river_sea_flood`, `overheating`, `storm`, `subsidence`, `surface_water` (empty for pure carbon measures) |
| `cost_low_gbp`, `cost_high_gbp` | int | pounds, installed price, low ≤ high |
| `annual_bill_saving_gbp` | int | pounds per year, 0 if none |
| `co2_saved_kg_per_year` | int | kg, 0 if none |
| `resilience_points` | int | 0–15, points added to the score component named by **this row's `category`** (so a `carbon` measure adds to the carbon component, a `flood` measure to the flood component). `hazards_reduced` is shown on screen only and does not move points |
| `property_types` | list | from `detached`, `semi_detached`, `terraced`, `flat`, `bungalow`, `other`; empty = all |
| `renter_ok` | bool | can a renter do it without the landlord |
| `needs_landlord` | bool | – |
| `source_url` | url | where the cost or saving figure came from |

**`data/reference/funding.csv`**

| Column | Type | Allowed values / unit |
| --- | --- | --- |
| `id` | text | kebab-case, unique |
| `name` | text | ≤ 50 chars |
| `provider` | text | e.g. `UK Government`, `Lloyds (illustrative)` |
| `kind` | enum | `grant`, `loan`, `mortgage_further_advance`, `insurance_discount`, `cashback` |
| `max_amount_gbp` | int or empty | pounds; empty = no cap |
| `apr_percent` | float or empty | loans only |
| `income_bands` | list | from the income bands above; empty = all |
| `tenures` | list | from the tenures above; empty = all |
| `categories` | list | measure categories it can pay for; empty = all |
| `is_mock` | bool | `true` for anything Lloyds-branded or invented |
| `source_url` | url or empty | required unless `is_mock` |

## 6. Files and personal data

**Uploads (work certificates).** `POST /homes/{id}/work` is `multipart/form-data` with fields `measure_id` (text), `completed_on` (`YYYY-MM-DD`, not in the future), `cost_gbp` (int, optional) and `certificate` (file, optional).
- Allowed: PDF, JPEG, PNG, checked by the file's first bytes (`%PDF`, `\xFF\xD8\xFF`, `\x89PNG`), not by its name or `Content-Type`. Anything else → `415 unsupported_file`. Over 5 MB → `413 file_too_large`. One file per work record.
- Stored under a random name (`<uuid>.<ext>`); the original file name is kept only as metadata (`certificate_name`, at most 100 characters).
- M1: local folder `backend/uploads/` (git-ignored). M2: a private object-storage bucket (spec §14). The API never returns a storage URL that works without login.
- Download: `GET /homes/{id}/work/{event_id}/certificate` → the file, owner only (`404` for anyone else). `PassportEvent.detail` for `work_recorded` holds `{"measure_id", "completed_on", "cost_gbp", "has_certificate", "certificate_name"}`.
- The public passport shows `has_certificate: true/false` only. Certificates are never public.

**What counts as personal data here.** Email, address and postcode once linked to an account, household answers (tenure, income band, budget, priorities), the `vulnerable` answer (may reveal health, so it is **special category data**), uploaded certificates, and IP addresses in logs.

**Rules both sides follow.**
1. `vulnerable` is optional (`bool | null`, default `null`). The form shows it in its own box with this text, and the box is unticked by default: "Optional. If someone in your home is over 75, disabled, has a long-term illness or young children, tell us and we will put safety measures first. We only use this to order your plan and you can remove it any time." Answering is the user's explicit consent; changing it back to "prefer not to say" sets `null`.
2. **Nothing personal goes to the LLM.** The explanation prompt may contain only property facts, hazard levels, score components and measures. Never email, address, postcode, house number, income band, budget, tenure or `vulnerable`. N's `llm.py` has a test that builds a prompt for a demo home and asserts none of those values appear in it.
3. No analytics, advertising or tracking cookies or scripts. `hrp_auth` is the only cookie and it is strictly necessary, so no cookie banner is needed. A footer link points to `/privacy`.
4. Logs never contain passwords, cookies, tokens, full request bodies or uploaded files. Postcodes may be logged; emails may not.
5. The public passport contains no `household`, no email and no certificate files (§3).

---

## Changing this contract

1. Open a PR that changes this file **and** the matching schemas, fixtures and `docs/openapi.json` together.
2. Title starts with `contract:`. Both N and L approve before merge.
3. Bump the version line at the top (`contract-v2`) and add a line to `docs/DECISIONS.md`.
4. After merge: N runs `make types`, L pulls, both re-run `make test`.
