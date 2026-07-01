# CODEX.md — Mandatory Continuation Contract

You are continuing the **BaleCrewBuilder** repository.

Your task is to continue the Builder Platform, not to build one fixed Bale bot project.

## Product boundary

BaleCrewBuilder is a Documentation First project generator platform:

1. A project is created from a human idea or uploaded document.
2. CrewAI or a fallback provider creates a Project Bot Document.
3. A human reviewer approves or rejects the document.
4. A Bot Blueprint is generated or manually submitted.
5. The Blueprint is validated by strict Pydantic rules.
6. The deterministic Generator renders a project-specific backend, Bale bot layer, frontend panel, tests, docs, and deployment files from templates.

Never bypass the approval and validation gates.

## Current implementation status

The repository already contains the core Builder Platform, data model, document flow, Blueprint schema, validation service, generator core, backend templates, Bale multi-bot templates, frontend templates, fixture-based tests, and handoff documentation.

The project is **not product-complete**. The next work must focus on closing implementation gaps, not changing the architecture.

## Non-negotiable continuation rules

1. Do not generate project files directly from raw prompt text.
2. Do not hard-code a ticket, CRM, appointment, or support domain.
3. Keep CrewAI limited to documentation and structured Blueprint assistance.
4. Keep deterministic generation inside the Generator module and Jinja2 templates.
5. Keep User Bot and Admin Bot separate when the Blueprint defines both.
6. Keep backend services as the business-logic authority.
7. Keep frontend and bot layers thin; they must call backend services.
8. Add tests for every new endpoint, service, template, or validation rule.
9. Update docs whenever behavior changes.
10. Report changed files, tests run, and remaining gaps after each task.

## Required read order

Read these files before making code changes:

1. `ai/CODEX.md`
2. `ai/00_start_here/00_INDEX.md`
3. `ai/CLAUDE.md`
4. `ai/02_non_negotiable_contracts/01_PRODUCT_SCOPE_CONTRACT.md`
5. `ai/02_non_negotiable_contracts/02_STATIC_VS_DYNAMIC_DOCS_CONTRACT.md`
6. `ai/02_non_negotiable_contracts/03_REPOSITORY_STRUCTURE_CONTRACT.md`
7. `ai/03_architecture_contracts/01_CREWAI_DOCUMENTATION_APPROVAL_CONTRACT.md`
8. `ai/03_architecture_contracts/02_BOT_BLUEPRINT_SCHEMA_CONTRACT.md`
9. `ai/03_architecture_contracts/03_GENERATOR_CONTRACT.md`
10. `ai/03_architecture_contracts/04_MODULAR_TEMPLATE_RULES.md`
11. `ai/04_generation_rules/01_MULTI_BOT_BALE_GENERATION_RULES.md`
12. `ai/04_generation_rules/02_BACKEND_BUILDER_GENERATION_RULES.md`
13. `ai/04_generation_rules/03_FRONTEND_MINIAPP_PANEL_GENERATION_RULES.md`
14. `ai/04_generation_rules/04_SECURITY_AUTH_RBAC_AUDIT_RULES.md`
15. `ai/05_execution_plan/01_PHASES_TASKS_ACCEPTANCE_CRITERIA.md`
16. `ai/05_execution_plan/02_CODEX_CONTINUATION_BACKLOG.md`
17. `ai/06_quality_gates/01_DEFINITION_OF_DONE_AND_REJECTION.md`
18. `docs/limitations-and-future-phases.md`
19. `docs/testing-and-runbook.md`

## First implementation priority

Start with Phase 10 in `ai/05_execution_plan/02_CODEX_CONTINUATION_BACKLOG.md` unless the user explicitly assigns another phase.

The recommended first task is the generated artifact download flow:

- Add an endpoint to download the generated ZIP artifact.
- Add a service method that resolves the latest completed generation run for a project.
- Return the existing ZIP from `generated_artifacts` using FastAPI `FileResponse`.
- Add tests for success, project not found, no completed generation, no ZIP artifact, and missing file on disk.
- Update API docs and README after implementation.

## Output discipline

After each implementation task, return:

1. Summary of what changed.
2. Exact files changed.
3. Tests added or changed.
4. Commands run.
5. Result of tests.
6. Known remaining gaps.
7. Whether the implemented phase meets acceptance criteria.
