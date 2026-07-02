# Limitations and Future Phases

The Builder Platform foundation and several Codex continuation tasks have been implemented. This document records known technical debt, honest limitations of the current implementation, and suggested directions for future work.

---

## Known limitations in the current implementation

### 1. Generated service stubs are not functional

All methods in `backend/app/services/blueprint_service.py` raise `HTTPException(status_code=501)`. They must be replaced with real business logic before the generated project can serve requests. This is by design — the generator creates a skeleton, not a complete application.

### 2. Authentication integration remains project-specific

Generated `backend/app/core/security.py` includes password hashing and JWT create/decode helpers. `AuthService.authenticate()` still intentionally returns `None` until the generated project's user lookup is implemented, and `verify_miniapp_token()` fails closed until backend-side Bale Mini App HMAC verification is wired. A developer must implement:
- real database user lookup by username
- password verification against the stored password hash
- HMAC validation for raw Bale Mini App `initData`
- `auth_date` freshness checks and user upsert/session issuance

### 3. Bot command handlers delegate, but backend action endpoints are stubs

Generated bot command handlers no longer raise `NotImplementedError`. They dispatch commands, verify registered users/admins through `BackendClient`, delegate command actions to backend endpoints, and send controlled user-facing replies through `BaleClient`.

The generated backend still needs real internal bot action/RBAC/audit endpoints behind the generated client paths. Business logic must remain in backend services, not in bot handlers.

### 4. Alembic scaffold exists, but initial migrations are not generated

The generator creates SQLAlchemy ORM models and an Alembic scaffold wired to `Base.metadata`. It does not generate or apply an initial migration during generation. A developer must run and review `alembic revision --autogenerate -m "initial"` and then apply it with `alembic upgrade head`.

### 5. No real Bale webhook calls in tests

The test suite does not make real HTTP requests to the Bale API. Webhook handler tests use mocked or synthetic update payloads. The `BaleClient` in `bale/shared/client.py` is generated but its network calls are not executed during testing.

### 6. CrewAI document generation requires external credentials

`POST /projects/{id}/documents/generate` requires a running CrewAI configuration with LLM API credentials. Without these, document generation will fail. Use `POST /projects/{id}/documents` (manual) or `POST /projects/{id}/documents/upload` as alternatives for local development.

### 7. Artifact storage abstraction is local-only

Generated ZIP artifacts are downloadable through `GET /projects/{id}/download`, and artifact access now goes through a storage abstraction. The only implemented backend is `ARTIFACT_STORAGE_BACKEND=local`, which stores generated files under `GENERATION_OUTPUT_DIR`. Production deployments should add durable object storage, retention policy, and signed or authenticated download access.

### 8. Redis integration is not exercised in the current test suite

The generated `bale/shared/idempotency.py` references a Redis-backed duplicate update check. The Builder Platform's own test suite does not test Redis integration. The Redis service is defined in `docker-compose.yml` but is not actively used by any tested code path in the current implementation.

### 9. Celery worker generation is opt-in and skeletal

When `generation.enabled_modules` includes `celery_worker`, the generator creates `backend/app/workers/celery_app.py`, `backend/app/workers/tasks.py`, and Celery/Redis settings. These are skeletons only; real tasks must call backend service-layer methods.

### 10. Generated frontend is generic, not product-polished

Generated route pages are field-driven for list, form, detail, dashboard, report, and settings-style routes. They use generated API hooks and include loading, error, and empty states. They are still generic generated UI; production information architecture, domain-specific presentation, advanced validation, and visual polish remain application work.

### 11. Production deployment is minimal, not hardened

Generated projects include a minimal Docker-based deployment package with backend/frontend Dockerfiles, `deploy/docker-compose.prod.yml`, `deploy/.env.example`, and `docs/deployment.md`. This is intentionally VPS/container friendly, but it is not a complete production operations setup. TLS termination, backups, observability, secret rotation, migration automation, and artifact hardening remain manual.

### 12. Separate requirements endpoints are deferred

The Builder Platform does not currently persist requirements as a separate resource. Requirements extraction is represented by Project Bot Document generation and review. `POST /projects/{id}/analyze` and `GET /projects/{id}/requirements` should remain future work until a requirements model, service, schemas, and tests are added.

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
| 11 — Generation response accuracy | Complete | Generation response includes artifact metadata and `download_url` |
| 12 — Generated backend security primitives | Complete | Password hashing and JWT helpers generated; Mini App HMAC still fails closed |
| 13 — AI Blueprint proposal flow | Complete | `mode=ai` can propose structured Blueprints; validation remains mandatory |
| 14 — Endpoint wiring realism | Complete | Generated endpoints pass body/path/current user/db into service stubs |
| 15 — Bale bot handler backend delegation | Complete | Generated handlers use `BackendClient`; backend actions remain project-specific |
| 16 — Frontend field-driven pages | Complete | Generated list/form/detail/panel pages from Blueprint metadata |
| 17 — Celery worker skeleton | Complete | Optional `celery_worker` module generates Celery app/task stubs |
| 18 — Production deployment templates | Complete | Minimal Docker-based generated deployment package |
| 19 — Generated Alembic scaffold | Complete | Alembic config/env/template generated; initial migration remains manual |
| 20 — Artifact storage abstraction | Complete | Local storage backend abstracted; production object storage remains future work |

---

## Suggested future phases

### Next phase — Generated service layer implementation for simple entity CRUD

Generate functional service methods for simple Blueprint entities while keeping business-specific operations as explicit 501 stubs.

### Follow-up — Production deployment hardening

Extend the minimal generated Docker deployment with TLS/reverse proxy examples, backup guidance, observability, secret rotation, and a tested migration flow.

### Follow-up — Generated initial Alembic migration

Generate and/or validate an initial migration revision deterministically, or add integration tests that run `alembic revision --autogenerate` against generated projects.

### Follow-up — Real Bale webhook integration tests

Add integration tests that spin up a real (or sandboxed) Bale bot, send test webhook updates, and assert that the generated bot handlers respond correctly.

### Follow-up — Production artifact storage

Add a durable artifact storage backend, such as S3-compatible object storage, with retention policy and signed or authenticated download access.

### Follow-up — Blueprint editor UI

Add a web-based Blueprint editor on the Builder Platform frontend that allows a reviewer to visually edit entities, roles, and API endpoints before validation.

### Follow-up — Persisted requirements resource

Add a dedicated requirements model and API only if product workflow needs requirements outside the Project Bot Document lifecycle.
