# Generated Project Usage

When `POST /projects/{id}/generate` completes, the generator writes a set of files derived entirely from the validated Blueprint. This document explains the structure of the generated output and what a developer must do before the generated project is production-ready.

---

## Downloading the generated ZIP

After a successful generation run, download the latest completed generated project ZIP from the Builder Platform:

```bash
curl -L -o generated-project.zip http://localhost:8000/projects/{PROJECT_ID}/download
```

Unpack it into a working directory:

```bash
unzip generated-project.zip -d generated-project
cd generated-project
```

The ZIP is selected from the latest completed generation run only. Running or failed generation runs are ignored, and the endpoint returns an explicit error if no completed run or ZIP artifact exists.

---

## Generated project structure

```
README.md                          project README with project name and bot list
docs/
  generation_manifest.json         blueprint hash, file list, template profile, timestamp
backend/
  app/
    main.py                        FastAPI app factory
    core/
      config.py                    Pydantic Settings — reads from .env
      security.py                  password hashing, JWT encode/decode
    db/
      base.py                      SQLAlchemy declarative base
      session.py                   async engine + session factory
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
      auth_service.py              authentication + Mini App token verification (stubs)
      audit_service.py             AuditService.log_action (stub)
      blueprint_service.py         service stubs for every Blueprint API endpoint
      {entity_name}_service.py     CRUD service stub per entity
  tests/
    test_{entity_name}.py          test stub file per entity
bale/
  shared/
    client.py                      BaleClient (httpx wrapper) with per-bot factory functions
    webhook.py                     HMAC signature verification, update parsing
    idempotency.py                 duplicate update detection
  {bot_key}/
    webhook.py                     FastAPI router for this bot's webhook path
    commands.py                    command dispatcher + handler stubs
  tests/
    test_{bot_key}_webhook.py      webhook test stubs for each bot
frontend/
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
      WebPanel.tsx                 web panel mode placeholder
      {ComponentName}Page.tsx      one page component per Blueprint miniapp route
  tests/
    frontend.test.ts               frontend test stubs
```

---

## Running the generated backend

### 1. Set environment variables

The generated `backend/app/core/config.py` reads from environment variables. Copy the generated `.env.example` (if present) or set them manually:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mydb"
export SECRET_KEY="your-secret-key"
export USER_BOT_TOKEN="your-user-bot-token"
export ADMIN_BOT_TOKEN="your-admin-bot-token"   # only if Blueprint defines an admin bot
```

### 2. Apply database migrations

The generated backend does not include Alembic migrations out of the box. You must create them from the generated models:

```bash
cd backend
alembic init app/db/migrations   # only if no alembic.ini exists
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

> **Verify in your environment:** `--autogenerate` requires a running PostgreSQL instance and `asyncpg` installed.

### 3. Run the backend

```bash
cd backend
pip install -r requirements.txt   # if present; or: pip install fastapi uvicorn sqlalchemy asyncpg
uvicorn app.main:app --reload
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

### Authentication stubs — `backend/app/services/auth_service.py`

`authenticate()` and `verify_miniapp_token()` raise `NotImplementedError`. These must be replaced with real database lookups and HMAC validation respectively.

### Entity service stubs — `backend/app/services/{entity_name}_service.py`

Each entity gets a CRUD service file with stub methods. Implement the actual database logic.

### Bot command handlers — `bale/{bot_key}/commands.py`

All command handler functions raise `NotImplementedError`. Replace them with calls to the appropriate backend service:

```python
# generated stub (replace this)
async def handle_my_tickets(update: dict[str, Any]) -> None:
    raise NotImplementedError

# your implementation
async def handle_my_tickets(update: dict[str, Any]) -> None:
    chat_id = update["message"]["chat"]["id"]
    tickets = await ticket_service.list_my_tickets(...)
    await client.send_message(chat_id, format_ticket_list(tickets))
```

---

## Bot webhook setup

After deployment, register each bot's webhook URL with Bale:

```python
from bale.shared.client import make_user_bot_client

client = make_user_bot_client()
await client.set_webhook("https://yourdomain.com/webhook/user", secret_token="...")
```

Webhook paths are defined in the Blueprint and appear in each bot's `webhook.py`.

---

## The generation manifest

`docs/generation_manifest.json` records:

```json
{
  "blueprint_hash": "sha256 of the validated Blueprint",
  "template_profile": "fastapi_react_bale_v1",
  "enabled_modules": ["rbac", "audit_log", "bale_client", "miniapp_auth"],
  "custom_logic_blocks": [],
  "generated_files": ["backend/app/main.py", "..."],
  "generated_at": "2026-06-23T10:00:00+00:00"
}
```

Use `blueprint_hash` to verify that the generated files match the Blueprint you intended. If you change the Blueprint and regenerate, the hash will change.
