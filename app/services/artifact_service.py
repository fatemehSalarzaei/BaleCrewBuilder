from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.db.models.projects import ProjectModel
from app.schemas.generation import GenerationRunStatus
from app.services.artifact_storage import (
    ArtifactStoragePathError,
    LocalArtifactStorage,
    get_artifact_storage,
)


class NoCompletedGenerationRunError(Exception):
    pass


class ZipArtifactNotFoundError(Exception):
    pass


class ZipArtifactFileMissingError(Exception):
    pass


@dataclass(frozen=True)
class DownloadableArtifact:
    path: Path
    filename: str


class ArtifactService:
    def __init__(
        self,
        db: AsyncSession,
        storage: LocalArtifactStorage | None = None,
    ) -> None:
        self._db = db
        self._storage = storage or get_artifact_storage()

    async def get_latest_project_zip(self, project_id: UUID) -> DownloadableArtifact:
        project = await self._db.get(ProjectModel, project_id)
        if project is None:
            from app.services.project_service import ProjectNotFoundError

            raise ProjectNotFoundError(project_id)

        run = await self._latest_completed_run(project_id)
        if run is None:
            raise NoCompletedGenerationRunError(project_id)

        artifact = await self._zip_artifact_for_run(run.id)
        if artifact is None:
            raise ZipArtifactNotFoundError(run.id)

        resolved = self._storage.resolve_download(artifact.storage_path)
        if not resolved.path.is_file():
            raise ZipArtifactFileMissingError(str(resolved.path))

        safe_filename = Path(artifact.filename).name or f"{project_id}.zip"
        return DownloadableArtifact(path=resolved.path, filename=safe_filename)

    async def _latest_completed_run(self, project_id: UUID) -> GenerationRunModel | None:
        stmt = (
            sa.select(GenerationRunModel)
            .where(
                GenerationRunModel.project_id == project_id,
                GenerationRunModel.status == GenerationRunStatus.COMPLETED,
            )
            .order_by(
                GenerationRunModel.finished_at.desc(),
                GenerationRunModel.started_at.desc(),
            )
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _zip_artifact_for_run(self, run_id: UUID) -> GeneratedArtifactModel | None:
        stmt = (
            sa.select(GeneratedArtifactModel)
            .where(
                GeneratedArtifactModel.generation_run_id == run_id,
                GeneratedArtifactModel.artifact_type == "zip",
            )
            .order_by(GeneratedArtifactModel.created_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
