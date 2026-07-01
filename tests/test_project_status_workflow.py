"""Tests for project status lifecycle: transitions, guards, and gate compliance.

Covers all allowed transitions in the official status machine (CLAUDE.md R2, R9),
representative illegal transitions, and the terminal DOCUMENT_REJECTED state.
"""
import pytest

from app.schemas.project import ProjectCreate, ProjectStatus
from app.services.project_service import (
    IllegalStatusTransitionError,
    ProjectNotFoundError,
    ProjectService,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create(ps: ProjectService, name: str = "Status Test") -> ProjectStatus:
    return await ps.create(ProjectCreate(name=name))


async def _advance(ps: ProjectService, project_id, *statuses: ProjectStatus) -> None:
    for s in statuses:
        await ps.transition(project_id, s)


# ── Initial state ─────────────────────────────────────────────────────────────


async def test_new_project_starts_as_draft_created(project_service: ProjectService) -> None:
    project = await _create(project_service)
    assert project.status == ProjectStatus.DRAFT_CREATED


async def test_get_project_returns_current_status(project_service: ProjectService) -> None:
    project = await _create(project_service)
    fetched = await project_service.get(project.id)
    assert fetched.status == ProjectStatus.DRAFT_CREATED


# ── Allowed transitions: Documentation phase ──────────────────────────────────


async def test_draft_created_to_document_generating(project_service: ProjectService) -> None:
    p = await _create(project_service, "Doc Gen")
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)
    assert updated.status == ProjectStatus.DOCUMENT_GENERATING


async def test_document_generating_to_document_drafted(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(project_service, p.id, ProjectStatus.DOCUMENT_GENERATING)
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_DRAFTED)
    assert updated.status == ProjectStatus.DOCUMENT_DRAFTED


async def test_document_generating_to_document_generation_failed(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(project_service, p.id, ProjectStatus.DOCUMENT_GENERATING)
    updated = await project_service.transition(
        p.id, ProjectStatus.DOCUMENT_GENERATION_FAILED
    )
    assert updated.status == ProjectStatus.DOCUMENT_GENERATION_FAILED


async def test_document_generation_failed_can_retry_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service,
        p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_GENERATION_FAILED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)
    assert updated.status == ProjectStatus.DOCUMENT_GENERATING


async def test_document_drafted_to_document_review_pending(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_REVIEW_PENDING)
    assert updated.status == ProjectStatus.DOCUMENT_REVIEW_PENDING


async def test_review_pending_to_document_change_requested(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_CHANGE_REQUESTED)
    assert updated.status == ProjectStatus.DOCUMENT_CHANGE_REQUESTED


async def test_change_requested_can_restart_document_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_CHANGE_REQUESTED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)
    assert updated.status == ProjectStatus.DOCUMENT_GENERATING


async def test_review_pending_to_document_approved(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_APPROVED)
    assert updated.status == ProjectStatus.DOCUMENT_APPROVED


async def test_review_pending_to_document_rejected(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DOCUMENT_REJECTED)
    assert updated.status == ProjectStatus.DOCUMENT_REJECTED


# ── Allowed transitions: Blueprint phase ──────────────────────────────────────


async def test_document_approved_to_blueprint_generating(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_GENERATING)
    assert updated.status == ProjectStatus.BLUEPRINT_GENERATING


async def test_blueprint_generating_to_blueprint_generated(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_GENERATED)
    assert updated.status == ProjectStatus.BLUEPRINT_GENERATED


async def test_blueprint_generating_to_blueprint_validation_failed(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_VALIDATION_FAILED)
    assert updated.status == ProjectStatus.BLUEPRINT_VALIDATION_FAILED


async def test_blueprint_validation_failed_can_retry_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_VALIDATION_FAILED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_GENERATING)
    assert updated.status == ProjectStatus.BLUEPRINT_GENERATING


async def test_blueprint_generated_to_blueprint_validated(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_VALIDATED)
    assert updated.status == ProjectStatus.BLUEPRINT_VALIDATED


async def test_blueprint_generated_to_blueprint_validation_failed(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.BLUEPRINT_VALIDATION_FAILED)
    assert updated.status == ProjectStatus.BLUEPRINT_VALIDATION_FAILED


# ── Allowed transitions: Implementation phase ─────────────────────────────────


async def test_blueprint_validated_to_implementation_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_GENERATING)
    assert updated.status == ProjectStatus.IMPLEMENTATION_GENERATING


async def test_implementation_generating_to_implementation_generated(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_GENERATED)
    assert updated.status == ProjectStatus.IMPLEMENTATION_GENERATED


async def test_implementation_generating_to_implementation_failed(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_FAILED)
    assert updated.status == ProjectStatus.IMPLEMENTATION_FAILED


async def test_implementation_failed_can_retry_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_FAILED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_GENERATING)
    assert updated.status == ProjectStatus.IMPLEMENTATION_GENERATING


