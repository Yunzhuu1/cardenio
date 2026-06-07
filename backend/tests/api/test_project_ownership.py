"""Project ownership and access-control API tests."""

from httpx import AsyncClient


async def test_project_routes_require_bearer_token(app_client: AsyncClient) -> None:
    resp = await app_client.get("/api/v1/projects", headers={"Authorization": ""})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_create_project_binds_current_user(app_client: AsyncClient) -> None:
    resp = await app_client.post("/api/v1/projects", json={"title": "owned"})

    assert resp.status_code == 201
    project = resp.json()
    assert project["owner_user_id"].startswith("usr_")

    me_resp = await app_client.get("/api/v1/auth/me")
    assert project["owner_user_id"] == me_resp.json()["id"]


async def test_list_projects_only_returns_current_user_projects(
    app_client: AsyncClient,
) -> None:
    user_a_project = await create_project(app_client, "user-a-project")
    user_b_headers = await register_headers(app_client, "user-b@example.com")

    user_b_create = await app_client.post(
        "/api/v1/projects",
        json={"title": "user-b-project"},
        headers=user_b_headers,
    )
    assert user_b_create.status_code == 201

    user_a_list = await app_client.get("/api/v1/projects")
    user_a_ids = {item["id"] for item in user_a_list.json()["items"]}
    assert user_a_project in user_a_ids
    assert user_b_create.json()["id"] not in user_a_ids

    user_b_list = await app_client.get("/api/v1/projects", headers=user_b_headers)
    user_b_ids = {item["id"] for item in user_b_list.json()["items"]}
    assert user_b_create.json()["id"] in user_b_ids
    assert user_a_project not in user_b_ids


async def test_other_user_project_access_returns_403(app_client: AsyncClient) -> None:
    project_id = await create_project(app_client, "private-project")
    other_headers = await register_headers(app_client, "other@example.com")

    get_resp = await app_client.get(
        f"/api/v1/projects/{project_id}",
        headers=other_headers,
    )
    patch_resp = await app_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"title": "stolen"},
        headers=other_headers,
    )
    delete_resp = await app_client.delete(
        f"/api/v1/projects/{project_id}",
        headers=other_headers,
    )

    assert get_resp.status_code == 403
    assert patch_resp.status_code == 403
    assert delete_resp.status_code == 403
    assert get_resp.json()["error"]["code"] == "forbidden"


async def test_other_user_cannot_access_project_scoped_resources(
    app_client: AsyncClient,
) -> None:
    project_id = await create_project(app_client, "private-project")
    other_headers = await register_headers(app_client, "other-resource@example.com")

    source_resp = await app_client.get(
        f"/api/v1/projects/{project_id}/source",
        headers=other_headers,
    )
    understanding_resp = await app_client.get(
        f"/api/v1/projects/{project_id}/understanding",
        headers=other_headers,
    )
    settings_resp = await app_client.get(
        f"/api/v1/projects/{project_id}/settings",
        headers=other_headers,
    )

    assert source_resp.status_code == 403
    assert understanding_resp.status_code == 403
    assert settings_resp.status_code == 403


async def test_missing_project_still_returns_404(app_client: AsyncClient) -> None:
    resp = await app_client.get("/api/v1/projects/missing")

    assert resp.status_code == 404


async def create_project(app_client: AsyncClient, title: str) -> str:
    resp = await app_client.post("/api/v1/projects", json={"title": title})
    assert resp.status_code == 201
    return resp.json()["id"]


async def register_headers(app_client: AsyncClient, email: str) -> dict[str, str]:
    resp = await app_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "display_name": "Other User",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
