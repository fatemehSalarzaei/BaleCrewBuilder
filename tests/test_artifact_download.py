from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import ZipFile

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.schemas.generation import GenerationRunStatus


async def _create_project(client: AsyncClient) -> UUID:
    response = await client.post("/projects", json={"name": "Artifact Project"})
    assert response.status_code == 201
    return UUID(response.json()["id"])


async def _add_run(
    db: AsyncSession,
    project_id: UUID,
    *,
    status: str = GenerationRunStatus.COMPLETED,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> UUID:
    now = datetime.now(timezone.utc)
    run_id = uuid4()
    db.add(
        GenerationRunModel(
            id=run_id,
            project_id=project_id,
            blueprint_id=None,
            status=status,
            template_profile="fastapi_react_bale_v1",
            started_at=started_at or now,
            finished_at=finished_at,
        )
    )
    await db.commit()
    return run_id


async def _add_zip_artifact(
    db: AsyncSession,
    run_id: UUID,
    zip_path: Path,
    *,
    filename: str | None = None,
) -> UUID:
    artifact_id = uuid4()
    db.add(
        GeneratedArtifactModel(
            id=artifact_id,
            generation_run_id=run_id,
            artifact_type="zip",
            filename=filename or zip_path.name,
            storage_path=str(zip_path),
            created_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return artifact_id


def _write_zip(path: Path, content: str = "hello") -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("README.md", content)


async def test_download_returns_latest_completed_zip(
    client: AsyncClient, db: AsyncSession, tmp_path: Path
) -> None:
    project_id = await _create_project(client)
    older_run = await _add_run(
        db,
        project_id,
        finished_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    latest_run = await _add_run(db, project_id, finished_at=datetime.now(timezone.utc))
    running_run = await _add_run(
        db,
        project_id,
        status=GenerationRunStatus.RUNNING,
        started_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    older_zip = tmp_path / "older.zip"
    latest_zip = tmp_path / "latest.zip"
    running_zip = tmp_path / "running.zip"
    _write_zip(older_zip, "older")
    _write_zip(latest_zip, "latest")
    _write_zip(running_zip, "running")
    await _add_zip_artifact(db, older_run, older_zip)
    await _add_zip_artifact(db, latest_run, latest_zip, filename="../latest.zip")
    await _add_zip_artifact(db, running_run, running_zip)

    response = await client.get(f"/projects/{project_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert 'filename="latest.zip"' in response.headers["content-disposition"]
    assert response.content == latest_zip.read_bytes()


async def test_download_project_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/projects/{uuid4()}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


async def test_download_without_completed_generation_run_returns_409(
    client: AsyncClient, db: AsyncSession
) -> None:
    project_id = await _create_project(client)
    await _add_run(db, project_id, status=GenerationRunStatus.RUNNING)
    await _add_run(db, project_id, status=GenerationRunStatus.FAILED)

    response = await client.get(f"/projects/{project_id}/download")

    assert response.status_code == 409
    assert response.json()["detail"] == "No completed generation run found for project"


async def test_download_completed_run_without_zip_artifact_returns_404(
    client: AsyncClient, db: AsyncSession
) -> None:
    project_id = await _create_project(client)
    await _add_run(db, project_id, finished_at=datetime.now(timezone.utc))

    response = await client.get(f"/projects/{project_id}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "No ZIP artifact found for latest completed generation run"


async def test_download_missing_zip_file_on_disk_returns_410(
    client: AsyncClient, db: AsyncSession, tmp_path: Path
) -> None:
    project_id = await _create_project(client)
    run_id = await _add_run(db, project_id, finished_at=datetime.now(timezone.utc))
    await _add_zip_artifact(db, run_id, tmp_path / "missing.zip")

    response = await client.get(f"/projects/{project_id}/download")

    assert response.status_code == 410
    assert response.json()["detail"] == "ZIP artifact file is missing on disk"
