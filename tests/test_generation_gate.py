"""Integration tests for POST /projects/{project_id}/generate endpoint."""
import uuid
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectCreate, ProjectStatus
from app.services.blueprint_service import BlueprintService
from app.services.project_service import ProjectService

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load_valid_blueprint() -> dict:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        return yaml.safe_load(f)


async def _fast_track_to_document_approved(ps: ProjectService, project_id: UUID) -> None:
    await ps.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_APPROVED)


async def _prepare_validated_project(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> UUID:
    resp = await client.post("/projects", json={"name": "Gen Test Project"})
    assert resp.status_code == 201
    project_id = UUID(resp.json()["id"])
    await _fast_track_to_document_approved(project_service, project_id)
    await blueprint_service.store(project_id, BotBlueprint.model_validate(_load_valid_blueprint()))
    await blueprint_service.validate(project_id)
    return project_id


# ── Gate enforcement ──────────────────────────────────────────────────────────


async def test_generate_blocked_when_project_in_draft(client: AsyncClient) -> None:
    resp = await client.post("/projects", json={"name": "Draft Project"})
    project_id = resp.json()["id"]
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.status_code == 409


async def test_generate_blocked_when_only_document_approved(
    client: AsyncClient, project_service: ProjectService
) -> None:
    resp = await client.post("/projects", json={"name": "Approved Only"})
    project_id = UUID(resp.json()["id"])
    await _fast_track_to_document_approved(project_service, project_id)
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.status_code == 409


async def test_generate_project_not_found(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await client.post(f"/projects/{fake_id}/generate")
    assert resp.status_code == 404


# ── Successful generation ─────────────────────────────────────────────────────


async def test_generate_returns_201_when_blueprint_validated(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.status_code == 201


async def test_generate_returns_completed_status(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["finished_at"] is not None
    assert data["error_message"] is None


async def test_generate_response_contains_correct_project_id(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.json()["project_id"] == str(project_id)


async def test_generate_response_contains_template_profile(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.json()["template_profile"] == "fastapi_react_bale_v1"


# ── DB records ────────────────────────────────────────────────────────────────


async def test_generation_run_is_recorded_in_db(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
    db: AsyncSession,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    run_id = UUID(resp.json()["id"])

    row = await db.get(GenerationRunModel, run_id)
    assert row is not None
    assert row.status == "COMPLETED"
    assert str(row.project_id) == str(project_id)


async def test_generation_creates_artifact_records(
    client: AsyncClient,
    project_service: ProjectService,
    blueprint_service: BlueprintService,
    db: AsyncSession,
) -> None:
    project_id = await _prepare_validated_project(client, project_service, blueprint_service)
    resp = await client.post(f"/projects/{project_id}/generate")
    run_id = UUID(resp.json()["id"])

    stmt = sa.select(GeneratedArtifactModel).where(
        GeneratedArtifactModel.generation_run_id == run_id
    )
    result = await db.execute(stmt)
    artifacts = result.scalars().all()
    assert len(artifacts) > 0

    filenames = {a.filename for a in artifacts}
    assert "README.md" in filenames
    assert "docs/generation_manifest.json" in filenames
