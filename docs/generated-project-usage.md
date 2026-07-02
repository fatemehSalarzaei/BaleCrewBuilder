# Generated Project Usage

When `POST /projects/{id}/generate` completes, the generator writes a set of files derived entirely from the validated Blueprint and records them as generated artifacts. This document explains the structure of the generated output and what a developer must do before the generated project is production-ready.

---

## Downloading the generated ZIP

After a successful generation run, download the latest completed generated project ZIP from the Builder Platform:

```bash
curl -L -o generated-project.zip http://localhost:8000/projects/{PROJECT_ID}/download
```

Generation records one `file` artifact for each generated file. When the Blueprint uses `output_format=zip`, generation also creates a ZIP artifact and the `POST /projects/{PROJECT_ID}/generate` response includes `download_url`. Artifact metadata includes type, filename, and creation time; storage paths remain internal to the Builder Platform.

Unpack it into a working directory:

```bash
unzip generated-project.zip -d generated-project
cd generated-project
```

`GET /projects/{PROJECT_ID}/download` selects the ZIP from the latest completed generation run only. Running or failed generation runs are ignored, and the endpoint returns an explicit error if no completed run or ZIP artifact exists.

---

## Generated project structure

```
README.md                          project README with project name and bot list
docs/
  generation_manifest.json         blueprint hash, file list, template profile, timestamp
  deployment.md                    Docker Compose production deployment guide
backend/
  Dockerfile                       production backend image
  alembic.ini                      Alembic config for generated backend migrations
  app/
    main.py                        FastAPI app factory
    core/
      config.py                    Pydantic Settings — reads from .env
      security.py                  password hashing, JWT encode/decode
    db/
      base.py                      SQLAlchemy declarative base
      session.py                   async engine + session factory
      migrations/
        env.py                     async Alembic env wired to Base.metadata
        script.py.mako             Alembic revision template
        versions/                  generated migration revisions go here
          .gitkeep                 keeps the empty revisions directory in generated output
    api/
      deps.py                      get_current_user, require_roles, get_db
      router.py                    mounts entity routers + blueprint endpoint router
      routes/
        endpoints.py               Blueprint API endpoints (auth, RBAC, audit wired)
        {entity_name}.py           one route file per Blueprint entity
    models/
      {entity_name}.py             SQLAlchemy ORM model per entity
    schemas/
      {entity_name}.py             Pydantic v2 read/create schemas per entity
    services/
      auth_service.py              auth service shell; Mini App verification fails closed
      miniapp_auth_service.py      raw initData parser/freshness checks; HMAC contract TODO
      audit_service.py             AuditService.log_action (stub)
      blueprint_service.py         service stubs for every Blueprint API endpoint
      {entity_name}_service.py     CRUD service stub per entity
    workers/                       Celery app + task stubs when celery_worker is enabled
  tests/
    test_{entity_name}.py          test stub file per entity
bale/
  scripts/
    register_webhooks.py           dry-run capable Bale webhook registration helper
    delete_webhooks.py             dry-run capable Bale webhook deletion helper
  shared/
    client.py                      BaleClient (httpx wrapper) with per-bot factory functions
    backend_client.py              backend action/RBAC/audit client for bot handlers
    webhook.py                     HMAC signature verification, update parsing
    idempotency.py                 duplicate update detection
  {bot_key}/
    webhook.py                     FastAPI router for this bot's webhook path
    commands.py                    command dispatcher + BackendClient-backed handlers
  tests/
    test_{bot_key}_webhook.py      webhook test stubs for each bot
    test_webhook_registration_config.py
    test_bale_integration_optional.py
frontend/
  Dockerfile                       production frontend static image
  package.json                     React + Vite + TypeScript project
  tsconfig.json
  vite.config.ts
  index.html
  src/
    main.tsx
    App.tsx                        route configuration with AdminGuard for admin routes
    lib/
      api-client.ts                base HTTP client using fetch
      bale-miniapp-auth.ts         Bale Mini App initData auth bootstrap
    components/
      AdminGuard.tsx               frontend guard component for admin-only routes
    hooks/
      useApi.ts                    generic data-fetching hook
    pages/
      WebPanel.tsx                 Mini App/Web Panel bootstrap page
      {ComponentName}Page.tsx      field-driven page per Blueprint miniapp route
  tests/
    frontend.test.ts               frontend test stubs
deploy/
  docker-compose.prod.yml          backend/frontend/postgres/redis production stack
  .env.example                     production environment variable template
```

