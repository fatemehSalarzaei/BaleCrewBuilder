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
    _extract_headings,
    _heading_to_safe_key,
    _derive_flows_from_headings,
    _derive_test_stubs_from_headings,
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


def test_placeholder_blueprint_is_deterministic_with_document() -> None:
    content = "# Section One\n\nSome text.\n\n## Section Two\n\nMore text."
    bp1 = build_placeholder_blueprint("Stable", "Doc Title", content)
    bp2 = build_placeholder_blueprint("Stable", "Doc Title", content)
    assert bp1.model_dump() == bp2.model_dump()


# ── Document-derived content unit tests ──────────────────────────────────────


def test_extract_headings_returns_h1_and_h2() -> None:
    content = "# First\n\nParagraph.\n\n## Second\n\n### Third"
    assert _extract_headings(content) == ["First", "Second", "Third"]


def test_extract_headings_ignores_non_heading_lines() -> None:
    content = "Normal line\n# Heading\nAnother normal line"
    assert _extract_headings(content) == ["Heading"]


def test_extract_headings_empty_content_returns_empty() -> None:
    assert _extract_headings("") == []


def test_heading_to_safe_key_produces_valid_identifier() -> None:
    import re
    for heading in ["User Management", "Resource Tracking", "123 Numbers", "!Special chars!"]:
        key = _heading_to_safe_key(heading)
        assert re.match(r"^[a-z_][a-z0-9_]*$", key), (
            f"'{heading}' produced invalid key: '{key}'"
        )


def test_heading_to_safe_key_lowercases_and_replaces_spaces() -> None:
    assert _heading_to_safe_key("User Management") == "user_management"


def test_derive_flows_produces_one_flow_per_unique_heading() -> None:
    flows = _derive_flows_from_headings(["Feature A", "Feature B", "Feature A"])
    assert len(flows) == 2
    keys = {f.key for f in flows}
    assert len(keys) == 2


def test_derive_flows_caps_at_five() -> None:
    headings = [f"Section {i}" for i in range(10)]
    flows = _derive_flows_from_headings(headings)
    assert len(flows) == 5


def test_derive_flows_flow_keys_are_valid() -> None:
    import re
    flows = _derive_flows_from_headings(["User Setup", "Data Import", "Reporting"])
    for flow in flows:
        assert re.match(r"^[a-z_][a-z0-9_]*$", flow.key), (
            f"Invalid flow key: '{flow.key}'"
        )


def test_derive_test_stubs_caps_at_five() -> None:
    headings = [f"Heading {i}" for i in range(10)]
    stubs = _derive_test_stubs_from_headings(headings)
    assert len(stubs) == 5


def test_derive_test_stubs_deduplicates() -> None:
    stubs = _derive_test_stubs_from_headings(["User", "User", "Admin"])
    assert len(stubs) == 2


def test_placeholder_blueprint_with_document_title_in_role_descriptions() -> None:
    bp = build_placeholder_blueprint("My Platform", "Design Spec v1", "# Intro\n\nText.")
    for role in bp.roles:
        assert "Design Spec v1" in role.description, (
            f"Document title not found in role '{role.key}' description: {role.description!r}"
        )


def test_placeholder_blueprint_with_document_headings_creates_flows() -> None:
    content = "# User Management\n\n## Resource Tracking\n\nDetails."
    bp = build_placeholder_blueprint("Test", "Spec", content)
    assert len(bp.flows) == 2
    flow_names = {f.name for f in bp.flows}
    assert "User Management" in flow_names
    assert "Resource Tracking" in flow_names


def test_placeholder_blueprint_with_document_headings_creates_test_stubs() -> None:
    content = "# Feature A\n\n# Feature B\n"
    bp = build_placeholder_blueprint("Test", "Spec", content)
    stubs = bp.testing.test_stubs
    assert any("feature_a" in s for s in stubs), f"Expected feature_a stub in {stubs}"
    assert any("feature_b" in s for s in stubs), f"Expected feature_b stub in {stubs}"


def test_placeholder_blueprint_empty_document_content_still_valid() -> None:
    bp = build_placeholder_blueprint("Test Project", "Empty Spec", "")
    result = BlueprintValidationService().validate(bp)
    assert result.is_valid, f"Blueprint with empty content failed: {result.errors}"
    assert bp.flows == []
    assert bp.testing.test_stubs == []


def test_placeholder_blueprint_no_document_args_same_as_before() -> None:
    """No-arg backward-compatible call still produces a valid, deterministic blueprint."""
    bp = build_placeholder_blueprint("Backward Compat")
    assert bp.roles[0].description != ""  # description is now always set
    result = BlueprintValidationService().validate(bp)
    assert result.is_valid


def test_placeholder_blueprint_different_content_produces_different_output() -> None:
    bp_a = build_placeholder_blueprint(
        "Platform", "Spec A", "# User Management\n\nDetails."
    )
    bp_b = build_placeholder_blueprint(
        "Platform", "Spec B", "# Resource Tracking\n\nDetails."
    )
    assert bp_a.model_dump() != bp_b.model_dump(), (
        "Different document content must produce different Blueprint placeholders"
    )


