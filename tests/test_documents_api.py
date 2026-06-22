from httpx import AsyncClient


async def _create_project(client: AsyncClient, name: str = "Test Project") -> str:
    resp = await client.post("/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_document_returns_201(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={
            "title": "Initial Idea",
            "content": "# My Bot\nThis bot will help users manage reservations.",
            "kind": "MARKDOWN",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id
    assert data["title"] == "Initial Idea"
    assert data["kind"] == "MARKDOWN"
    assert "# My Bot" in data["content"]
    assert "id" in data
    assert "created_at" in data


async def test_create_document_default_kind_is_markdown(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Plain idea", "content": "Some raw idea text"},
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "MARKDOWN"


async def test_create_document_raw_text_kind(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Raw text doc", "content": "plain content", "kind": "RAW_TEXT"},
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "RAW_TEXT"


async def test_create_document_project_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/projects/00000000-0000-0000-0000-000000000002/documents",
        json={"title": "Doc", "content": "Content"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_create_document_missing_content_returns_422(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "No content doc"},
    )

    assert response.status_code == 422


async def test_create_document_empty_content_returns_422(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Empty content", "content": ""},
    )

    assert response.status_code == 422


async def test_create_document_missing_title_returns_422(client: AsyncClient) -> None:
    project_id = await _create_project(client)

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"content": "content but no title"},
    )

    assert response.status_code == 422


async def test_document_content_is_stored_verbatim(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    content = "## Overview\n\nThis platform handles **reservations**.\n\n- Feature A\n- Feature B"

    response = await client.post(
        f"/projects/{project_id}/documents",
        json={"title": "Verbatim check", "content": content},
    )

    assert response.status_code == 201
    assert response.json()["content"] == content
