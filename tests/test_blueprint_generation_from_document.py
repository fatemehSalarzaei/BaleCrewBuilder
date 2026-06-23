"""Tests for Phase 3: Blueprint placeholder generation from approved documents.

Covers:
- Gate: cannot generate before DOCUMENT_APPROVED
- Gate: cannot generate without a stored document
- Happy path: generate → store → BLUEPRINT_GENERATED
- Blueprint is retrievable after generation
- Generated Blueprint passes validation (BLUEPRINT_VALIDATED)
- Implementation generation still blocked until validation passes
- Implementation generation allowed after validation passes
- Placeholder determinism: same project name → same slug
- valid_multi_bot.yaml fixture still passes validation
- Invalid YAML fixtures return actionable errors
"""
import pytest
import yaml
from pathlib import Path
from uuid import UUID

from httpx import AsyncClient

from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectStatus
from app.services.blueprint_service import (
    BlueprintService,
    build_placeholder_blueprint,
    _to_slug,
)
from app.services.project_service import ProjectService
from app.services.validation_service import BlueprintValidationService

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_project(client: AsyncClient, name: str = "Blueprint Gen Test") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _fast_track_to_document_approved(ps: ProjectService, project_id: str) -> None:
    pid = UUID(project_id)
    await ps.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await ps.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    await ps.transition(pid, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    await ps.transition(pid, ProjectStatus.DOCUMENT_APPROVED)


async def _create_document(client: AsyncClient, project_id: str, title: str = "Spec") -> str:
    resp = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": title, "content": "# Requirements\n\nBuild a Bale bot platform."},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _approved_project_with_document(
    client: AsyncClient, project_service: ProjectService, name: str = "Approved Bot"
) -> tuple[str, str]:
    """Return (project_id, document_id) of a project at DOCUMENT_APPROVED with one document."""
    project_id = await _create_project(client, name)
    doc_id = await _create_document(client, project_id)
    await _fast_track_to_document_approved(project_service, project_id)
    return project_id, doc_id


async def _get_project_status(client: AsyncClient, project_id: str) -> str:
    return (await client.get(f"/projects/{project_id}")).json()["status"]


# ── build_placeholder_blueprint unit tests (no DB/HTTP) ──────────────────────


def test_placeholder_blueprint_parses_without_error() -> None:
    bp = build_placeholder_blueprint("My Test Project")
    assert isinstance(bp, BotBlueprint)


def test_placeholder_blueprint_project_name_is_set() -> None:
    bp = build_placeholder_blueprint("Reservation System")
    assert bp.project.name == "Reservation System"


def test_placeholder_blueprint_slug_is_valid() -> None:
    import re
    bp = build_placeholder_blueprint("My Cool Bot")
    assert re.match(r"^[a-z][a-z0-9-]*$", bp.project.slug)


def test_placeholder_blueprint_slug_derived_from_name() -> None:
    bp = build_placeholder_blueprint("Task Manager")
    assert bp.project.slug == "task-manager"


def test_to_slug_handles_spaces() -> None:
    assert _to_slug("Hello World") == "hello-world"


def test_to_slug_handles_uppercase() -> None:
    assert _to_slug("MyProject") == "myproject"


def test_to_slug_handles_leading_digit() -> None:
    slug = _to_slug("123 Bot")
    assert slug[0].isalpha()


def test_to_slug_collapses_multiple_separators() -> None:
    assert _to_slug("hello  --  world") == "hello-world"


def test_placeholder_blueprint_has_two_bots() -> None:
    bp = build_placeholder_blueprint("Test")
    assert len(bp.bots) == 2


def test_placeholder_blueprint_bots_have_separate_tokens() -> None:
    bp = build_placeholder_blueprint("Test")
    token_envs = [bot.token_env for bot in bp.bots]
    assert len(token_envs) == len(set(token_envs)), "bots must have unique token_env values"


def test_placeholder_blueprint_bots_have_separate_webhooks() -> None:
    bp = build_placeholder_blueprint("Test")
    webhooks = [bot.webhook_path for bot in bp.bots]
    assert len(webhooks) == len(set(webhooks)), "bots must have unique webhook paths"


def test_placeholder_blueprint_has_all_core_entities() -> None:
    from app.services.validation_service import CORE_ENTITIES
    bp = build_placeholder_blueprint("Test")
    entity_names = {e.name for e in bp.database.entities}
    assert CORE_ENTITIES <= entity_names


def test_placeholder_blueprint_document_status_is_approved() -> None:
    bp = build_placeholder_blueprint("Test")
    assert bp.workflow.document_status == "DOCUMENT_APPROVED"


def test_placeholder_blueprint_uses_known_template_profile() -> None:
    from app.services.validation_service import KNOWN_TEMPLATE_PROFILES
    bp = build_placeholder_blueprint("Test")
    assert bp.generation.template_profile in KNOWN_TEMPLATE_PROFILES


def test_placeholder_blueprint_passes_validation() -> None:
    bp = build_placeholder_blueprint("Resource Tracker")
    result = BlueprintValidationService().validate(bp)
    assert result.is_valid, f"Placeholder failed validation: {result.errors}"
    assert result.errors == []


def test_placeholder_blueprint_is_deterministic() -> None:
    bp1 = build_placeholder_blueprint("Stable Project")
    bp2 = build_placeholder_blueprint("Stable Project")
    assert bp1.model_dump() == bp2.model_dump()


# ── YAML fixture smoke tests ──────────────────────────────────────────────────


