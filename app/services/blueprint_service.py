from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_validations import BlueprintValidationModel
from app.db.models.blueprints import BlueprintModel
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
        db: AsyncSession,
        validation_service: BlueprintValidationService,
    ) -> None:
        self.db = db
        self._project_service = ProjectService(db=db)
        self._validation_service = validation_service

    async def store(self, project_id: UUID, blueprint: BotBlueprint) -> BotBlueprint:
        project = await self._project_service.get(project_id)

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
            await self._project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATING)
            await self._project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATED)

        blueprint_data = blueprint.model_dump(mode="json")

        stmt = sa.select(BlueprintModel).where(BlueprintModel.project_id == project_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.blueprint_data = blueprint_data
            existing.stored_at = datetime.now(timezone.utc)
        else:
            existing = BlueprintModel(
                id=uuid4(),
                project_id=project_id,
                blueprint_data=blueprint_data,
                stored_at=datetime.now(timezone.utc),
            )
            self.db.add(existing)

        await self.db.commit()
        return blueprint

    async def get(self, project_id: UUID) -> BotBlueprint:
        stmt = sa.select(BlueprintModel).where(BlueprintModel.project_id == project_id)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise BlueprintNotFoundError(project_id)
        return BotBlueprint.model_validate(row.blueprint_data)

    async def get_stored_at(self, project_id: UUID) -> datetime | None:
        stmt = sa.select(BlueprintModel.stored_at).where(
            BlueprintModel.project_id == project_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def validate(self, project_id: UUID) -> ValidationResult:
        blueprint = await self.get(project_id)
        result = self._validation_service.validate(blueprint)

        stmt = sa.select(BlueprintModel).where(BlueprintModel.project_id == project_id)
        db_result = await self.db.execute(stmt)
        bp_row = db_result.scalar_one_or_none()
        if bp_row is None:
            raise BlueprintNotFoundError(project_id)

        validation_row = BlueprintValidationModel(
            id=uuid4(),
            blueprint_id=bp_row.id,
            is_valid=result.is_valid,
            errors=result.errors,
            validated_at=datetime.now(timezone.utc),
        )
        self.db.add(validation_row)

        project = await self._project_service.get(project_id)
        if project.status == ProjectStatus.BLUEPRINT_GENERATED:
            target = (
                ProjectStatus.BLUEPRINT_VALIDATED
                if result.is_valid
                else ProjectStatus.BLUEPRINT_VALIDATION_FAILED
            )
            await self._project_service.transition(project_id, target)

        await self.db.commit()
        return result

    async def get_validation_result(self, project_id: UUID) -> ValidationResult | None:
        stmt = sa.select(BlueprintModel).where(BlueprintModel.project_id == project_id)
        result = await self.db.execute(stmt)
        bp_row = result.scalar_one_or_none()
        if bp_row is None:
            return None

        val_stmt = (
            sa.select(BlueprintValidationModel)
            .where(BlueprintValidationModel.blueprint_id == bp_row.id)
            .order_by(BlueprintValidationModel.validated_at.desc())
            .limit(1)
        )
        val_result = await self.db.execute(val_stmt)
        row = val_result.scalar_one_or_none()
        if row is None:
            return None
        return ValidationResult(is_valid=row.is_valid, errors=row.errors)
