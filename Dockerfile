FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libheif1 libreoffice-writer-nogui \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --frozen --no-dev --no-cache

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

ENV PATH="/app/.venv/bin:$PATH"
ENV SOFFICE_PATH="/usr/bin/soffice"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
