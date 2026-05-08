.DEFAULT_GOAL := install

.PHONY: install format lint stan test check run stop db-upgrade db-downgrade

install:
	uv python install
	uv sync

format:
	uv run ruff format .

lint:
	uv run ruff check .

stan:
	uv run ty check src

test:
	uv run pytest -v

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
	uv run uvicorn src.main:app --reload

stop:
	-pkill -f "$(CURDIR)/.venv/bin/uvicorn src.main:app --reload"
	docker compose down
