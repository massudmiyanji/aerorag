.PHONY: help up down logs lint format test check corpus

help:  ## Show available targets
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-8s %s\n", $$1, $$2}'

up:  ## Start Qdrant
	docker compose up -d

down:  ## Stop Qdrant (data is kept in the named volume)
	docker compose down

logs:  ## Follow container logs
	docker compose logs -f

lint:  ## Lint, format check and type check
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

format:  ## Auto-fix lint issues and format code
	uv run ruff check --fix .
	uv run ruff format .

test:  ## Run the test suite
	uv run pytest

check: lint test  ## Everything CI runs

corpus:  ## Download the document corpus into data/raw
	uv run python scripts/download_corpus.py
