from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.projects import ProjectModel
from app.schemas.project import ProjectCreate, ProjectRead, ProjectStatus


class ProjectNotFoundError(Exception):
    pass


class IllegalStatusTransitionError(Exception):
    pass


_ALLOWED_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT_CREATED: {ProjectStatus.DOCUMENT_GENERATING},
    ProjectStatus.DOCUMENT_GENERATING: {
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_GENERATION_FAILED,
    },
    ProjectStatus.DOCUMENT_GENERATION_FAILED: {ProjectStatus.DOCUMENT_GENERATING},
    ProjectStatus.DOCUMENT_DRAFTED: {ProjectStatus.DOCUMENT_REVIEW_PENDING},
    ProjectStatus.DOCUMENT_REVIEW_PENDING: {
        ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
        ProjectStatus.DOCUMENT_REJECTED,
        ProjectStatus.DOCUMENT_APPROVED,
    },
    ProjectStatus.DOCUMENT_CHANGE_REQUESTED: {ProjectStatus.DOCUMENT_GENERATING},
    ProjectStatus.DOCUMENT_REJECTED: set(),  # terminal — workflow stops here
    ProjectStatus.DOCUMENT_APPROVED: {ProjectStatus.BLUEPRINT_GENERATING},
    ProjectStatus.BLUEPRINT_GENERATING: {
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATION_FAILED,
    },
    ProjectStatus.BLUEPRINT_GENERATED: {
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.BLUEPRINT_VALIDATION_FAILED,
    },
    ProjectStatus.BLUEPRINT_VALIDATION_FAILED: {ProjectStatus.BLUEPRINT_GENERATING},
    ProjectStatus.BLUEPRINT_VALIDATED: {ProjectStatus.IMPLEMENTATION_GENERATING},
    ProjectStatus.IMPLEMENTATION_GENERATING: {
        ProjectStatus.IMPLEMENTATION_GENERATED,
        ProjectStatus.IMPLEMENTATION_FAILED,
    },
    ProjectStatus.IMPLEMENTATION_FAILED: {ProjectStatus.IMPLEMENTATION_GENERATING},
    ProjectStatus.IMPLEMENTATION_GENERATED: {ProjectStatus.IMPLEMENTATION_REVIEW_PENDING},
    ProjectStatus.IMPLEMENTATION_REVIEW_PENDING: {ProjectStatus.IMPLEMENTATION_APPROVED},
    ProjectStatus.IMPLEMENTATION_APPROVED: {ProjectStatus.READY_FOR_DEPLOY},
    ProjectStatus.READY_FOR_DEPLOY: {ProjectStatus.DEPLOYED},
    ProjectStatus.DEPLOYED: set(),
}


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payload: ProjectCreate) -> ProjectRead:
        now = datetime.now(timezone.utc)
        row = ProjectModel(
            id=uuid4(),
            name=payload.name,
            description=payload.description,
            status=ProjectStatus.DRAFT_CREATED,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        return ProjectRead.model_validate(row)

    async def get(self, project_id: UUID) -> ProjectRead:
        row = await self.db.get(ProjectModel, project_id)
        if row is None:
            raise ProjectNotFoundError(project_id)
        return ProjectRead.model_validate(row)

    async def transition(self, project_id: UUID, target: ProjectStatus) -> ProjectRead:
        row = await self.db.get(ProjectModel, project_id)
        if row is None:
            raise ProjectNotFoundError(project_id)
        allowed = _ALLOWED_TRANSITIONS.get(ProjectStatus(row.status), set())
        if target not in allowed:
            raise IllegalStatusTransitionError(
                f"{row.status} -> {target} is not allowed"
            )
        row.status = target
        row.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return ProjectRead.model_validate(row)
