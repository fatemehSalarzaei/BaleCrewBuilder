from uuid import UUID

from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


class GenerationBlockedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class GenerationGateService:
    """Enforces Documentation First and Blueprint validation gates (CLAUDE.md R2, R9)."""

    def __init__(self, project_service: ProjectService) -> None:
        self._project_service = project_service

    def assert_blueprint_generation_allowed(self, project_id: UUID) -> None:
        project = self._project_service.get(project_id)
        if project.status != ProjectStatus.DOCUMENT_APPROVED:
            raise GenerationBlockedError(
                f"Blueprint generation requires DOCUMENT_APPROVED. "
                f"Current status: {project.status}"
            )

    def assert_implementation_generation_allowed(self, project_id: UUID) -> None:
        project = self._project_service.get(project_id)
        if project.status != ProjectStatus.BLUEPRINT_VALIDATED:
            raise GenerationBlockedError(
                f"Implementation generation requires BLUEPRINT_VALIDATED. "
                f"Current status: {project.status}"
            )
