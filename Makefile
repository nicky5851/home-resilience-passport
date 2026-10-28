# Home Resilience Passport — run `make help` for the list.
SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml
BACKEND := cd backend &&
HAS_FRONTEND := $(wildcard frontend/package.json)

.PHONY: help install db migrate dev api test lint format openapi openapi-check types seed flood-data validate-data fixtures fixtures-inputs epc-data train coverage studio-openapi studio-openapi-check studio-types studio-record studio-test

help: ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-15s %s\n", $$1, $$2}'

install: ## Install back-end (and front-end) dependencies
	$(BACKEND) uv sync
ifneq ($(HAS_FRONTEND),)
	cd frontend && pnpm install
endif

db: ## Start Postgres and wait until it is ready
	$(COMPOSE) up -d --wait db

migrate: db ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

dev: migrate ## Postgres + API (:8000) + front end (:3000)
	@trap 'kill 0' EXIT; \
	( $(BACKEND) uv run uvicorn app.main:app --reload --port 8000 ) & \
	$(if $(HAS_FRONTEND),( cd frontend && pnpm dev ) &,) \
	wait

api: migrate ## Postgres + API only
	$(BACKEND) uv run uvicorn app.main:app --reload --port 8000

test: ## All tests
	$(BACKEND) uv run pytest -q
ifneq ($(HAS_FRONTEND),)
	cd frontend && pnpm test
endif

coverage: ## Back-end tests with a line-coverage report per file (routes: app/api/)
	$(BACKEND) uv run pytest -q --cov --cov-report=term-missing:skip-covered

lint: ## All linters and type checks
	$(BACKEND) uv run ruff check . && uv run ruff format --check .
ifneq ($(HAS_FRONTEND),)
	cd frontend && pnpm lint && pnpm typecheck
endif

format: ## Auto-format back-end code
	$(BACKEND) uv run ruff format . && uv run ruff check --fix .

openapi: ## Write docs/openapi.json from the app (no server needed)
	$(BACKEND) uv run python -m scripts.export_openapi

openapi-check: ## Fail if docs/openapi.json differs from the app's schema
	$(BACKEND) uv run python -m scripts.export_openapi --check

types: ## Regenerate frontend/src/lib/api/schema.d.ts from docs/openapi.json
	cd frontend && pnpm types

studio-openapi: ## Write docs/openapi-studio.json from Studio's own routers (no server needed)
	$(BACKEND) uv run python -m scripts.export_openapi_studio

studio-openapi-check: ## Fail if docs/openapi-studio.json differs from Studio's schema
	$(BACKEND) uv run python -m scripts.export_openapi_studio --check

studio-types: ## Regenerate frontend/src/features/studio/api/schema.d.ts from docs/openapi-studio.json
	cd frontend && pnpm studio:types

studio-record: migrate ## Record live-API fallbacks for the 5 demo homes (needs real network)
	$(BACKEND) uv run python -m scripts.record_studio_fallbacks

studio-test: ## Studio's own backend tests only
	$(BACKEND) uv run pytest -q tests/studio

seed: migrate ## Load data/reference/*.csv and cache the 5 demo homes for offline demos
	$(BACKEND) uv run python -m app.db.seed

flood-data: migrate ## Download (if missing) and load EA RoFRS flood postcodes
	$(BACKEND) uv run python -m app.db.load_rofrs

validate-data: ## Check A's CSVs against CONTRACT.md §5
	$(BACKEND) uv run python -m scripts.validate_data

fixtures: ## Rebuild demo fixture outputs (risk, score) from their inputs, offline
	$(BACKEND) uv run python -m scripts.make_fixtures

fixtures-inputs: ## Record real HazardInputs for the demo homes (contract: PR needs L), then outputs
	$(BACKEND) uv run python -m scripts.make_fixtures --inputs

epc-data: ## Stream 3 regions of the EPC bulk data into data/raw/epc_bulk.csv (needs EPC_API_TOKEN)
	$(BACKEND) uv run python -m ml.download

train: ## Prepare data and train the EPC model (downloads the extract first if missing)
	@test -f data/raw/epc_bulk.csv || $(MAKE) epc-data
	$(BACKEND) uv run --group ml python -m ml.train
