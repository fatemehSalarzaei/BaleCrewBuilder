from datetime import datetime, timezone
from uuid import UUID

from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectStatus
from app.services.project_service import IllegalStatusTransitionError, ProjectService
from app.services.validation_service import BlueprintValidationService, ValidationResult


class BlueprintNotFoundError(Exception):
    pass


class BlueprintSubmissionNotAllowedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


_SUBMISSION_ALLOWED_STATUSES: frozenset[ProjectStatus] = frozenset({
    ProjectStatus.DOCUMENT_APPROVED,
    ProjectStatus.BLUEPRINT_GENERATED,
    ProjectStatus.BLUEPRINT_VALIDATION_FAILED,
})


class BlueprintService:
    def __init__(
        self,
        project_service: ProjectService,
        validation_service: BlueprintValidationService,
    ) -> None:
        self._project_service = project_service
        self._validation_service = validation_service
        self._store: dict[UUID, BotBlueprint] = {}
        self._validation_results: dict[UUID, ValidationResult] = {}
        self._stored_at: dict[UUID, datetime] = {}

    def store(self, project_id: UUID, blueprint: BotBlueprint) -> BotBlueprint:
        project = self._project_service.get(project_id)

        if project.status not in _SUBMISSION_ALLOWED_STATUSES:
            raise BlueprintSubmissionNotAllowedError(
                f"Blueprint submission requires project status to be one of "
                f"{[s.value for s in _SUBMISSION_ALLOWED_STATUSES]}. "
                f"Current status: {project.status}"
            )

        if project.status in (
            ProjectStatus.DOCUMENT_APPROVED,
            ProjectStatus.BLUEPRINT_VALIDATION_FAILED,
        ):
            self._project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATING)
            self._project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATED)

        self._store[project_id] = blueprint
        self._stored_at[project_id] = datetime.now(timezone.utc)
        self._validation_results.pop(project_id, None)
        return blueprint

    def get(self, project_id: UUID) -> BotBlueprint:
        blueprint = self._store.get(project_id)
        if blueprint is None:
            raise BlueprintNotFoundError(project_id)
        return blueprint

    def get_stored_at(self, project_id: UUID) -> datetime | None:
        return self._stored_at.get(project_id)

    def validate(self, project_id: UUID) -> ValidationResult:
        blueprint = self.get(project_id)
        result = self._validation_service.validate(blueprint)
        self._validation_results[project_id] = result

        project = self._project_service.get(project_id)
        if project.status == ProjectStatus.BLUEPRINT_GENERATED:
            target = (
                ProjectStatus.BLUEPRINT_VALIDATED
                if result.is_valid
                else ProjectStatus.BLUEPRINT_VALIDATION_FAILED
            )
            self._project_service.transition(project_id, target)

        return result

    def get_validation_result(self, project_id: UUID) -> ValidationResult | None:
        return self._validation_results.get(project_id)
