# BaleCrewBuilder

AI-Assisted Bale Bot Project Builder Platform.

## For Claude

Read these files before implementing anything:

1. [ai/CLAUDE.md](ai/CLAUDE.md) — mandatory implementation contract and absolute rules
2. [ai/00_start_here/00_INDEX.md](ai/00_start_here/00_INDEX.md) — full read order and pack overview

All implementation documentation lives under [`ai/`](ai/). See [ai/README.md](ai/README.md) for the complete folder structure and study order.

## For developers

- Implementation documentation: [`ai/`](ai/)
- Phase prompts: [`ai/07_claude_prompts/01_CLAUDE_PHASE_PROMPTS_STRICT.md`](ai/07_claude_prompts/01_CLAUDE_PHASE_PROMPTS_STRICT.md)
- Reference proposal: [`ai/01_reference/REFERENCE_PROJECT_PROPOSAL_v1_1.md`](ai/01_reference/REFERENCE_PROJECT_PROPOSAL_v1_1.md)

## Local development setup

```bash
cp .env.example .env          # edit DATABASE_URL / SECRET_KEY as needed
docker-compose up -d          # starts PostgreSQL and Redis
pip install -e ".[dev]"
```

## Database migrations

Migration files live in [`app/db/migrations/versions/`](app/db/migrations/versions/).
[`alembic.ini`](alembic.ini) is at the repo root; run all `alembic` commands from there.

### Apply all migrations (create schema)

```bash
alembic upgrade head
```

### Roll back the last migration

```bash
alembic downgrade -1
```

### Generate a new migration after editing models

```bash
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

> **Note:** `--autogenerate` requires a running PostgreSQL instance (configured via
> `DATABASE_URL` in `.env`) and `asyncpg` installed. It compares the live schema
> against SQLAlchemy metadata to produce the diff.

### Inspect current migration state

```bash
alembic current     # revision applied to the connected database
alembic history     # full migration chain (no DB connection needed)
alembic upgrade --sql head   # emit SQL to stdout without connecting
```

## Running tests

Tests use an in-memory SQLite database via `aiosqlite` — no PostgreSQL required.

```bash
pytest
```
