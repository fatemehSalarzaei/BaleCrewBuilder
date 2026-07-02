# Developer Setup

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.12 or later |
| Docker + Docker Compose | any recent version |
| `pip` | bundled with Python |

PostgreSQL and Redis are started via Docker Compose. You do not need to install them locally.

---

## 1. Clone and enter the repository

```bash
git clone https://github.com/fatemehSalarzaei/BaleCrewBuilder.git
cd BaleCrewBuilder
```

---

## 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -e ".[dev]"
```

This installs both runtime dependencies and dev/test extras (`pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`, `pyyaml`).

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` if you need to change the database URL or secret key. The defaults match the Docker Compose service names and work out of the box for local development:

```
APP_ENV=development
SECRET_KEY=change-me-to-a-random-secret
DATABASE_URL=postgresql+asyncpg://builder:builder@localhost:5432/builder
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
```

> **Never commit `.env`.** It is in `.gitignore`.

---

## 5. Start backing services

```bash
docker-compose up -d
```

This starts:
- `postgres` — PostgreSQL 16 on port 5432, database `builder`, user/password `builder`
- `redis` — Redis 7 on port 6379

Wait a few seconds for the health checks to pass before proceeding.

---

## 6. Apply database migrations

```bash
alembic upgrade head
```

This applies the checked-in initial Builder Platform schema migration, including the current project, document, Blueprint, generation, artifact, AI run, and upload tables. `alembic.ini` is at the repo root — always run `alembic` commands from there.

---

## 7. Run the Builder Platform

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

---

## 8. Run tests

Tests use an in-memory SQLite database via `aiosqlite`. **No running PostgreSQL is required to run the test suite.**

```bash
pytest                      # run the full test suite
pytest tests/test_e2e_sample_generation.py   # run Phase 8 E2E tests only
pytest -q                   # quiet output
pytest -x                   # stop on first failure
```

---

## Common troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `asyncpg` connection refused | PostgreSQL not running | `docker-compose up -d` |
| `alembic upgrade head` fails | Bad `DATABASE_URL` in `.env` | Check `.env` matches Docker Compose defaults |
| `ModuleNotFoundError` | Virtual env not activated or deps not installed | Activate venv and re-run `pip install -e ".[dev]"` |
| `alembic --autogenerate` produces empty migration | Asyncpg not installed or no DB connection | Ensure `asyncpg` is installed and PostgreSQL is running |
| Port 5432 already in use | Local PostgreSQL running | Stop local PostgreSQL or change Docker Compose port mapping |
