# 03 — CrewAI Documentation and Approval Contract

## CrewAI responsibility

CrewAI is responsible for analysis and structured decision-making:

- parse project intent;
- extract actors, roles, flows, data needs, integrations, security needs;
- determine whether User Bot and Admin Bot are required;
- decide which features belong in bot, panel, backend;
- produce a Project Bot Document;
- incorporate human feedback;
- produce a Bot Blueprint after document approval.

CrewAI is not allowed to bypass validation or generate final project files directly.

## Required CrewAI flows

### 1. Documentation Flow

Input:

- raw idea;
- uploaded document text;
- optional user notes.

Output:

- `project_bot_document.md`;
- extracted requirement objects;
- clarification questions when necessary.

### 2. Approval Flow

Input:

- Project Bot Document;
- human decision: approve, request changes, reject, split scope, freeze scope.

Output:

- updated document;
- approval record;
- status transition.

### 3. Blueprint Flow

Input:

- approved Project Bot Document.

Output:

- `bot_blueprint.yaml/json` matching schema.

## Human approval decisions

| Decision | Required behavior |
|---|---|
| Approve | Set `DOCUMENT_APPROVED`, allow Blueprint generation. |
| Request Changes | Set `DOCUMENT_CHANGE_REQUESTED`, store feedback, regenerate document. |
| Reject | Stop workflow. Do not generate Blueprint or code. |
| Split Scope | Produce MVP/future-scope split before approval. |
| Freeze Scope | Lock approved scope; later changes require change request. |

## Approval data model requirements

The Builder Platform must store:

- project id;
- document version;
- reviewer id/name if available;
- decision;
- feedback;
- timestamp;
- previous status;
- next status.

## Hard gates

- Blueprint generation is forbidden before `DOCUMENT_APPROVED`.
- Implementation generation is forbidden before `BLUEPRINT_VALIDATED`.
- A new feedback request invalidates previous implementation eligibility until document is approved again.

## Project Bot Document minimum sections

The generated document must include:

1. Project overview.
2. Actors and roles.
3. User Bot spec.
4. Admin Bot spec or explicit justification for no Admin Bot.
5. Mini App/Web Panel spec.
6. Backend API spec.
7. Database design.
8. Security/auth/RBAC/audit rules.
9. Notification/event rules.
10. MVP scope and out-of-scope.
11. Acceptance criteria.
12. Implementation plan.
