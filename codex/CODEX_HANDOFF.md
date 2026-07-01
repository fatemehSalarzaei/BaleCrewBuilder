# CODEX_HANDOFF.md — Standalone Continuation Contract

## Purpose

Continue BaleCrewBuilder from the current repository state without overwriting the existing Claude/AI documentation pack.

This document is a Codex-specific handoff. It must live under `codex/` and must not replace existing files under `ai/` or `docs/`.

## Product boundary

BaleCrewBuilder is a Builder Platform, not a single bot project.

The platform must preserve this pipeline:

```text
Project
→ Project Document
→ Human Review / Approval
→ Bot Blueprint
→ Blueprint Validation
→ Deterministic Generator
→ Generated Bale project artifacts
```

## Non-negotiable implementation rules

1. Do not generate implementation files directly from raw prompt text.
2. Do not bypass document approval.
3. Do not bypass Blueprint validation.
4. Do not hard-code one sample domain such as ticketing, appointment, CRM, or support.
5. Do not merge User Bot and Admin Bot unless the Blueprint defines a single-bot project.
6. Do not store Bale bot tokens in generated source code.
7. Do not put business logic inside bot handlers or frontend components.
8. Generated bot handlers and frontend pages must delegate to backend services.
9. Add tests for every new API route, service behavior, and generator output rule.
10. Keep this `codex/` folder separate from the existing architecture docs.

## Current repository status summary

The Builder Platform already has:

- FastAPI application structure.
- PostgreSQL and Redis Docker Compose services.
- SQLAlchemy/Alembic persistence layer.
- Project status workflow.
- Document creation, upload, review, feedback, and approval flow.
- Blueprint schema and validation service.
- Deterministic generator core using Jinja2 templates.
- Backend, Bale bot, and frontend template modules.
- ZIP packaging function inside the generation flow.
- E2E sample generation tests.

The repository is not yet product-complete because several generated outputs are still skeletons and artifact access is incomplete.

## First implementation target

Start with Phase 10:

```text
Artifact download and artifact management
```

Do not start frontend improvements, Celery generation, production Docker templates, or real Bale integration before Phase 10 is complete and tested.
