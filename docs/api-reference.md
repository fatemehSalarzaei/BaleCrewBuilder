# API Reference

This page lists the routes mounted by `app/main.py` today. It does not list planned
endpoints as current behavior.

Interactive OpenAPI docs are available at `http://localhost:8000/docs` when the
Builder Platform is running.

## Mounted Endpoints

| Method | Path | Request schema | Response schema | Success | Common errors |
|--------|------|----------------|-----------------|---------|---------------|
| `GET` | `/health` | None | `HealthResponse` | `200 OK` | None |
| `POST` | `/projects` | `ProjectCreate` | `ProjectRead` | `201 Created` | `422` validation error |
| `GET` | `/projects/{project_id}` | None | `ProjectRead` | `200 OK` | `404 Project not found` |
| `POST` | `/projects/{project_id}/documents` | `DocumentCreate` | `DocumentRead` | `201 Created` | `404 Project not found`, `422` validation error |
| `GET` | `/projects/{project_id}/document` | None | `DocumentRead` | `200 OK` | `404 Project not found`, `404 No document found for project` |
| `POST` | `/projects/{project_id}/documents/generate` | `DocumentGenerateRequest` | `DocumentGenerateResponse` | `201 Created` | `404 Project not found`, `409` invalid status transition, `502` documentation flow failed, `500` status recovery failed |
| `POST` | `/projects/{project_id}/documents/upload` | `multipart/form-data` file plus `store_as_document` and `title` query params | `DocumentUploadResponse` | `201 Created` | `404 Project not found`, `422` unsupported file type or validation error |
| `POST` | `/projects/{project_id}/documents/{document_id}/submit-review` | None | `DocumentSubmitReviewResponse` | `200 OK` | `404 Project not found`, `404 Document not found`, `409` invalid status transition |
| `POST` | `/projects/{project_id}/document/approve` | `DocumentApproveCreate` | `ReviewRead` | `201 Created` | `404 Project not found`, `409` invalid review decision/status |
| `POST` | `/projects/{project_id}/document/feedback` | `DocumentFeedbackCreate` | `ReviewRead` | `201 Created` | `404 Project not found`, `409` invalid review decision/status, `422` validation error |
| `GET` | `/projects/{project_id}/reviews` | None | `list[ReviewRead]` | `200 OK` | `404 Project not found` |
| `POST` | `/projects/{project_id}/blueprint/generate` | Query: `mode=placeholder\|ai`, optional `additional_context` | `BlueprintGenerateResponse` | `201 Created` | `404 Project not found`, `409` document not approved or missing, `422` invalid AI proposal, `502` AI proposal flow failed |
| `POST` | `/projects/{project_id}/blueprint` | `BotBlueprint` | `BotBlueprint` | `201 Created` | `404 Project not found`, `409` blueprint submission not allowed, `422` validation error |
| `GET` | `/projects/{project_id}/blueprint` | None | `BotBlueprint` | `200 OK` | `404 Project not found`, `404 No blueprint stored for this project` |
| `POST` | `/projects/{project_id}/blueprint/validate` | None | `ValidationResultRead` | `200 OK` | `404 Project not found`, `404 No blueprint stored for this project; submit one first` |
| `POST` | `/projects/{project_id}/generate` | None | `GenerationRunRead` | `201 Created` | `404 Project not found`, `409` generation gate blocked, `422` unknown template profile/module or missing template |
| `GET` | `/projects/{project_id}/runs` | None | `list[GenerationRunRead]` | `200 OK` | `404 Project not found` |
| `GET` | `/projects/{project_id}/download` | None | `FileResponse` ZIP | `200 OK` | `404 Project not found`, `409 No completed generation run found for project`, `404 No ZIP artifact found for latest completed generation run`, `410 ZIP artifact file is missing on disk`, `500` artifact storage path error |

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

The previously discussed `POST /projects/{project_id}/analyze` and
`GET /projects/{project_id}/requirements` endpoints are future work, not mounted
routes.
