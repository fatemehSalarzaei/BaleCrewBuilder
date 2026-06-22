# 13 — Definition of Done and Rejection Criteria

## Global Definition of Done

A phase is done only when:

- required files exist;
- tests exist;
- tests pass or exact blocker is documented;
- architecture contract is not violated;
- no fixed generated project is hard-coded;
- Documentation First gate remains enforced;
- Generator remains deterministic;
- User/Admin multi-bot rules are preserved when applicable;
- security rules are not bypassed.

## Project-level Definition of Done

The Builder Platform MVP is done when:

1. A project can be created.
2. A document can be uploaded or entered.
3. CrewAI documentation flow abstraction can produce/store Project Bot Document.
4. Human can approve/request changes/reject.
5. Blueprint can be generated only after approval.
6. Blueprint is validated by strict schema.
7. Generator can produce project files from valid Blueprint.
8. Generated project includes backend, Bale bot layer, frontend panel, tests, docs, Docker/env.
9. Multi-bot project generates User Bot and Admin Bot separately.
10. User-only project does not generate Admin Bot.
11. Generated code does not contain unrelated sample domain hard-coding.

## Automatic rejection criteria

Reject an implementation if any of these occur:

- Code generation starts from raw text.
- Project can generate implementation before `DOCUMENT_APPROVED`.
- Project can generate implementation before `BLUEPRINT_VALIDATED`.
- CrewAI output is written directly as final project files without Generator validation.
- Templates are a fixed sample project.
- User Bot and Admin Bot share token/env/webhook/handler namespace.
- Admin operations lack RBAC or audit.
- Mini App trusts `initDataUnsafe`.
- Business logic is placed in frontend or bot handler instead of services.
- Generated endpoints lack role metadata.
- Generated project cannot be packaged.
- Tests are omitted.

## Required review questions after each phase

- Did this phase implement the Builder Platform or accidentally implement a generated project?
- Does it preserve Documentation First?
- Does it preserve deterministic generation?
- Does it keep CrewAI and Generator separated?
- Are templates modular and Blueprint-driven?
- Are multi-bot rules enforced?
- Are auth/RBAC/audit rules enforced?
- Are tests sufficient for the phase?
