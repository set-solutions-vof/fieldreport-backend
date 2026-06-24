.DEFAULT_GOAL := install

.PHONY: install format format-check lint stan test check run stop db-upgrade db-downgrade demo-reset

install:
	uv python install
	uv sync

format:
	uv run ruff format .

format-check:
	uv run ruff format . --check

lint:
	uv run ruff check .

stan:
	uv run ty check src

test:
	PYTHONPATH=$(CURDIR) uv run pytest -v

check: format-check lint stan test

db-upgrade:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade base

demo-reset:
	PYTHONPATH=$(CURDIR) uv run python scripts/reset_demo.py


all: format lint stan test

run:
	@if ! nc -z localhost 5432 2>/dev/null || ! nc -z localhost 10000 2>/dev/null; then \
		if ! docker info >/dev/null 2>&1; then \
			echo "Error: Docker is not running. Start Docker Desktop and try again."; \
			exit 1; \
		fi; \
		echo "PostgreSQL or Azurite not detected — starting via Docker Compose..."; \
		docker compose up db azurite -d --wait; \
	fi
	@cp -n .env.example .env 2>/dev/null || true
	uv run alembic upgrade head
	@report_worker_pid=""; \
	trap 'if [ -n "$$report_worker_pid" ]; then kill "$$report_worker_pid" 2>/dev/null || true; fi' EXIT INT TERM; \
	uv run python -m src.workers.report_generation_worker & \
	report_worker_pid=$$!; \
	uv run uvicorn src.main:app --reload

stop:
	-pkill -f "$(CURDIR)/.venv/bin/uvicorn src.main:app --reload"
	-pkill -f "$(CURDIR)/.venv/bin/python -m src.workers.report_generation_worker"
	docker compose down
