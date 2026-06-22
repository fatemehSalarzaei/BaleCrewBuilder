from httpx import AsyncClient


async def test_create_project_returns_201(client: AsyncClient) -> None:
    response = await client.post(
        "/projects", json={"name": "My Bot Project", "description": "A builder project"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Bot Project"
    assert data["description"] == "A builder project"
    assert data["status"] == "DRAFT_CREATED"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_project_minimal_payload(client: AsyncClient) -> None:
    response = await client.post("/projects", json={"name": "Minimal"})

    assert response.status_code == 201
    data = response.json()
    assert data["description"] == ""
    assert data["status"] == "DRAFT_CREATED"


async def test_create_project_empty_name_returns_422(client: AsyncClient) -> None:
    response = await client.post("/projects", json={"name": ""})

    assert response.status_code == 422


async def test_create_project_missing_name_returns_422(client: AsyncClient) -> None:
    response = await client.post("/projects", json={"description": "No name"})

    assert response.status_code == 422


async def test_get_project_returns_project(client: AsyncClient) -> None:
    created = (await client.post("/projects", json={"name": "Fetch Me"})).json()
    project_id = created["id"]

    response = await client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Fetch Me"
    assert data["status"] == "DRAFT_CREATED"


async def test_get_project_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/projects/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_projects_are_isolated_between_tests(client: AsyncClient) -> None:
    response = await client.get("/projects/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 404
