# BaleCrewBuilder

**AI-Assisted Bale Bot Project Builder Platform**

BaleCrewBuilder is a platform that accepts a project idea or uploaded document, generates a structured Project Bot Document with AI assistance, requires human approval at each gate, produces a validated Bot Blueprint, and then deterministically generates a complete Bale bot project — FastAPI backend, Bale User/Admin bots, React/Vite Mini App frontend, database models, tests, and documentation.

Different Blueprints produce different projects. The platform is not a fixed template for one domain.

---

## What BaleCrewBuilder does

1. A developer or product owner describes a project via the REST API.
2. CrewAI (or a manually written document) produces a **Project Bot Document**.
3. A human reviewer approves or rejects the document.
4. Once approved, the platform generates a **Bot Blueprint** — a structured JSON/YAML specification of entities, roles, API endpoints, bot commands, and frontend routes.
5. The Blueprint is validated by a strict Pydantic schema.
6. A **Deterministic Generator** converts the validated Blueprint into a project ZIP using Jinja2 templates.

The same Blueprint always produces the same file list. No LLM call happens inside the generation step.

---

## Architecture overview

```
Builder Platform (FastAPI)
  │
  ├── Document ingestion + CrewAI documentation flow
  │
  ├── Human review gate  ─── Gate 1: DOCUMENT_APPROVED
  │
  ├── Blueprint generation + validation
  │
  ├── Human review gate  ─── Gate 2: BLUEPRINT_VALIDATED
  │
  └── Deterministic Generator (Jinja2 templates)
        │
        ├── Backend module   → backend/ (FastAPI + SQLAlchemy + Alembic)
        ├── Bale bots module → bale/ (user_bot + admin_bot if Blueprint requires it)
        ├── Frontend module  → frontend/ (React + Vite + TypeScript)
        └── Manifest         → docs/generation_manifest.json
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/fatemehSalarzaei/BaleCrewBuilder.git
cd BaleCrewBuilder

# 2. Create virtual environment and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env          # edit DATABASE_URL / SECRET_KEY as needed

# 4. Start PostgreSQL and Redis
docker-compose up -d

# 5. Apply database migrations
alembic upgrade head

# 6. Run the Builder Platform
uvicorn app.main:app --reload
# → http://localhost:8000  (API docs at http://localhost:8000/docs)

# 7. Run tests (no PostgreSQL required)
pytest
```

See [docs/developer-setup.md](docs/developer-setup.md) for full setup instructions and troubleshooting.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/developer-setup.md](docs/developer-setup.md) | Python version, dependencies, env vars, DB setup, test execution |
| [docs/api-reference.md](docs/api-reference.md) | Current mounted Builder Platform endpoints, route modules, schemas, statuses, and common errors |
| [docs/architecture-overview.md](docs/architecture-overview.md) | Current Builder Platform modules and data flow from project creation to ZIP download |
| [docs/generator-modules.md](docs/generator-modules.md) | Deterministic generator modules, output mapping, and generated vs stubbed behavior |
| [docs/generation-workflow.md](docs/generation-workflow.md) | Step-by-step REST API walkthrough for generating a project |
| [docs/sample-blueprints.md](docs/sample-blueprints.md) | The two Phase 8 fixtures and how they differ |
| [docs/generated-project-usage.md](docs/generated-project-usage.md) | Generated project structure, what stubs must be replaced |
| [docs/approval-gates.md](docs/approval-gates.md) | Why and how the two approval gates are enforced |
| [docs/limitations-and-future-phases.md](docs/limitations-and-future-phases.md) | Known limitations, honest phase status, suggested next steps |

---

## Builder Platform API endpoints

All endpoints are under the `/projects` prefix except `/health`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects/{id}` | Get project status |
| `POST` | `/projects/{id}/documents` | Create document manually |
| `POST` | `/projects/{id}/documents/generate` | Generate document via AI |
| `POST` | `/projects/{id}/documents/upload` | Upload a document file |
| `GET` | `/projects/{id}/document` | Get the latest project document |
| `POST` | `/projects/{id}/documents/{doc_id}/submit-review` | Submit document for review |
| `POST` | `/projects/{id}/document/approve` | Approve the document |
| `POST` | `/projects/{id}/document/feedback` | Submit reviewer feedback |
| `GET` | `/projects/{id}/reviews` | List review history |
| `POST` | `/projects/{id}/blueprint/generate` | Generate Blueprint from approved document |
| `POST` | `/projects/{id}/blueprint` | Store a Blueprint manually |
| `GET` | `/projects/{id}/blueprint` | Get stored Blueprint |
| `POST` | `/projects/{id}/blueprint/validate` | Validate the Blueprint |
| `POST` | `/projects/{id}/generate` | Run code generation and return run/artifact metadata |
| `GET` | `/projects/{id}/runs` | List generation runs for a project |
| `GET` | `/projects/{id}/download` | Download the latest completed generated project ZIP |

Interactive API documentation is available at `http://localhost:8000/docs` when the server is running.

