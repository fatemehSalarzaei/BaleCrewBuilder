from uuid import UUID

from httpx import AsyncClient

from app.ai.blueprint_flow import BlueprintFlow, BlueprintFlowInput
from app.api import deps
from app.main import app
from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


async def _create_project(client: AsyncClient, name: str = "AI Blueprint") -> str:
    response = await client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _approve_project(project_service: ProjectService, project_id: str) -> None:
    pid = UUID(project_id)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_APPROVED)


async def _create_document(client: AsyncClient, project_id: str, content: str) -> str:
    response = await client.post(
        f"/projects/{project_id}/documents",
        json={
            "title": "Approved Product Document",
            "content": content,
            "kind": "MARKDOWN",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _approved_project_with_document(
    client: AsyncClient,
    project_service: ProjectService,
    *,
    content: str,
) -> tuple[str, str]:
    project_id = await _create_project(client)
    document_id = await _create_document(client, project_id, content)
    await _approve_project(project_service, project_id)
    return project_id, document_id


async def test_blueprint_generate_placeholder_mode_still_works(
    client: AsyncClient,
    project_service: ProjectService,
) -> None:
    project_id, document_id = await _approved_project_with_document(
        client,
        project_service,
        content="# Overview\n\n## Data Entities\n\n- Requests\n",
    )

    response = await client.post(
        f"/projects/{project_id}/blueprint/generate?mode=placeholder"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["source_document_id"] == document_id
    assert data["project_status"] == "BLUEPRINT_GENERATED"
    assert data["blueprint"]["api"]["endpoints"] == []


async def test_blueprint_generate_default_mode_is_placeholder(
    client: AsyncClient,
    project_service: ProjectService,
) -> None:
    project_id, _ = await _approved_project_with_document(
        client,
        project_service,
        content="# Overview\n\n## API Endpoints\n\n- GET /requests\n",
    )

    response = await client.post(f"/projects/{project_id}/blueprint/generate")

    assert response.status_code == 201
    assert response.json()["blueprint"]["api"]["endpoints"] == []


async def test_fallback_ai_mode_derives_entities_and_endpoints(
    client: AsyncClient,
    project_service: ProjectService,
) -> None:
    project_id, document_id = await _approved_project_with_document(
        client,
        project_service,
        content=(
            "# Project Overview\n\n"
            "A reusable operations platform.\n\n"
            "## Data Entities\n\n"
            "- Requests: submitted by members\n"
            "- Reviews: admin decisions\n\n"
            "## API Endpoints\n\n"
            "- GET /requests\n"
            "- POST /requests\n"
            "- POST /admin/reviews\n"
        ),
    )

    response = await client.post(f"/projects/{project_id}/blueprint/generate?mode=ai")

    assert response.status_code == 201
    data = response.json()
    assert data["source_document_id"] == document_id
    assert data["project_status"] == "BLUEPRINT_GENERATED"

    blueprint = data["blueprint"]
    entity_names = {entity["name"] for entity in blueprint["database"]["entities"]}
    assert {"request", "review"} <= entity_names

    endpoint_paths = {endpoint["path"] for endpoint in blueprint["api"]["endpoints"]}
    assert {"/requests", "/admin/reviews"} <= endpoint_paths
    admin_endpoint = next(
        endpoint
        for endpoint in blueprint["api"]["endpoints"]
        if endpoint["path"] == "/admin/reviews"
    )
    assert admin_endpoint["allowed_roles"] == ["admin"]
    assert admin_endpoint["audit_required"] is True


async def test_invalid_ai_blueprint_output_returns_422(
    client: AsyncClient,
    project_service: ProjectService,
) -> None:
    class InvalidBlueprintFlow(BlueprintFlow):
        async def run(self, input_data: BlueprintFlowInput):
            return {"project": {"name": "Invalid"}}

    project_id, _ = await _approved_project_with_document(
        client,
        project_service,
        content="# Overview\n\nApproved document.",
    )
    app.dependency_overrides[deps.get_blueprint_flow_dep] = lambda: InvalidBlueprintFlow()
    try:
        response = await client.post(f"/projects/{project_id}/blueprint/generate?mode=ai")
    finally:
        del app.dependency_overrides[deps.get_blueprint_flow_dep]

    assert response.status_code == 422
    assert "AI Blueprint proposal was invalid" in response.json()["detail"]


async def test_ai_generated_blueprint_must_still_be_validated_before_generation(
    client: AsyncClient,
    project_service: ProjectService,
) -> None:
    project_id, _ = await _approved_project_with_document(
        client,
        project_service,
        content=(
            "# Project Overview\n\n"
            "## Data Entities\n\n"
            "- Requests\n\n"
            "## API Endpoints\n\n"
            "- GET /requests\n"
        ),
    )

    proposal_response = await client.post(
        f"/projects/{project_id}/blueprint/generate?mode=ai"
    )
    assert proposal_response.status_code == 201

    blocked_response = await client.post(f"/projects/{project_id}/generate")
    assert blocked_response.status_code == 409

    validation_response = await client.post(f"/projects/{project_id}/blueprint/validate")
    assert validation_response.status_code == 200
    assert validation_response.json()["is_valid"] is True

    generation_response = await client.post(f"/projects/{project_id}/generate")
    assert generation_response.status_code == 201
