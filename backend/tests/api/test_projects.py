"""Project CRUD API tests (M0-T3)."""

from httpx import AsyncClient


async def test_patch_project_updates_metadata(app_client: AsyncClient) -> None:
    create_resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "project-before",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    project_id = create_resp.json()["id"]

    resp = await app_client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "title": "project-after",
            "ui_language": "en",
            "source_language": "zh-CN",
            "output_language": "en",
            "adaptation_direction": "cinematic",
        },
    )

    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "project-after"
    assert updated["ui_language"] == "en"
    assert updated["source_language"] == "zh-CN"
    assert updated["output_language"] == "en"
    assert updated["adaptation_direction"] == "cinematic"

    get_resp = await app_client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "project-after"


async def test_patch_project_missing_project_returns_404(
    app_client: AsyncClient,
) -> None:
    resp = await app_client.patch(
        "/api/v1/projects/missing",
        json={"title": "missing"},
    )

    assert resp.status_code == 404


async def test_update_settings_syncs_language_metadata(
    app_client: AsyncClient,
) -> None:
    create_resp = await app_client.post(
        "/api/v1/projects",
        json={"title": "settings-language"},
    )
    project_id = create_resp.json()["id"]

    resp = await app_client.put(
        f"/api/v1/projects/{project_id}/settings",
        json={
            "ui_language": "en",
            "source_language": "zh-CN",
            "output_language": "en",
            "data_storage_location": "configured_sqlite_database",
            "allow_model_training": False,
            "local_processing_reserved": True,
            "shot_hints_enabled": False,
        },
    )

    assert resp.status_code == 200
    project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
    assert project_resp.status_code == 200
    project = project_resp.json()
    assert project["ui_language"] == "en"
    assert project["source_language"] == "zh-CN"
    assert project["output_language"] == "en"


async def test_delete_project_hides_project_and_cascades_data(
    app_client: AsyncClient,
) -> None:
    create_resp = await app_client.post(
        "/api/v1/projects",
        json={"title": "delete-me"},
    )
    project_id = create_resp.json()["id"]
    chapter_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/source/chapters",
        json={"title": "Chapter 1", "text": "Line one.\n\nLine two.", "order": 1},
    )
    assert chapter_resp.status_code == 201
    settings_resp = await app_client.put(
        f"/api/v1/projects/{project_id}/settings",
        json={
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
            "data_storage_location": "configured_sqlite_database",
            "allow_model_training": False,
            "local_processing_reserved": True,
            "shot_hints_enabled": True,
        },
    )
    assert settings_resp.status_code == 200

    delete_resp = await app_client.delete(f"/api/v1/projects/{project_id}")

    assert delete_resp.status_code == 204
    assert await _status(app_client.get(f"/api/v1/projects/{project_id}")) == 404
    assert await _status(app_client.get(f"/api/v1/projects/{project_id}/source")) == 404
    assert await _status(app_client.get(f"/api/v1/projects/{project_id}/settings")) == 404

    list_resp = await app_client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    assert all(item["id"] != project_id for item in list_resp.json()["items"])


async def test_delete_project_missing_project_returns_404(
    app_client: AsyncClient,
) -> None:
    resp = await app_client.delete("/api/v1/projects/missing")

    assert resp.status_code == 404


async def _status(awaitable) -> int:
    response = await awaitable
    return response.status_code
