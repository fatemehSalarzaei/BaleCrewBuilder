# Codex Standalone Handoff — BaleCrewBuilder

This folder is intentionally separate from the existing `ai/` and `docs/` folders.

## Non-overlap rule

Do not replace, rename, or edit any existing documentation file just because this Codex handoff exists.

These files are additive only and should be copied into the repository under:

```text
codex/
```

They are designed to guide Codex continuation work without conflicting with the existing Claude/AI implementation pack.

## Read order for Codex

1. `codex/CODEX_HANDOFF.md`
2. `codex/CODEX_CONTINUATION_BACKLOG.md`
3. `codex/CODEX_RUNBOOK.md`
4. `codex/CODEX_REVIEW_NOTES.md`
5. `codex/prompts/PHASE_10_ARTIFACT_DOWNLOAD.md`

## Relationship to existing project docs

Existing docs remain authoritative for the original architecture contract:

- `ai/CLAUDE.md`
- `ai/00_start_here/00_INDEX.md`
- `ai/02_non_negotiable_contracts/*`
- `ai/03_architecture_contracts/*`
- `ai/04_generation_rules/*`
- `ai/05_execution_plan/01_PHASES_TASKS_ACCEPTANCE_CRITERIA.md`
- `docs/*`

The `codex/` folder is only a continuation handoff that records the current gaps and next implementation phases.
