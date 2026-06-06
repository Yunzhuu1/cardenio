"""M2-T1 acceptance: understanding generation and confirmation (FR-2)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "understanding-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def add_three_chapters(app_client: AsyncClient, project_id: str) -> None:
    for i in range(3):
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={
                "title": f"Chapter {i + 1}",
                "text": f"第{i + 1}章 第一段。\n\n主角继续追查线索{i + 1}。",
                "order": i + 1,
            },
        )
        assert resp.status_code == 201


async def add_chapters_with_internal_monologue(
    app_client: AsyncClient, project_id: str
) -> None:
    texts = [
        (
            "I am standing in the archive now.\n\n"
            "I remembered the locked room and felt afraid because maybe my "
            "father had hidden the letter from me for years, and I thought "
            "the truth would destroy every memory I still trusted."
        ),
        "She opens the cabinet.\n\nThe dust rises under the lamp.",
        "He waits outside.\n\nThe rain keeps falling.",
    ]
    for i, text in enumerate(texts):
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": f"Chapter {i + 1}", "text": text, "order": i + 1},
        )
        assert resp.status_code == 201


async def add_style_sample_chapters(app_client: AsyncClient, project_id: str) -> None:
    texts = [
        (
            "Rain tapped the locked archive. The room stayed dark. "
            "A secret note waited under the cold light."
        ),
        (
            "The knife was missing. Fear moved through the hallway. "
            "Every shadow looked like a warning."
        ),
        (
            "She read the letter in silence. Memory returned with the rain. "
            "No one laughed."
        ),
    ]
    for i, text in enumerate(texts):
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": f"Chapter {i + 1}", "text": text, "order": i + 1},
        )
        assert resp.status_code == 201


class TestUnderstandingGeneration:
    """API-7/8: understanding is generated, editable, and confirmable."""

    async def test_generate_requires_three_chapters(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "chapter_threshold_unmet"
        assert error["details"]["current_chapters"] == 0

    async def test_generate_and_get_understanding(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await add_three_chapters(app_client, project_id)

        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )
        assert generate_resp.status_code == 202
        generated = generate_resp.json()
        assert generated["type"] == "understanding"
        assert generated["state"] == "draft"
        assert generated["data"]["logline"]
        assert generated["data"]["synopsis"]
        assert "narrative" in generated["data"]

        get_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/understanding"
        )
        assert get_resp.status_code == 200
        current = get_resp.json()
        assert current["version"] == generated["version"]
        assert current["data"] == generated["data"]

    async def test_generate_marks_internal_monologue_as_non_visualizable(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await add_chapters_with_internal_monologue(app_client, project_id)

        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )
        assert generate_resp.status_code == 202
        data = generate_resp.json()["data"]

        assert data["narrative"] == {
            "perspective": "first_person",
            "tense": "present",
            "unreliable": True,
        }
        assert len(data["non_visualizable"]) >= 1
        mark = data["non_visualizable"][0]
        assert mark["source_ref"] == {"chapter": 1, "paragraphs": [2]}
        assert "externalized" in mark["note"]

    async def test_generate_samples_style_fingerprint_into_project_meta(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await add_style_sample_chapters(app_client, project_id)

        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )
        assert generate_resp.status_code == 202
        style_fingerprint = generate_resp.json()["data"]["style_fingerprint"]
        assert "image-dense" in style_fingerprint
        assert "avg_sentence_length=" in style_fingerprint
        assert style_fingerprint != "stub"

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["style_fingerprint"] == style_fingerprint

    async def test_update_understanding_persists_editable_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await add_three_chapters(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )
        data = generate_resp.json()["data"]
        data["logline"] = "作者编辑后的 logline"
        data["themes"] = ["记忆", "和解"]
        data["strengths"] = ["人物目标清晰"]

        update_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/understanding",
            json=data,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["state"] == "draft"
        assert updated["parent_version"] == generate_resp.json()["version"]
        assert updated["data"]["logline"] == "作者编辑后的 logline"
        assert updated["data"]["themes"] == ["记忆", "和解"]

        get_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/understanding"
        )
        assert get_resp.json()["data"]["strengths"] == ["人物目标清晰"]

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.json()["style_fingerprint"] == data["style_fingerprint"]

    async def test_confirm_understanding_marks_gate_confirmed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await add_three_chapters(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )

        confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:confirm"
        )
        assert confirm_resp.status_code == 200
        confirmed = confirm_resp.json()
        assert confirmed["state"] == "confirmed"
        assert confirmed["parent_version"] == generate_resp.json()["version"]

        get_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/understanding"
        )
        assert get_resp.json()["state"] == "confirmed"

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.post(
            "/api/v1/projects/missing/understanding:generate"
        )
        assert resp.status_code == 404

    async def test_confirm_missing_understanding_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:confirm"
        )
        assert resp.status_code == 404