---

## Running the generated backend

### 1. Set environment variables

The generated `backend/app/core/config.py` reads from environment variables. Copy the generated `.env.example` (if present) or set them manually:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mydb"
export SECRET_KEY="your-secret-key"
export MINIAPP_AUTH_MAX_AGE_SECONDS="86400"     # raw initData freshness window
export PUBLIC_BASE_URL="https://yourdomain.com" # public backend origin for webhook setup
export USER_BOT_TOKEN="your-user-bot-token"
export ADMIN_BOT_TOKEN="your-admin-bot-token"   # only if Blueprint defines an admin bot
export BACKEND_BASE_URL="http://localhost:8000" # used by generated Bale bot handlers
export BACKEND_SERVICE_TOKEN="..."              # optional service token for backend bot calls
export CELERY_BROKER_URL="redis://localhost:6379/0"      # only if celery_worker enabled
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"  # only if celery_worker enabled
```

### 2. Create and apply database migrations

The generated backend includes an Alembic scaffold wired to `Base.metadata` and generated model modules. It does not include a fake initial migration. Create and review the initial migration from the generated models:

```bash
cd backend
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

> **Verify in your environment:** `--autogenerate` requires a reachable database and the generated backend dependencies installed. Review the generated revision before applying it to production.

### 3. Run the backend

```bash
cd backend
pip install -r requirements.txt   # if present; or: pip install fastapi uvicorn sqlalchemy asyncpg
uvicorn app.main:app --reload
```

If the Blueprint enabled `celery_worker`, start a worker after installing backend dependencies:

```bash
cd backend
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

---

## Running the generated frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000` by default. Set `VITE_API_BASE_URL` in a `.env` file inside `frontend/` to point at a different backend URL:

```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Docker production deployment package

Generated projects include a minimal Docker-based deployment package for VPS or container-host deployment:

```bash
cp deploy/.env.example deploy/.env
# edit deploy/.env and replace every placeholder
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env build
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d
```

The compose stack includes `backend`, `frontend`, `postgres`, and `redis`. If the Blueprint enables `celery_worker`, it also includes a `celery_worker` service. These templates are a starting point, not full production readiness: TLS, backups, observability, secret rotation, and deployment hardening remain application work. See the generated `docs/deployment.md` for environment setup, migration caveats, webhook registration, and health checks.

---

## What must be implemented manually

The generator creates a working skeleton. The following components are **stubs** that must be replaced with real business logic before the generated project is production-ready:

### Service stubs — `backend/app/services/blueprint_service.py`

Every Blueprint API endpoint calls a method in `blueprint_service.py`. All methods raise `HTTPException(status_code=501, detail="not yet implemented")`. Replace each with real logic:

```python
# generated stub (replace this)
async def submit_ticket(self) -> Any:
    raise HTTPException(status_code=501, detail="TicketService.submit_ticket: not yet implemented")

# your implementation
async def submit_ticket(self, data: TicketCreate, submitter_id: UUID) -> TicketRead:
    ticket = TicketModel(title=data.title, ...)
    db.add(ticket)
    await db.commit()
    return TicketRead.model_validate(ticket)
