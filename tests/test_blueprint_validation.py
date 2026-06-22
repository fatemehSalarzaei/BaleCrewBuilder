"""
Tests for Blueprint schema parsing, validation service rules, and blueprint API endpoints.
"""

import copy
from pathlib import Path
from uuid import UUID

import yaml
import pytest
from httpx import AsyncClient

from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectStatus
from app.services.blueprint_service import BlueprintService, BlueprintSubmissionNotAllowedError
from app.services.project_service import ProjectService
from app.services.validation_service import BlueprintValidationService

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


# ── helpers ──────────────────────────────────────────────────────────────────


def _load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return yaml.safe_load(f)


def _parse(data: dict) -> BotBlueprint:
    return BotBlueprint.model_validate(data)


def _validate(filename: str):
    return BlueprintValidationService().validate(_parse(_load(filename)))


def _fast_track_to_document_approved(ps: ProjectService, project_id: UUID) -> None:
    ps.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    ps.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)
    ps.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    ps.transition(project_id, ProjectStatus.DOCUMENT_APPROVED)


# ── YAML fixture parsing ──────────────────────────────────────────────────────


def test_valid_multi_bot_yaml_parses_without_error():
    bp = _parse(_load("valid_multi_bot.yaml"))
    assert bp.project.name == "Resource Platform"
    assert len(bp.bots) == 2
    assert bp.bots[0].key == "user_bot"
    assert bp.bots[1].key == "admin_bot"
    assert bp.miniapp.enabled is True


def test_invalid_shared_webhook_yaml_parses_without_error():
    bp = _parse(_load("invalid_shared_webhook.yaml"))
    assert len(bp.bots) == 2
    assert bp.bots[0].token_env == bp.bots[1].token_env


def test_invalid_admin_route_yaml_parses_without_error():
    bp = _parse(_load("invalid_admin_route_roles.yaml"))
    admin_route = next(r for r in bp.miniapp.routes if r.path.startswith("/admin/"))
    assert "member" in admin_route.allowed_roles


# ── Valid fixture: passes validation ─────────────────────────────────────────


def test_valid_multi_bot_blueprint_passes_validation():
    result = _validate("valid_multi_bot.yaml")
    assert result.is_valid, f"Expected valid blueprint but got errors: {result.errors}"
    assert result.errors == []


# ── Rule 1: workflow document_status ─────────────────────────────────────────


def test_wrong_document_status_fails():
    data = _load("valid_multi_bot.yaml")
    data["workflow"]["document_status"] = "DRAFT_CREATED"
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("DOCUMENT_APPROVED" in e for e in result.errors)
    assert any("DRAFT_CREATED" in e for e in result.errors)


def test_document_generating_status_fails():
    data = _load("valid_multi_bot.yaml")
    data["workflow"]["document_status"] = "DOCUMENT_GENERATING"
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("DOCUMENT_APPROVED" in e for e in result.errors)


# ── Rule 2: at least one bot ─────────────────────────────────────────────────


def test_no_bots_fails():
    data = _load("valid_multi_bot.yaml")
    data["bots"] = []
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("at least one bot" in e for e in result.errors)


# ── Rule 3: shared token_env / webhook_path ───────────────────────────────────


def test_shared_token_env_fails():
    result = _validate("invalid_shared_webhook.yaml")
    assert not result.is_valid
    assert any("token_env" in e for e in result.errors)


def test_shared_webhook_path_fails():
    result = _validate("invalid_shared_webhook.yaml")
    assert not result.is_valid
    assert any("webhook_path" in e for e in result.errors)


def test_shared_webhook_error_names_both_bots():
    result = _validate("invalid_shared_webhook.yaml")
    webhook_errors = [e for e in result.errors if "webhook_path" in e]
    assert len(webhook_errors) == 1
    assert "user_bot" in webhook_errors[0]
    assert "admin_bot" in webhook_errors[0]


# ── Rule 4: admin route allows user role ──────────────────────────────────────


def test_admin_route_allowing_user_role_fails():
    result = _validate("invalid_admin_route_roles.yaml")
    assert not result.is_valid
    assert any("admin route" in e.lower() for e in result.errors)


def test_admin_route_error_names_the_route_and_role():
    result = _validate("invalid_admin_route_roles.yaml")
    admin_errors = [e for e in result.errors if "/admin/" in e]
    assert len(admin_errors) == 1
    assert "member" in admin_errors[0]


def test_user_route_allowing_user_role_is_valid():
    data = _load("valid_multi_bot.yaml")
    result = BlueprintValidationService().validate(_parse(data))
    assert result.is_valid


# ── Rule 5: auth_required without allowed_roles ───────────────────────────────


def test_protected_endpoint_without_roles_fails():
    data = _load("valid_multi_bot.yaml")
    data["api"]["endpoints"].append({
        "name": "secret_endpoint",
        "method": "GET",
        "path": "/api/v1/secret",
        "auth_required": True,
        "allowed_roles": [],
        "request_schema": None,
        "response_schema": None,
        "service_method": "secret_service.get",
        "audit_required": False,
    })
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("secret_endpoint" in e for e in result.errors)
    assert any("allowed_roles" in e for e in result.errors)


