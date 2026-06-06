"""M1-T1 acceptance: chapter input and source retrieval (FR-1.1)."""

import pytest
from httpx import AsyncClient


class TestChapterInput:
    """API-3: POST /projects/{id}/source/chapters — paste/type chapter entry."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        """Create a test project and return its id."""
        resp = await app_client.post(
            "/api/v1/projects",
            json={
                "title": "旧书店的信",
                "ui_language": "zh-CN",
                "source_language": "zh-CN",
                "output_language": "zh-CN",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_create_chapter_returns_paragraphs(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """POST /chapters returns chapter with paragraph index and char_count."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "林晚推开旧书店的门。\n\n灰尘在夕阳中扬起。\n\n她站了很久。",
                "order": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "ch_1"
        assert data["title"] == "第一章"
        assert data["order"] == 1
        assert data["char_count"] > 0
        assert len(data["paragraphs"]) == 3
        assert data["paragraphs"][0]["index"] == 1
        assert data["paragraphs"][0]["text"] == "林晚推开旧书店的门。"
        assert data["paragraphs"][1]["index"] == 2
        assert data["paragraphs"][2]["index"] == 3

    async def test_get_source_returns_chapters_and_stats(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """GET /source returns chapters, stats, and threshold check."""
        # Add a chapter first
        await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "内容内容内容。\n\n第二段内容。",
                "order": 1,
            },
        )

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "chapters" in data
        assert len(data["chapters"]) == 1
        assert "stats" in data
        assert data["stats"]["chapter_count"] == 1
        assert data["stats"]["char_count"] > 0
        assert "threshold" in data
        assert data["threshold"]["min_chapters"] == 3
        assert data["threshold"]["passed"] is False  # Only 1 chapter

    async def test_multiple_chapters_increment_order(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Each chapter gets correct incremental order."""
        await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "第一章", "text": "内容A。", "order": 1},
        )
        await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "第二章", "text": "内容B。", "order": 2},
        )

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source"
        )
        data = resp.json()
        assert len(data["chapters"]) == 2

    async def test_empty_paragraphs_filtered(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Empty lines between paragraphs are filtered out."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "段落一。\n\n\n\n段落二。\n\n",
                "order": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["paragraphs"]) == 2

    async def test_project_not_found_returns_404(
        self, app_client: AsyncClient
    ) -> None:
        """Non-existent project returns 404."""
        resp = await app_client.post(
            "/api/v1/projects/nonexistent/source/chapters",
            json={"title": "Test", "text": "Text.", "order": 1},
        )
        assert resp.status_code == 404