There are no separate persisted requirements endpoints yet. `POST /projects/{id}/analyze` and `GET /projects/{id}/requirements` are deferred; current requirements extraction happens through Project Bot Document generation and review.

---

## Generation artifacts

`POST /projects/{id}/generate` records one `file` artifact for each generated file. When the validated Blueprint requests `output_format=zip`, generation also creates a ZIP artifact and the response includes `download_url`.

`GET /projects/{id}/download` returns the ZIP artifact from the latest completed generation run. Running and failed runs are ignored, and artifact storage paths are not exposed in public API responses.

---

## Approval gates

**Gate 1:** `POST /projects/{id}/blueprint/generate` requires status `DOCUMENT_APPROVED`. Attempting to generate a Blueprint before document approval returns `409 Conflict`.

**Gate 2:** `POST /projects/{id}/generate` requires status `BLUEPRINT_VALIDATED`. Attempting to generate code before Blueprint validation returns `409 Conflict`.

See [docs/approval-gates.md](docs/approval-gates.md) for the full gate design and rationale.

---

## Sample Blueprints

Two sample Blueprint fixtures demonstrate multi-bot vs user-only generation:

- [`tests/fixtures/blueprints/support_ticket_like.yaml`](tests/fixtures/blueprints/support_ticket_like.yaml) — support platform with User Bot + Admin Bot
- [`tests/fixtures/blueprints/appointment_form_like.yaml`](tests/fixtures/blueprints/appointment_form_like.yaml) — booking platform with User Bot only

```bash
# Run the Phase 8 E2E generation tests
pytest tests/test_e2e_sample_generation.py -v
```

See [docs/sample-blueprints.md](docs/sample-blueprints.md) for details.

---

## Running tests

Tests use an in-memory SQLite database — no PostgreSQL required.

```bash
pytest                                          # all tests
pytest tests/test_e2e_sample_generation.py     # Phase 8 E2E tests (48 tests)
pytest tests/test_backend_template_generation.py  # backend generation tests (51 tests)
pytest -q                                       # quiet
pytest -x                                       # stop on first failure
```

---

## Database migrations

Builder Platform migrations live in [`app/db/migrations/versions/`](app/db/migrations/versions/). Run all Builder Platform `alembic` commands from the repo root. Generated projects include their own Alembic scaffold, but their initial migration must be autogenerated and reviewed inside the generated backend.

```bash
alembic upgrade head          # apply all migrations
alembic downgrade -1          # roll back the last migration
alembic current               # show applied revision
alembic history               # show migration chain
```

---

## Current limitations

- Generated service stubs raise `HTTPException(501)` and must be replaced with real logic.
- Generated password hashing and JWT helpers are implemented, but `AuthService.authenticate()` still requires project-specific user lookup and `verify_miniapp_token()` fails closed until real Bale Mini App HMAC verification is wired.
- Bot command handlers delegate to the generated backend client abstraction, but the generated backend internal bot action/RBAC/audit endpoints still need project-specific implementations.
- Generated frontend pages are field-driven for list/form/detail/dashboard-style routes, but production UI polish and domain-specific presentation remain manual.
- Generated projects include an Alembic scaffold, but the initial migration must still be autogenerated, reviewed, and applied by the developer.
- Generated project ZIPs can be downloaded with `GET /projects/{id}/download`.
- Artifact storage goes through an abstraction, but the only implemented backend is local filesystem storage; production object storage, retention, and signed/authenticated download access are not implemented.
- Generated projects include minimal Docker-based deployment templates, but production hardening is still required.
- CrewAI document generation requires external LLM credentials.

See [docs/limitations-and-future-phases.md](docs/limitations-and-future-phases.md) for the full list.

---

## For Claude

Read these files before implementing anything:

1. [ai/CLAUDE.md](ai/CLAUDE.md) — mandatory implementation contract and absolute rules
2. [ai/00_start_here/00_INDEX.md](ai/00_start_here/00_INDEX.md) — full read order and pack overview

All AI implementation documentation lives under [`ai/`](ai/).
