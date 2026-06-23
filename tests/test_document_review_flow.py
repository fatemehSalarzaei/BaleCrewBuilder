"""End-to-end tests for the Phase 2 document review workflow.

Full pipeline covered:
  DRAFT_CREATED
    → (generate) → DOCUMENT_DRAFTED
    → (submit-review) → DOCUMENT_REVIEW_PENDING
    → (feedback/approve) → DOCUMENT_CHANGE_REQUESTED | DOCUMENT_APPROVED

Also covers error paths: wrong status, missing project, missing document,
cross-project document mismatch.
"""
import pytest
from httpx import AsyncClient

from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_project(client: AsyncClient, name: str = "Review Flow") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _generate_document(client: AsyncClient, project_id: str) -> dict:
    resp = await client.post(
        f"/projects/{project_id}/documents/generate",
        json={"raw_requirements": "Build a task management bot for teams."},
    )
    assert resp.status_code == 201
    return resp.json()


async def _submit_review(client: AsyncClient, project_id: str, document_id: str):
    return await client.post(
        f"/projects/{project_id}/documents/{document_id}/submit-review"
    )


async def _get_project_status(client: AsyncClient, project_id: str) -> str:
    resp = await client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    return resp.json()["status"]


# ── Precondition: generate reaches DOCUMENT_DRAFTED ──────────────────────────


async def test_generated_document_reaches_document_drafted(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    await _generate_document(client, project_id)
    assert await _get_project_status(client, project_id) == "DOCUMENT_DRAFTED"


async def test_generated_document_has_id(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    assert data["document"]["id"]
    assert data["document"]["project_id"] == project_id


# ── submit-review endpoint ────────────────────────────────────────────────────


async def test_submit_review_returns_200(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]

    resp = await _submit_review(client, project_id, document_id)
    assert resp.status_code == 200


async def test_submit_review_transitions_to_review_pending(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]

    await _submit_review(client, project_id, document_id)

    assert await _get_project_status(client, project_id) == "DOCUMENT_REVIEW_PENDING"


async def test_submit_review_response_contains_correct_status(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]

    resp = await _submit_review(client, project_id, document_id)
    body = resp.json()
    assert body["project_status"] == "DOCUMENT_REVIEW_PENDING"
    assert body["project_id"] == project_id
    assert body["document_id"] == document_id


async def test_submit_review_project_not_found_returns_404(client: AsyncClient) -> None:
    resp = await _submit_review(
        client,
        "00000000-0000-0000-0000-000000000099",
        "00000000-0000-0000-0000-000000000001",
    )
    assert resp.status_code == 404
    assert "project" in resp.json()["detail"].lower()


async def test_submit_review_missing_document_returns_404(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    await _generate_document(client, project_id)  # project is now DOCUMENT_DRAFTED

    resp = await _submit_review(
        client, project_id, "00000000-0000-0000-0000-000000000099"
    )
    assert resp.status_code == 404
    assert "document" in resp.json()["detail"].lower()


async def test_submit_review_wrong_project_document_returns_404(
    client: AsyncClient,
) -> None:
    """Document belonging to project A cannot be submitted for project B."""
    project_a = await _create_project(client, "Project A")
    project_b = await _create_project(client, "Project B")

    data_a = await _generate_document(client, project_a)
    document_id_a = data_a["document"]["id"]

    # put project B in DOCUMENT_DRAFTED so the transition isn't the blocker
    await _generate_document(client, project_b)

    resp = await _submit_review(client, project_b, document_id_a)
    assert resp.status_code == 404


async def test_submit_review_when_not_drafted_returns_409(client: AsyncClient) -> None:
    """Project still at DRAFT_CREATED — cannot jump to DOCUMENT_REVIEW_PENDING."""
    project_id = await _create_project(client, "Not Drafted Yet")

    # use any valid-format uuid as document_id; project check comes first
    # but we need a real document — create one manually
    doc_resp = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Doc", "content": "Some content."},
    )
    assert doc_resp.status_code == 201
    document_id = doc_resp.json()["id"]

    # project is DRAFT_CREATED, transition to DOCUMENT_REVIEW_PENDING is illegal
    resp = await _submit_review(client, project_id, document_id)
    assert resp.status_code == 409


async def test_submit_review_twice_returns_409(client: AsyncClient) -> None:
    """Calling submit-review a second time must fail because project is
    already DOCUMENT_REVIEW_PENDING (not DOCUMENT_DRAFTED)."""
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]

    first = await _submit_review(client, project_id, document_id)
    assert first.status_code == 200

    second = await _submit_review(client, project_id, document_id)
    assert second.status_code == 409


# ── Approval/feedback requires DOCUMENT_REVIEW_PENDING ───────────────────────


async def test_approve_before_submit_review_returns_409(client: AsyncClient) -> None:
    """Approval must fail when project is still DOCUMENT_DRAFTED."""
    project_id = await _create_project(client)
    await _generate_document(client, project_id)

    resp = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Skipping review step"},
    )
    assert resp.status_code == 409


