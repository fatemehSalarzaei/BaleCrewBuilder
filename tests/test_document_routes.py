from uuid import uuid4

from httpx import AsyncClient


async def _create_project(client: AsyncClient, name: str = "Document Routes") -> str:
    response = await client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def test_get_latest_document_returns_latest_project_document(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    first = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "First", "content": "first document"},
    )
    second = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Second", "content": "second document"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = await client.get(f"/projects/{project_id}/document")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == second.json()["id"]
    assert data["project_id"] == project_id
    assert data["title"] == "Second"
    assert data["content"] == "second document"


async def test_get_latest_document_project_not_found_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/projects/{uuid4()}/document")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


async def test_get_latest_document_without_document_returns_404(
    client: AsyncClient,
) -> None:
    project_id = await _create_project(client)

    response = await client.get(f"/projects/{project_id}/document")

    assert response.status_code == 404
    assert response.json()["detail"] == "No document found for project"
