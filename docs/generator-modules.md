# Generator Modules

`GeneratorCore` validates a `BotBlueprint`, builds a normalized template context,
then runs four deterministic modules. The modules write files into a generated
project directory and the core writes `docs/generation_manifest.json`.

## Module Map

| Module | Builder code | Generated output |
|--------|--------------|------------------|
| `CoreModule` | `app/generator/modules/core.py` | Project README, backend/frontend Dockerfiles, `deploy/docker-compose.prod.yml`, `deploy/.env.example`, and `docs/deployment.md`. |
| `BackendModule` | `app/generator/modules/backend.py` | `backend/` FastAPI app, requirements, Alembic scaffold, config/security/db/api/service templates, per-entity models/schemas/services/routes/tests, and optional Celery worker files. |
| `BaleBotsModule` | `app/generator/modules/bale_bots.py` | `bale/` shared client/webhook/backend-client helpers, webhook registration scripts, optional integration-test scaffold, and one command/webhook package per Blueprint bot. |
| `FrontendModule` | `app/generator/modules/frontend.py` | `frontend/` React/Vite/TypeScript app, API client, Mini App auth bootstrap, admin guard, hooks, web panel, tests, and one page component per Mini App route. |

## CoreModule

Generated files:

- `README.md`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `deploy/docker-compose.prod.yml`
- `deploy/.env.example`
- `docs/deployment.md`

The deployment templates are intentionally simple VPS/container-host templates.
They do not provide full production hardening, managed secrets, object storage,
or Kubernetes.

## BackendModule

Always generated:

- package and app `__init__.py` files
- `backend/requirements.txt`
- `backend/alembic.ini`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/db/migrations/env.py`
- `backend/app/db/migrations/script.py.mako`
- `backend/app/api/deps.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/endpoints.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/miniapp_auth_service.py`
- `backend/app/services/audit_service.py`
- `backend/app/services/blueprint_service.py`

Per Blueprint entity:

- `backend/app/models/{entity_name}.py`
- `backend/app/schemas/{entity_name}.py`
- `backend/app/services/{entity_name}_service.py`
- `backend/app/api/routes/{entity_name}.py`
- `backend/tests/test_{entity_name}.py`

When `generation.enabled_modules` includes `celery_worker`:

- `backend/app/workers/__init__.py`
- `backend/app/workers/celery_app.py`
- `backend/app/workers/tasks.py`

Generated backend security primitives include password hashing and JWT
encode/decode helpers. Project-specific user lookup, domain behavior, real Bale
Mini App HMAC enablement, and service methods behind Blueprint endpoints remain
developer-owned.

## BaleBotsModule

Always generated shared files:

- `bale/scripts/register_webhooks.py`
- `bale/scripts/delete_webhooks.py`
- `bale/shared/client.py`
- `bale/shared/backend_client.py`
- `bale/shared/webhook.py`
- `bale/shared/idempotency.py`
- `bale/tests/test_webhook_registration_config.py`
- `bale/tests/test_bale_integration_optional.py`

Per Blueprint bot:

- `bale/{bot_key}/__init__.py`
- `bale/{bot_key}/webhook.py`
- `bale/{bot_key}/commands.py`
- `bale/tests/test_{bot_key}_webhook.py`

User and admin bot templates are selected from each bot audience. Admin commands
are generated only for admin-audience bots. Command handlers delegate to the
generated backend client abstraction and avoid embedding business logic.

## FrontendModule

Always generated:

- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/api-client.ts`
- `frontend/src/lib/bale-miniapp-auth.ts`
- `frontend/src/pages/WebPanel.tsx`
- `frontend/src/components/AdminGuard.tsx`
- `frontend/src/hooks/useApi.ts`
- `frontend/tests/frontend.test.ts`

Per Mini App route:

- `frontend/src/pages/{ComponentName}.tsx`

Route pages are field-driven from Blueprint route metadata, API dependencies, and
entity fields where they can be inferred. List, form, and detail routes include
generic loading/error/empty states. Dashboard, report, and settings routes render
structured panels rather than domain-specific business logic.

## Generated Versus Stubbed

Generated and usable:

- project structure and documentation
- FastAPI backend scaffolding
- SQLAlchemy model and schema scaffolds from Blueprint entities
- Alembic configuration and migration environment
- password hashing and JWT helper primitives
- Bale client, backend client, webhook adapters, and webhook registration helpers
- React/Vite frontend shell, API client/hooks, admin guard, and route pages
- Docker-based deployment templates
- generation manifest

Intentionally stubbed or developer-owned:

- generated backend business service implementations behind Blueprint endpoints
- project-specific user lookup in `AuthService.authenticate`
- real Bale Mini App HMAC activation until the exact production contract and bot
  token configuration are wired
- domain-specific UI behavior and presentation
- Celery task business logic
- production object storage, retention, signed downloads, and deployment hardening