def test_placeholder_blueprint_different_title_produces_different_roles() -> None:
    bp_a = build_placeholder_blueprint("Platform", "Alpha Spec", "")
    bp_b = build_placeholder_blueprint("Platform", "Beta Spec", "")
    role_descs_a = [r.description for r in bp_a.roles]
    role_descs_b = [r.description for r in bp_b.roles]
    assert role_descs_a != role_descs_b, (
        "Different document titles must produce different role descriptions"
    )


def test_placeholder_blueprint_with_document_still_passes_validation() -> None:
    content = "# Authentication\n\n## User Roles\n\n## API Design\n\nDetails."
    bp = build_placeholder_blueprint("Auth Platform", "Auth Spec", content)
    result = BlueprintValidationService().validate(bp)
    assert result.is_valid, f"Document-derived Blueprint failed validation: {result.errors}"


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


# ── Document-derived Blueprint content (integration) ─────────────────────────


async def _create_document_with_content(
    client: AsyncClient, project_id: str, title: str, content: str
) -> str:
    resp = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": title, "content": content},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_generate_blueprint_includes_document_title_in_role_descriptions(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """The generated placeholder Blueprint must embed the source document title."""
    project_id = await _create_project(client, "Doc Derived Test")
    await _create_document_with_content(
        client, project_id,
        title="Platform Design Spec",
        content="# Overview\n\nThis platform manages resources.",
    )
    await _fast_track_to_document_approved(project_service, project_id)

    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 201

    roles = resp.json()["blueprint"]["roles"]
    for role in roles:
        assert "Platform Design Spec" in role["description"], (
            f"Document title not found in role '{role['key']}' description: {role['description']!r}"
        )


async def test_generate_blueprint_includes_document_headings_as_flows(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Section headings from the document appear as suggested flows in the Blueprint."""
    project_id = await _create_project(client, "Flow Derive Test")
    await _create_document_with_content(
        client, project_id,
        title="Feature Spec",
        content="# User Registration\n\n## Resource Management\n\nDetails here.",
    )
    await _fast_track_to_document_approved(project_service, project_id)

    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 201

    flows = resp.json()["blueprint"]["flows"]
    flow_names = {f["name"] for f in flows}
    assert "User Registration" in flow_names, (
        f"Expected 'User Registration' flow from document heading; got: {flow_names}"
    )
    assert "Resource Management" in flow_names, (
        f"Expected 'Resource Management' flow from document heading; got: {flow_names}"
    )


async def test_generate_blueprint_includes_document_headings_as_test_stubs(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client, "Stub Derive Test")
    await _create_document_with_content(
        client, project_id,
        title="Stub Spec",
        content="# Authentication\n\n# Authorization\n\nDetails.",
    )
    await _fast_track_to_document_approved(project_service, project_id)

    resp = await client.post(f"/projects/{project_id}/blueprint/generate")
    assert resp.status_code == 201

    stubs = resp.json()["blueprint"]["testing"]["test_stubs"]
    assert any("authentication" in s for s in stubs), (
        f"Expected authentication test stub; got: {stubs}"
    )


async def test_generate_blueprint_different_docs_produce_different_blueprints(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Different approved document contents must produce meaningfully different Blueprint placeholders."""
    # Project A: analytics platform
    pid_a = await _create_project(client, "Analytics Platform")
    await _create_document_with_content(
        client, pid_a,
        title="Analytics Spec",
        content="# Dashboard Analytics\n\n## Report Generation\n\nGenerate reports.",
    )
    await _fast_track_to_document_approved(project_service, pid_a)
    resp_a = await client.post(f"/projects/{pid_a}/blueprint/generate")
    assert resp_a.status_code == 201

    # Project B: booking platform
    pid_b = await _create_project(client, "Booking Platform")
    await _create_document_with_content(
        client, pid_b,
        title="Booking Spec",
        content="# Reservation Flow\n\n## Calendar Integration\n\nManage bookings.",
    )
    await _fast_track_to_document_approved(project_service, pid_b)
    resp_b = await client.post(f"/projects/{pid_b}/blueprint/generate")
    assert resp_b.status_code == 201

    bp_a = resp_a.json()["blueprint"]
    bp_b = resp_b.json()["blueprint"]

    # Role descriptions must differ (document title embedded)
    roles_a = {r["key"]: r["description"] for r in bp_a["roles"]}
    roles_b = {r["key"]: r["description"] for r in bp_b["roles"]}
    assert roles_a != roles_b, "Role descriptions must differ when document titles differ"

    # Flows must differ (section headings differ)
    flow_names_a = {f["name"] for f in bp_a["flows"]}
    flow_names_b = {f["name"] for f in bp_b["flows"]}
    assert flow_names_a != flow_names_b, (
        "Flows must differ when document section headings differ"
    )


async def test_generate_blueprint_document_derived_content_passes_validation(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Blueprint generated from document with multiple headings must pass Blueprint validation."""
    project_id = await _create_project(client, "Complex Platform")
    await _create_document_with_content(
        client, project_id,
        title="Complex Platform Spec",
        content=(
            "# User Authentication\n\n## Role Management\n\n"
            "## API Design\n\n# Deployment Notes\n\nExtra content."
        ),
    )
    await _fast_track_to_document_approved(project_service, project_id)
    await client.post(f"/projects/{project_id}/blueprint/generate")

    resp = await client.post(f"/projects/{project_id}/blueprint/validate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True, (
        f"Document-derived Blueprint failed validation: {data['errors']}"
    )
