from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.schemas.generation import GenerationRunStatus


async def _create_project(client: AsyncClient, name: str = "Runs API") -> UUID:
    response = await client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return UUID(response.json()["id"])


async def _add_run(
    db: AsyncSession,
    project_id: UUID,
    *,
    started_at: datetime,
    finished_at: datetime | None = None,
    status: str = GenerationRunStatus.COMPLETED,
    error_message: str | None = None,
) -> UUID:
    run_id = uuid4()
    db.add(
        GenerationRunModel(
            id=run_id,
            project_id=project_id,
            blueprint_id=None,
            status=status,
            template_profile="fastapi_react_bale_v1",
            started_at=started_at,
            finished_at=finished_at,
            error_message=error_message,
        )
    )
    await db.commit()
    return run_id


async def _add_artifact(
    db: AsyncSession,
    run_id: UUID,
    *,
    artifact_type: str,
    filename: str,
) -> None:
    db.add(
        GeneratedArtifactModel(
            id=uuid4(),
            generation_run_id=run_id,
            artifact_type=artifact_type,
            filename=filename,
            storage_path=str(Path("/tmp") / filename),
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def test_list_generation_runs_returns_newest_first_with_artifacts(
    client: AsyncClient,
    db: AsyncSession,
) -> None:
    project_id = await _create_project(client)
    now = datetime.now(timezone.utc)
    older_run = await _add_run(
        db,
        project_id,
        started_at=now - timedelta(hours=2),
        finished_at=now - timedelta(hours=1),
    )
    latest_run = await _add_run(
        db,
        project_id,
        started_at=now,
        status=GenerationRunStatus.RUNNING,
    )
    await _add_artifact(
        db,
        older_run,
        artifact_type="file",
        filename="README.md",
    )
    await _add_artifact(
        db,
        older_run,
        artifact_type="zip",
        filename="../artifact.zip",
    )

    response = await client.get(f"/projects/{project_id}/runs")

    assert response.status_code == 200
    data = response.json()
    assert [run["id"] for run in data] == [str(latest_run), str(older_run)]
    assert data[0]["artifacts"] == []
    assert data[0]["download_url"] is None
    assert data[1]["artifacts"] == [
        {
            "artifact_type": "file",
            "filename": "README.md",
            "created_at": data[1]["artifacts"][0]["created_at"],
        },
        {
            "artifact_type": "zip",
            "filename": "../artifact.zip",
            "created_at": data[1]["artifacts"][1]["created_at"],
        },
    ]
    assert data[1]["download_url"] == f"/projects/{project_id}/download"
    assert "storage_path" not in data[1]["artifacts"][0]


async def test_list_generation_runs_existing_project_without_runs_returns_empty_list(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    response = await client.get(f"/projects/{project_id}/runs")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_generation_runs_project_not_found_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/projects/{uuid4()}/runs")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"
