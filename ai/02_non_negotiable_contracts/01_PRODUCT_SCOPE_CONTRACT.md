# 01 — Product Scope Contract

## Product definition

The system to implement is the **Builder Platform**. It receives an initial project idea or document and produces, after review and validation, a generated Bale bot project.

The generated Bale bot project may be different each time. The platform must not assume a fixed domain.

## In scope for the Builder Platform

- Project creation and status management.
- Document upload and parsing.
- CrewAI documentation flow.
- Project Bot Document generation.
- Human review, feedback, approval, rejection.
- Bot Blueprint generation after document approval.
- Blueprint validation by Pydantic/JSON schema.
- Deterministic Generator module.
- Modular templates for backend, Bale bots, frontend, docs, Docker, tests.
- Project output packaging as ZIP or repository directory.
- Run history, AI run metadata, validation errors, generated artifact records.

## In scope for generated projects

Generated projects must be capable of containing:

- Python FastAPI backend.
- User Bale Bot.
- Admin Bale Bot if required by Blueprint.
- Shared Bale API client.
- Mini App/Web Panel frontend.
- PostgreSQL models and migrations.
- Redis-backed state/idempotency/session support.
- Celery worker skeleton.
- RBAC and audit log.
- Bale Mini App auth validation.
- Tests, Docker, README, docs.

## Out of scope for MVP unless explicitly requested later

- Production deployment automation.
- Kubernetes.
- Marketplace.
- Multi-messenger runtime support.
- Payment flows.
- Visual flow editor.
- Fully autonomous business-logic coding without review.
- Arbitrary integration generator for every third-party service.

## Core product pipeline

```text
Raw idea or uploaded document
    ↓
Document parsing and normalization
    ↓
CrewAI Documentation Flow
    ↓
Project Bot Document
    ↓
Human Review Gate
    ↓
Approved Project Document
    ↓
CrewAI Blueprint Flow
    ↓
Validated Bot Blueprint
    ↓
Deterministic Generator
    ↓
Generated Project
    ↓
Tests, lint, package
```

## Project states

The platform must support at minimum:

```text
DRAFT_CREATED
DOCUMENT_GENERATING
DOCUMENT_DRAFTED
DOCUMENT_REVIEW_PENDING
DOCUMENT_CHANGE_REQUESTED
DOCUMENT_APPROVED
BLUEPRINT_GENERATING
BLUEPRINT_GENERATED
BLUEPRINT_VALIDATION_FAILED
BLUEPRINT_VALIDATED
IMPLEMENTATION_GENERATING
IMPLEMENTATION_FAILED
IMPLEMENTATION_GENERATED
IMPLEMENTATION_REVIEW_PENDING
IMPLEMENTATION_APPROVED
READY_FOR_DEPLOY
DEPLOYED
```

## Required state gate

`IMPLEMENTATION_GENERATING` is allowed only when:

- status is `DOCUMENT_APPROVED` or later;
- a Blueprint exists;
- Blueprint validation result is `BLUEPRINT_VALIDATED`;
- validation errors list is empty.