def test_valid_multi_bot_fixture_passes_validation() -> None:
    with open(FIXTURES / "valid_multi_bot.yaml") as f:
        data = yaml.safe_load(f)
    bp = BotBlueprint.model_validate(data)
    result = BlueprintValidationService().validate(bp)
    assert result.is_valid, f"valid_multi_bot.yaml should pass: {result.errors}"


def test_invalid_shared_webhook_returns_actionable_errors() -> None:
    with open(FIXTURES / "invalid_shared_webhook.yaml") as f:
        data = yaml.safe_load(f)
    bp = BotBlueprint.model_validate(data)
    result = BlueprintValidationService().validate(bp)
    assert not result.is_valid
    assert any("webhook" in e.lower() or "token" in e.lower() for e in result.errors)


def test_invalid_admin_route_roles_returns_actionable_errors() -> None:
    with open(FIXTURES / "invalid_admin_route_roles.yaml") as f:
        data = yaml.safe_load(f)
    bp = BotBlueprint.model_validate(data)
    result = BlueprintValidationService().validate(bp)
    assert not result.is_valid
    assert any("admin" in e.lower() for e in result.errors)


# ── Endpoint: gate enforcement ────────────────────────────────────────────────


async def test_generate_blocked_when_project_not_found(client: AsyncClient) -> None:
    resp = await client.post(
        "/projects/00000000-0000-0000-0000-000000000099/blueprint/generate"
    )
    assert resp.status_code == 404


async def test_generate_blocked_when_draft_created(client: AsyncClient) -> None:
    project_id = await _create_project(client, "Draft Only")
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 409
    assert "DOCUMENT_APPROVED" in resp.json()["detail"]


async def test_generate_blocked_when_document_drafted(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client, "Drafted Only")
    pid = UUID(project_id)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 409


async def test_generate_blocked_when_document_review_pending(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client, "Review Pending")
    pid = UUID(project_id)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 409


async def test_generate_blocked_when_no_document_stored(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Project is DOCUMENT_APPROVED but has no stored document."""
    project_id = await _create_project(client, "Approved No Doc")
    await _fast_track_to_document_approved(project_service, project_id)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 409
    assert "document" in resp.json()["detail"].lower()


# ── Endpoint: happy path ──────────────────────────────────────────────────────


async def test_generate_blueprint_returns_201(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 201


async def test_generate_blueprint_response_shape(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, doc_id = await _approved_project_with_document(client, project_service)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    data = resp.json()
    assert "blueprint" in data
    assert "source_document_id" in data
    assert "project_status" in data
    assert data["source_document_id"] == doc_id


async def test_generate_blueprint_source_document_id_is_latest(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client, "Latest Doc Test")
    _first_doc_id = await _create_document(client, project_id, "First Doc")
    second_doc_id = await _create_document(client, project_id, "Second Doc")
    await _fast_track_to_document_approved(project_service, project_id)

    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 201
    assert resp.json()["source_document_id"] == second_doc_id


async def test_generate_blueprint_transitions_to_blueprint_generated(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    await client.post(f"/projects/{project_id}/blueprint/generate")
    assert await _get_project_status(client, project_id) == "BLUEPRINT_GENERATED"


async def test_generated_blueprint_is_retrievable(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service, "Retrievable")
    await client.post(f"/projects/{project_id}/blueprint/generate")

    resp = await client.get(f"/projects/{project_id}/blueprint")
    assert resp.status_code == 200
    bp = resp.json()
    assert bp["project"]["name"] == "Retrievable"


async def test_generated_blueprint_project_name_matches_project(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(
        client, project_service, "Task Tracker Pro"
    )
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.json()["blueprint"]["project"]["name"] == "Task Tracker Pro"


async def test_generated_blueprint_has_two_bots(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    bots = resp.json()["blueprint"]["bots"]
    assert len(bots) == 2


async def test_generated_blueprint_response_status_is_blueprint_generated(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.json()["project_status"] == "BLUEPRINT_GENERATED"


# ── Validation of generated blueprint ────────────────────────────────────────


async def test_generated_blueprint_passes_validation_endpoint(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    await client.post(f"/projects/{project_id}/blueprint/generate")

    resp = await client.post(f"/projects/{project_id}/blueprint/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["errors"] == []


async def test_generated_blueprint_validate_transitions_to_blueprint_validated(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id, _ = await _approved_project_with_document(client, project_service)
    await client.post(f"/projects/{project_id}/blueprint/generate")
    await client.post(f"/projects/{project_id}/blueprint/validate")
    assert await _get_project_status(client, project_id) == "BLUEPRINT_VALIDATED"


# ── Implementation generation gate ───────────────────────────────────────────


async def test_implementation_blocked_after_generation_before_validation(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """After /blueprint/generate, status is BLUEPRINT_GENERATED.
    Implementation generation must still be blocked until validation passes."""
    project_id, _ = await _approved_project_with_document(client, project_service)
    await client.post(f"/projects/{project_id}/blueprint/generate")

    assert await _get_project_status(client, project_id) == "BLUEPRINT_GENERATED"
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.status_code == 409


async def test_implementation_allowed_after_generate_and_validate(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Full path: generate Blueprint → validate → implementation generation starts."""
    project_id, _ = await _approved_project_with_document(client, project_service)
    await client.post(f"/projects/{project_id}/blueprint/generate")
    await client.post(f"/projects/{project_id}/blueprint/validate")

    assert await _get_project_status(client, project_id) == "BLUEPRINT_VALIDATED"
    resp = await client.post(f"/projects/{project_id}/generate")
    assert resp.status_code == 201