def test_public_endpoint_without_roles_is_valid():
    data = _load("valid_multi_bot.yaml")
    data["api"]["endpoints"].append({
        "name": "public_endpoint",
        "method": "GET",
        "path": "/public",
        "auth_required": False,
        "allowed_roles": [],
        "request_schema": None,
        "response_schema": "PublicResponse",
        "service_method": "public_service.get",
        "audit_required": False,
    })
    result = BlueprintValidationService().validate(_parse(data))
    assert result.is_valid


# ── Rule 6: admin-only endpoint without audit ────────────────────────────────


def test_admin_only_endpoint_without_audit_fails():
    data = _load("valid_multi_bot.yaml")
    data["api"]["endpoints"].append({
        "name": "admin_action_no_audit",
        "method": "POST",
        "path": "/api/v1/admin/action",
        "auth_required": True,
        "allowed_roles": ["admin"],
        "request_schema": "ActionRequest",
        "response_schema": None,
        "service_method": "admin_service.perform_action",
        "audit_required": False,  # ← missing audit (INVALID)
    })
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("admin_action_no_audit" in e for e in result.errors)
    assert any("audit_required" in e for e in result.errors)


def test_mixed_role_endpoint_without_audit_is_valid():
    """Endpoints accessible by both user and admin roles do not require audit."""
    data = _load("valid_multi_bot.yaml")
    data["api"]["endpoints"].append({
        "name": "shared_read",
        "method": "GET",
        "path": "/api/v1/items",
        "auth_required": True,
        "allowed_roles": ["member", "admin"],
        "request_schema": None,
        "response_schema": "ItemList",
        "service_method": "item_service.list",
        "audit_required": False,
    })
    result = BlueprintValidationService().validate(_parse(data))
    assert result.is_valid


# ── Rule 7: missing core entities ────────────────────────────────────────────


def test_missing_core_entities_fails():
    data = _load("valid_multi_bot.yaml")
    data["database"]["entities"] = [
        e for e in data["database"]["entities"] if e["name"] not in ("audit_logs", "processed_updates")
    ]
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    errors_text = " ".join(result.errors)
    assert "audit_logs" in errors_text
    assert "processed_updates" in errors_text


def test_empty_database_entities_fails():
    data = _load("valid_multi_bot.yaml")
    data["database"]["entities"] = []
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("core entities" in e for e in result.errors)


# ── Rule 8: miniapp enabled without auth_endpoint ────────────────────────────


def test_miniapp_enabled_without_auth_endpoint_fails():
    data = _load("valid_multi_bot.yaml")
    data["miniapp"]["auth_endpoint"] = None
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("auth_endpoint" in e for e in result.errors)


def test_miniapp_disabled_without_auth_endpoint_is_valid():
    data = _load("valid_multi_bot.yaml")
    data["miniapp"]["enabled"] = False
    data["miniapp"]["auth_endpoint"] = None
    result = BlueprintValidationService().validate(_parse(data))
    assert result.is_valid


# ── Rule 9: unknown template profile / modules ────────────────────────────────


def test_unknown_template_profile_fails():
    data = _load("valid_multi_bot.yaml")
    data["generation"]["template_profile"] = "unknown_profile_v99"
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("unknown_profile_v99" in e for e in result.errors)


def test_unknown_module_fails():
    data = _load("valid_multi_bot.yaml")
    data["generation"]["enabled_modules"].append("nonexistent_module")
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert any("nonexistent_module" in e for e in result.errors)


def test_multiple_unknown_modules_all_reported():
    data = _load("valid_multi_bot.yaml")
    data["generation"]["enabled_modules"] += ["mod_a", "mod_b"]
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    errors_text = " ".join(result.errors)
    assert "mod_a" in errors_text
    assert "mod_b" in errors_text


# ── Multiple errors reported together ─────────────────────────────────────────


def test_multiple_violations_reported_in_single_pass():
    data = _load("valid_multi_bot.yaml")
    data["workflow"]["document_status"] = "DRAFT_CREATED"
    data["database"]["entities"] = []
    data["miniapp"]["auth_endpoint"] = None
    result = BlueprintValidationService().validate(_parse(data))
    assert not result.is_valid
    assert len(result.errors) >= 3


# ── BlueprintService: store and validate via service layer ────────────────────


