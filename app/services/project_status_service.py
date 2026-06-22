from uuid import UUID

from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


class ProjectStatusService:
    def __init__(self, project_service: ProjectService) -> None:
        self._project_service = project_service

    async def get_status(self, project_id: UUID) -> ProjectStatus:
        return (await self._project_service.get(project_id)).status

    async def is_document_review_eligible(self, project_id: UUID) -> bool:
        return (await self.get_status(project_id)) == ProjectStatus.DOCUMENT_REVIEW_PENDING

    async def is_blueprint_generation_eligible(self, project_id: UUID) -> bool:
        return (await self.get_status(project_id)) == ProjectStatus.DOCUMENT_APPROVED

    async def is_implementation_eligible(self, project_id: UUID) -> bool:
        return (await self.get_status(project_id)) == ProjectStatus.BLUEPRINT_VALIDATED

    async def is_document_rejected(self, project_id: UUID) -> bool:
        return (await self.get_status(project_id)) == ProjectStatus.DOCUMENT_REJECTED