async def test_feedback_before_submit_review_returns_409(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    await _generate_document(client, project_id)

    resp = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Too early"},
    )
    assert resp.status_code == 409


# ── Post-submit-review: feedback creates review record ───────────────────────


async def test_feedback_after_submit_review_creates_record(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    await _submit_review(client, project_id, data["document"]["id"])

    resp = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={
            "decision": "REQUEST_CHANGES",
            "feedback": "Please add details about admin bot commands.",
            "reviewer_name": "Alice",
        },
    )
    assert resp.status_code == 201
    review = resp.json()
    assert review["decision"] == "REQUEST_CHANGES"
    assert review["previous_status"] == "DOCUMENT_REVIEW_PENDING"
    assert review["next_status"] == "DOCUMENT_CHANGE_REQUESTED"
    assert review["reviewer_name"] == "Alice"
    assert review["id"]


async def test_feedback_transitions_to_change_requested(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    await _submit_review(client, project_id, data["document"]["id"])

    await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Revise."},
    )

    assert await _get_project_status(client, project_id) == "DOCUMENT_CHANGE_REQUESTED"


# ── Approve reaches DOCUMENT_APPROVED ────────────────────────────────────────


async def test_approve_after_submit_review_reaches_document_approved(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    await _submit_review(client, project_id, data["document"]["id"])

    resp = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Looks great!", "reviewer_name": "Bob"},
    )
    assert resp.status_code == 201
    review = resp.json()
    assert review["decision"] == "APPROVE"
    assert review["next_status"] == "DOCUMENT_APPROVED"

    assert await _get_project_status(client, project_id) == "DOCUMENT_APPROVED"


async def test_approve_stores_document_id_when_provided(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]
    await _submit_review(client, project_id, document_id)

    resp = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"document_id": document_id},
    )
    assert resp.status_code == 201
    assert resp.json()["document_id"] == document_id


# ── Full end-to-end flow ──────────────────────────────────────────────────────


async def test_full_draft_to_approved_pipeline(client: AsyncClient) -> None:
    """Complete happy path: generate → submit-review → approve."""
    project_id = await _create_project(client, "E2E Pipeline")
    assert await _get_project_status(client, project_id) == "DRAFT_CREATED"

    # 1. Generate document
    data = await _generate_document(client, project_id)
    document_id = data["document"]["id"]
    assert await _get_project_status(client, project_id) == "DOCUMENT_DRAFTED"

    # 2. Submit for review
    resp = await _submit_review(client, project_id, document_id)
    assert resp.status_code == 200
    assert await _get_project_status(client, project_id) == "DOCUMENT_REVIEW_PENDING"

    # 3. Approve
    await client.post(f"/projects/{project_id}/document/approve", json={})
    assert await _get_project_status(client, project_id) == "DOCUMENT_APPROVED"


async def test_full_draft_with_changes_then_resubmit_and_approve(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """Complete cycle with one round of changes requested."""
    from uuid import UUID

    project_id = await _create_project(client, "Revision Cycle")
    pid = UUID(project_id)

    # 1. Generate + submit review
    data = await _generate_document(client, project_id)
    doc_id = data["document"]["id"]
    await _submit_review(client, project_id, doc_id)

    # 2. Reviewer requests changes
    await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Needs more detail."},
    )
    assert await _get_project_status(client, project_id) == "DOCUMENT_CHANGE_REQUESTED"

    # 3. Re-generate (service transitions: change_requested → generating → drafted)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)

    # 4. Create a new document version and re-submit
    doc_resp = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Revised Doc", "content": "## Revised\n\nAdded detail."},
    )
    new_doc_id = doc_resp.json()["id"]
    await _submit_review(client, project_id, new_doc_id)

    # 5. Approve
    await client.post(f"/projects/{project_id}/document/approve", json={})
    assert await _get_project_status(client, project_id) == "DOCUMENT_APPROVED"

    # Review history should have two entries
    reviews = (await client.get(f"/projects/{project_id}/reviews")).json()
    assert len(reviews) == 2
    assert reviews[0]["decision"] == "REQUEST_CHANGES"
    assert reviews[1]["decision"] == "APPROVE"


async def test_generation_still_blocked_after_document_approved(
    client: AsyncClient,
) -> None:
    """Approval gate: Blueprint must still be validated before generation."""
    project_id = await _create_project(client, "Gate Check")
    data = await _generate_document(client, project_id)
    doc_id = data["document"]["id"]
    await _submit_review(client, project_id, doc_id)
    await client.post(f"/projects/{project_id}/document/approve", json={})

    impl_resp = await client.post(f"/projects/{project_id}/generate")
    assert impl_resp.status_code == 409