def test_blueprint_service_stores_blueprint(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    from app.schemas.project import ProjectCreate
    project = project_service.create(ProjectCreate(name="BP Store Test"))
    _fast_track_to_document_approved(project_service, project.id)

    bp = _parse(_load("valid_multi_bot.yaml"))
    result = blueprint_service.store(project.id, bp)

    assert result.project.name == "Resource Platform"
    project_after = project_service.get(project.id)
    assert project_after.status == ProjectStatus.BLUEPRINT_GENERATED


def test_blueprint_service_validates_valid_blueprint(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    from app.schemas.project import ProjectCreate
    project = project_service.create(ProjectCreate(name="BP Validate Test"))
    _fast_track_to_document_approved(project_service, project.id)

    blueprint_service.store(project.id, _parse(_load("valid_multi_bot.yaml")))
    result = blueprint_service.validate(project.id)

    assert result.is_valid
    assert result.errors == []
    assert project_service.get(project.id).status == ProjectStatus.BLUEPRINT_VALIDATED


def test_blueprint_service_validates_invalid_blueprint_marks_failed(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    from app.schemas.project import ProjectCreate
    project = project_service.create(ProjectCreate(name="BP Fail Test"))
    _fast_track_to_document_approved(project_service, project.id)

    blueprint_service.store(project.id, _parse(_load("invalid_shared_webhook.yaml")))
    result = blueprint_service.validate(project.id)

    assert not result.is_valid
    assert project_service.get(project.id).status == ProjectStatus.BLUEPRINT_VALIDATION_FAILED


def test_blueprint_service_rejects_submission_on_wrong_status(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    from app.schemas.project import ProjectCreate
    project = project_service.create(ProjectCreate(name="Wrong Status"))
    # Project is in DRAFT_CREATED — not yet DOCUMENT_APPROVED

    with pytest.raises(BlueprintSubmissionNotAllowedError):
        blueprint_service.store(project.id, _parse(_load("valid_multi_bot.yaml")))


def test_blueprint_resubmission_after_failure(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    from app.schemas.project import ProjectCreate
    project = project_service.create(ProjectCreate(name="Retry Test"))
    _fast_track_to_document_approved(project_service, project.id)

    blueprint_service.store(project.id, _parse(_load("invalid_shared_webhook.yaml")))
    blueprint_service.validate(project.id)
    assert project_service.get(project.id).status == ProjectStatus.BLUEPRINT_VALIDATION_FAILED

    blueprint_service.store(project.id, _parse(_load("valid_multi_bot.yaml")))
    result = blueprint_service.validate(project.id)

    assert result.is_valid
    assert project_service.get(project.id).status == ProjectStatus.BLUEPRINT_VALIDATED


# ── Blueprint API endpoints ───────────────────────────────────────────────────


async def _create_approved_project(client: AsyncClient, ps: ProjectService, name: str = "API BP Test") -> str:
    resp = await client.post("/projects", json={"name": name})
    pid = UUID(resp.json()["id"])
    _fast_track_to_document_approved(ps, pid)
    return str(pid)


async def test_api_store_blueprint_returns_201(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service)
    bp_data = _load("valid_multi_bot.yaml")

    response = await client.post(f"/projects/{project_id}/blueprint", json=bp_data)

    assert response.status_code == 201
    assert response.json()["project"]["name"] == "Resource Platform"


async def test_api_get_blueprint_returns_stored(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service)
    bp_data = _load("valid_multi_bot.yaml")
    await client.post(f"/projects/{project_id}/blueprint", json=bp_data)

    response = await client.get(f"/projects/{project_id}/blueprint")

    assert response.status_code == 200
    assert response.json()["blueprint_version"] == "1.0"


async def test_api_get_blueprint_not_found_returns_404(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="No BP")

    response = await client.get(f"/projects/{project_id}/blueprint")

    assert response.status_code == 404


async def test_api_validate_valid_blueprint_returns_is_valid_true(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="Validate OK")
    await client.post(f"/projects/{project_id}/blueprint", json=_load("valid_multi_bot.yaml"))

    response = await client.post(f"/projects/{project_id}/blueprint/validate")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["errors"] == []


async def test_api_validate_invalid_blueprint_returns_errors(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="Validate Fail")
    await client.post(f"/projects/{project_id}/blueprint", json=_load("invalid_shared_webhook.yaml"))

    response = await client.post(f"/projects/{project_id}/blueprint/validate")

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert len(data["errors"]) > 0


async def test_api_validate_updates_project_status_to_validated(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="Status Update")
    await client.post(f"/projects/{project_id}/blueprint", json=_load("valid_multi_bot.yaml"))
    await client.post(f"/projects/{project_id}/blueprint/validate")

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "BLUEPRINT_VALIDATED"


async def test_api_validate_updates_project_status_to_validation_failed(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="Status Fail")
    await client.post(f"/projects/{project_id}/blueprint", json=_load("invalid_shared_webhook.yaml"))
    await client.post(f"/projects/{project_id}/blueprint/validate")

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "BLUEPRINT_VALIDATION_FAILED"


async def test_api_store_blueprint_on_wrong_project_status_returns_409(
    client: AsyncClient,
) -> None:
    resp = await client.post("/projects", json={"name": "Not Approved"})
    project_id = resp.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/blueprint",
        json=_load("valid_multi_bot.yaml"),
    )

    assert response.status_code == 409


async def test_api_validate_without_blueprint_returns_404(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_approved_project(client, project_service, name="No BP Validate")

    response = await client.post(f"/projects/{project_id}/blueprint/validate")

    assert response.status_code == 404
