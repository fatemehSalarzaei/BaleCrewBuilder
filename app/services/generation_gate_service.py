from uuid import UUID

from app.schemas.project import ProjectStatus
from app.services.blueprint_service import BlueprintNotFoundError, BlueprintService
from app.services.project_service import ProjectService


class GenerationBlockedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class GenerationGateService:
    """Enforces Documentation First and Blueprint validation gates (CLAUDE.md R2, R9)."""

    def __init__(self, project_service: ProjectService, blueprint_service: BlueprintService) -> None:
        self._project_service = project_service
        self._blueprint_service = blueprint_service

    async def assert_blueprint_generation_allowed(self, project_id: UUID) -> None:
        project = await self._project_service.get(project_id)
        if project.status == ProjectStatus.DOCUMENT_REJECTED:
            raise GenerationBlockedError(
                f"Blueprint generation is permanently blocked: document was rejected. "
                f"Current status: {project.status}"
            )
        if project.status != ProjectStatus.DOCUMENT_APPROVED:
            raise GenerationBlockedError(
                f"Blueprint generation requires DOCUMENT_APPROVED. "
                f"Current status: {project.status}"
            )

    async def assert_implementation_generation_allowed(self, project_id: UUID) -> None:
        project = await self._project_service.get(project_id)
        if project.status == ProjectStatus.DOCUMENT_REJECTED:
            raise GenerationBlockedError(
                f"Implementation generation is permanently blocked: document was rejected. "
                f"Current status: {project.status}"
            )
        if project.status != ProjectStatus.BLUEPRINT_VALIDATED:
            raise GenerationBlockedError(
                f"Implementation generation requires BLUEPRINT_VALIDATED. "
                f"Current status: {project.status}"
            )

        try:
            await self._blueprint_service.get(project_id)
        except BlueprintNotFoundError:
            raise GenerationBlockedError(
                "Implementation generation blocked: no Blueprint is stored for this project."
            )

        result = await self._blueprint_service.get_validation_result(project_id)
        if result is None:
            raise GenerationBlockedError(
                "Implementation generation blocked: no Blueprint validation result found."
            )
        if not result.is_valid or result.errors:
            raise GenerationBlockedError(
                f"Implementation generation blocked: Blueprint validation failed with "
                f"{len(result.errors)} error(s)."
            )
