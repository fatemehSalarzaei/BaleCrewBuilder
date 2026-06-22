# README for Human Operator

This package is a stricter version of Claude's documentation. It aims to prevent Claude from being misunderstood.

## Important changes from the previous package

1. The `*_SPEC.md` files have been changed to `*_GENERATION_RULES.md` to make it clear that these are not project-specific specs.
2. Static Docs and Dynamic Docs have been separated.
3. Explicit rule added: Claude should build the Builder platform, not a sample bot.
4. Explicit rule added: CrewAI itself is not a deterministic Generator.
5. The Generator should be deterministic, template-based, and Blueprint-driven.
6. Templates should not be static ready-made projects.
7. User Bot and Admin Bot should only be generated when they come from Blueprint, but the platform should support multi-bot functionality.
8. Documentation First and Human Approval have become mandatory gates.
9. Implementation rejection criteria added.

## Suggested usage with Claude

First, place the `CLAUDE.md` file in the root of the project. Then give Claude the strict contract files. Then run the phases one by one from `12_CLAUDE_PHASE_PROMPTS_STRICT.md`.

Claude should not implement the entire project in one prompt.

## Important management control

After each phase, ask Claude to report:

- What files were changed;

- What tests were added;
- What commands were executed;
- What risks remain;
- Whether the architectural gates were met or not.