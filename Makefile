# Home Resilience Passport — run `make help` for the list.
SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml
BACKEND := cd backend &&
HAS_FRONTEND := $(wildcard frontend/package.json)

.PHONY: help install db migrate dev api test lint format openapi openapi-check types seed validate-data fixtures train

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

seed: migrate ## Load data/reference/*.csv into the database
	$(BACKEND) uv run python -m app.db.seed

validate-data: ## Check A's CSVs against CONTRACT.md §5
	$(BACKEND) uv run python -m scripts.validate_data

fixtures: ## Rebuild fixture outputs from the real pipeline (added in N8)
	@echo "make fixtures arrives in N8" && exit 1

train: ## Prepare data and train the EPC model (added in N12)
	@echo "make train arrives in N12" && exit 1
