# Home Resilience Passport

A web app where a UK homeowner enters a postcode and a few household details and gets their home's
climate risks today and in 2050, a Resilience Score (A–G), a costed improvement plan, a funding
bundle and a shareable passport. Built for the TCS Sustainathon UK&I (Lloyds Banking Group challenge).

- Spec: [`docs/CODING_SPEC.md`](docs/CODING_SPEC.md) · Contract: [`docs/CONTRACT.md`](docs/CONTRACT.md)
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
