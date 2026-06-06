"""M4-T1 acceptance: outline generation (FR-6)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "outline-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def intent_payload() -> dict:
    return {
        "keep": ["father-daughter confrontation"],
        "no_delete": ["the sealed letter"],
        "no_merge": ["Lin Wan", "Chen Mo"],
        "must_keep_lines": ["You hid this from me."],
        "mood_floor": "tense",
        "allow_new_plot": False,
        "allow_reorder": True,
        "allow_new_ending": False,
        "target_type": "short_drama",
    }


async def add_outline_source(app_client: AsyncClient, project_id: str) -> None:
    chapters = [
        "Lin Wan opened the archive.\n\nChen Mo watched Lin Wan hide the letter.",
        "Lin Wan found another clue.\n\nOld Master Qiao warned Chen Mo.",
        "Chen Mo returned at dawn.\n\nLin Wan chose to confront the secret.",
    ]
    for index, text in enumerate(chapters):
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": f"Chapter {index + 1}", "text": text, "order": index + 1},
        )
        assert resp.status_code == 201


async def move_project_to_confirmed_characters(
    app_client: AsyncClient,
    project_id: str,
) -> None:
    await add_outline_source(app_client, project_id)
    understanding_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/understanding:generate"
    )
    assert understanding_resp.status_code == 202
    understanding_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/understanding:confirm"
    )
    assert understanding_confirm_resp.status_code == 200
    characters_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/characters:generate"
    )
    assert characters_resp.status_code == 202
    characters_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/characters:confirm"
    )
    assert characters_confirm_resp.status_code == 200


async def move_project_to_intent_set(app_client: AsyncClient, project_id: str) -> None:
    await move_project_to_confirmed_characters(app_client, project_id)
    intent_resp = await app_client.put(
        f"/api/v1/projects/{project_id}/intent",
        json=intent_payload(),
    )
    assert intent_resp.status_code == 200


class TestOutlineGeneration:
    """API-14/15: scene outline can be generated and retrieved."""

    async def test_generate_requires_confirmed_characters(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(f"/api/v1/projects/{project_id}/outline:generate")

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "state_gate_blocked"
        assert error["details"]["artifact"] == "characters"

    async def test_generate_outline_with_complete_scene_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await move_project_to_confirmed_characters(app_client, project_id)

        resp = await app_client.post(f"/api/v1/projects/{project_id}/outline:generate")

        assert resp.status_code == 202
        generated = resp.json()
        assert generated["type"] == "outline"
        assert generated["state"] == "draft"
        scenes = generated["data"]["scenes"]
        assert len(scenes) == 3
        for scene in scenes:
            assert scene["id"]
            assert scene["heading"]["int_ext"] in {"INT", "EXT"}
            assert scene["heading"]["location"]
            assert scene["heading"]["time"] in {"DAY", "NIGHT", "DAWN", "DUSK"}
            assert scene["source_ref"]["chapter"] >= 1
            assert scene["source_ref"]["paragraphs"]
            assert scene["synopsis"]
            assert scene["goal"]
            assert scene["conflict"]
            assert scene["mood"]
            assert scene["characters"]
            assert scene["ending_state"]

        first_scene = scenes[0]
        assert first_scene["source_ref"] == {"chapter": 1, "paragraphs": [1, 2]}
        assert first_scene["foreshadowing"]
        assert first_scene["relation_changes"]

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == generated["version"]

    async def test_generate_after_intent_updates_project_state(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await move_project_to_intent_set(app_client, project_id)

        resp = await app_client.post(f"/api/v1/projects/{project_id}/outline:generate")
        assert resp.status_code == 202

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "outlined"

    async def test_missing_outline_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        assert resp.status_code == 404

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.post("/api/v1/projects/missing/outline:generate")
        assert resp.status_code == 404