# ── Allowed transitions: Post-implementation ──────────────────────────────────


async def test_implementation_generated_to_review_pending(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_GENERATED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_REVIEW_PENDING)
    assert updated.status == ProjectStatus.IMPLEMENTATION_REVIEW_PENDING


async def test_implementation_review_pending_to_approved(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_GENERATED,
        ProjectStatus.IMPLEMENTATION_REVIEW_PENDING,
    )
    updated = await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_APPROVED)
    assert updated.status == ProjectStatus.IMPLEMENTATION_APPROVED


async def test_implementation_approved_to_ready_for_deploy(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_GENERATED,
        ProjectStatus.IMPLEMENTATION_REVIEW_PENDING,
        ProjectStatus.IMPLEMENTATION_APPROVED,
    )
    updated = await project_service.transition(p.id, ProjectStatus.READY_FOR_DEPLOY)
    assert updated.status == ProjectStatus.READY_FOR_DEPLOY


async def test_ready_for_deploy_to_deployed(project_service: ProjectService) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_GENERATED,
        ProjectStatus.IMPLEMENTATION_REVIEW_PENDING,
        ProjectStatus.IMPLEMENTATION_APPROVED,
        ProjectStatus.READY_FOR_DEPLOY,
    )
    updated = await project_service.transition(p.id, ProjectStatus.DEPLOYED)
    assert updated.status == ProjectStatus.DEPLOYED


# ── Terminal states ───────────────────────────────────────────────────────────


async def test_document_rejected_is_terminal(project_service: ProjectService) -> None:
    p = await _create(project_service, "Terminal")
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_REJECTED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)


async def test_deployed_is_terminal(project_service: ProjectService) -> None:
    p = await _create(project_service, "Deployed Final")
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
        ProjectStatus.IMPLEMENTATION_GENERATING,
        ProjectStatus.IMPLEMENTATION_GENERATED,
        ProjectStatus.IMPLEMENTATION_REVIEW_PENDING,
        ProjectStatus.IMPLEMENTATION_APPROVED,
        ProjectStatus.READY_FOR_DEPLOY,
        ProjectStatus.DEPLOYED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.READY_FOR_DEPLOY)


# ── Blocked transitions required by the task ──────────────────────────────────


async def test_draft_created_cannot_jump_to_document_approved(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Skip To Approved")
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_APPROVED)


async def test_document_drafted_cannot_jump_to_document_approved(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Drafted Skip")
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_APPROVED)


async def test_document_approved_cannot_jump_to_implementation_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Approved Skip Impl")
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_GENERATING)


async def test_blueprint_generated_cannot_jump_to_implementation_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Blueprint Skip Impl")
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.IMPLEMENTATION_GENERATING)


# ── Additional representative illegal transitions ─────────────────────────────


async def test_draft_created_cannot_go_to_document_drafted(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_DRAFTED)


async def test_draft_created_cannot_go_to_blueprint_generating(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.BLUEPRINT_GENERATING)


async def test_document_generating_cannot_go_to_review_pending(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(project_service, p.id, ProjectStatus.DOCUMENT_GENERATING)
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_REVIEW_PENDING)


async def test_document_approved_cannot_go_back_to_review_pending(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_REVIEW_PENDING)


async def test_blueprint_validated_cannot_go_back_to_document_approved(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service)
    await _advance(
        project_service, p.id,
        ProjectStatus.DOCUMENT_GENERATING,
        ProjectStatus.DOCUMENT_DRAFTED,
        ProjectStatus.DOCUMENT_REVIEW_PENDING,
        ProjectStatus.DOCUMENT_APPROVED,
        ProjectStatus.BLUEPRINT_GENERATING,
        ProjectStatus.BLUEPRINT_GENERATED,
        ProjectStatus.BLUEPRINT_VALIDATED,
    )
    with pytest.raises(IllegalStatusTransitionError):
        await project_service.transition(p.id, ProjectStatus.DOCUMENT_APPROVED)


# ── Error handling ────────────────────────────────────────────────────────────


async def test_transition_unknown_project_raises_not_found(
    project_service: ProjectService,
) -> None:
    import uuid
    with pytest.raises(ProjectNotFoundError):
        await project_service.transition(uuid.uuid4(), ProjectStatus.DOCUMENT_GENERATING)


async def test_transition_returns_updated_project_read(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Return Check")
    result = await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)
    assert result.id == p.id
    assert result.name == "Return Check"
    assert result.status == ProjectStatus.DOCUMENT_GENERATING


async def test_transition_updates_updated_at_timestamp(
    project_service: ProjectService,
) -> None:
    p = await _create(project_service, "Timestamp Check")
    before = p.updated_at
    result = await project_service.transition(p.id, ProjectStatus.DOCUMENT_GENERATING)
    assert result.updated_at >= before
