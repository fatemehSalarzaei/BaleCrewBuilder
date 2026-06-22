# 02 — Static vs Dynamic Documentation Contract

## Why this matters

This project has two different document classes. Confusing them is a critical architecture error.

## Static documents

Static documents are repository-level instructions for Claude and the Builder Platform.

They define:

- platform rules;
- schemas;
- generation constraints;
- template architecture;
- security rules;
- phase tasks;
- acceptance criteria.

Static documents do not define one final generated bot project.

Examples:

```text
CLAUDE.md
04_BOT_BLUEPRINT_SCHEMA_CONTRACT.md
05_GENERATOR_CONTRACT.md
07_MULTI_BOT_BALE_GENERATION_RULES.md
08_BACKEND_BUILDER_GENERATION_RULES.md
09_FRONTEND_MINIAPP_PANEL_GENERATION_RULES.md
```

## Dynamic documents

Dynamic documents are produced by CrewAI for each user project.

They define the actual project-specific system:

```text
docs/project_bot_document.md
docs/user_bot_spec.md
docs/admin_bot_spec.md
docs/miniapp_panel_spec.md
docs/backend_api_spec.md
docs/database_design.md
docs/security_spec.md
docs/acceptance_criteria.md
docs/bot_blueprint.yaml
```

## Non-negotiable rule

Static documents define **how to generate**. Dynamic documents define **what to generate for a specific project**.

Claude must not treat static examples as fixed generated project content.

## Example

Static rule:

```text
Generated projects must support User Bot and Admin Bot when Blueprint defines them.
```

Dynamic project-specific output:

```yaml
bots:
  - key: user_bot
    commands: [/start, /book, /my_appointments]
  - key: admin_bot
    commands: [/start, /today, /schedule]
```

The commands must come from the dynamic Blueprint, not from the static rule file.
