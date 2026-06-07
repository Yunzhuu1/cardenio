"""M8-T2 acceptance: privacy and training settings (NFR-1)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "settings-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def settings_payload() -> dict:
    return {
        "ui_language": "zh-CN",
        "source_language": "zh-CN",
        "output_language": "zh-CN",
        "data_storage_location": "configured_sqlite_database",
        "data_storage_notice": (
            "Project source text, generated artifacts, and settings are stored in the "
            "configured Cardenio SQLite database for this backend environment."
        ),
        "allow_model_training": False,
        "training_notice": (
            "Cardenio does not use project data for model training. The MVP keeps this "
            "setting locked off so unpublished manuscripts are not treated as training data."
        ),
        "local_processing_reserved": True,
        "local_processing_notice": (
            "The architecture keeps provider access behind the backend gateway and reserves "
            "a local/private processing path for deployments that require it."
        ),
        "shot_hints_enabled": True,
    }


class TestProjectSettings:
    """API-29: project settings expose privacy and training commitments."""

    async def test_get_default_settings_exposes_privacy_commitment(
        self,
        app_client: AsyncClient,
        project_id: str,
    ) -> None:
        resp = await app_client.get(f"/api/v1/projects/{project_id}/settings")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["type"] == "settings"
        assert payload["state"] == "confirmed"
        assert payload["version"] is None
        data = payload["data"]
        assert data["data_storage_location"] == "configured_sqlite_database"
        assert "SQLite database" in data["data_storage_notice"]
        assert data["allow_model_training"] is False
        assert "does not use project data for model training" in data["training_notice"]
        assert data["local_processing_reserved"] is True
        assert data["shot_hints_enabled"] is False

    async def test_update_settings_saves_versioned_artifact(
        self,
        app_client: AsyncClient,
        project_id: str,
    ) -> None:
        first_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/settings",
            json=settings_payload(),
        )
        updated_payload = settings_payload()
        updated_payload["shot_hints_enabled"] = False

        second_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/settings",
            json=updated_payload,
        )

        assert first_resp.status_code == 200
        assert second_resp.status_code == 200
        first = first_resp.json()
        second = second_resp.json()
        assert first["type"] == "settings"
        assert first["state"] == "confirmed"
        assert first["data"]["allow_model_training"] is False
        assert second["parent_version"] == first["version"]
        assert second["data"]["shot_hints_enabled"] is False

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/settings")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == second["version"]

    async def test_training_opt_in_is_rejected(
        self,
        app_client: AsyncClient,
        project_id: str,
    ) -> None:
        payload = settings_payload()
        payload["allow_model_training"] = True

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/settings",
            json=payload,
        )

        assert resp.status_code == 422

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.get("/api/v1/projects/missing/settings")

        assert resp.status_code == 404
