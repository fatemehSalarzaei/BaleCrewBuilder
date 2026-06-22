from dataclasses import dataclass, field

from app.schemas.blueprint import BotBlueprint

CORE_ENTITIES: frozenset[str] = frozenset({
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
})

KNOWN_TEMPLATE_PROFILES: frozenset[str] = frozenset({"fastapi_react_bale_v1"})

KNOWN_MODULES: frozenset[str] = frozenset({
    "rbac",
    "audit_log",
    "bale_client",
    "miniapp_auth",
    "celery_worker",
    "redis_session",
    "pdf_export",
    "notification_service",
})


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


class BlueprintValidationService:
    def validate(self, blueprint: BotBlueprint) -> ValidationResult:
        errors: list[str] = []
        self._check_workflow(blueprint, errors)
        self._check_bots(blueprint, errors)
        self._check_miniapp(blueprint, errors)
        self._check_database(blueprint, errors)
        self._check_api_endpoints(blueprint, errors)
        self._check_generation(blueprint, errors)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # ── Rule 1: document_status must be DOCUMENT_APPROVED ───────────────────

    def _check_workflow(self, bp: BotBlueprint, errors: list[str]) -> None:
        if bp.workflow.document_status != "DOCUMENT_APPROVED":
            errors.append(
                f"workflow.document_status must be 'DOCUMENT_APPROVED'; "
                f"got {bp.workflow.document_status!r}. "
                "Blueprint cannot be validated before document approval."
            )

    # ── Rule 2 & 3: bots exist; no shared token_env or webhook_path ─────────

    def _check_bots(self, bp: BotBlueprint, errors: list[str]) -> None:
        if not bp.bots:
            errors.append(
                "Blueprint must define at least one bot. "
                "Add a user_bot (and admin_bot if the project requires admin operations)."
            )
            return

        seen_token_envs: dict[str, str] = {}
        seen_webhook_paths: dict[str, str] = {}

        for bot in bp.bots:
            if bot.token_env in seen_token_envs:
                errors.append(
                    f"Bots '{seen_token_envs[bot.token_env]}' and '{bot.key}' share "
                    f"token_env '{bot.token_env}'. Each bot must use a separate "
                    "token environment variable (R5: separate bots)."
                )
            else:
                seen_token_envs[bot.token_env] = bot.key

            if bot.webhook_path in seen_webhook_paths:
                errors.append(
                    f"Bots '{seen_webhook_paths[bot.webhook_path]}' and '{bot.key}' share "
                    f"webhook_path '{bot.webhook_path}'. Each bot must have its own "
                    "webhook path (R5: separate bots)."
                )
            else:
                seen_webhook_paths[bot.webhook_path] = bot.key

    # ── Rule 4 & 8: admin routes; miniapp auth endpoint ─────────────────────

    def _check_miniapp(self, bp: BotBlueprint, errors: list[str]) -> None:
        if not bp.miniapp.enabled:
            return

        if not bp.miniapp.auth_endpoint:
            errors.append(
                "miniapp.auth_endpoint must be set when miniapp.enabled=true. "
                "Backend must expose an auth route (e.g. POST /auth/bale-miniapp) "
                "for HMAC-validated Mini App bootstrapping."
            )

        user_role_keys = {r.key for r in bp.roles if not r.is_admin}

        for route in bp.miniapp.routes:
            if not route.path.startswith("/admin/"):
                continue
            violating = sorted(set(route.allowed_roles) & user_role_keys)
            if violating:
                errors.append(
                    f"Mini App admin route '{route.path}' grants access to "
                    f"non-admin roles: {violating}. "
                    "Routes under /admin/* must only allow admin or operator roles."
                )

    # ── Rule 7: core database entities present ───────────────────────────────

    def _check_database(self, bp: BotBlueprint, errors: list[str]) -> None:
        existing = {e.name for e in bp.database.entities}
        missing = sorted(CORE_ENTITIES - existing)
        if missing:
            errors.append(
                f"Database is missing required core entities: {missing}. "
                "These tables are mandatory for RBAC, audit, bot idempotency, "
                "and Bale account mapping."
            )

    # ── Rules 5 & 6: auth without roles; admin-only without audit ────────────

    def _check_api_endpoints(self, bp: BotBlueprint, errors: list[str]) -> None:
        admin_role_keys = {r.key for r in bp.roles if r.is_admin}

        for ep in bp.api.endpoints:
            if ep.auth_required and not ep.allowed_roles:
                errors.append(
                    f"Endpoint '{ep.name}' ({ep.method} {ep.path}) has "
                    "auth_required=true but no allowed_roles. "
                    "Every protected endpoint must declare at least one allowed role."
                )

            if not ep.allowed_roles or not admin_role_keys:
                continue
            is_admin_only = all(role in admin_role_keys for role in ep.allowed_roles)
            if is_admin_only and not ep.audit_required:
                errors.append(
                    f"Endpoint '{ep.name}' ({ep.method} {ep.path}) is admin-only "
                    "but audit_required=false. Admin operations must be audited."
                )

    # ── Rule 9: known template profile and modules ───────────────────────────

    def _check_generation(self, bp: BotBlueprint, errors: list[str]) -> None:
        if bp.generation.template_profile not in KNOWN_TEMPLATE_PROFILES:
            errors.append(
                f"generation.template_profile '{bp.generation.template_profile}' is "
                f"not recognised. Known profiles: {sorted(KNOWN_TEMPLATE_PROFILES)}."
            )

        unknown = sorted(set(bp.generation.enabled_modules) - KNOWN_MODULES)
        if unknown:
            errors.append(
                f"generation.enabled_modules contains unknown modules: {unknown}. "
                f"Known modules: {sorted(KNOWN_MODULES)}."
            )
