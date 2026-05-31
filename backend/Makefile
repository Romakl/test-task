.PHONY: help install dev run run-mock-elk generate seed-rules db-up db-down migrate revision test test-v test-cov lint lint-fix format format-check type-check check fix security sbom audit pre-commit clean docker-build docker-up docker-down docker-logs

BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)CEF Filter Proxy — available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-18s$(NC) %s\n", $$1, $$2}'

# --- Setup -------------------------------------------------------------------
install: ## Install runtime dependencies
	uv sync --frozen

dev: ## Install all dependencies (dev + security extras)
	uv sync --all-extras
	uv run pre-commit install || true

seed-rules: ## Create config/rules.yaml from the example (if missing)
	@test -f config/rules.yaml || cp config/rules.example.yaml config/rules.yaml
	@echo "config/rules.yaml ready"

# --- Run ---------------------------------------------------------------------
run: ## Run the proxy + management API (hot reload)
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

run-mock-elk: ## Run a mock ELK UDP receiver that prints what it gets (port 5140)
	uv run python -m tools.mock_elk_receiver --host 127.0.0.1 --port 5140

generate: ## Send synthetic CEF alerts to the proxy (usage: make generate ARGS="--count 20")
	uv run python -m tools.generate_cef --host 127.0.0.1 --port 5514 $(ARGS)

# --- Database ----------------------------------------------------------------
db-up: ## Start a local Postgres in Docker (port 5432)
	docker run -d --name cef-postgres -e POSTGRES_USER=cef -e POSTGRES_PASSWORD=cef -e POSTGRES_DB=cef -p 5432:5432 postgres:17-alpine

db-down: ## Stop and remove the local Postgres
	docker rm -f cef-postgres || true

migrate: ## Apply database migrations (alembic upgrade head)
	uv run alembic upgrade head

revision: ## Create a migration from model changes (usage: make revision MSG="...")
	uv run alembic revision --autogenerate -m "$(MSG)"

# --- Quality -----------------------------------------------------------------
lint: ## Run ruff linter
	uv run ruff check .

lint-fix: ## Run ruff linter with autofix
	uv run ruff check . --fix

format: ## Format with ruff
	uv run ruff format .

format-check: ## Check formatting
	uv run ruff format . --check

type-check: ## Run mypy
	uv run mypy app

check: lint format-check type-check ## Run lint + format-check + type-check

fix: lint-fix format ## Autofix lint + format

# --- Tests -------------------------------------------------------------------
test: ## Run tests
	uv run pytest

test-v: ## Run tests (verbose)
	uv run pytest -v

test-cov: ## Run tests with coverage report
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# --- Security ----------------------------------------------------------------
security: ## Run the local security gate (bandit + pip-audit)
	uv run bandit -c pyproject.toml -r app tools
	uv run pip-audit

audit: ## Dependency vulnerability audit
	uv run pip-audit

sbom: ## Generate a CycloneDX SBOM (requires syft on PATH)
	syft dir:. -o cyclonedx-json=sbom.json
	@echo "$(GREEN)SBOM written to sbom.json$(NC)"

pre-commit: ## Run all pre-commit hooks
	uv run pre-commit run --all-files

# --- Docker ------------------------------------------------------------------
docker-build: ## Build the container image
	docker compose build

docker-up: ## Start proxy + mock ELK via compose
	docker compose up -d

docker-down: ## Stop compose stack
	docker compose down

docker-logs: ## Tail proxy logs
	docker compose logs -f proxy

# --- Cleanup -----------------------------------------------------------------
clean: ## Remove caches and build artefacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml sbom.json *.sarif
