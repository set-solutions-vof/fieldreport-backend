# fieldreport-backend

FastAPI backend for the Fieldreport platform.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop

## Setup

```bash
cp .env.example .env  # fill in values
make install
make run
```

`make run` starts PostgreSQL when needed, applies the latest database migrations, and then starts the API.

`make stop` stops the local API process and tears down the Docker services.

See `Makefile` for all available commands.
