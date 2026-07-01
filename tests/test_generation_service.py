from pathlib import Path
from uuid import UUID

import yaml
from httpx import AsyncClient

from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectStatus
from app.services.blueprint_service import BlueprintService
from app.services.project_service import ProjectService

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_valid_blueprint() -> dict:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return yaml.safe_load(f)


async def _prepare_validated_project(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> UUID:
    response = await client.post("/projects", json={"name": "Generation Response"})
    assert response.status_code == 201
    project_id = UUID(response.json()["id"])

    await project_service.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)
    await project_service.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    await project_service.transition(project_id, ProjectStatus.DOCUMENT_APPROVED)
    await blueprint_service.store(project_id, BotBlueprint.model_validate(_load_valid_blueprint()))
    await blueprint_service.validate(project_id)

    return project_id


async def test_generate_response_includes_artifacts_and_download_url(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> None:
    project_id = await _prepare_validated_project(
        client, project_service, blueprint_service
    )

    response = await client.post(f"/projects/{project_id}/generate")

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["project_id"] == str(project_id)
    assert data["blueprint_id"]
    assert data["status"] == "COMPLETED"
    assert data["template_profile"] == "fastapi_react_bale_v1"
    assert data["started_at"]
    assert data["finished_at"]
    assert data["error_message"] is None
    assert data["download_url"] == f"/projects/{project_id}/download"

    artifacts = data["artifacts"]
    assert artifacts
    assert {"artifact_type", "filename", "created_at"} == set(artifacts[0])
    assert {artifact["artifact_type"] for artifact in artifacts} >= {"file", "zip"}
    assert any(
        artifact["filename"] == "docs/generation_manifest.json"
        for artifact in artifacts
    )
    assert any(artifact["filename"].endswith(".zip") for artifact in artifacts)
    assert all("storage_path" not in artifact for artifact in artifacts)
    assert all(not Path(artifact["filename"]).is_absolute() for artifact in artifacts)
