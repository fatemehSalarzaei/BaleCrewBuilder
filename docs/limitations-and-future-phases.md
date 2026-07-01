# Limitations and Future Phases

Phases 0–10 of BaleCrewBuilder have been implemented. This document records known technical debt, honest limitations of the current implementation, and suggested directions for future work.

---

## Known limitations in the current implementation

### 1. Generated service stubs are not functional

All methods in `backend/app/services/blueprint_service.py` raise `HTTPException(status_code=501)`. They must be replaced with real business logic before the generated project can serve requests. This is by design — the generator creates a skeleton, not a complete application.

### 2. Authentication stubs raise NotImplementedError

`AuthService.authenticate()` and `AuthService.verify_miniapp_token()` in the generated `auth_service.py` raise `NotImplementedError`. A developer must implement:
- real database user lookup by username
- password hash verification
- HMAC validation for Bale Mini App `initData`

### 3. Bot command handlers are stubs

All bot command handlers in `bale/{bot_key}/commands.py` raise `NotImplementedError`. They dispatch to the correct handler based on command text, but the handlers themselves contain no logic. Each must be implemented to call the appropriate backend service.

### 4. No Alembic migrations in generated projects

The generator creates SQLAlchemy ORM models but does not generate Alembic migrations for the generated project. A developer must run `alembic init` and `alembic revision --autogenerate` inside the generated `backend/` directory after deployment.

### 5. No real Bale webhook calls in tests

The test suite does not make real HTTP requests to the Bale API. Webhook handler tests use mocked or synthetic update payloads. The `BaleClient` in `bale/shared/client.py` is generated but its network calls are not executed during testing.

### 6. CrewAI document generation requires external credentials

`POST /projects/{id}/documents/generate` requires a running CrewAI configuration with LLM API credentials. Without these, document generation will fail. Use `POST /projects/{id}/documents` (manual) or `POST /projects/{id}/documents/upload` as alternatives for local development.

### 7. Local filesystem artifact storage

Generated ZIP artifacts are downloadable through `GET /projects/{id}/download`, but artifact storage is still local filesystem based. Production deployments should add durable object storage, retention policy, and signed or authenticated download access.

### 8. Redis integration is not exercised in the current test suite

The generated `bale/shared/idempotency.py` references a Redis-backed duplicate update check. The Builder Platform's own test suite does not test Redis integration. The Redis service is defined in `docker-compose.yml` but is not actively used by any tested code path in the current implementation.

### 9. Celery worker skeleton not generated

The generation rules reference Celery for long-running tasks. The current Generator does not produce a Celery worker file. Long-running operations in generated services would need a worker queue added manually.

### 10. Generated frontend is a stub

Generated page components (`{ComponentName}Page.tsx`) are minimal placeholders. They do not include form handling, data tables, or error states. The `useApi.ts` hook is a generic stub. A developer must implement the actual UI logic.

### 11. Production deployment not documented

There is no documentation or configuration for deploying either the Builder Platform or a generated project to a production environment. Docker files for production deployment (multi-stage builds, gunicorn, nginx) are not generated.

---

## Honest status of each phase

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Repository foundation | Complete | FastAPI app, Docker Compose, pytest setup |
| 1 — Core data model | Complete | 9 ORM models, initial Alembic migration, status transitions |
| 2 — Document ingestion | Complete | Manual, AI-generated, and file-upload document flows |
| 3 — Blueprint schema and validation | Complete | Pydantic v2 schema, validation service, placeholder generation from document |
| 4 — Deterministic Generator core | Complete | Renderer, template registry, context builder, manifest, packager |
| 5 — Backend generated templates | Complete | 13 core templates + per-entity templates, service stubs |
| 6 — Bale multi-bot templates | Complete | user_bot + admin_bot + shared client, audience-driven selection |
| 7 — Frontend Mini App/Web Panel | Complete | React/Vite, Blueprint-driven routes, AdminGuard, Bale auth bootstrap |
| 8 — E2E sample generation tests | Complete | 48 E2E tests, support_ticket and appointment fixtures |
| 9 — Documentation and handoff | Complete | This docs set |
| 10 — Download and artifact management | Complete | Latest completed ZIP artifact can be downloaded via API |

---

## Suggested future phases

### Phase 11 — Production deployment templates

Add Docker multi-stage build files, gunicorn configuration, nginx reverse proxy config, and environment variable documentation for deploying a generated project to a VPS or container platform.

### Phase 12 — Real Bale webhook integration tests

Add integration tests that spin up a real (or sandboxed) Bale bot, send test webhook updates, and assert that the generated bot handlers respond correctly.

### Phase 13 — Celery worker generation

Add a generated `workers/` directory with a Celery app factory, task stubs for long-running Blueprint service methods, and Redis-backed task state.

### Phase 14 — Frontend page generation from Blueprint fields

Extend the frontend generator to produce data tables, forms, and detail views from Blueprint entity field definitions. Currently only page-level placeholders are generated.

### Phase 15 — Blueprint editor UI

Add a web-based Blueprint editor on the Builder Platform frontend that allows a reviewer to visually edit entities, roles, and API endpoints before validation.
