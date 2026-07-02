# API Reference

This page lists the routes mounted by `app/main.py` today. It does not list planned
endpoints as current behavior.

Interactive OpenAPI docs are available at `http://localhost:8000/docs` when the
Builder Platform is running.

## Implemented APIs

| Method | Path | Route module | Request schema | Response schema | Success | Common errors |
|--------|------|--------------|----------------|-----------------|---------|---------------|
| `GET` | `/health` | `app/api/routes/health.py` | None | `HealthResponse` | `200 OK` | None |
| `POST` | `/projects` | `app/api/routes/projects.py` | `ProjectCreate` | `ProjectRead` | `201 Created` | `422` validation error |
| `GET` | `/projects/{project_id}` | `app/api/routes/projects.py` | None | `ProjectRead` | `200 OK` | `404 Project not found` |
| `POST` | `/projects/{project_id}/documents` | `app/api/routes/documents.py` | `DocumentCreate` | `DocumentRead` | `201 Created` | `404 Project not found`, `422` validation error |
| `GET` | `/projects/{project_id}/document` | `app/api/routes/documents.py` | None | `DocumentRead` | `200 OK` | `404 Project not found`, `404 No document found for project` |
| `POST` | `/projects/{project_id}/documents/generate` | `app/api/routes/documents.py` | `DocumentGenerateRequest` | `DocumentGenerateResponse` | `201 Created` | `404 Project not found`, `409` invalid status transition, `502` documentation flow failed, `500` status recovery failed |
| `POST` | `/projects/{project_id}/documents/upload` | `app/api/routes/documents.py` | `multipart/form-data` file plus `store_as_document` and `title` query params | `DocumentUploadResponse` | `201 Created` | `404 Project not found`, `422` unsupported file type or validation error |
| `POST` | `/projects/{project_id}/documents/{document_id}/submit-review` | `app/api/routes/documents.py` | None | `DocumentSubmitReviewResponse` | `200 OK` | `404 Project not found`, `404 Document not found`, `409` invalid status transition |
| `POST` | `/projects/{project_id}/document/approve` | `app/api/routes/approvals.py` | `DocumentApproveCreate` | `ReviewRead` | `201 Created` | `404 Project not found`, `409` invalid review decision/status |
| `POST` | `/projects/{project_id}/document/feedback` | `app/api/routes/approvals.py` | `DocumentFeedbackCreate` | `ReviewRead` | `201 Created` | `404 Project not found`, `409` invalid review decision/status, `422` validation error |
| `GET` | `/projects/{project_id}/reviews` | `app/api/routes/approvals.py` | None | `list[ReviewRead]` | `200 OK` | `404 Project not found` |
| `POST` | `/projects/{project_id}/blueprint/generate` | `app/api/routes/blueprints.py` | Query: `mode=placeholder\|ai`, optional `additional_context` | `BlueprintGenerateResponse` | `201 Created` | `404 Project not found`, `409` document not approved or missing, `422` invalid AI proposal, `502` AI proposal flow failed |
| `POST` | `/projects/{project_id}/blueprint` | `app/api/routes/blueprints.py` | `BotBlueprint` | `BotBlueprint` | `201 Created` | `404 Project not found`, `409` blueprint submission not allowed, `422` validation error |
| `GET` | `/projects/{project_id}/blueprint` | `app/api/routes/blueprints.py` | None | `BotBlueprint` | `200 OK` | `404 Project not found`, `404 No blueprint stored for this project` |
| `POST` | `/projects/{project_id}/blueprint/validate` | `app/api/routes/blueprints.py` | None | `ValidationResultRead` | `200 OK` | `404 Project not found`, `404 No blueprint stored for this project; submit one first` |
| `POST` | `/projects/{project_id}/generate` | `app/api/routes/generator.py` | None | `GenerationRunRead` | `201 Created` | `404 Project not found`, `409` generation gate blocked, `422` unknown template profile/module or missing template |
| `GET` | `/projects/{project_id}/runs` | `app/api/routes/runs.py` | None | `list[GenerationRunRead]` | `200 OK` | `404 Project not found` |
| `GET` | `/projects/{project_id}/download` | `app/api/routes/artifacts.py` | None | `FileResponse` ZIP | `200 OK` | `404 Project not found`, `409 No completed generation run found for project`, `404 No ZIP artifact found for latest completed generation run`, `410 ZIP artifact file is missing on disk`, `500` artifact storage path error |

## Notes

`POST /projects/{project_id}/generate` returns run metadata plus generated
artifact metadata. The response includes `download_url` when the completed run
has a ZIP artifact.

`GET /projects/{project_id}/download` returns the ZIP from the latest completed
generation run for the project. Running and failed runs are ignored.

There is no separate persisted requirements model today. Requirements extraction
is represented by Project Bot Document generation and review:

```text
POST /projects/{project_id}/documents/generate
```

## Planned APIs

These endpoints have been discussed but are not mounted in `app/main.py` and
should not be treated as current behavior:

| Method | Path | Status | Current substitute |
|--------|------|--------|--------------------|
| `POST` | `/projects/{project_id}/analyze` | Planned | Use `POST /projects/{project_id}/documents/generate` to create a reviewed Project Bot Document. |
| `GET` | `/projects/{project_id}/requirements` | Planned | Requirements are represented inside the latest Project Bot Document. |
