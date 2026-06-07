"""Auth API tests."""

from httpx import AsyncClient


async def test_register_returns_bearer_token(app_client: AsyncClient) -> None:
    resp = await app_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Author@Example.com",
            "password": "correct horse battery staple",
            "display_name": "Author",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_at"]
    assert body["user"]["id"].startswith("usr_")
    assert body["user"]["email"] == "author@example.com"
    assert body["user"]["display_name"] == "Author"
    assert "password" not in body["user"]


async def test_register_duplicate_email_returns_409(app_client: AsyncClient) -> None:
    payload = {
        "email": "author@example.com",
        "password": "correct horse battery staple",
    }
    first = await app_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    duplicate = await app_client.post(
        "/api/v1/auth/register",
        json={**payload, "email": "AUTHOR@example.com"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "version_conflict"


async def test_login_returns_token_for_valid_credentials(
    app_client: AsyncClient,
) -> None:
    await register_user(app_client)

    resp = await app_client.post(
        "/api/v1/auth/login",
        json={
            "email": "author@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "author@example.com"


async def test_login_wrong_password_returns_401(app_client: AsyncClient) -> None:
    await register_user(app_client)

    resp = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "author@example.com", "password": "wrong-password"},
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_me_requires_bearer_token(app_client: AsyncClient) -> None:
    resp = await app_client.get("/api/v1/auth/me", headers={"Authorization": ""})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthenticated"


async def test_me_returns_current_user(app_client: AsyncClient) -> None:
    auth = await register_user(app_client)

    resp = await app_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth['access_token']}"},
    )

    assert resp.status_code == 200
    assert resp.json() == auth["user"]


async def test_logout_revokes_current_token(app_client: AsyncClient) -> None:
    auth = await register_user(app_client)
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    logout_resp = await app_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 204

    me_resp = await app_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401
    assert me_resp.json()["error"]["code"] == "unauthenticated"


async def register_user(app_client: AsyncClient) -> dict:
    resp = await app_client.post(
        "/api/v1/auth/register",
        json={
            "email": "author@example.com",
            "password": "correct horse battery staple",
            "display_name": "Author",
        },
    )
    assert resp.status_code == 201
    return resp.json()
