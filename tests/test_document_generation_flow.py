"""Tests for Phase 2: POST /projects/{project_id}/documents/generate endpoint.

Uses the fallback documentation flow — no real LLM credentials required.
"""
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models.ai_runs import AIRunModel
from app.main import app


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_project(client: AsyncClient, name: str = "Test Bot Project") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _generate_document(
    client: AsyncClient,
    project_id: str,
    raw_requirements: str = "Build a task management bot for teams.",
    title: str | None = None,
) -> dict:
    body: dict = {"raw_requirements": raw_requirements}
    if title:
        body["title"] = title
    resp = await client.post(
        f"/projects/{project_id}/documents/generate", json=body
    )
    return resp


# ── Success path ──────────────────────────────────────────────────────────────


async def test_generate_document_returns_201(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _generate_document(client, project_id)
    assert resp.status_code == 201


async def test_generate_document_response_shape(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await _generate_document(client, project_id)
    data = resp.json()
    assert "document" in data
    assert "ai_run_id" in data
    assert "ai_run_status" in data


async def test_generate_document_stores_content(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    requirements = "Users need to sign up and create tasks."
    resp = await _generate_document(client, project_id, raw_requirements=requirements)
    assert resp.status_code == 201
    doc = resp.json()["document"]
    assert doc["project_id"] == project_id
    assert requirements in doc["content"]
    assert doc["kind"] == "MARKDOWN"
    assert len(doc["content"]) > 0
    assert doc["id"]
    assert doc["created_at"]


async def test_generate_document_title_contains_project_name(client: AsyncClient) -> None:
    project_id = await _create_project(client, name="Reservation System")
    resp = await _generate_document(client, project_id)
    assert resp.status_code == 201
    doc = resp.json()["document"]
    assert "Reservation System" in doc["title"]


async def test_generate_document_custom_title_overrides_flow_title(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    custom_title = "My Custom Bot Document"
    resp = await _generate_document(
        client, project_id, title=custom_title
    )
    assert resp.status_code == 201
    assert resp.json()["document"]["title"] == custom_title


async def test_generate_document_records_completed_ai_run(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    resp = await _generate_document(client, project_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ai_run_status"] == "COMPLETED"
    assert UUID(data["ai_run_id"])


async def test_generate_document_transitions_project_to_document_drafted(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    await _generate_document(client, project_id)
    resp = await client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DOCUMENT_DRAFTED"


async def test_generate_document_with_additional_context(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await client.post(
        f"/projects/{project_id}/documents/generate",
        json={
            "raw_requirements": "Build a scheduling bot.",
            "additional_context": "Must support Persian calendar.",
        },
    )
    assert resp.status_code == 201
    assert "Must support Persian calendar." in resp.json()["document"]["content"]


# ── Error paths ───────────────────────────────────────────────────────────────


async def test_generate_document_missing_project_returns_404(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/projects/00000000-0000-0000-0000-000000000099/documents/generate",
        json={"raw_requirements": "Build a bot."},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_generate_document_missing_requirements_returns_422(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    resp = await client.post(
        f"/projects/{project_id}/documents/generate",
        json={"title": "No requirements"},
    )
    assert resp.status_code == 422


async def test_generate_document_empty_requirements_returns_422(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    resp = await client.post(
        f"/projects/{project_id}/documents/generate",
        json={"raw_requirements": ""},
    )
    assert resp.status_code == 422


async def test_generate_document_failed_flow_allows_retry(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    class FailingFlow:
        async def run(self, input_data):
            raise RuntimeError("Interrupted")

    app.dependency_overrides[deps.get_documentation_flow_dep] = lambda: FailingFlow()
    try:
        failed = await client.post(
            f"/projects/{project_id}/documents/generate",
            json={"raw_requirements": "Build a bot."},
        )
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    assert failed.status_code == 502
    project = await client.get(f"/projects/{project_id}")
    assert project.json()["status"] == "DOCUMENT_GENERATION_FAILED"

    retry = await client.post(
        f"/projects/{project_id}/documents/generate",
        json={"raw_requirements": "Build a bot again."},
    )
    assert retry.status_code == 201


async def test_generate_document_failed_flow_records_failed_ai_run(
    client: AsyncClient, db: AsyncSession
) -> None:
    from app.ai.documentation_flow import DocumentationFlow
    from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput

    class AlwaysFailingFlow(DocumentationFlow):
        async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
            raise RuntimeError("Simulated LLM failure")

    app.dependency_overrides[deps.get_documentation_flow_dep] = (
        lambda: AlwaysFailingFlow()
    )
    try:
        project_id = await _create_project(client)
        resp = await client.post(
            f"/projects/{project_id}/documents/generate",
            json={"raw_requirements": "Build a bot."},
        )
        assert resp.status_code == 502
        assert "Documentation flow failed" in resp.json()["detail"]
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    result = await db.execute(select(AIRunModel))
    runs = result.scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "FAILED"
    assert "Simulated LLM failure" in runs[0].error_message


async def test_generate_document_failed_flow_does_not_create_document(
    client: AsyncClient, db: AsyncSession
) -> None:
    from app.ai.documentation_flow import DocumentationFlow
    from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput
    from app.db.models.project_documents import ProjectDocumentModel

    class AlwaysFailingFlow(DocumentationFlow):
        async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
            raise RuntimeError("Flow crashed")

    app.dependency_overrides[deps.get_documentation_flow_dep] = (
        lambda: AlwaysFailingFlow()
    )
    try:
        project_id = await _create_project(client)
        resp = await client.post(
            f"/projects/{project_id}/documents/generate",
            json={"raw_requirements": "Build a bot."},
        )
        assert resp.status_code == 502
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    result = await db.execute(select(ProjectDocumentModel))
    docs = result.scalars().all()
    assert len(docs) == 0, "No document should be stored when the flow fails"


# ── Gate compliance ───────────────────────────────────────────────────────────


async def test_generate_document_does_not_auto_approve(client: AsyncClient) -> None:
    """Document generation must NOT set status to DOCUMENT_APPROVED."""
    project_id = await _create_project(client)
    await _generate_document(client, project_id)
    resp = await client.get(f"/projects/{project_id}")
    assert resp.json()["status"] == "DOCUMENT_DRAFTED"
    assert resp.json()["status"] != "DOCUMENT_APPROVED"


async def test_implementation_generation_blocked_after_document_drafted(
    client: AsyncClient,
) -> None:
    """After document generation, implementation generation is still blocked
    because Blueprint is not yet validated."""
    project_id = await _create_project(client)
    gen_resp = await _generate_document(client, project_id)
    assert gen_resp.status_code == 201

    impl_resp = await client.post(f"/projects/{project_id}/generate")
    assert impl_resp.status_code == 409


# ── Manual creation endpoint still works ─────────────────────────────────────


async def test_manual_document_creation_still_works(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Manual Doc", "content": "# Manual\n\nContent.", "kind": "MARKDOWN"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Manual Doc"
    assert data["project_id"] == project_id
