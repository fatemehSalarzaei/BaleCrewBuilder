from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.db.models.projects import ProjectModel
from app.schemas.generation import GeneratedArtifactRead, GenerationRunRead
from app.services.project_service import ProjectNotFoundError


class GenerationRunService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_project(self, project_id: UUID) -> list[GenerationRunRead]:
        project = await self._db.get(ProjectModel, project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        stmt = (
            sa.select(GenerationRunModel)
            .where(GenerationRunModel.project_id == project_id)
            .order_by(
                GenerationRunModel.started_at.desc(),
                GenerationRunModel.finished_at.desc(),
            )
        )
        result = await self._db.execute(stmt)
        runs = list(result.scalars().all())
        if not runs:
            return []

        artifacts_by_run = await self._artifacts_by_run([run.id for run in runs])
        response: list[GenerationRunRead] = []
        for run in runs:
            run_read = GenerationRunRead.model_validate(run)
            artifacts = artifacts_by_run.get(run.id, [])
            run_read.artifacts = artifacts
            if any(artifact.artifact_type == "zip" for artifact in artifacts):
                run_read.download_url = f"/projects/{project_id}/download"
            response.append(run_read)
        return response

    async def _artifacts_by_run(
        self, run_ids: list[UUID]
    ) -> dict[UUID, list[GeneratedArtifactRead]]:
        stmt = (
            sa.select(GeneratedArtifactModel)
            .where(GeneratedArtifactModel.generation_run_id.in_(run_ids))
            .order_by(GeneratedArtifactModel.created_at.asc())
        )
        result = await self._db.execute(stmt)

        artifacts_by_run: dict[UUID, list[GeneratedArtifactRead]] = {}
        for artifact in result.scalars().all():
            artifacts_by_run.setdefault(artifact.generation_run_id, []).append(
                GeneratedArtifactRead.model_validate(artifact)
            )
        return artifacts_by_run
