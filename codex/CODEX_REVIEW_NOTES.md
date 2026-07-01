# Codex Review Notes — Current Gaps

## Confirmed gaps to address

### 1. Artifact download missing

The generator stores generated artifacts and ZIP metadata but the API does not expose a download endpoint.

Impact: users cannot retrieve generated projects through the API.

### 2. Generation response is too thin

The generation route returns only run metadata. It does not expose artifact list, ZIP metadata, or download URL.

Impact: frontend/API consumers cannot know where to retrieve the generated output.

### 3. Placeholder Blueprint generation is not enough for real products

The deterministic placeholder Blueprint is useful for tests and initial flow validation, but it does not extract full domain entities, API endpoints, or business flows.

Impact: generated projects remain generic unless a human submits a complete custom Blueprint.

### 4. Generated backend auth is not production-ready

Security templates still contain TODOs for password hashing, JWT, and Mini App verification.

Impact: generated projects cannot safely authenticate users without manual implementation.

### 5. Generated bot handlers are dispatch stubs

Handlers route commands but do not call backend service methods.

Impact: generated bots are not functional beyond webhook/dispatch structure.

### 6. Generated frontend is route-level only

Frontend routes are generated but page contents are placeholders.

Impact: generated Mini App/Web Panel is not yet usable as a management interface.

### 7. Celery worker module is declared but not generated

`celery_worker` exists as a known module but no worker templates are produced.

Impact: long-running generated operations need manual worker setup.

## Blind spots / implementation risks

1. Do not let Codex “simplify” the architecture by skipping approval gates.
2. Do not let Codex replace the deterministic generator with LLM file generation.
3. Do not let Codex hard-code the current sample project into templates.
4. Do not let Codex implement Mini App auth by trusting frontend `initDataUnsafe`.
5. Do not let Codex mix generated-project code into the Builder Platform source tree.
6. Do not let Codex silently edit existing architecture docs when adding continuation notes.
