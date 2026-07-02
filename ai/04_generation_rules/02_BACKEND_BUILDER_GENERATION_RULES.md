# 08 — Backend Builder Generation Rules

## Purpose

This file defines how the Builder Platform generates backend projects from Blueprint. It is not a backend spec for one fixed generated project.

## Required backend stack

Generated backend must use:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- Celery skeleton
- httpx for Bale API
- pytest

## Required core backend structure

```text
backend/app/
  main.py
  core/
    config.py
    security.py
    logging.py
  db/
    session.py
    base.py
    migrations/
  models/
  schemas/
  api/
    deps.py
    routes/
  services/
  bot/
  miniapp/
  workers/
```

## Core modules always generated

- app bootstrap;
- config from env;
- database session;
- RBAC models;
- audit log;
- Bale account mapping;
- bot registry;
- processed update idempotency;
- Mini App auth validation;
- health check.

## Project-specific modules generated from Blueprint

For each Blueprint entity, generate:

```text
models/{entity}.py
schemas/{entity}.py
services/{entity}_service.py
api/routes/{entity_plural}.py
tests/test_{entity_plural}.py
```

Entity names must be sanitized and normalized. Do not allow path injection.

## API rules

Every generated endpoint must map to:

- request schema if body exists;
- response schema;
- service method;
- auth dependency;
- role dependency when required;
- audit call if `audit_required=true`.

No endpoint may directly perform complex business logic.

## Service layer rules

Services own business logic.

Generated service method pattern:

```text
validate permission/context
validate input
load required entities
apply business rule
persist changes
write audit if required
return typed output
```

## Database rules

Core tables are mandatory:

- users;
- roles;
- permissions;
- user_roles;
- role_permissions;
- bale_accounts;
- bots;
- bot_conversations;
- processed_updates;
- audit_logs;
- app_settings.

Project-specific tables come from Blueprint.

## Migration rules

Generated project must include Alembic setup. For MVP, generated models plus initial migration script are acceptable. Do not leave database initialization unspecified.

## Builder Platform backend APIs

The Builder Platform itself must implement these APIs:

```text
POST /projects
GET /projects/{id}
POST /projects/{id}/documents
POST /projects/{id}/documents/generate
POST /projects/{id}/documents/upload
GET /projects/{id}/document
POST /projects/{id}/documents/{document_id}/submit-review
POST /projects/{id}/document/feedback
POST /projects/{id}/document/approve
GET /projects/{id}/reviews
POST /projects/{id}/blueprint/generate
POST /projects/{id}/blueprint
GET /projects/{id}/blueprint
POST /projects/{id}/blueprint/validate
POST /projects/{id}/generate
GET /projects/{id}/runs
GET /projects/{id}/download
```

Separate persisted requirements endpoints such as `POST /projects/{id}/analyze`
and `GET /projects/{id}/requirements` are not current Builder Platform APIs.
Requirements extraction is represented by Project Bot Document generation and
review. Add separate requirements persistence only as a future phase with an
explicit model, service, and tests.

## Required persistence for Builder Platform

At minimum:

- projects;
- project_documents;
- document_reviews;
- blueprints;
- blueprint_validations;
- generation_runs;
- generated_artifacts;
- ai_runs;
- uploaded_files.

## Tests required

Builder Platform must have tests for:

- creating project;
- uploading document metadata;
- document approval gate;
- rejecting generation before approval;
- blueprint validation;
- generator run creation;
- artifact packaging.
