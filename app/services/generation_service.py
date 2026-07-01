from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.generated_artifacts import GeneratedArtifactModel
from app.db.models.generation_runs import GenerationRunModel
from app.generator import GeneratorCore
from app.generator.packager import package_as_zip
from app.schemas.blueprint import OutputFormat
from app.schemas.generation import (
    GeneratedArtifactRead,
    GenerationRunRead,
    GenerationRunStatus,
)
from app.schemas.project import ProjectStatus
from app.services.blueprint_service import BlueprintService
from app.services.generation_gate_service import GenerationGateService
from app.services.project_service import ProjectService


class GenerationService:
    def __init__(
        self,
        db: AsyncSession,
        gate: GenerationGateService,
        blueprint_svc: BlueprintService,
        output_dir: Path | None = None,
    ) -> None:
        self._db = db
        self._gate = gate
        self._blueprint_svc = blueprint_svc
        self._project_svc = ProjectService(db=db)
        self._output_dir = output_dir or Path(settings.generation_output_dir)

    async def run_generation(self, project_id: UUID) -> GenerationRunRead:
        await self._gate.assert_implementation_generation_allowed(project_id)

        blueprint = await self._blueprint_svc.get(project_id)
        blueprint_db_id = await self._blueprint_svc.get_row_id(project_id)

        run_id = uuid4()
        run = GenerationRunModel(
            id=run_id,
            project_id=project_id,
            blueprint_id=blueprint_db_id,
            status=GenerationRunStatus.RUNNING,
            template_profile=blueprint.generation.template_profile,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(run)
        await self._db.commit()

        run_output_dir = self._output_dir / str(run_id)
        run_output_dir.mkdir(parents=True, exist_ok=True)

        await self._project_svc.transition(project_id, ProjectStatus.IMPLEMENTATION_GENERATING)

        try:
            result = GeneratorCore().run(blueprint, run_output_dir)

            zip_path: Path | None = None
            if blueprint.generation.output_format == OutputFormat.ZIP:
                zip_path = self._output_dir / f"{run_id}.zip"
                package_as_zip(run_output_dir, zip_path)

            now = datetime.now(timezone.utc)
            artifact_reads: list[GeneratedArtifactRead] = []
            for rel_path in result.generated_files:
                artifact = GeneratedArtifactModel(
                    id=uuid4(),
                    generation_run_id=run_id,
                    artifact_type="file",
                    filename=rel_path,
                    storage_path=str(run_output_dir / rel_path),
                    created_at=now,
                )
                self._db.add(artifact)
                artifact_reads.append(GeneratedArtifactRead.model_validate(artifact))

            if zip_path:
                artifact = GeneratedArtifactModel(
                    id=uuid4(),
                    generation_run_id=run_id,
                    artifact_type="zip",
                    filename=zip_path.name,
                    storage_path=str(zip_path),
                    created_at=now,
                )
                self._db.add(artifact)
                artifact_reads.append(GeneratedArtifactRead.model_validate(artifact))

            await self._project_svc.transition(project_id, ProjectStatus.IMPLEMENTATION_GENERATED)
            run.status = GenerationRunStatus.COMPLETED
            run.finished_at = datetime.now(timezone.utc)
            await self._db.commit()

        except Exception as exc:
            await self._project_svc.transition(project_id, ProjectStatus.IMPLEMENTATION_FAILED)
            run.status = GenerationRunStatus.FAILED
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(exc)
            await self._db.commit()
            raise

        return self._build_generation_response(
            run=run,
            artifacts=artifact_reads,
        )

    @staticmethod
    def _build_generation_response(
        run: GenerationRunModel,
        artifacts: list[GeneratedArtifactRead],
    ) -> GenerationRunRead:
        response = GenerationRunRead.model_validate(run)
        response.artifacts = artifacts
        if any(artifact.artifact_type == "zip" for artifact in artifacts):
            response.download_url = f"/projects/{run.project_id}/download"
        return response
