# Approval Gates

BaleCrewBuilder enforces two mandatory gates before code generation is permitted. These gates exist to guarantee that all generated output derives from reviewed, structured, validated data — never from raw user input.

---

## Gate 1 — Document approval

**Requirement:** The project must reach status `DOCUMENT_APPROVED` before a Blueprint can be generated.

**Enforced by:** `POST /projects/{id}/blueprint/generate`

**What happens if skipped:**

```http
HTTP 409 Conflict
{
  "detail": "Blueprint generation requires project status DOCUMENT_APPROVED. Current status: DRAFT_CREATED"
}
```

**Why this gate exists:**

The Project Bot Document is a structured specification of what the project should do — entities, roles, workflows, and interfaces. Without a human-reviewed document, the Blueprint has no trusted source of truth. Generating code from an unreviewed document would embed unverified assumptions directly into the output.

**Status path to reach Gate 1:**

```
DRAFT_CREATED
  → DOCUMENT_GENERATING (or DOCUMENT_DRAFTED if created manually)
  → DOCUMENT_REVIEW_PENDING
  → DOCUMENT_APPROVED  ← Gate 1 passes here
```

If a reviewer requests changes the project moves to `DOCUMENT_CHANGE_REQUESTED`. The document must be revised and re-submitted before approval can be granted.

---

## Gate 2 — Blueprint validation

**Requirement:** The project must have a stored Blueprint that has passed validation (`BLUEPRINT_VALIDATED`) before code generation is permitted.

**Enforced by:** `POST /projects/{id}/generate`

**What happens if skipped:**

```http
HTTP 409 Conflict
{
  "detail": "Generation requires BLUEPRINT_VALIDATED status."
}
```

**Why this gate exists:**

The Deterministic Generator uses the Blueprint as its only input. If the Blueprint is structurally invalid — missing required fields, invalid role references, malformed entity definitions — the Generator would produce broken or incomplete code. Validation catches these problems before any file is written.

**Status path to reach Gate 2:**

```
DOCUMENT_APPROVED
  → BLUEPRINT_GENERATING → BLUEPRINT_GENERATED
  → BLUEPRINT_VALIDATED  ← Gate 2 passes here
```

If validation fails the project moves to `BLUEPRINT_VALIDATION_FAILED`. The Blueprint must be corrected and re-submitted, then re-validated.

---

## Why CrewAI must not write implementation files directly

Rule R3 in [`ai/CLAUDE.md`](../ai/CLAUDE.md):

> CrewAI may analyze, document, propose, review, and create Blueprint data. CrewAI must not be treated as the uncontrolled file generator.

CrewAI (and any LLM) produces probabilistic output. Allowing an LLM to write implementation files directly would bypass both approval gates, embed domain assumptions that were never reviewed, and produce output that cannot be deterministically reproduced.

The approved separation of concerns is:

| Component | Role |
|-----------|------|
| CrewAI | Analyzes input, proposes document content, suggests Blueprint structure |
| Human reviewer | Approves or rejects each artifact |
| Deterministic Generator | Converts a *validated* Blueprint into project files using Jinja2 templates |

---

## Full project status enum

For reference, the complete status enum as implemented:

```
DRAFT_CREATED
DOCUMENT_GENERATING
DOCUMENT_DRAFTED
DOCUMENT_REVIEW_PENDING
DOCUMENT_CHANGE_REQUESTED
DOCUMENT_REJECTED
DOCUMENT_APPROVED              ← Gate 1
BLUEPRINT_GENERATING
BLUEPRINT_GENERATED
BLUEPRINT_VALIDATION_FAILED
BLUEPRINT_VALIDATED            ← Gate 2
IMPLEMENTATION_GENERATING
IMPLEMENTATION_FAILED
IMPLEMENTATION_GENERATED
IMPLEMENTATION_REVIEW_PENDING
IMPLEMENTATION_APPROVED
READY_FOR_DEPLOY
DEPLOYED
```

Transitions are enforced by `ProjectService.transition()`. Illegal transitions raise `IllegalStatusTransitionError`, which the API converts to a `409 Conflict` response.
