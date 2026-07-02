# Codex Continuation Backlog — BaleCrewBuilder

This backlog is intentionally separate from `ai/05_execution_plan/01_PHASES_TASKS_ACCEPTANCE_CRITERIA.md`.

It does not rewrite the original phase plan. It records the current continuation status and starts the next tasks from the implementation that exists now.

---

## Completed continuation work

The following continuation tasks are implemented and covered by tests:

1. Artifact download and artifact management
   - `GET /projects/{project_id}/download` returns the ZIP artifact for the latest completed generation run.
   - Precise errors exist for missing project, no completed run, missing ZIP artifact, and missing file on disk.

2. Generation response accuracy
   - `POST /projects/{project_id}/generate` returns run metadata, generated artifact metadata, and `download_url` when a ZIP artifact exists.
   - Local filesystem paths are not exposed.

3. Document generation failure recovery
   - Failed documentation flow transitions the project to `DOCUMENT_GENERATION_FAILED`.
   - Retry from `DOCUMENT_GENERATION_FAILED` is allowed.

4. AI-assisted Blueprint proposal flow
   - `POST /projects/{project_id}/blueprint/generate?mode=ai` can propose structured Blueprint data from an approved document.
   - Human storage/review and `/blueprint/validate` remain mandatory before code generation.

5. Generated backend security primitives
   - Generated password hashing and JWT create/decode helpers are implemented.
   - Mini App token verification still fails closed until the Bale HMAC contract is fully wired.

6. Schema-aware generated endpoint wiring
   - Generated endpoints pass request body, path params, current user, and DB session into service stubs.
   - RBAC and audit calls are preserved.

7. Generated Bale bot handler backend delegation
   - Generated bot command handlers call `bale/shared/backend_client.py`.
   - User registration, admin authorization, permission checks, command actions, and audit delegation go through backend abstractions.
   - Handlers no longer raise `NotImplementedError`.

8. Field-driven frontend route pages
   - Generated list/form/detail pages use inferred entity fields and API hooks.
   - Dashboard/report/settings-style pages render structured panels and connected API dependencies.
   - Loading, error, and empty states are generated.

9. Optional Celery worker skeleton
   - When `generation.enabled_modules` includes `celery_worker`, generated projects include `backend/app/workers/celery_app.py`, `tasks.py`, Celery settings, and Celery/Redis requirements.
   - Worker tasks remain service-layer orchestration stubs.

10. Minimal production deployment templates
   - Every generated project includes `backend/Dockerfile`, `frontend/Dockerfile`, `deploy/docker-compose.prod.yml`, `deploy/.env.example`, and `docs/deployment.md`.
   - Celery worker service is included only when `celery_worker` is enabled.
   - Admin bot token placeholders are included only when the Blueprint defines an admin bot.

11. Generated Alembic migration scaffold
   - Generated projects include `backend/alembic.ini`, `backend/app/db/migrations/env.py`, `script.py.mako`, and a versions package.
   - Alembic env imports generated model modules and uses `Base.metadata`.
   - Initial migration revision is still created and reviewed by the developer.

---

## Current real limitations

- Generated Blueprint business service methods may still raise `HTTPException(status_code=501)` because business logic is intentionally project-specific.
- Generated entity service files remain CRUD/service skeletons and need real persistence logic.
- Real Bale Mini App HMAC verification is not implemented yet; generated code rejects/fails closed instead of trusting frontend data.
- Generated backend internal bot action/RBAC/audit endpoints referenced by `BackendClient` still need project-specific implementations.
- Generated initial Alembic migration content is not created during generation.
- Production deployment templates are minimal and not production-hardened.
- Real Bale network integration tests are missing.
- Artifact storage is local filesystem based.
- Production-grade artifact storage, retention, and signed/authenticated download access are missing.

---

## Next task candidates

### Task 08 — Generated service layer implementation for simple entity CRUD

Generate functional service methods for simple Blueprint entities while keeping business-specific operations as explicit 501 stubs.

Acceptance criteria:

- Basic list/create/read/update/delete service methods work for simple entities.
- Generated routes continue to delegate to services.
- Auth, RBAC, and audit behavior remain intact.
- Tests cover generated simple-entity CRUD paths.

### Task 09 — Generated initial Alembic migration validation

Add a tested path for creating and validating the initial migration from generated models.

Acceptance criteria:

- `alembic revision --autogenerate -m "initial"` works against generated projects.
- Generated revision is reviewed in tests for expected tables.
- Documentation explains how to run and inspect migrations.

### Task 10 — Backend Mini App HMAC verification

Implement generated backend verification for raw Bale Mini App `initData` once the Bale contract is confirmed.

Acceptance criteria:

- Frontend still sends only raw `initData`.
- Backend validates HMAC and `auth_date` freshness.
- Invalid/expired Mini App auth is rejected.
- No frontend `initDataUnsafe` authorization is introduced.

### Task 11 — Generated backend bot action endpoints

Generate backend internal endpoints/services for bot action delegation used by `bale/shared/backend_client.py`.

Acceptance criteria:

- Generated bot client paths have backend counterparts.
- Registration/admin/permission checks use backend data.
- Sensitive admin bot actions write audit logs.
- Bot handlers remain interface adapters only.

### Task 12 — Production deployment hardening

Harden the minimal generated Docker deployment path.

Acceptance criteria:

- TLS/reverse proxy guidance is generated.
- Backup and restore guidance is documented.
- Runtime health checks are stronger than smoke checks.
- Migration workflow is tested.
- No secrets are hard-coded.

### Task 13 — Artifact storage hardening

Move Builder Platform artifact storage beyond local filesystem assumptions.

Acceptance criteria:

- Storage abstraction supports durable object storage.
- Retention/cleanup policy is documented and testable.
- Download access is authenticated or signed.
