# AI Docs — Claude Bale Bot Builder

This folder (`ai/`) is where all of Claude's implementation documentation for implementing the project is located.

The purpose of this documentation is to implement the **Builder Platform**; not to produce a fixed sample bot project.

## Structure rule

All Claude and AI-related documentation should be kept in this `ai/` folder. Product files, backend, frontend, generator code, and the main project should not be placed in this folder.

## Compulsory study arrangement for Claude

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

## Key Rules

- Claude must implement the **Builder Platform**, not a specific bot.

- CrewAI must generate documentation and blueprints for each separate project.
- Generator must be deterministic, template-driven, and blueprint-driven.
- Templates must not be static sample projects.
- No code generation is allowed before `DOCUMENT_APPROVED`.
- No Generator execution is allowed before `BLUEPRINT_VALIDATED`.
- User Bot and Admin Bot must be separate, but connected to the same backend and service layer.

## Folder structure

```text
ai/
  CLAUDE.md
  README.md
  00_start_here/
  01_reference/
  02_non_negotiable_contracts/
  03_architecture_contracts/
  04_generation_rules/
  05_execution_plan/
  06_quality_gates/
  07_claude_prompts/
```

## Recommended way to run

Place the `ai/` folder in the root of the project repository. Then tell Claude to read `ai/CLAUDE.md` first and then `ai/00_start_here/00_INDEX.md`. The project should be executed in phases, with only the prompts in `ai/07_claude_prompts/01_CLAUDE_PHASE_PROMPTS_STRICT.md`.
