# Generation Workflow

BaleCrewBuilder follows a **Documentation First** pipeline. Code generation is blocked until both a document and a Blueprint have been approved and validated. This guarantees that all generated output derives from reviewed, structured data — never from raw user input alone.

---

## Pipeline overview

```
POST /projects                        → DRAFT_CREATED
  ↓
POST /projects/{id}/documents/generate (or /upload, or /documents)
                                      → DOCUMENT_GENERATING → DOCUMENT_DRAFTED
  ↓
POST /projects/{id}/documents/{doc_id}/submit-review
                                      → DOCUMENT_REVIEW_PENDING
  ↓
POST /projects/{id}/document/approve  → DOCUMENT_APPROVED
  ↓                 (gate 1 — must reach DOCUMENT_APPROVED before Blueprint)
POST /projects/{id}/blueprint/generate → BLUEPRINT_GENERATING → BLUEPRINT_GENERATED
  ↓
POST /projects/{id}/blueprint/validate → BLUEPRINT_VALIDATED (or BLUEPRINT_VALIDATION_FAILED)
  ↓                 (gate 2 — must reach BLUEPRINT_VALIDATED before generation)
POST /projects/{id}/generate          → IMPLEMENTATION_GENERATING → IMPLEMENTATION_GENERATED
  ↓
GET /projects/{id}/download           → latest completed generation ZIP
```

---

## Step-by-step API calls

Replace `BASE_URL` with `http://localhost:8000` and `PROJECT_ID` with the UUID returned by step 1.

---

### Step 1 — Create a project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Bot Platform", "description": "A platform for managing resources via Bale bots."}'
```

**Expected status:** `201 Created`  
**Project status after:** `DRAFT_CREATED`  
**Response contains:** `id` (use as `PROJECT_ID` in subsequent calls)

---

### Step 2a — Generate a document via AI (requires CrewAI config)

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a resource management platform with Bale bots for users and admins."}'
```

**Expected status:** `201 Created`  
**Project status after:** `DOCUMENT_DRAFTED`

> **Note:** The AI document generation flow requires CrewAI to be configured. In a development environment without CrewAI credentials, use step 2b instead.

> **Requirements note:** The Builder Platform does not currently persist a separate requirements object. There is no current `POST /projects/{PROJECT_ID}/analyze` or `GET /projects/{PROJECT_ID}/requirements` API. Requirements extraction is represented by Project Bot Document generation and review.

---

### Step 2b — Create a document manually

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Resource Management Platform",
    "content": "# Overview\n\n## User Management\n\n## Resource Management\n\n## Admin Controls"
  }'
```

**Expected status:** `201 Created`  
**Project status after:** `DOCUMENT_DRAFTED`

---

### Step 2c — Upload a document file (Markdown or plain text)

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents/upload \
  -F "file=@my_document.md"
```

**Expected status:** `201 Created`  
**Project status after:** `DOCUMENT_DRAFTED`

---

### Step 3 — Submit the document for review

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/documents/{DOCUMENT_ID}/submit-review
```

**Expected status:** `200 OK`  
**Project status after:** `DOCUMENT_REVIEW_PENDING`

---

### Step 4 — Approve the document

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/document/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "Alice"}'
```

**Expected status:** `200 OK`  
**Project status after:** `DOCUMENT_APPROVED`

> **Gate 1:** Blueprint generation is blocked (`409 Conflict`) if the project is not in `DOCUMENT_APPROVED` status. You cannot skip this step.

If the document needs changes before approval:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/document/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback": "Please add more detail about RBAC roles.", "reviewer_name": "Alice"}'
```

---

### Step 5 — Generate a Blueprint placeholder from the approved document

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint/generate
```

**Expected status:** `201 Created`  
**Project status after:** `BLUEPRINT_GENERATED`  
**Response contains:** a `BotBlueprint` JSON object derived from the document's headings and title.

> This endpoint creates a deterministic placeholder Blueprint. A developer should review and refine the Blueprint JSON before validation.

---

### Step 6 — Validate the Blueprint

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint/validate
```

**Expected status:** `200 OK`  
**Project status after:** `BLUEPRINT_VALIDATED` (or `BLUEPRINT_VALIDATION_FAILED` if errors exist)  
**Response contains:** `{"is_valid": true, "errors": []}`

> **Gate 2:** Code generation is blocked (`409 Conflict`) unless the Blueprint is `BLUEPRINT_VALIDATED` with zero errors.

To submit a custom Blueprint instead of using the generated placeholder:

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/blueprint \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/blueprints/valid_multi_bot.yaml   # (convert to JSON first)
```

---

### Step 7 — Trigger code generation

```bash
curl -X POST http://localhost:8000/projects/{PROJECT_ID}/generate
```

**Expected status:** `201 Created`  
**Project status after:** `IMPLEMENTATION_GENERATED`  
**Response contains:** generation run metadata, generated file artifact metadata, ZIP artifact metadata when `output_format=zip`, and `download_url` when a ZIP artifact exists.

The generated project is written through the configured artifact storage backend and recorded as `generated_artifacts`. The default backend is `ARTIFACT_STORAGE_BACKEND=local`, which stores files under `GENERATION_OUTPUT_DIR`. The response includes artifact type, filename, and creation timestamp only; storage paths are not exposed.

---

### Step 8 — Download the generated ZIP

```bash
curl -L -o generated-project.zip http://localhost:8000/projects/{PROJECT_ID}/download
```

**Expected status:** `200 OK`  
**Response contains:** the ZIP artifact for the latest completed generation run.

The endpoint returns clear errors when the project does not exist, no completed generation run exists, the latest completed run has no ZIP artifact, or the ZIP artifact record cannot be resolved by the configured storage backend. For the default local backend, a missing ZIP file returns `410 Gone`.

---

### Checking project status at any point

```bash
curl http://localhost:8000/projects/{PROJECT_ID}
```

Returns the current project with its `status` field.

---

## What the generator produces

For each generation run the generator creates:

```
backend/          FastAPI backend (models, schemas, services, routes, tests)
bale/             Bale bot layer (shared client + per-bot webhook/commands)
frontend/         React + Vite frontend (pages, hooks, auth bootstrap)
docs/generation_manifest.json   blueprint hash, file list, template profile
README.md         project-level README
```

All content is derived from the validated Blueprint. The same Blueprint always produces the same file list (deterministic output).
