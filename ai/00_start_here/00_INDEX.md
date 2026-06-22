# Claude Strict Implementation Pack — AI-Assisted Bale Bot Project Builder

**Version:** 3.0 AI-folder structure  
**Root docs folder:** `ai/`  
**Target:** Implement the Builder Platform, not a single generated bot project.  
**Primary architecture:** Documentation First → Human Approval → Blueprint → Deterministic Generator → Generated Project.  
**Reference document:** `ai/01_reference/REFERENCE_PROJECT_PROPOSAL_v1_1.md`.

## Folder rule

All AI/Claude documentation must live under the `ai/` folder.

Claude must treat `ai/` as the source of implementation rules, architecture contracts, phase prompts, and quality gates. Application source code must not be placed inside `ai/`.

## Read order for Claude

Claude must read and obey these files in this order:

1. `ai/CLAUDE.md`
2. `ai/00_start_here/00_INDEX.md`
3. `ai/02_non_negotiable_contracts/01_PRODUCT_SCOPE_CONTRACT.md`
4. `ai/02_non_negotiable_contracts/02_STATIC_VS_DYNAMIC_DOCS_CONTRACT.md`
5. `ai/02_non_negotiable_contracts/03_REPOSITORY_STRUCTURE_CONTRACT.md`
6. `ai/03_architecture_contracts/01_CREWAI_DOCUMENTATION_APPROVAL_CONTRACT.md`
7. `ai/03_architecture_contracts/02_BOT_BLUEPRINT_SCHEMA_CONTRACT.md`
8. `ai/03_architecture_contracts/03_GENERATOR_CONTRACT.md`
9. `ai/03_architecture_contracts/04_MODULAR_TEMPLATE_RULES.md`
10. `ai/04_generation_rules/01_MULTI_BOT_BALE_GENERATION_RULES.md`
11. `ai/04_generation_rules/02_BACKEND_BUILDER_GENERATION_RULES.md`
12. `ai/04_generation_rules/03_FRONTEND_MINIAPP_PANEL_GENERATION_RULES.md`
13. `ai/04_generation_rules/04_SECURITY_AUTH_RBAC_AUDIT_RULES.md`
14. `ai/05_execution_plan/01_PHASES_TASKS_ACCEPTANCE_CRITERIA.md`
15. `ai/06_quality_gates/01_DEFINITION_OF_DONE_AND_REJECTION.md`
16. `ai/07_claude_prompts/01_CLAUDE_PHASE_PROMPTS_STRICT.md`

## Purpose of this pack

This pack is not a product pitch. It is an implementation contract for Claude.

Claude must implement a platform that can generate different Bale bot projects from project-specific documents and validated Bot Blueprints. Claude must not implement only one sample bot, ticket bot, appointment bot, or hard-coded generated project.

## Core non-negotiable distinction

| Layer | Responsible for | Must be implemented as |
|---|---|---|
| Claude | Build the Builder Platform | Source code of the platform |
| CrewAI inside the platform | Generate project-specific documents and Bot Blueprint | Controlled flows and agents |
| Human | Approve/reject/request changes | Review gate in Builder |
| Generator | Produce files from validated Blueprint | Deterministic code module + templates |
| Generated Project | Output per project | ZIP/repo generated from Blueprint |

## Renamed rule files

The previous names `*_SPEC.md` could be misunderstood as fixed project specifications. In this strict pack they are renamed to `*_GENERATION_RULES.md`. They define generation rules and platform capabilities, not the final specification of one bot project.
