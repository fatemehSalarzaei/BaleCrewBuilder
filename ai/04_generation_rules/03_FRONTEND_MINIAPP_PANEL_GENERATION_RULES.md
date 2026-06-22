# 09 — Frontend Mini App / Web Panel Generation Rules

## Purpose

This file defines frontend generation rules for generated projects. It does not define fixed pages for all projects.

## Principle

Mini App is the same frontend panel running inside Bale WebView.

The frontend must support two modes:

```text
Bale Mini App mode
Normal Web Panel mode
```

## Required frontend stack

MVP allowed stack:

- React + Vite + TypeScript
- Tailwind CSS
- TanStack Query
- React Hook Form
- Zod

Production option:

- Next.js + TypeScript

Pick one per implementation phase and keep it consistent.

## Required frontend structure

```text
frontend/src/
  app/
  routes/
    user/
    admin/
  components/
  features/
  lib/
    api.ts
    auth.ts
    bale.ts
    permissions.ts
  schemas/
  hooks/
```

## Route generation rules

Routes come from Blueprint:

```yaml
miniapp:
  routes:
    - path: /user/dashboard
      allowed_roles: [customer]
    - path: /admin/dashboard
      allowed_roles: [admin, operator]
```

Do not generate fixed domain pages unless Blueprint defines them.

## Auth rules

Mini App mode:

1. Read `window.Bale.WebApp.initData`.
2. Send raw initData to backend `/auth/bale-miniapp`.
3. Backend validates HMAC/auth_date.
4. Backend returns internal session/JWT.
5. Frontend uses JWT for API calls.

Frontend must not trust `initDataUnsafe` for authorization.

Web Panel mode:

- Use normal login/session strategy provided by generated backend or MVP placeholder.
- Reuse same API client.

## RBAC UI rules

Frontend may hide UI elements, but backend is the authority.

Admin routes must be guarded on frontend and backend.

## Page template types

Generator may support:

- dashboard;
- list;
- detail;
- form;
- report;
- settings;
- profile;
- approval queue.

Page type is selected from Blueprint.

## API integration rules

Each generated page must declare its API dependencies:

```yaml
api_dependencies:
  - GET /api/tickets
  - POST /api/tickets
```

Generator must create API hooks from endpoint definitions.

## Mini App UX rules

Generated frontend must support:

- responsive layout;
- safe area handling where needed;
- loading/error states;
- role-based navigation;
- user/admin route separation;
- link compatibility inside Bale WebView.

## Tests required

Generated frontend must include at least:

- API client unit tests or stubs;
- auth bootstrap test or documented manual test;
- route guard test or documented manual test;
- generated page smoke test when tooling is configured.
