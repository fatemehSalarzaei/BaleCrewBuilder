from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enumerations ────────────────────────────────────────────────────────────


class BotAudience(StrEnum):
    USERS = "users"
    ADMINS = "admins"
    OPERATORS = "operators"
    CUSTOM = "custom"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class PageType(StrEnum):
    DASHBOARD = "dashboard"
    LIST = "list"
    FORM = "form"
    DETAIL = "detail"
    SETTINGS = "settings"
    REPORT = "report"


class OutputFormat(StrEnum):
    ZIP = "zip"
    REPOSITORY = "repository"


# ── Leaf specs ───────────────────────────────────────────────────────────────


class ActorSpec(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    type: Literal["user", "admin", "operator", "bot"]


class RoleSpec(BaseModel):
    key: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    is_admin: bool = Field(default=False)


class PermissionSpec(BaseModel):
    key: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    description: str = Field(default="")
    roles: list[str] = Field(default_factory=list)


class EntityFieldSpec(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    type: str = Field(min_length=1, max_length=100)
    nullable: bool = Field(default=True)
    default: str | int | float | bool | None = Field(default=None)
    primary_key: bool = Field(default=False)
    unique: bool = Field(default=False)
    indexed: bool = Field(default=False)


class EntitySpec(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    table_name: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    fields: list[EntityFieldSpec] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    indexes: list[str] = Field(default_factory=list)
    audit: bool = Field(default=False)


class DatabaseSpec(BaseModel):
    entities: list[EntitySpec] = Field(default_factory=list)


class BotCommandSpec(BaseModel):
    command: str = Field(min_length=1, max_length=100)
    description: str = Field(default="")
    handler: str = Field(min_length=1)
    allowed_roles: list[str] = Field(default_factory=list)


class BotSecurityPolicySpec(BaseModel):
    require_registered_user: bool = Field(default=True)
    rate_limit: str | None = Field(default=None)
    audit_sensitive_callbacks: bool = Field(default=False)


class BotSpec(BaseModel):
    key: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    title: str = Field(min_length=1, max_length=200)
    audience: BotAudience
    token_env: str = Field(min_length=1, max_length=200)
    webhook_path: str = Field(min_length=1, max_length=500)
    allowed_roles: list[str] = Field(default_factory=list)
    miniapp_default_route: str | None = Field(default=None)
    commands: list[BotCommandSpec] = Field(default_factory=list)
    handlers: list[str] = Field(default_factory=list)
    security_policy: BotSecurityPolicySpec = Field(default_factory=BotSecurityPolicySpec)


class MiniAppRouteSpec(BaseModel):
    path: str = Field(min_length=1)
    allowed_roles: list[str] = Field(default_factory=list)
    page_type: PageType
    api_dependencies: list[str] = Field(default_factory=list)


class MiniAppSpec(BaseModel):
    enabled: bool = Field(default=False)
    auth_endpoint: str | None = Field(default=None)
    routes: list[MiniAppRouteSpec] = Field(default_factory=list)


class ApiEndpointSpec(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    method: HttpMethod
    path: str = Field(min_length=1)
    auth_required: bool = Field(default=True)
    allowed_roles: list[str] = Field(default_factory=list)
    request_schema: str | None = Field(default=None)
    response_schema: str | None = Field(default=None)
    service_method: str = Field(min_length=1)
    audit_required: bool = Field(default=False)


class ApiSpec(BaseModel):
    endpoints: list[ApiEndpointSpec] = Field(default_factory=list)


class FlowStepSpec(BaseModel):
    step: int = Field(ge=1)
    action: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    target: str | None = Field(default=None)


class FlowSpec(BaseModel):
    key: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    trigger: str = Field(min_length=1)
    steps: list[FlowStepSpec] = Field(default_factory=list)
    bots_involved: list[str] = Field(default_factory=list)
    api_calls: list[str] = Field(default_factory=list)


class SecuritySpec(BaseModel):
    miniapp_hmac_validation: bool = Field(default=True)
    jwt_enabled: bool = Field(default=True)
    bot_webhook_secret: bool = Field(default=True)
    audit_log_enabled: bool = Field(default=True)
    rbac_enabled: bool = Field(default=True)


class TestingSpec(BaseModel):
    test_framework: str = Field(default="pytest")
    coverage_target: int = Field(default=80, ge=0, le=100)
    test_stubs: list[str] = Field(default_factory=list)


class BackendSpec(BaseModel):
    framework: str = Field(default="fastapi")
    python_version: str = Field(default="3.12")
    async_mode: bool = Field(default=True)
    additional_packages: list[str] = Field(default_factory=list)


# ── Top-level specs ──────────────────────────────────────────────────────────


class ProjectSpec(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9-]*$")
    platform: Literal["bale"] = "bale"
    backend: Literal["fastapi"] = "fastapi"
    frontend: Literal["miniapp_panel"] = "miniapp_panel"
    generation_mode: Literal["documentation_first"] = "documentation_first"


class WorkflowSpec(BaseModel):
    documentation_required: bool = Field(default=True)
    human_approval_required: bool = Field(default=True)
    document_status: str = Field(min_length=1)
    implementation_starts_after: str = Field(default="BLUEPRINT_VALIDATED")


class GenerationSpec(BaseModel):
    template_profile: str = Field(min_length=1)
    enabled_modules: list[str] = Field(default_factory=list)
    custom_logic_blocks: list[str] = Field(default_factory=list)
    output_format: OutputFormat = Field(default=OutputFormat.ZIP)


# ── Root Blueprint ───────────────────────────────────────────────────────────


class BotBlueprint(BaseModel):
    blueprint_version: str = Field(default="1.0")
    project: ProjectSpec
    workflow: WorkflowSpec
    actors: list[ActorSpec] = Field(default_factory=list)
    roles: list[RoleSpec] = Field(default_factory=list)
    permissions: list[PermissionSpec] = Field(default_factory=list)
    bots: list[BotSpec] = Field(default_factory=list)
    miniapp: MiniAppSpec = Field(default_factory=MiniAppSpec)
    backend: BackendSpec = Field(default_factory=BackendSpec)
    database: DatabaseSpec = Field(default_factory=DatabaseSpec)
    flows: list[FlowSpec] = Field(default_factory=list)
    api: ApiSpec = Field(default_factory=ApiSpec)
    security: SecuritySpec = Field(default_factory=SecuritySpec)
    testing: TestingSpec = Field(default_factory=TestingSpec)
    generation: GenerationSpec


# ── API response schemas ─────────────────────────────────────────────────────


class ValidationResultRead(BaseModel):
    is_valid: bool
    errors: list[str]


class BlueprintGenerateResponse(BaseModel):
    blueprint: BotBlueprint
    source_document_id: UUID
    project_status: str