```

### Authentication integration — `backend/app/services/auth_service.py`

Password hashing and JWT encode/decode utilities are generated in `backend/app/core/security.py`. `AuthService.authenticate()` intentionally returns `None` until project-specific user lookup is implemented.

Mini App login is backend-only and fail-closed by default:

- The frontend sends only raw `window.Bale.WebApp.initData`.
- The backend rejects `initDataUnsafe`/JSON-like payloads.
- Missing `hash`/`signature` is rejected.
- Missing, invalid, future, or expired `auth_date` is rejected using `MINIAPP_AUTH_MAX_AGE_SECONDS`.
- Even structurally valid signed input is rejected until the exact Bale Mini App HMAC derivation contract is confirmed and implemented.

Before enabling Mini App login in production, confirm the official Bale contract for the data-check string and bot-token secret derivation, implement signature comparison with `hmac.compare_digest`, then add the generated project's Bale account lookup/upsert and JWT issuance.

### Entity service stubs — `backend/app/services/{entity_name}_service.py`

Each entity gets a CRUD service file with stub methods. Implement the actual database logic.

### Bot backend action handlers — `bale/{bot_key}/commands.py`

Command handlers no longer raise `NotImplementedError`; they delegate to `bale/shared/backend_client.py`, send user-facing responses through `BaleClient`, and fail closed when backend registration/RBAC checks are unavailable. The generated backend still needs real internal endpoints behind paths such as `/internal/bale/actions/{action}`, `/internal/bale/users/verify`, `/internal/bale/admin/verify`, `/internal/bale/permissions/check`, and `/internal/bale/audit`.

```python
async def handle_my_tickets(update: dict[str, Any]) -> None:
    await _call_command_action(update, command="/my_tickets", handler="handle_my_tickets")
```

Implement the corresponding backend service-layer action instead of putting business logic in the bot handler.

### Frontend route pages — `frontend/src/pages/{ComponentName}Page.tsx`

Generated pages now use Blueprint route type, API dependencies, and inferred entity fields to render list tables, controlled forms, detail views, and structured dashboard/report/settings panels. They include loading, error, and empty states and call generated hooks from `frontend/src/hooks/useApi.ts`.

They are still generic generated UI. Domain-specific presentation, richer validation, and production UX polish remain application work.

### Celery task stubs — `backend/app/workers/`

When `celery_worker` is enabled, the generator creates a Celery app and task stubs from Blueprint flows/custom logic blocks. These tasks are orchestration stubs only; implement service-layer calls inside them and keep business rules in backend services.

---

## Bot webhook setup

After deployment, register each bot's webhook URL with Bale using the generated helper scripts:

```bash
export PUBLIC_BASE_URL="https://yourdomain.com"
export USER_BOT_TOKEN="..."
export USER_BOT_TOKEN_WEBHOOK_SECRET="..."
export ADMIN_BOT_TOKEN="..."                    # only if Blueprint defines an admin bot
export ADMIN_BOT_TOKEN_WEBHOOK_SECRET="..."     # only if Blueprint defines an admin bot

python -m bale.scripts.register_webhooks --dry-run
python -m bale.scripts.register_webhooks
```

The helpers derive each URL from `PUBLIC_BASE_URL` plus the Blueprint webhook path. They keep User Bot and Admin Bot registration separate, read each token from its Blueprint-defined `token_env`, and print only sanitized status. Use dry-run first; it constructs URLs without requiring token values or calling the Bale network.

To remove registered webhooks:

```bash
python -m bale.scripts.delete_webhooks --dry-run
python -m bale.scripts.delete_webhooks
```

Generated unit tests cover URL construction and bot-specific webhook paths without calling Bale. Optional real-network smoke tests are skipped unless explicitly enabled:

```bash
export RUN_BALE_INTEGRATION_TESTS=1
pytest bale/tests/test_bale_integration_optional.py
```

Those optional tests require the relevant bot token environment variables and must not be run in normal CI unless the CI environment is intentionally configured for Bale integration.

---

## The generation manifest

`docs/generation_manifest.json` records:

```json
{
  "blueprint_hash": "sha256 of the validated Blueprint",
  "template_profile": "fastapi_react_bale_v1",
  "template_version": "unversioned",
  "enabled_modules": ["rbac", "audit_log", "bale_client", "miniapp_auth"],
  "custom_logic_blocks": [],
  "generated_files": ["backend/app/main.py", "..."],
  "generated_at": "2026-06-23T10:00:00+00:00",
  "validation_result": {"is_valid": true, "errors": []},
  "test_command_results": []
}
```

Use `blueprint_hash` to verify that the generated files match the Blueprint you intended. If you change the Blueprint and regenerate, the hash will change. `template_version` is currently `unversioned` until templates gain explicit version metadata. `test_command_results` is empty unless a future generation workflow runs generated-project test commands and records their results.
