"""M1-T4 acceptance: chapter count threshold (FR-1.3).

Verifies that the 3-chapter minimum is checked and properly surfaced.
"""

import pytest
from httpx import AsyncClient


class TestThresholdCheck:
    """FR-1.3: minimum 3 chapters required before downstream generation."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        resp = await app_client.post(
            "/api/v1/projects", json={"title": "threshold-test"}
        )
        return resp.json()["id"]

    async def test_source_shows_threshold_blocked(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """GET /source shows threshold.blocked=true when < 3 chapters."""
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["threshold"]["min_chapters"] == 3
        assert data["threshold"]["passed"] is False
        assert data["threshold"]["blocked"] is True

    async def test_source_shows_threshold_passed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """GET /source shows threshold passed when >= 3 chapters."""
        for i in range(3):
            await app_client.post(
                f"/api/v1/projects/{project_id}/source/chapters",
                json={"title": f"第{i+1}章", "text": f"内容{i+1}", "order": i + 1},
            )

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source"
        )
        data = resp.json()
        assert data["threshold"]["passed"] is True
        assert data["threshold"]["blocked"] is False

    async def test_threshold_endpoint_returns_409_when_blocked(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """GET /source/threshold returns 409 when < 3 chapters."""
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source/threshold"
        )
        assert resp.status_code == 409
        error = resp.json()
        assert error["error"]["code"] == "chapter_threshold_unmet"

    async def test_threshold_endpoint_returns_200_when_passed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """GET /source/threshold returns 200 when >= 3 chapters."""
        for i in range(4):
            await app_client.post(
                f"/api/v1/projects/{project_id}/source/chapters",
                json={"title": f"第{i+1}章", "text": f"内容{i+1}", "order": i + 1},
            )

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source/threshold"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] is True
        assert data["current_chapters"] == 4

    async def test_zero_chapters_returns_blocked(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """A fresh project with no chapters has 0 chapters and is blocked."""
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source/threshold"
        )
        assert resp.status_code == 409
        details = resp.json()["error"]["details"]
        assert details["current_chapters"] == 0
        assert details["passed"] is False
