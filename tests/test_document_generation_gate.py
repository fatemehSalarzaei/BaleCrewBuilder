from uuid import UUID

import pytest
from httpx import AsyncClient

from app.schemas.project import ProjectCreate, ProjectStatus
from app.services.generation_gate_service import GenerationBlockedError, GenerationGateService
from app.services.project_service import ProjectService


def _fast_track_to_review(ps: ProjectService, project_id: UUID) -> None:
    ps.transition(project_id, ProjectStatus.DOCUMENT_GENERATING)
    ps.transition(project_id, ProjectStatus.DOCUMENT_DRAFTED)
    ps.transition(project_id, ProjectStatus.DOCUMENT_REVIEW_PENDING)


def _fast_track_to_blueprint_validated(ps: ProjectService, project_id: UUID) -> None:
    _fast_track_to_review(ps, project_id)
    ps.transition(project_id, ProjectStatus.DOCUMENT_APPROVED)
    ps.transition(project_id, ProjectStatus.BLUEPRINT_GENERATING)
    ps.transition(project_id, ProjectStatus.BLUEPRINT_GENERATED)
    ps.transition(project_id, ProjectStatus.BLUEPRINT_VALIDATED)


async def test_blueprint_generation_blocked_in_draft_created(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Gate Draft"))
    gate = GenerationGateService(project_service=project_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        gate.assert_blueprint_generation_allowed(project.id)
    assert "DOCUMENT_APPROVED" in exc_info.value.reason
    assert "DRAFT_CREATED" in exc_info.value.reason


async def test_blueprint_generation_blocked_in_review_pending(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Gate Review"))
    _fast_track_to_review(project_service, project.id)
    gate = GenerationGateService(project_service=project_service)

    with pytest.raises(GenerationBlockedError):
        gate.assert_blueprint_generation_allowed(project.id)


async def test_blueprint_generation_blocked_after_change_requested(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Gate Change"))
    _fast_track_to_review(project_service, project.id)
    project_service.transition(project.id, ProjectStatus.DOCUMENT_CHANGE_REQUESTED)
    gate = GenerationGateService(project_service=project_service)

    with pytest.raises(GenerationBlockedError):
        gate.assert_blueprint_generation_allowed(project.id)


async def test_blueprint_generation_allowed_after_approval(
    client: AsyncClient, project_service: ProjectService
) -> None:
    resp = await client.post("/projects", json={"name": "Approved Project"})
    project_id = UUID(resp.json()["id"])
    _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    gate = GenerationGateService(project_service=project_service)
    gate.assert_blueprint_generation_allowed(project_id)  # must not raise


async def test_implementation_blocked_when_only_draft_created(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Impl Gate Draft"))
    gate = GenerationGateService(project_service=project_service)

    with pytest.raises(GenerationBlockedError) as exc_info:
        gate.assert_implementation_generation_allowed(project.id)
    assert "BLUEPRINT_VALIDATED" in exc_info.value.reason


async def test_implementation_blocked_when_only_document_approved(
    client: AsyncClient, project_service: ProjectService
) -> None:
    resp = await client.post("/projects", json={"name": "Only Approved"})
    project_id = UUID(resp.json()["id"])
    _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    gate = GenerationGateService(project_service=project_service)
    with pytest.raises(GenerationBlockedError) as exc_info:
        gate.assert_implementation_generation_allowed(project_id)
    assert "BLUEPRINT_VALIDATED" in exc_info.value.reason


async def test_implementation_allowed_at_blueprint_validated(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Blueprint Validated"))
    _fast_track_to_blueprint_validated(project_service, project.id)
    gate = GenerationGateService(project_service=project_service)

    gate.assert_implementation_generation_allowed(project.id)  # must not raise


async def test_implementation_blocked_when_blueprint_validation_failed(
    project_service: ProjectService,
) -> None:
    project = project_service.create(ProjectCreate(name="Blueprint Failed"))
    _fast_track_to_review(project_service, project.id)
    project_service.transition(project.id, ProjectStatus.DOCUMENT_APPROVED)
    project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATION_FAILED)

    gate = GenerationGateService(project_service=project_service)
    with pytest.raises(GenerationBlockedError):
        gate.assert_implementation_generation_allowed(project.id)


async def test_change_request_after_approval_invalidates_blueprint_gate(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """If document goes back to DOCUMENT_CHANGE_REQUESTED, blueprint gate must block."""
    resp = await client.post("/projects", json={"name": "Re-review"})
    project_id = UUID(resp.json()["id"])
    _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATING)
    project_service.transition(project_id, ProjectStatus.BLUEPRINT_VALIDATION_FAILED)
    project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATING)
    project_service.transition(project_id, ProjectStatus.BLUEPRINT_GENERATED)
    project_service.transition(project_id, ProjectStatus.BLUEPRINT_VALIDATED)

    gate = GenerationGateService(project_service=project_service)
    gate.assert_implementation_generation_allowed(project_id)

    project_service.transition(project_id, ProjectStatus.IMPLEMENTATION_GENERATING)
    project_service.transition(project_id, ProjectStatus.IMPLEMENTATION_FAILED)

    with pytest.raises(GenerationBlockedError):
        gate.assert_implementation_generation_allowed(project_id)


async def test_project_status_service_eligibility_helpers(
    project_service: ProjectService,
) -> None:
    from app.services.project_status_service import ProjectStatusService

    project = project_service.create(ProjectCreate(name="Status Helpers"))
    svc = ProjectStatusService(project_service=project_service)

    assert not svc.is_document_review_eligible(project.id)
    assert not svc.is_blueprint_generation_eligible(project.id)
    assert not svc.is_implementation_eligible(project.id)

    _fast_track_to_review(project_service, project.id)
    assert svc.is_document_review_eligible(project.id)
    assert not svc.is_blueprint_generation_eligible(project.id)

    project_service.transition(project.id, ProjectStatus.DOCUMENT_APPROVED)
    assert not svc.is_document_review_eligible(project.id)
    assert svc.is_blueprint_generation_eligible(project.id)
    assert not svc.is_implementation_eligible(project.id)

    project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATING)
    project_service.transition(project.id, ProjectStatus.BLUEPRINT_GENERATED)
    project_service.transition(project.id, ProjectStatus.BLUEPRINT_VALIDATED)
    assert svc.is_implementation_eligible(project.id)
