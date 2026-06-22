"""
Tests for GenerationGateService: Documentation First gate (R2) and Blueprint validation gate (R9).
"""
from pathlib import Path
from uuid import UUID

import yaml
import pytest
from httpx import AsyncClient

from app.schemas.blueprint import BotBlueprint
from app.schemas.project import ProjectCreate, ProjectStatus
from app.services.blueprint_service import BlueprintService
from app.services.generation_gate_service import GenerationBlockedError, GenerationGateService
from app.services.project_service import ProjectService

FIXTURES = Path(__file__).parent / "fixtures" / "blueprints"


def _load(filename: str) -> dict:
    with open(FIXTURES / filename) as f:
        return yaml.safe_load(f)


def _parse(data: dict) -> BotBlueprint:
    return BotBlueprint.model_validate(data)


def _load_valid_blueprint() -> BotBlueprint:
    return _parse(_load("valid_multi_bot.yaml"))


def _load_invalid_blueprint() -> BotBlueprint:
    return _parse(_load("invalid_shared_webhook.yaml"))


async def _fast_track_to_review(ps: ProjectService, project_id: UUID) -> None:
    await ps.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)


async def _fast_track_to_document_approved(ps: ProjectService, project_id: UUID) -> None:
    await _fast_track_to_review(ps, project_id)
    await ps.transition(project_id, ProjectStatus.DOCUMENT_APPROVED)


# ── Blueprint generation gate ─────────────────────────────────────────────────


