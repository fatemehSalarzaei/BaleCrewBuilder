# 06 — Modular Template Rules

## Correct template meaning

A template is a reusable rendering unit parameterized by Blueprint data.

A template is not a finished project.
A template is not a fixed ticket bot.
A template is not a place to hard-code business logic.

## Template classes

### 1. Core templates

Always generated:

- FastAPI app bootstrap;
- config;
- logging;
- database session;
- auth base;
- RBAC base;
- audit log base;
- Bale client abstraction;
- Docker/env files.

### 2. Module templates

Generated only when enabled by Blueprint:

- multi-bot;
- file upload;
- notifications;
- approval flow;
- reports;
- scheduled jobs;
- custom integrations.

### 3. Entity templates

Generated per Blueprint entity:

- SQLAlchemy model;
- Pydantic schema;
- service class;
- API route;
- tests.

### 4. Bot templates

Generated per Blueprint bot and command:

- command registry;
- keyboards;
- handlers;
- callback routing;
- Mini App launch buttons;
- tests.

### 5. Frontend templates

Generated per Mini App/Web Panel route:

- page component;
- API hooks;
- form schemas;
- role guard;
- route registration.

### 6. Custom block templates

AI-assisted or custom logic must be isolated and declared.

## Template anti-patterns

Forbidden:

- `ticket.py` always generated for every project;
- `/api/tickets` hard-coded in core template;
- `/pending_tickets` hard-coded in Admin Bot template;
- admin access checks only in frontend;
- generated pages without API dependency mapping;
- a single all-purpose handler file for every command;
- business rule hidden inside Jinja condition.

## Template selection rule

Templates are selected by:

```text
Blueprint.generation.enabled_modules
+ Blueprint.entities
+ Blueprint.api.endpoints
+ Blueprint.bots
+ Blueprint.miniapp.routes
+ Blueprint.security policies
```

## Template versioning

Every template profile must have a version:

```yaml
generation:
  template_profile: fastapi_react_bale_v1
  template_version: 1.0.0
```

Changing template output structure requires version bump.

## Required template tests

The Builder Platform must include tests for:

- rendering core project;
- rendering user-only project;
- rendering user+admin multi-bot project;
- rendering at least two different domains from different Blueprints;
- rejecting invalid Blueprint;
- ensuring no hard-coded sample domain appears unless requested by Blueprint.
