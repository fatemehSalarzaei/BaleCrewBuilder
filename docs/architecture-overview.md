# Architecture Overview

BaleCrewBuilder is a documentation-first Builder Platform. It uses AI only to
draft structured project documents and optional Blueprint proposals, then relies
on human approval, schema validation, and deterministic templates to generate a
Bale bot project.

## Builder Platform Modules

| Area | Main code | Responsibility |
|------|-----------|----------------|
| FastAPI app | `app/main.py`, `app/api/routes/` | Mounts the REST API for projects, documents, reviews, blueprints, generation runs, and artifact downloads. |
| Schemas | `app/schemas/` | Pydantic request/response models plus the `BotBlueprint` contract consumed by the generator. |
| DB models | `app/db/models/` | SQLAlchemy models for projects, documents, reviews, Blueprints, validation results, generation runs, generated artifacts, AI runs, and uploads. |
| Project workflow | `app/services/project_service.py` | Owns project status transitions and prevents bypassing document/Blueprint gates. |
| Documents | `app/api/routes/documents.py`, `app/services/document_service.py`, `app/services/ai_run_service.py` | Stores Project Bot Documents, runs documentation flow, records AI run status, and supports upload/manual document creation. |
| AI flows | `app/ai/` | Provides fallback and CrewAI-backed flows for Project Bot Document drafting and AI-assisted Blueprint proposals. AI produces structured data only; it does not write generated project files. |
| Reviews | `app/api/routes/approvals.py`, `app/services/approval_service.py` | Records human review decisions and moves projects through document approval states. |
| Blueprints | `app/api/routes/blueprints.py`, `app/services/blueprint_service.py`, `app/services/validation_service.py` | Stores Bot Blueprints, optionally proposes Blueprints from approved documents, and validates them before generation. |
| Generation | `app/api/routes/generator.py`, `app/services/generation_service.py`, `app/generator/` | Runs deterministic generation from a validated `BotBlueprint`, records run/artifact metadata, and packages output. |
| Artifacts | `app/api/routes/artifacts.py`, `app/services/artifact_service.py`, `app/services/artifact_storage.py` | Resolves the latest completed ZIP artifact and returns it through `FileResponse`; local filesystem storage is the current backend. |

## Data Flow

1. `POST /projects` creates a project in `DRAFT_CREATED`.
2. A Project Bot Document is created manually, uploaded, or generated through
   `POST /projects/{project_id}/documents/generate`.
3. A reviewer submits the document for review and approves it. Blueprint
   generation is blocked until the project reaches `DOCUMENT_APPROVED`.
4. `POST /projects/{project_id}/blueprint/generate` creates a placeholder or
   AI-assisted Blueprint proposal from the approved document, or
   `POST /projects/{project_id}/blueprint` stores a manually supplied Blueprint.
5. `POST /projects/{project_id}/blueprint/validate` runs Blueprint validation.
   Code generation is blocked until the project reaches `BLUEPRINT_VALIDATED`.
6. `POST /projects/{project_id}/generate` runs `GeneratorCore` with the stored
   validated Blueprint, writes generated files, creates artifact metadata, and
   creates a ZIP artifact when `output_format=zip`.
7. `GET /projects/{project_id}/runs` lists generation runs newest first.
8. `GET /projects/{project_id}/download` returns the ZIP artifact for the latest
   completed generation run.

## Component Diagram

```mermaid
flowchart LR
    Client[API client or reviewer] --> API[FastAPI app]

    API --> Projects[Project routes and ProjectService]
    API --> Documents[Document routes and services]
    API --> Reviews[Approval routes and service]
    API --> Blueprints[Blueprint routes and services]
    API --> Generation[Generation route and GenerationService]
    API --> Artifacts[Artifact route and ArtifactService]

    Documents --> DocFlow[DocumentationFlow fallback or CrewAI]
    Documents --> AIRuns[AIRunService]
    Blueprints --> BlueprintFlow[BlueprintFlow fallback or CrewAI]
    Blueprints --> Validation[BlueprintValidationService]
    Generation --> Gate[GenerationGateService]
    Generation --> GeneratorCore[GeneratorCore]
    GeneratorCore --> Modules[Core, Backend, BaleBots, Frontend modules]
    GeneratorCore --> Manifest[generation_manifest.json]
    Generation --> Storage[ArtifactStorage local backend]
    Artifacts --> Storage
    Artifacts --> Zip[FileResponse ZIP]

    API --> Schemas[Pydantic schemas]
    DBModels[SQLAlchemy models] --> DB
    Projects --> DB[(Database)]
    Documents --> DB
    Reviews --> DB
    Blueprints --> DB
    Generation --> DB
```

## Generation Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI routes
    participant Project as ProjectService
    participant Docs as Document/AIRun services
    participant Review as ApprovalService
    participant Blueprint as BlueprintService
    participant Gate as GenerationGateService
    participant Gen as GenerationService
    participant Core as GeneratorCore
    participant Store as ArtifactStorage/DB
    participant Download as ArtifactService

    Client->>API: POST /projects
    API->>Project: create project
    Project-->>Client: DRAFT_CREATED
    Client->>API: POST /documents, /documents/upload, or /documents/generate
    API->>Docs: create Project Bot Document
    Docs-->>Client: DOCUMENT_DRAFTED document
    Client->>API: POST /documents/{document_id}/submit-review
    API->>Project: transition to DOCUMENT_REVIEW_PENDING
    Client->>API: POST /document/approve
    API->>Review: record approval
    Review->>Project: transition to DOCUMENT_APPROVED
    Client->>API: POST /blueprint/generate or POST /blueprint
    API->>Blueprint: store proposed/manual BotBlueprint
    Client->>API: POST /blueprint/validate
    API->>Blueprint: validate semantic Blueprint rules
    Blueprint->>Project: transition to BLUEPRINT_VALIDATED when valid
    Client->>API: POST /generate
    API->>Gate: assert DOCUMENT_APPROVED and BLUEPRINT_VALIDATED gates
    API->>Gen: run generation
    Gen->>Core: deterministic render from BotBlueprint
    Core-->>Gen: generated files and manifest
    Gen->>Store: create file artifacts and ZIP artifact when output_format=zip
    Gen-->>Client: GenerationRunRead with artifacts and download_url
    Client->>API: GET /download
    API->>Download: resolve latest completed ZIP artifact
    Download->>Store: verify artifact metadata and local file
    Download-->>Client: FileResponse ZIP
```

## Gate Boundaries

The Builder Platform keeps two hard gates:

- Blueprint proposal/storage requires an approved Project Bot Document.
- Deterministic generation requires a validated Blueprint.

The generator does not call an LLM and does not generate files from raw prompt
text. It consumes only a `BotBlueprint` that passes schema and semantic
validation.
