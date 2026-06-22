from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.schemas.project import ProjectCreate, ProjectRead, ProjectStatus


class ProjectNotFoundError(Exception):
    pass


class IllegalStatusTransitionError(Exception):
    pass


_ALLOWED_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT_CREATED: {ProjectStatus.DOCUMENT_GENERATING},
    ProjectStatus.DOCUMENT_GENERATING: {ProjectStatus.DOCUMENT_DRAFTED},
    ProjectStatus.DOCUMENT_DRAFTED: {ProjectStatus.DOCUMENT_REVIEW_PENDING},
    ProjectStatus.DOCUMENT_REVIEW_PENDING: {
        ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
        ProjectStatus.DOCUMENT_APPROVED,
    },
    ProjectStatus.DOCUMENT_CHANGE_REQUESTED: {ProjectStatus.DOCUMENT_GENERATING},
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
    def __init__(self) -> None:
        self._store: dict[UUID, ProjectRead] = {}

    def create(self, payload: ProjectCreate) -> ProjectRead:
        now = datetime.now(timezone.utc)
        project = ProjectRead(
            id=uuid4(),
            name=payload.name,
            description=payload.description,
            status=ProjectStatus.DRAFT_CREATED,
            created_at=now,
            updated_at=now,
        )
        self._store[project.id] = project
        return project

    def get(self, project_id: UUID) -> ProjectRead:
        project = self._store.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    def transition(self, project_id: UUID, target: ProjectStatus) -> ProjectRead:
        project = self.get(project_id)
        allowed = _ALLOWED_TRANSITIONS.get(project.status, set())
        if target not in allowed:
            raise IllegalStatusTransitionError(
                f"{project.status} -> {target} is not allowed"
            )
        updated = project.model_copy(
            update={"status": target, "updated_at": datetime.now(timezone.utc)}
        )
        self._store[project_id] = updated
        return updated
