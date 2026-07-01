# AI Implementation Index — BaleCrewBuilder

**Version:** 3.1 Codex/Claude continuation structure  
**Root docs folder:** `ai/`  
**Target:** Continue the Builder Platform, not a single generated bot project.  
**Primary architecture:** Documentation First → Human Approval → Blueprint → Deterministic Generator → Generated Project.  
**Reference document:** `ai/01_reference/REFERENCE_PROJECT_PROPOSAL_v1_1.md`.

## Folder rule

All AI implementation documentation must live under the `ai/` folder.

Claude, Codex, or any other implementation agent must treat `ai/` as the source of implementation rules, architecture contracts, phase prompts, and quality gates. Application source code must not be placed inside `ai/`.

## Read order for Codex

Codex must read and obey these files in this order:

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

## Read order for Claude

Claude may continue to use the original Claude implementation pack, but must also read the Codex continuation backlog before starting new work:

1. `ai/CLAUDE.md`
2. `ai/00_start_here/00_INDEX.md`
3. `ai/05_execution_plan/02_CODEX_CONTINUATION_BACKLOG.md`
4. `docs/limitations-and-future-phases.md`
5. `docs/testing-and-runbook.md`

## Purpose of this pack

This pack is not a product pitch. It is an implementation contract for AI coding agents.

The repository must remain a platform that can generate different Bale bot projects from project-specific documents and validated Bot Blueprints. It must not drift into a single ticket bot, appointment bot, CRM bot, or hard-coded generated project.

## Core non-negotiable distinction

| Layer | Responsible for | Must be implemented as |
|---|---|---|
| Builder Platform | Manage project lifecycle, documents, approval, Blueprint, validation, generation | FastAPI app in `app/` |
| CrewAI inside the platform | Generate project-specific documentation and structured Blueprint assistance | Controlled documentation/analysis flow only |
| Human reviewer | Approve, reject, or request changes | Review gate in Builder |
| Generator | Produce files from validated Blueprint | Deterministic Jinja2 template renderer |
| Generated Project | Output per project | ZIP/repository generated from Blueprint |
| Codex/Claude | Continue the Builder Platform implementation | Phase-based changes with tests |

## Continuation focus

The initial phases created a working skeleton and deterministic generator. The next phases must close product-readiness gaps:

1. Artifact download and artifact management.
2. Production deployment templates.
3. Real generated-project authentication implementation.
4. Real generated Bale webhook integration path.
5. Celery worker generation for long-running tasks.
6. Frontend field-driven pages.
7. Blueprint editor/API UX.
8. DOCX/PDF ingestion if required by product scope.

Do not start a later phase before the active phase has tests and acceptance criteria satisfied.

## Renamed rule files

The previous names `*_SPEC.md` could be misunderstood as fixed project specifications. In this strict pack they are named `*_GENERATION_RULES.md`. They define generation rules and platform capabilities, not the final specification of one generated bot project.
