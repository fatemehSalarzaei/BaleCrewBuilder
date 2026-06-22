# 12 — Strict Claude Phase Prompts

Use these prompts one at a time. Do not ask Claude to implement all phases in one pass.

## Global preface to paste before each phase

```text
You are implementing the AI-Assisted Bale Bot Project Builder Platform.
Read and obey CLAUDE.md and all strict contract docs.
Do not implement a fixed generated bot project.
Do not bypass Documentation First or Blueprint validation.
Do not use CrewAI as the deterministic Generator.
Implement only the requested phase.
At the end, report files changed, tests added, commands run, and remaining risks.
```

## Phase 0 prompt

```text
Implement Phase 0: repository foundation.
Create the backend project skeleton, FastAPI health endpoint, config/logging, pytest setup, and Docker Compose for PostgreSQL and Redis.
Do not implement generated bot domain logic.
Do not create ticket-specific files.
Acceptance criteria: app starts, health endpoint works, tests run.
```

## Phase 1 prompt

```text
Implement Phase 1: Builder Platform core data model and status workflow.
Add models for projects, uploaded_files, project_documents, document_reviews, blueprints, blueprint_validations, generation_runs, generated_artifacts, and ai_runs.
Add project status transitions and guards.
Implementation generation must be blocked unless document is approved and Blueprint is validated.
Add tests for status guards.
```

## Phase 2 prompt

```text
Implement Phase 2: Documentation First flow.
Add document upload metadata endpoints, text extraction for markdown/txt, Project Bot Document storage, feedback endpoint, approval endpoint, and audit/review records.
Do not generate code from raw text.
Add tests showing code generation is blocked before approval.
```

## Phase 3 prompt

```text
Implement Phase 3: Bot Blueprint schema and validation.
Create strict Pydantic v2 schemas for ProjectSpec, WorkflowSpec, BotSpec, RoleSpec, PermissionSpec, FlowSpec, ApiEndpointSpec, EntitySpec, MiniAppRouteSpec, SecuritySpec, GenerationSpec.
Validation must reject missing roles, shared bot webhook/token, admin routes open to users, and generation before DOCUMENT_APPROVED.
Add tests using valid and invalid Blueprint fixtures.
```

## Phase 4 prompt

```text
Implement Phase 4: deterministic Generator core.
Create generator module with renderer, template_registry, context_builder, validators, packager, and manifest builder.
The Generator must accept only a validated Blueprint.
Do not call LLMs inside Generator.
Add tests for deterministic file list, unknown template rejection, and output path safety.
```

## Phase 5 prompt

```text
Implement Phase 5: backend generated project templates.
Add Jinja2 templates for FastAPI backend core, auth/RBAC/audit, dynamic entities, dynamic API routes, services, tests, Docker/env.
Templates must be parameterized by Blueprint and must not hard-code ticket or appointment domain.
Add tests rendering two different entity sets.
```

## Phase 6 prompt

```text
Implement Phase 6: Bale multi-bot templates.
Add shared Bale client using httpx, webhook/router templates, User Bot templates, Admin Bot templates, idempotency, permission checks, and bot tests.
User/Admin bots must have separate tokens, webhooks, command namespaces, handlers, and policies.
Admin Bot must enforce role checks and audit sensitive actions.
```

## Phase 7 prompt

```text
Implement Phase 7: frontend Mini App/Web Panel templates.
Add React/Vite/TypeScript template with user/admin routes generated from Blueprint, API client, auth bootstrap, Bale Mini App initData forwarding, route guards, and loading/error states.
Mini App is the same frontend as Web Panel in Bale mode.
Do not generate fixed pages unless Blueprint defines them.
```

## Phase 8 prompt

```text
Implement Phase 8: end-to-end generation tests.
Add two Blueprint fixtures for different domains and verify the generated outputs differ correctly.
One fixture must have User Bot + Admin Bot. Another may be User Bot only.
Verify no hard-coded sample domain is generated when not in Blueprint.
```

## Phase 9 prompt

```text
Implement Phase 9: documentation and handoff.
Add README, local setup, generation workflow, approval gate explanation, sample commands, generated project run instructions, known limitations, and future work.
```
