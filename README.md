# Home Resilience Passport

A web app where a UK homeowner enters a postcode and a few household details and gets their home's
climate risks today and in 2050, a Resilience Score (A–G), a costed improvement plan, a funding
bundle and a shareable passport. Built for the TCS Sustainathon UK&I (Lloyds Banking Group challenge).

- Spec: [`docs/CODING_SPEC.md`](docs/CODING_SPEC.md) · Contract: [`docs/CONTRACT.md`](docs/CONTRACT.md) · Who starts where: [`docs/HANDOFF.md`](docs/HANDOFF.md)
- Coverage: England and Wales.

## Requirements

Git, Docker Desktop, Python 3.12, [`uv`](https://docs.astral.sh/uv/), Node 22 LTS (`nvm use`), `pnpm`.

## Run it

```bash
cp .env.example .env     # then fill in what you have
make install             # back-end (and front-end) dependencies
make dev                 # Postgres + API on :8000 (+ front end on :3000)
curl localhost:8000/api/v1/health   # {"status":"ok"}
```

API docs: http://localhost:8000/docs

## EPC API token

Address lists and property facts come from the EPC register. Without a token the app still
works: the address list is empty and users enter their home's details by hand.

- **Each person gets their own token.** Sign in at
  https://get-energy-performance-data.communities.gov.uk and copy the token shown under
  **"My Bearer token"**. Do not share one token between people.
- **The integration site gives test-only tokens.** A token from the integration (test) site only
  works against its own API (`https://api.get-energy-performance-data.epb-integration.communities.gov.uk`)
  and returns test homes, not real ones; against the live API it gets `403 UNAUTHORISED`. For real
  data use a live token and leave `EPC_API_BASE_URL` empty (it defaults to the live API).
- **Tokens go only in `.env`** (`EPC_API_TOKEN=...`), which git ignores. Never put a token in
  git (including `.env.example`, code, tests or fixtures) or in chat, issues or pull requests.
  If one leaks, get a new one from the same page.

## Everyday commands

| Command | What it does |
| --- | --- |
| `make dev` | Postgres + API + front end |
| `make test` / `make lint` | All tests / all linters |
| `make openapi` / `make types` | Write `docs/openapi.json` / regenerate front-end types |
| `make seed` / `make validate-data` | Load / check `data/reference/*.csv` |
| `make help` | Everything else |

## Data attribution

Contains public sector information licensed under the Open Government Licence v3.0.
Climate data: Open-Meteo, CMIP6.
