.DEFAULT_GOAL := install

.PHONY: install format format-check lint stan test check run worker stop db-upgrade db-downgrade

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


all: format lint stan test

run:
	@if ! nc -z localhost 5432 2>/dev/null; then \
		if ! docker info >/dev/null 2>&1; then \
			echo "Error: Docker is not running. Start Docker Desktop and try again."; \
			exit 1; \
		fi; \
		echo "PostgreSQL not detected — starting via Docker Compose..."; \
		docker compose up db -d --wait; \
	fi
	@cp -n .env.example .env 2>/dev/null || true
	uv run alembic upgrade head
	@template_worker_pid=""; \
	audio_worker_pid=""; \
	trap 'if [ -n "$$template_worker_pid" ]; then kill "$$template_worker_pid" 2>/dev/null || true; fi; if [ -n "$$audio_worker_pid" ]; then kill "$$audio_worker_pid" 2>/dev/null || true; fi' EXIT INT TERM; \
	uv run python -m src.workers.template_analysis_worker & \
	template_worker_pid=$$!; \
	uv run python -m src.workers.audio_pipeline_worker & \
	audio_worker_pid=$$!; \
	uv run uvicorn src.main:app --reload


worker:
	@cp -n .env.example .env 2>/dev/null || true
	uv run python -m src.workers.template_analysis_worker

stop:
	-pkill -f "$(CURDIR)/.venv/bin/uvicorn src.main:app --reload"
	-pkill -f "$(CURDIR)/.venv/bin/python -m src.workers.template_analysis_worker"
	-pkill -f "$(CURDIR)/.venv/bin/python -m src.workers.audio_pipeline_worker"
	docker compose down
