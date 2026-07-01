# Codex Continuation Backlog — BaleCrewBuilder

This backlog is intentionally separate from `ai/05_execution_plan/01_PHASES_TASKS_ACCEPTANCE_CRITERIA.md`.

It does not rewrite the original phase plan. It only defines continuation phases after the already implemented foundation.

---

## Phase 10 — Artifact Download and Artifact Management

### Problem

The generator writes output files and creates ZIP artifacts, but there is no API endpoint for downloading the latest generated ZIP.

### Required behavior

Add:

```text
GET /projects/{project_id}/download
```

The endpoint must:

1. Verify the project exists.
2. Find the latest completed generation run for the project.
3. Find the ZIP artifact linked to that run.
4. Verify the ZIP file exists on disk.
5. Return the ZIP using FastAPI `FileResponse`.
6. Return clear errors for:
   - project not found;
   - no completed generation run;
   - no ZIP artifact;
   - ZIP path missing on disk.

### Suggested files to add/change

```text
app/api/routes/artifacts.py
app/api/deps.py
app/services/artifact_service.py
app/schemas/artifact.py
app/main.py
tests/test_artifact_download.py
```

### Acceptance criteria

- `GET /projects/{project_id}/download` returns a ZIP for the latest completed run.
- The endpoint does not allow downloading artifacts from failed/running runs.
- Missing project returns 404.
- No completed run returns 409 or 404 with an explicit message.
- Missing ZIP artifact returns 404 or 409 with an explicit message.
- Missing file on disk returns 410 Gone or 500 with an explicit message; prefer 410.
- Tests cover success and all failure branches.

---

## Phase 11 — Generation Response Accuracy

### Problem

The generation workflow documentation says the response includes generated file list and manifest hash, but the actual response model only returns generation run metadata.

### Required behavior

Either update the API response schema or update the documentation. Prefer improving the API response.

### Suggested files to change

```text
app/schemas/generation.py
app/services/generation_service.py
app/api/routes/generator.py
tests/test_generation_service.py
docs/generation-workflow.md
```

### Acceptance criteria

- Generation response includes the run ID, status, generated artifact metadata, and ZIP filename/path or download URL.
- Documentation matches the actual response.
- Tests assert the response shape.

---

## Phase 12 — Generated Backend Security Implementation

### Problem

Generated backend security functions are TODO stubs.

### Required behavior

Generated projects should include working password hashing and JWT encode/decode utilities.

Mini App HMAC verification must be implemented only if the Bale Mini App verification contract is confirmed and documented.

### Suggested files to change

```text
app/generator/templates/backend/app/core/security.py.j2
app/generator/templates/backend/app/services/auth_service.py.j2
app/generator/templates/backend/app/api/deps.py.j2
pyproject.toml
```

### Acceptance criteria

- Generated password hashing works.
- Generated JWT create/decode works.
- Generated auth dependency rejects invalid tokens.
- Tests cover token success and failure.
- Mini App verification remains explicit and testable, not trusted from frontend unsafe data.

---

## Phase 13 — Generated Service Layer Realism

### Problem

Generated endpoint services are stubs and often raise 501/NotImplementedError.

### Required behavior

For Blueprint-defined entities, generate basic CRUD service methods and route wiring.

Blueprint-specific business operations may remain explicit TODOs, but generic entity CRUD must be functional.

### Acceptance criteria

- Generated entity list/create/read/update/delete works for simple entities.
- Generated routes call service methods with request payloads and path params.
- Tests are generated per entity.

---

## Phase 14 — Bale Bot Handler Integration

### Problem

Generated bot command handlers dispatch but do not call backend services.

### Required behavior

Generate handler wiring based on `BotCommandSpec.handler` and Blueprint service mappings.

### Acceptance criteria

- Command handlers do not contain business logic.
- Command handlers call backend service/client abstractions.
- Admin bot handlers enforce role checks and audit hooks.
- Tests cover user bot and admin bot command dispatch.

---

## Phase 15 — Frontend Field-Driven Pages

### Problem

Generated frontend pages are placeholders.

### Required behavior

Generate route pages from Blueprint route type and entity field definitions.

### Acceptance criteria

- `list` routes produce table pages.
- `form` routes produce forms.
- `detail` routes produce detail views.
- Admin routes remain guarded.
- API errors and loading states are handled.

---

## Phase 16 — Celery Worker Generation

### Problem

`celery_worker` is a known module but worker templates are not generated.

### Required behavior

When Blueprint enables `celery_worker`, generate worker configuration and task stubs.

### Acceptance criteria

- Generated project includes Celery app factory.
- Redis/broker settings are configurable.
- Long-running service methods can be mapped to tasks.
- Tests or documented test stubs are generated.

---

## Phase 17 — Production Deployment Templates

### Problem

Generated projects do not include production deployment templates.

### Required behavior

Generate Dockerfile, docker-compose production profile, and environment documentation.

### Acceptance criteria

- Generated backend can run in Docker.
- Generated frontend can be built and served.
- Environment variables are documented.
- No secrets are hard-coded.