async def test_blueprint_generation_blocked_in_draft_created(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Gate Draft"))
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_blueprint_generation_allowed(project.id)
    assert "DOCUMENT_APPROVED" in exc_info.value.reason
    assert "DRAFT_CREATED" in exc_info.value.reason


async def test_blueprint_generation_blocked_in_review_pending(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Gate Review"))
    await _fast_track_to_review(project_service, project.id)
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError):
        await gate.assert_blueprint_generation_allowed(project.id)


async def test_blueprint_generation_blocked_after_change_requested(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Gate Change"))
    await _fast_track_to_review(project_service, project.id)
    await project_service.transition(project.id, ProjectStatus.DOCUMENT_CHANGE_REQUESTED)
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError):
        await gate.assert_blueprint_generation_allowed(project.id)


async def test_blueprint_generation_permanently_blocked_after_rejection(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Rejected Project"))
    await _fast_track_to_review(project_service, project.id)
    await project_service.transition(project.id, ProjectStatus.DOCUMENT_REJECTED)
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_blueprint_generation_allowed(project.id)
    assert "rejected" in exc_info.value.reason.lower()


async def test_blueprint_generation_allowed_after_approval(
    client: AsyncClient, project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    resp = await client.post("/projects", json={"name": "Approved Project"})
    project_id = UUID(resp.json()["id"])
    await _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    await gate.assert_blueprint_generation_allowed(project_id)  # must not raise


# ── Implementation generation gate — status checks ───────────────────────────


async def test_implementation_generation_permanently_blocked_after_rejection(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Rejected Impl"))
    await _fast_track_to_review(project_service, project.id)
    await project_service.transition(project.id, ProjectStatus.DOCUMENT_REJECTED)
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    assert "rejected" in exc_info.value.reason.lower()


async def test_rejected_project_cannot_transition_further(
    project_service: ProjectService,
) -> None:
    from app.services.project_service import IllegalStatusTransitionError

    project = await project_service.create(ProjectCreate(name="Terminal Reject"))
    await _fast_track_to_review(project_service, project.id)
    await project_service.transition(project.id, ProjectStatus.DOCUMENT_REJECTED)

    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(project.id, ProjectStatus.DOCUMENT_GENERATING)


async def test_implementation_blocked_when_only_draft_created(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Impl Gate Draft"))
    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    assert "BLUEPRINT_VALIDATED" in exc_info.value.reason


async def test_implementation_blocked_when_only_document_approved(
    client: AsyncClient, project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    resp = await client.post("/projects", json={"name": "Only Approved"})
    project_id = UUID(resp.json()["id"])
    await _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project_id)
    assert "BLUEPRINT_VALIDATED" in exc_info.value.reason


async def test_implementation_blocked_when_blueprint_validation_failed(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Blueprint Failed"))
    await _fast_track_to_review(project_service, project.id)
    await project_service.transition(project.id, ProjectStatus.DOCUMENT_APPROVED)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATION_FAILED)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError):
        await gate.assert_implementation_generation_allowed(project.id)


# ── Implementation generation gate — Blueprint and validation checks ──────────


async def test_implementation_allowed_at_blueprint_validated(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    project = await project_service.create(ProjectCreate(name="Blueprint Validated"))
    await _fast_track_to_document_approved(project_service, project.id)
    await blueprint_service.store(project.id, _load_valid_blueprint())
    await blueprint_service.validate(project.id)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    await gate.assert_implementation_generation_allowed(project.id)  # must not raise


async def test_change_request_after_approval_invalidates_blueprint_gate(
    client: AsyncClient, project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """Blueprint gate blocks after implementation fails — status no longer BLUEPRINT_VALIDATED."""
    resp = await client.post("/projects", json={"name": "Re-review"})
    project_id = UUID(resp.json()["id"])
    await _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})
    await blueprint_service.store(project_id, _load_valid_blueprint())
    await blueprint_service.validate(project_id)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    await gate.assert_implementation_generation_allowed(project_id)  # must not raise

    await project_service.transition(project_id, ProjectStatus.IMPLEMENTATION_GENERATING)
    await project_service.transition(project_id, ProjectStatus.IMPLEMENTATION_FAILED)

    with pytest.raises(GenerationBlockedError):
        await gate.assert_implementation_generation_allowed(project_id)


# ── Phase 5 gate-tightening: Blueprint and validation result checks ───────────


async def test_implementation_blocked_when_no_blueprint_stored_despite_validated_status(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """Status is BLUEPRINT_VALIDATED but no Blueprint row in DB → gate must block."""
    project = await project_service.create(ProjectCreate(name="Status Only"))
    await _fast_track_to_document_approved(project_service, project.id)
    # Bypass BlueprintService: manually advance status without storing a Blueprint
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATED)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATED)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    assert "blueprint" in exc_info.value.reason.lower()


async def test_implementation_blocked_when_blueprint_stored_but_no_validation_result(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """Blueprint stored but validate() never called; status bypassed to BLUEPRINT_VALIDATED → must block."""
    project = await project_service.create(ProjectCreate(name="No Validation"))
    await _fast_track_to_document_approved(project_service, project.id)
    # store() transitions DOCUMENT_APPROVED → BLUEPRINT_GENERATING → BLUEPRINT_GENERATED
    await blueprint_service.store(project.id, _load_valid_blueprint())
    # Bypass BlueprintService.validate(): manually jump to BLUEPRINT_VALIDATED
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATED)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    assert "validation" in exc_info.value.reason.lower()


async def test_implementation_blocked_when_blueprint_validation_result_is_invalid(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """Blueprint exists + is_valid=False validation result + status bypassed to BLUEPRINT_VALIDATED → must block."""
    project = await project_service.create(ProjectCreate(name="Invalid Result"))
    await _fast_track_to_document_approved(project_service, project.id)
    # Store an invalid blueprint and validate — creates is_valid=False record, status → BLUEPRINT_VALIDATION_FAILED
    await blueprint_service.store(project.id, _load_invalid_blueprint())
    await blueprint_service.validate(project.id)
    # Manually advance status to BLUEPRINT_VALIDATED without replacing the failing validation result
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATED)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATED)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    reason = exc_info.value.reason.lower()
    assert "error" in reason or "invalid" in reason or "failed" in reason


async def test_implementation_blocked_when_document_approved_no_blueprint_stored(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """Status DOCUMENT_APPROVED with no Blueprint stored → blocked at status check."""
    project = await project_service.create(ProjectCreate(name="Approved No Blueprint"))
    await _fast_track_to_document_approved(project_service, project.id)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        await gate.assert_implementation_generation_allowed(project.id)
    assert "BLUEPRINT_VALIDATED" in exc_info.value.reason


async def test_implementation_allowed_after_revalidation_success(
    project_service: ProjectService, blueprint_service: BlueprintService
) -> None:
    """After initial validation failure, re-storing a valid Blueprint and re-validating → gate allows."""
    project = await project_service.create(ProjectCreate(name="Revalidation"))
    await _fast_track_to_document_approved(project_service, project.id)

    # First attempt: store invalid blueprint and validate → BLUEPRINT_VALIDATION_FAILED
    await blueprint_service.store(project.id, _load_invalid_blueprint())
    await blueprint_service.validate(project.id)

    # Second attempt: re-store valid blueprint (allowed from BLUEPRINT_VALIDATION_FAILED) and re-validate
    await blueprint_service.store(project.id, _load_valid_blueprint())
    await blueprint_service.validate(project.id)

    gate = GenerationGateService(project_service=project_service, blueprint_service=blueprint_service)
    await gate.assert_implementation_generation_allowed(project.id)  # must not raise


# ── ProjectStatusService eligibility helpers ──────────────────────────────────


async def test_project_status_service_eligibility_helpers(
    project_service: ProjectService,
) -> None:
    from app.services.project_status_service import ProjectStatusService

    project = await project_service.create(ProjectCreate(name="Status Helpers"))
    svc = ProjectStatusService(project_service=project_service)

    assert not await svc.is_document_review_eligible(project.id)
    assert not await svc.is_blueprint_generation_eligible(project.id)
    assert not await svc.is_implementation_eligible(project.id)

    await _fast_track_to_review(project_service, project.id)
    assert await svc.is_document_review_eligible(project.id)
    assert not await svc.is_blueprint_generation_eligible(project.id)

    await project_service.transition(project.id, ProjectStatus.DOCUMENT_APPROVED)
    assert not await svc.is_document_review_eligible(project.id)
    assert await svc.is_blueprint_generation_eligible(project.id)
    assert not await svc.is_implementation_eligible(project.id)

    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATED)
    await project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATED)
    assert await svc.is_implementation_eligible(project.id)
