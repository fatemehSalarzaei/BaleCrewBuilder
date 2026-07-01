# Prompt for Codex — Phase 10 Artifact Download

Use this prompt as the first implementation task.

```text
You are working on fatemehSalarzaei/BaleCrewBuilder.

Before changing code, read:
- codex/CODEX_HANDOFF.md
- codex/CODEX_CONTINUATION_BACKLOG.md
- codex/CODEX_RUNBOOK.md
- codex/CODEX_REVIEW_NOTES.md
- ai/CLAUDE.md

Task: implement Phase 10 — Artifact Download and Artifact Management.

Add GET /projects/{project_id}/download.

Requirements:
1. Verify the project exists.
2. Find the latest completed generation run for that project.
3. Find the ZIP artifact linked to that generation run.
4. Verify the ZIP file exists on disk.
5. Return the ZIP using FastAPI FileResponse.
6. Return precise errors for:
   - project not found;
   - no completed generation run;
   - no ZIP artifact;
   - ZIP path missing on disk.
7. Add service-level logic instead of putting database queries directly in the route.
8. Add tests for success and all failure branches.
9. Register the route in app/main.py.
10. Do not edit existing docs unless needed for the endpoint usage note.
11. Do not modify the architecture gates.
12. Do not generate project files from raw prompt text.

Suggested files:
- app/api/routes/artifacts.py
- app/services/artifact_service.py
- app/schemas/artifact.py
- app/api/deps.py
- app/main.py
- tests/test_artifact_download.py

Run:
- pytest tests/test_artifact_download.py -q
- pytest tests/test_generation_gate.py -q
- pytest tests/test_e2e_sample_generation.py -q
- pytest

Report:
1. Files changed.
2. Behavior implemented.
3. Tests run and results.
4. Known limitations.
```
