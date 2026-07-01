# Codex Continuation Backlog — BaleCrewBuilder

This backlog starts after the initial Builder Platform and generator skeleton. It is written for Codex continuation work.

The phases below must be implemented sequentially unless the user explicitly changes the priority.

## Phase 10 — Artifact download and artifact management

### Problem

The generator creates output directories and ZIP files, and stores artifact metadata, but the API does not expose a download endpoint for users to retrieve the generated project package.

### Tasks

- Add `GET /projects/{project_id}/download`.
- Resolve the latest completed generation run for the project.
- Locate the ZIP artifact in `generated_artifacts`.
- Return the ZIP with FastAPI `FileResponse`.
- Return precise errors for:
  - project not found;
  - no completed generation run;
  - no ZIP artifact;
  - artifact path missing on disk.
- Add tests for all success and failure cases.
- Update `README.md`, `docs/generation-workflow.md`, and `docs/generated-project-usage.md`.

### Expected files

- `app/api/routes/artifacts.py` or extend `app/api/routes/generator.py`
- `app/services/artifact_service.py`
- `app/api/deps.py`
- `app/main.py`
- `tests/test_artifact_download.py`
- `docs/generation-workflow.md`
- `docs/generated-project-usage.md`
- `README.md`

### Acceptance criteria

- A generated ZIP can be downloaded through the API after `IMPLEMENTATION_GENERATED`.
- Download is blocked when generation has not completed.
- Missing files produce an actionable API error.
- Tests pass without requiring PostgreSQL.

## Phase 11 — Align generation response schema with actual artifacts

### Problem

The public workflow documentation states that the generation response contains generated file list and manifest hash, but the current `GenerationRunRead` schema exposes only run metadata.

### Tasks

- Extend generation response with:
  - generated file list;
  - ZIP filename/path metadata where safe;
  - manifest filename;
  - optional manifest hash if already available or easy to compute deterministically.
- Keep internal storage paths out of public response unless explicitly needed.
- Add tests for response payload shape.
- Update documentation to match actual API behavior.

### Expected files

- `app/schemas/generation.py`
- `app/services/generation_service.py`
- `tests/test_generation_response.py` or update existing generation tests
- `docs/generation-workflow.md`
- `README.md`

### Acceptance criteria

- API response and docs are consistent.
- Existing tests remain green.
- No internal absolute path leaks in public API response unless documented.

## Phase 12 — Production deployment templates for generated projects

### Problem

Generated projects do not yet include production-ready Docker/runtime files.

### Tasks

- Generate backend Dockerfile.
- Generate frontend Dockerfile.
- Generate generated-project `docker-compose.yml`.
- Generate `.env.example` for generated projects.
- Add optional nginx/reverse-proxy template only if it is controlled by Blueprint/generation module.
- Add tests that assert generated deployment files exist and do not include secrets.

### Expected files

- `app/generator/modules/deployment.py` or extend module structure cleanly
- `app/generator/templates/deployment/...`
- `app/generator/template_registry.py`
- `app/services/validation_service.py`
- `tests/test_deployment_template_generation.py`
- `docs/generated-project-usage.md`

### Acceptance criteria

- Generated project can be started locally with documented Docker commands after business stubs are completed.
- No bot tokens or secrets are hard-coded.
- Deployment output is controlled by Blueprint modules.

## Phase 13 — Generated authentication implementation baseline

### Problem

Generated `AuthService`, password hashing, JWT encoding/decoding, and Mini App token validation are stubs. This blocks realistic generated backend usage.

### Tasks

- Add required generated backend dependencies for JWT and password hashing.
- Implement password hash/verify helpers in generated security template.
- Implement JWT encode/decode helpers.
- Implement a minimal user lookup contract that works with generated `users`, `roles`, and mapping tables.
- Implement Bale Mini App `initData` HMAC validation in backend service template.
- Add unit tests for valid/invalid password, JWT, and Mini App initData.

### Expected files

- `app/generator/templates/backend/app/core/security.py.j2`
- `app/generator/templates/backend/app/services/auth_service.py.j2`
- `app/generator/templates/backend/pyproject.toml.j2` if present, or equivalent dependency template
- `tests/test_backend_auth_template_generation.py`
- `docs/generated-project-usage.md`

### Acceptance criteria

- Generated auth code no longer raises `NotImplementedError` for core auth helpers.
- Mini App token verification does not trust unsafe frontend data.
- Tests cover positive and negative cases.

## Phase 14 — Real Bale webhook integration path

### Problem

Generated bot handlers and webhook tests are currently synthetic. The generated Bale client exists, but no real integration path validates webhook registration and end-to-end message handling.

