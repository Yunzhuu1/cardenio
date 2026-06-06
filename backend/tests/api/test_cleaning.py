"""M1-T5 acceptance: text cleaning (FR-1.4).

Verifies that cleaning preserves intentional line breaks and normalizes
encoding artifacts.
"""

import pytest
from httpx import AsyncClient

from cardenio.api.routes.source import _clean_basic


class TestTextCleaning:
    """FR-1.4: cleaning does not destroy intentional line breaks."""

    def test_crlf_normalized(self) -> None:
        """CRLF and CR are normalized to LF."""
        assert _clean_basic("段落一。\r\n\r\n段落二。") == "段落一。\n\n段落二。"
        assert _clean_basic("段落一。\r段落二。") == "段落一。\n段落二。"

    def test_collapse_excess_newlines(self) -> None:
        """3+ newlines collapse to 2 (paragraph boundary)."""
        assert _clean_basic("段落一。\n\n\n\n段落二。") == "段落一。\n\n段落二。"

    def test_preserves_paragraph_gaps(self) -> None:
        """Intentional double newlines are preserved."""
        text = "林晚推开门。\n\n灰尘在夕阳中扬起。\n\n她站了很久。"
        assert _clean_basic(text) == text

    def test_removes_bom(self) -> None:
        """UTF-8 BOM is removed."""
        assert _clean_basic("\ufeff开始") == "开始"

    def test_fullwidth_to_halfwidth_digits(self) -> None:
        """Full-width ASCII digits become half-width."""
        assert _clean_basic("０１２３４５６７８９") == "0123456789"

    def test_fullwidth_to_halfwidth_letters(self) -> None:
        """Full-width ASCII letters become half-width."""
        assert _clean_basic("ＡＢＣａｂｃ") == "ABCabc"

    def test_fullwidth_space_to_halfwidth(self) -> None:
        """Full-width space becomes half-width."""
        assert _clean_basic("你好　世界") == "你好 世界"

    def test_fullwidth_ascii_punctuation_to_halfwidth(self) -> None:
        """Full-width ASCII punctuation becomes half-width."""
        assert _clean_basic("A＃Ｂ／Ｃ［１］") == "A#B/C[1]"

    def test_chinese_punctuation_preserved(self) -> None:
        """Non-ASCII Chinese prose punctuation is preserved."""
        assert _clean_basic("你好，世界。她看着《旧书》。") == "你好，世界。她看着《旧书》。"

    def test_removes_control_chars(self) -> None:
        """Control characters are removed except \n and \t."""
        assert _clean_basic("段落一。\x00\x01\x02段落二。") == "段落一。段落二。"
        assert _clean_basic("段落一。\n段落二。") == "段落一。\n段落二。"

    def test_strips_trailing_whitespace(self) -> None:
        """Trailing whitespace per line is stripped."""
        assert _clean_basic("段落一。  \n段落二。   ") == "段落一。\n段落二。"

    def test_preserves_leading_indent(self) -> None:
        """Leading indentation (intentional) is preserved."""
        text = "  缩进段落\n\n普通段落"
        assert _clean_basic(text) == text

    def test_complex_scenario(self) -> None:
        """Combination: BOM + CRLF + fullwidth + control chars."""
        text = "\ufeff第一章\r\n\r\n０１２３\r\n\n\n\n  段落  \x00\n"
        expected = "第一章\n\n0123\n\n  段落\n"
        assert _clean_basic(text) == expected


class TestCleaningApiFlow:
    """FR-1.4: API entry points apply cleaning before indexing/preview."""

    @pytest.fixture
    async def project_id(self, app_client: AsyncClient) -> str:
        """Create a test project and return its id."""
        resp = await app_client.post(
            "/api/v1/projects",
            json={
                "title": "cleaning-test",
                "ui_language": "zh-CN",
                "source_language": "zh-CN",
                "output_language": "zh-CN",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_manual_chapter_input_is_cleaned(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """Pasted/typed chapter text is cleaned before paragraph indexing."""
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": "第一章",
                "text": "\ufeff第一段Ａ１  \r\n\r\n第二段　Ｂ２\x00",
                "order": 1,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["paragraphs"][0]["text"] == "第一段A1"
        assert data["paragraphs"][1]["text"] == "第二段 B2"

    async def test_txt_import_preview_is_cleaned(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        """TXT import preview uses cleaned text for chapter stats."""
        content = "\ufeff第一章　Ａ１\r\n\r\n正文\x00\r\n\n\n\n第二章　Ｂ２\r\n\r\n正文"

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/import",
            files={"file": ("novel.txt", content.encode("utf-8"), "text/plain")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["chapters"]) == 2
        assert data["chapters"][0]["title"] == "第一章 A1"
        assert data["chapters"][0]["char_count"] > 0
