"""M1-T3 acceptance: chapter segmentation (FR-1.2).

Tests: edit, delete, merge, split, and re-mapping of paragraph indices.
"""

import pytest
from httpx import AsyncClient


class TestChapterEdit:
    """API-6: PUT /chapters/{id} — edit a chapter."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        resp = await app_client.post(
            "/api/v1/projects", json={"title": "seg-test"}
        )
        return resp.json()["id"]

    @pytest.fixture
    async def chapter(self, app_client: AsyncClient, project_id: str) -> dict:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "第一章", "text": "段A。\n\n段B。", "order": 1},
        )
        return resp.json()

    async def test_edit_chapter_text(
        self, app_client: AsyncClient, project_id: str, chapter: dict
    ) -> None:
        """PUT /chapters/{id} replaces paragraphs."""
        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/source/chapters/{chapter['id']}",
            json={
                "id": chapter["id"],
                "title": "修改后的标题",
                "order": 1,
                "char_count": 100,
                "paragraphs": [
                    {"index": 1, "text": "新段一。"},
                    {"index": 2, "text": "新段二。"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "修改后的标题"
        assert len(data["paragraphs"]) == 2
        assert data["paragraphs"][1]["text"] == "新段二。"

    async def test_single_newline_paragraphs_are_split(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Single-newline prose is indexed as one paragraph per non-empty line."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "段A。\n段B。\n段C。 ",
                "order": 1,
            },
        )

        assert resp.status_code == 201
        paragraphs = resp.json()["paragraphs"]
        assert [p["text"] for p in paragraphs] == ["段A。", "段B。", "段C。"]

    async def test_blank_line_paragraphs_still_split_by_blocks(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Blank-line prose still treats multi-line blocks as one paragraph."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "段A第一行。\n段A第二行。\n\n段B。",
                "order": 1,
            },
        )

        assert resp.status_code == 201
        paragraphs = resp.json()["paragraphs"]
        assert [p["text"] for p in paragraphs] == ["段A第一行。\n段A第二行。", "段B。"]


class TestChapterDelete:
    """API-6: DELETE /chapters/{id} — remove a chapter."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        resp = await app_client.post(
            "/api/v1/projects", json={"title": "del-test"}
        )
        return resp.json()["id"]

    async def test_delete_chapter(self, app_client: AsyncClient, project_id: str) -> None:
        """DELETE removes chapter and returns 204."""
        # Create a chapter
        c = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "待删", "text": "内容。", "order": 1},
        )
        ch_id = c.json()["id"]

        # Delete it
        resp = await app_client.delete(
            f"/api/v1/projects/{project_id}/source/chapters/{ch_id}"
        )
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source"
        )
        assert len(get_resp.json()["chapters"]) == 0

    async def test_delete_nonexistent_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.delete(
            f"/api/v1/projects/{project_id}/source/chapters/ch_nonexistent"
        )
        assert resp.status_code == 404


class TestChapterResegment:
    """API-6: POST /chapters:resegment — split and merge."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        resp = await app_client.post(
            "/api/v1/projects", json={"title": "reseg-test"}
        )
        return resp.json()["id"]

    async def test_split_chapter(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Split a chapter into two at paragraph boundary."""
        # Create a chapter with 3 paragraphs
        c = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "长章",
                "text": "段落1。\n\n段落2。\n\n段落3。",
                "order": 1,
            },
        )
        ch_id = c.json()["id"]

        # Split after paragraph 2
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters:resegment",
            json={"op": "split", "chapter_id": ch_id, "at_paragraph": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should now have 2 chapters
        assert len(data["chapters"]) == 2

    async def test_merge_chapters(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Merge two chapters into one."""
        await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "第一章", "text": "段A。", "order": 1},
        )
        c2 = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "第二章", "text": "段B。", "order": 2},
        )

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters:resegment",
            json={
                "op": "merge",
                "chapter_ids": ["ch_1", c2.json()["id"]],
                "new_title": "合并章",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should now have 1 merged chapter
        assert len(data["chapters"]) == 1

    async def test_merge_needs_at_least_2(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Merge with < 2 chapters returns 400."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters:resegment",
            json={"op": "merge", "chapter_ids": ["ch_1"], "new_title": "不行"},
        )
        assert resp.status_code == 400

    async def test_split_at_boundary_returns_400(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Split at paragraph boundary of a 2-para chapter returns 400."""
        c = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": "短章", "text": "段A。\n\n段B。", "order": 1},
        )
        # Split at paragraph 1 would leave part2 empty? Let's check index 2
        # Since we index from 1, at_paragraph=2 should work
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters:resegment",
            json={
                "op": "split",
                "chapter_id": c.json()["id"],
                "at_paragraph": 99,  # beyond end
            },
        )
        # at_paragraph=99 > all paragraphs → part2 empty → 400
        assert resp.status_code == 400