### Tasks

- Add generated CLI/script for `setWebhook` per bot.
- Add generated environment variables for public base URL and per-bot webhook secret.
- Validate incoming webhook secret header if Bale supports it in the configured mode.
- Keep synthetic tests for unit coverage.
- Add optional integration tests marked with `pytest.mark.integration` that run only when real Bale tokens are provided.

### Expected files

- `app/generator/templates/bale/shared/client.py.j2`
- `app/generator/templates/bale/shared/webhook.py.j2`
- `app/generator/templates/bale/*/webhook.py.j2`
- `app/generator/templates/scripts/set_bale_webhooks.py.j2`
- `tests/test_bale_integration_template_generation.py`
- `docs/generated-project-usage.md`

### Acceptance criteria

- Generated project has a documented way to register webhooks for each bot.
- Unit tests do not require real Bale credentials.
- Integration tests are opt-in and safely skipped without credentials.

## Phase 15 — Celery worker generation

### Problem

Generation rules reference Celery for long-running tasks, but generated worker files are not produced yet.

### Tasks

- Add generated Celery app factory.
- Add task templates for long-running service operations.
- Add Redis broker/result backend configuration.
- Add tests that assert worker files are generated only when `celery_worker` module is enabled.
- Update Blueprint validation if module-specific dependencies are required.

### Expected files

- `app/generator/modules/workers.py`
- `app/generator/templates/workers/...`
- `app/services/validation_service.py`
- `tests/test_worker_template_generation.py`
- `docs/generated-project-usage.md`

### Acceptance criteria

- `celery_worker` module creates worker files and config.
- Projects without the module do not receive worker files.
- Generated worker tasks are stubs or adapters, not hidden business logic.

## Phase 16 — Frontend field-driven page generation

### Problem

Generated frontend pages are placeholders. They do not yet render entity fields, forms, lists, details, validation states, loading states, or error states from Blueprint data.

### Tasks

- Extend route/entity context for page generation.
- Generate list pages from entity fields.
- Generate form pages from entity fields.
- Generate detail pages from entity fields.
- Generate loading, empty, and error states.
- Keep AdminGuard behavior for admin-only routes.
- Add frontend template snapshot/string tests.

### Expected files

- `app/generator/modules/frontend.py`
- `app/generator/templates/frontend/src/pages/page.tsx.j2`
- `app/generator/templates/frontend/src/hooks/useApi.ts.j2`
- `tests/test_frontend_field_generation.py`
- `docs/generated-project-usage.md`

### Acceptance criteria

- Frontend output materially changes based on Blueprint entity fields and route page types.
- No hard-coded sample domain appears.
- Tests cover dashboard/list/form/detail route types.

## Phase 17 — Blueprint editor and reviewer UX API

### Problem

The current Builder Platform is API-first. For real product usage, reviewers need a structured way to inspect, edit, validate, and approve Blueprint data.

### Tasks

- Add endpoints to patch specific Blueprint sections safely.
- Add validation previews without changing project status.
- Add review history for Blueprint changes.
- Add optional frontend/admin panel scope only after backend API is stable.

### Expected files

- `app/api/routes/blueprints.py`
- `app/services/blueprint_service.py`
- `app/db/models/...` if history is stored separately
- migration file under `app/db/migrations/versions/`
- `tests/test_blueprint_editor_api.py`
- `docs/generation-workflow.md`

### Acceptance criteria

- Reviewer can safely edit Blueprint sections.
- Validation errors remain actionable.
- Blueprint edit history is traceable.

## Phase 18 — DOCX/PDF document ingestion

### Problem

Document upload currently supports text/Markdown style extraction only. Product usage may require DOCX/PDF upload.

### Tasks

- Add DOCX extraction using a stable dependency.
- Add PDF extraction only if acceptable extraction quality can be tested.
- Add file-size and content-type limits.
- Add tests with small fixture files.
- Keep unsupported file errors precise.

### Expected files

- `app/services/text_extraction_service.py`
- `pyproject.toml`
- `tests/test_document_upload_extraction.py`
- `docs/developer-setup.md`

### Acceptance criteria

- `.docx` extraction works for simple text documents.
- `.pdf` support is either implemented with tests or explicitly left unsupported.
- Upload errors are predictable and documented.

## Phase execution rule

For each phase, Codex must:

1. Implement the smallest complete vertical slice.
2. Add or update tests in the same change.
3. Run the narrow test file first.
4. Run the full test suite if dependencies are available.
5. Update documentation in the same change.
6. Report remaining gaps honestly.
