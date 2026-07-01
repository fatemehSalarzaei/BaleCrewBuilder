from uuid import UUID

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.documentation_flow import DocumentationFlow
from app.api import deps
from app.db.models.ai_runs import AIRunModel
from app.main import app
from app.schemas.ai import DocumentationFlowInput, DocumentationFlowOutput


class AlwaysFailingFlow(DocumentationFlow):
    async def run(self, input_data: DocumentationFlowInput) -> DocumentationFlowOutput:
        raise RuntimeError("Simulated documentation failure")


async def _create_project(client: AsyncClient) -> str:
    response = await client.post("/projects", json={"name": "Recovery Test"})
    assert response.status_code == 201
    return response.json()["id"]


async def _generate_document(client: AsyncClient, project_id: str) -> Response:
    return await client.post(
        f"/projects/{project_id}/documents/generate",
        json={"raw_requirements": "Build a reusable Bale builder project."},
    )


async def _project_status(client: AsyncClient, project_id: str) -> str:
    response = await client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    return response.json()["status"]


async def test_successful_document_generation_sets_document_drafted(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    response = await _generate_document(client, project_id)

    assert response.status_code == 201
    assert await _project_status(client, project_id) == "DOCUMENT_DRAFTED"


async def test_failed_document_generation_sets_document_generation_failed(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    app.dependency_overrides[deps.get_documentation_flow_dep] = (
        lambda: AlwaysFailingFlow()
    )
    try:
        response = await _generate_document(client, project_id)
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    assert response.status_code == 502
    assert "Documentation flow failed" in response.json()["detail"]
    assert await _project_status(client, project_id) == "DOCUMENT_GENERATION_FAILED"


async def test_retry_from_document_generation_failed_is_allowed(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    app.dependency_overrides[deps.get_documentation_flow_dep] = (
        lambda: AlwaysFailingFlow()
    )
    try:
        failed_response = await _generate_document(client, project_id)
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    assert failed_response.status_code == 502
    assert await _project_status(client, project_id) == "DOCUMENT_GENERATION_FAILED"

    retry_response = await _generate_document(client, project_id)

    assert retry_response.status_code == 201
    assert UUID(retry_response.json()["ai_run_id"])
    assert await _project_status(client, project_id) == "DOCUMENT_DRAFTED"


async def test_failed_document_generation_persists_failed_ai_run(
    client: AsyncClient,
    db: AsyncSession,
) -> None:
    project_id = await _create_project(client)
    app.dependency_overrides[deps.get_documentation_flow_dep] = (
        lambda: AlwaysFailingFlow()
    )
    try:
        response = await _generate_document(client, project_id)
    finally:
        del app.dependency_overrides[deps.get_documentation_flow_dep]

    assert response.status_code == 502

    result = await db.execute(select(AIRunModel))
    runs = result.scalars().all()
    assert len(runs) == 1
    assert runs[0].status == "FAILED"
    assert "Simulated documentation failure" in runs[0].error_message
