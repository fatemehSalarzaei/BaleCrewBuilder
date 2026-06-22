from uuid import UUID

from httpx import AsyncClient

from app.schemas.project import ProjectStatus
from app.services.project_service import ProjectService


async def _create_project(client: AsyncClient, name: str = "Review Project") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _fast_track_to_review(ps: ProjectService, project_id: str) -> None:
    pid = UUID(project_id)
    await ps.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await ps.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    await ps.transition(pid, ProjectStatus.DOCUMENT_REVIEW_PENDING)


async def test_approve_document_sets_document_approved(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Looks good!", "reviewer_name": "Alice"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["previous_status"] == "DOCUMENT_REVIEW_PENDING"
    assert data["next_status"] == "DOCUMENT_APPROVED"
    assert data["reviewer_name"] == "Alice"
    assert "id" in data
    assert "created_at" in data

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_APPROVED"


async def test_approve_stores_reviewer_and_feedback(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Well specified.", "reviewer_name": "Lead Reviewer"},
    )

    data = response.json()
    assert data["feedback"] == "Well specified."
    assert data["reviewer_name"] == "Lead Reviewer"
    assert data["project_id"] == project_id


async def test_approve_without_reviewer_name(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/approve", json={}
    )

    assert response.status_code == 201
    assert response.json()["reviewer_name"] is None


async def test_request_changes_sets_change_requested(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={
            "decision": "REQUEST_CHANGES",
            "feedback": "Please add more detail on the admin bot commands.",
            "reviewer_name": "Bob",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "REQUEST_CHANGES"
    assert data["previous_status"] == "DOCUMENT_REVIEW_PENDING"
    assert data["next_status"] == "DOCUMENT_CHANGE_REQUESTED"

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_CHANGE_REQUESTED"


async def test_reject_records_decision_and_transitions_to_rejected(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={
            "decision": "REJECT",
            "feedback": "The scope is completely wrong, please restart.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "REJECT"
    assert data["previous_status"] == "DOCUMENT_REVIEW_PENDING"
    assert data["next_status"] == "DOCUMENT_REJECTED"

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_REJECTED"


async def test_rejected_project_cannot_be_approved(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)
    await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REJECT", "feedback": "Rejected."},
    )

    response = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Trying to approve after reject"},
    )

    assert response.status_code == 409


async def test_request_changes_is_distinct_from_reject(
    client: AsyncClient, project_service: ProjectService
) -> None:
    """REQUEST_CHANGES must not produce DOCUMENT_REJECTED — it stays as revision."""
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Please add more detail."},
    )

    data = response.json()
    assert data["next_status"] == "DOCUMENT_CHANGE_REQUESTED"
    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_CHANGE_REQUESTED"


async def test_split_scope_requests_scope_revision(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={
            "decision": "SPLIT_SCOPE",
            "feedback": "MVP scope is too broad. Please separate MVP from future work.",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "SPLIT_SCOPE"
    assert data["next_status"] == "DOCUMENT_CHANGE_REQUESTED"

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_CHANGE_REQUESTED"


async def test_freeze_scope_locks_approved_document_without_status_change(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    await client.post(f"/projects/{project_id}/document/approve", json={})

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={
            "decision": "FREEZE_SCOPE",
            "feedback": "Scope locked as of this review.",
            "reviewer_name": "Charlie",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "FREEZE_SCOPE"
    assert data["previous_status"] == "DOCUMENT_APPROVED"
    assert data["next_status"] == "DOCUMENT_APPROVED"

    project = (await client.get(f"/projects/{project_id}")).json()
    assert project["status"] == "DOCUMENT_APPROVED"


async def test_approve_on_wrong_status_returns_409(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/document/approve",
        json={"feedback": "Too early"},
    )

    assert response.status_code == 409


async def test_request_changes_on_wrong_status_returns_409(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Not in review"},
    )

    assert response.status_code == 409


async def test_feedback_using_approve_decision_returns_422(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    await _fast_track_to_review(project_service, project_id)

    response = await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "APPROVE", "feedback": "Sneaking in via feedback endpoint"},
    )

    assert response.status_code == 422


async def test_approve_project_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/projects/00000000-0000-0000-0000-000000000099/document/approve",
        json={},
    )
    assert response.status_code == 404


async def test_feedback_project_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/projects/00000000-0000-0000-0000-000000000099/document/feedback",
        json={"decision": "REJECT", "feedback": "No project"},
    )
    assert response.status_code == 404


async def test_list_reviews_returns_full_history(
    client: AsyncClient, project_service: ProjectService
) -> None:
    project_id = await _create_project(client)
    pid = UUID(project_id)
    await _fast_track_to_review(project_service, project_id)

    await client.post(
        f"/projects/{project_id}/document/feedback",
        json={"decision": "REQUEST_CHANGES", "feedback": "Please revise section 2"},
    )

    await project_service.transition(pid, ProjectStatus.DOCUMENT_GENERATING)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_DRAFTED)
    await project_service.transition(pid, ProjectStatus.DOCUMENT_REVIEW_PENDING)

    await client.post(f"/projects/{project_id}/document/approve", json={"feedback": "Now good"})

    response = await client.get(f"/projects/{project_id}/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 2
    assert reviews[0]["decision"] == "REQUEST_CHANGES"
    assert reviews[1]["decision"] == "APPROVE"


async def test_list_reviews_empty_for_new_project(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    response = await client.get(f"/projects/{project_id}/reviews")
    assert response.status_code == 200
    assert response.json() == []
