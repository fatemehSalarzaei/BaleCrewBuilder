# Codex Review Notes — Current Gaps

## Implemented since the original review

- Artifact download is implemented through `GET /projects/{project_id}/download`.
- Generation responses include artifact metadata and a ZIP `download_url` when available.
- Document generation failure recovery moves projects to `DOCUMENT_GENERATION_FAILED` and allows retry.
- AI-assisted Blueprint proposal generation exists behind `mode=ai`, while placeholder mode remains available.
- Generated backend password hashing and JWT primitives are implemented.
- Generated API endpoint wiring is schema-aware enough to pass body, path params, current user, and DB session into service stubs.
- Generated Bale bot command handlers delegate to `BackendClient` instead of raising `NotImplementedError`.
- Generated frontend route pages are field-driven for list/form/detail/panel pages and include loading/error/empty states.
- Optional Celery worker skeleton generation exists when `celery_worker` is enabled.
- Minimal Docker-based deployment templates are generated for every project.
- Generated Alembic scaffold is included for backend projects.

## Confirmed gaps to address

### 1. Generated business services are still placeholders

`backend/app/services/blueprint_service.py` may still raise `HTTPException(status_code=501)` for Blueprint-specific operations.

Impact: generated projects still need project-specific backend business logic before they can serve real product workflows.

### 2. Generated entity services are still skeletal

Entity route/model/schema files are generated, but service persistence logic remains minimal.

Impact: basic generated CRUD behavior is not yet production-useful without developer implementation.

### 3. Real Bale Mini App HMAC verification is not implemented

Generated `verify_miniapp_token()` fails closed instead of trusting frontend data. This is safe, but not complete.

Impact: generated Mini App login cannot work until backend HMAC validation, `auth_date` freshness checks, and user upsert/session issuance are implemented.

### 4. Generated bot backend action endpoints are not implemented

Generated bot handlers call `BackendClient`, but the generated backend does not yet provide full internal endpoints for bot command actions, registration lookup, admin verification, permission checks, or bot audit writes.

Impact: generated bot handlers are correctly wired as adapters, but backend action implementations are still needed.

### 5. Generated initial Alembic migration content is missing

The generator creates SQLAlchemy models and an Alembic scaffold wired to `Base.metadata`, but it does not create a fake initial migration revision during generation.

Impact: generated projects require a developer to run and review `alembic revision --autogenerate -m "initial"` before applying migrations.

### 6. Production deployment is minimal and not hardened

Generated projects include backend/frontend Dockerfiles, `deploy/docker-compose.prod.yml`, `deploy/.env.example`, and `docs/deployment.md`. They do not yet include TLS/reverse proxy automation, backup guidance, secret rotation, observability, or a tested migration workflow.

Impact: generated projects have a simple VPS/container starting point, but are not production-ready packages.

### 7. Real Bale network integration tests are missing

Tests cover generated files and synthetic webhook/update paths, but not real Bale network behavior.

Impact: production bot behavior still needs integration validation outside the deterministic generator tests.

### 8. Artifact storage is local filesystem based

Artifact ZIP download works, but storage is local. Retention, cleanup, durable object storage, and signed/authenticated download access are not implemented.

Impact: Builder Platform artifact management is suitable for local/development use, not hardened production operation.

## Blind spots / implementation risks

1. Do not bypass `DOCUMENT_APPROVED` or `BLUEPRINT_VALIDATED`.
2. Do not replace the deterministic generator with LLM file generation.
3. Do not hard-code any current sample project into templates.
4. Do not implement Mini App auth by trusting frontend `initDataUnsafe`.
5. Do not put business logic in bot handlers or frontend components.
6. Do not mix generated-project code into the Builder Platform runtime.
7. Do not mark generated projects or the Builder Platform as production-ready while migrations, deployment hardening, artifact hardening, and real Bale integration tests remain incomplete.
