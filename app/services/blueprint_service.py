import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_validations import BlueprintValidationModel
from app.db.models.blueprints import BlueprintModel
from app.schemas.blueprint import (
    ActorSpec,
    ApiSpec,
    BackendSpec,
    BotAudience,
    BotCommandSpec,
    BotSecurityPolicySpec,
    BotSpec,
    BotBlueprint,
    DatabaseSpec,
    EntityFieldSpec,
    EntitySpec,
    GenerationSpec,
    MiniAppRouteSpec,
    MiniAppSpec,
    PageType,
    PermissionSpec,
    ProjectSpec,
    RoleSpec,
    SecuritySpec,
    TestingSpec,
    WorkflowSpec,
)
from app.schemas.project import ProjectStatus
from app.services.project_service import IllegalStatusTransitionError, ProjectService
from app.services.validation_service import BlueprintValidationService, ValidationResult


# ── Placeholder Blueprint builder ─────────────────────────────────────────────

_PLACEHOLDER_CORE_ENTITY_NAMES: list[str] = [
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "bale_accounts",
    "bots",
    "bot_conversations",
    "processed_updates",
    "audit_logs",
    "app_settings",
]


def _to_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "-", name.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug or not slug[0].isalpha():
        slug = "project-" + slug.lstrip("-")
    return slug[:100] or "project"


def build_placeholder_blueprint(project_name: str) -> BotBlueprint:
    """Return a deterministic, generic placeholder Blueprint from a project name.

    The result passes all BlueprintValidationService rules so it can be stored
    and immediately validated without manual editing. Domain-specific entities
    and API endpoints are intentionally omitted — the human reviewer fills them
    in after Blueprint generation.
    """
    slug = _to_slug(project_name)

    core_entities = [
        EntitySpec(
            name=entity_name,
            table_name=entity_name,
            fields=[
                EntityFieldSpec(name="id", type="uuid", primary_key=True, nullable=False)
            ],
        )
        for entity_name in _PLACEHOLDER_CORE_ENTITY_NAMES
    ]

    return BotBlueprint(
        blueprint_version="1.0",
        project=ProjectSpec(
            name=project_name,
            slug=slug,
            platform="bale",
            backend="fastapi",
            frontend="miniapp_panel",
            generation_mode="documentation_first",
        ),
        workflow=WorkflowSpec(
            documentation_required=True,
            human_approval_required=True,
            document_status="DOCUMENT_APPROVED",
            implementation_starts_after="BLUEPRINT_VALIDATED",
        ),
        actors=[
            ActorSpec(key="member", name="Member", type="user"),
            ActorSpec(key="admin_user", name="Administrator", type="admin"),
        ],
        roles=[
            RoleSpec(key="member", title="Member", is_admin=False),
            RoleSpec(key="admin", title="Administrator", is_admin=True),
        ],
        permissions=[
            PermissionSpec(key="view_data", description="View data", roles=["member", "admin"]),
            PermissionSpec(key="manage_data", description="Manage data", roles=["admin"]),
        ],
        bots=[
            BotSpec(
                key="user_bot",
                title=f"{project_name} Bot",
                audience=BotAudience.USERS,
                token_env="USER_BOT_TOKEN",
                webhook_path="/webhook/user",
                allowed_roles=["member"],
                commands=[
                    BotCommandSpec(
                        command="/start",
                        description="Start the bot",
                        handler="handle_start",
                        allowed_roles=["member"],
                    ),
                ],
                security_policy=BotSecurityPolicySpec(require_registered_user=True),
            ),
            BotSpec(
                key="admin_bot",
                title=f"{project_name} Admin Bot",
                audience=BotAudience.ADMINS,
                token_env="ADMIN_BOT_TOKEN",
                webhook_path="/webhook/admin",
                allowed_roles=["admin"],
                commands=[
                    BotCommandSpec(
                        command="/start",
                        description="Admin start",
                        handler="admin_handle_start",
                        allowed_roles=["admin"],
                    ),
                ],
                security_policy=BotSecurityPolicySpec(require_registered_user=True),
            ),
        ],
        miniapp=MiniAppSpec(
            enabled=True,
            auth_endpoint="/auth/bale-miniapp",
            routes=[
                MiniAppRouteSpec(
                    path="/dashboard",
                    allowed_roles=["member", "admin"],
                    page_type=PageType.DASHBOARD,
                ),
                MiniAppRouteSpec(
                    path="/admin/dashboard",
                    allowed_roles=["admin"],
                    page_type=PageType.DASHBOARD,
                ),
            ],
        ),
        backend=BackendSpec(framework="fastapi", python_version="3.12", async_mode=True),
        database=DatabaseSpec(entities=core_entities),
        api=ApiSpec(endpoints=[]),
        security=SecuritySpec(),
        testing=TestingSpec(),
        generation=GenerationSpec(
            template_profile="fastapi_react_bale_v1",
            enabled_modules=["rbac", "audit_log", "bale_client", "miniapp_auth"],
        ),
    )


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

    async def get_row_id(self, project_id: UUID) -> UUID:
        stmt = sa.select(BlueprintModel.id).where(BlueprintModel.project_id == project_id)
        result = await self.db.execute(stmt)
        row_id = result.scalar_one_or_none()
        if row_id is None:
            raise BlueprintNotFoundError(project_id)
        return row_id

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
