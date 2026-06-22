# 11 — Phases, Tasks, and Acceptance Criteria

Claude must implement phases sequentially. Do not skip phases. Do not combine unrelated phases.

## Phase 0 — Repository foundation

### Tasks

- Create backend project structure.
- Configure pyproject.
- Add FastAPI app skeleton.
- Add config/logging.
- Add Docker Compose with PostgreSQL/Redis.
- Add pytest setup.

### Acceptance criteria

- App starts.
- Health endpoint works.
- Tests run.
- No generated bot sample project exists.

## Phase 1 — Core data model and status workflow

### Tasks

- Implement Builder Platform models:
  - projects;
  - uploaded_files;
  - project_documents;
  - document_reviews;
  - blueprints;
  - blueprint_validations;
  - generation_runs;
  - generated_artifacts;
  - ai_runs.
- Implement project statuses.
- Implement status transition guard.

### Acceptance criteria

- Project can be created.
- Status transitions are controlled.
- Implementation generation cannot start before document approval.

## Phase 2 — Document ingestion and Documentation First flow

### Tasks

- Implement document upload metadata.
- Implement text extraction for Markdown/TXT first; DOCX/PDF optional later.
- Add CrewAI documentation flow abstraction.
- Add Project Bot Document storage.
- Add review feedback and approval endpoints.

### Acceptance criteria

- Project document can be generated/stored.
- Feedback creates new review record.
- Approve changes status to `DOCUMENT_APPROVED`.
- Generation endpoint still blocked until Blueprint valid.

## Phase 3 — Blueprint schema and validation

### Tasks

- Implement Pydantic Blueprint schemas.
- Implement validation service.
- Add API to generate/store Blueprint placeholder from approved document.
- Add strict validation rules.

### Acceptance criteria

- Invalid Blueprint rejected with actionable errors.
- Valid multi-bot Blueprint passes.
- Blueprint cannot be generated before document approval.

## Phase 4 — Deterministic Generator core

### Tasks

- Implement generator package.
- Implement template registry.
- Implement render context builder.
- Implement output root safety.
- Implement manifest generation.
- Implement ZIP packaging.

### Acceptance criteria

- Generator accepts only validated Blueprint.
- Same Blueprint produces stable file list.
- Unknown template/module fails.
- Manifest is produced.

## Phase 5 — Backend generated project templates

### Tasks

- Add backend core templates.
- Add auth/RBAC/audit templates.
- Add entity/API/service templates.
- Add tests templates.

### Acceptance criteria

- Generated backend has expected structure.
- Entity templates are dynamic from Blueprint.
- No hard-coded ticket domain appears unless Blueprint asks for it.

## Phase 6 — Bale multi-bot generated templates

### Tasks

- Add shared Bale client template using httpx.
- Add webhook/router templates.
- Add User Bot templates.
- Add Admin Bot templates.
- Add idempotency and permission templates.

### Acceptance criteria

- User Bot and Admin Bot are separate when Blueprint defines both.
- Tokens/webhooks are separate.
- Admin Bot has authorization and audit flow.
- Generated tests cover bot webhooks.

## Phase 7 — Frontend Mini App/Web Panel templates

### Tasks

- Add frontend app skeleton.
- Add Bale auth bootstrap.
- Add normal web panel mode placeholder.
- Add user/admin route generation.
- Add API client/hooks generation.

### Acceptance criteria

- Generated frontend routes follow Blueprint.
- Admin routes are guarded.
- Mini App auth sends raw initData to backend.
- No fixed domain pages are generated unless Blueprint defines them.

## Phase 8 — End-to-end sample generation tests

### Tasks

- Add at least two Blueprint fixtures:
  - support/ticket-like project;
  - appointment/form-like project.
- Generate projects from both.
- Verify output differs by Blueprint.
- Run generated backend tests where possible.

### Acceptance criteria

- Two distinct generated projects are produced.
- No hard-coded sample project assumption.
- Multi-bot project includes User/Admin Bot.
- User-only project does not include Admin Bot.

## Phase 9 — Documentation and handoff

### Tasks

- Add README.
- Add developer setup.
- Add generation workflow docs.
- Add generated project usage docs.
- Add limitations and future phases.

### Acceptance criteria

- A developer can run Builder locally.
- A developer can generate a project from a sample Blueprint.
- A developer understands approval gates.
