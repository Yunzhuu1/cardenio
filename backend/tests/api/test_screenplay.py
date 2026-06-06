"""M5-T1 acceptance: screenplay generation from outline (FR-7/FR-8)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "screenplay-test",
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


async def add_screenplay_source(app_client: AsyncClient, project_id: str) -> None:
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


async def move_to_confirmed_characters(
    app_client: AsyncClient,
    project_id: str,
) -> None:
    await add_screenplay_source(app_client, project_id)
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


async def generate_confirmed_outline(
    app_client: AsyncClient,
    project_id: str,
    *,
    set_intent: bool = False,
) -> dict:
    await move_to_confirmed_characters(app_client, project_id)
    if set_intent:
        intent_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=intent_payload(),
        )
        assert intent_resp.status_code == 200
    outline_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:generate"
    )
    assert outline_resp.status_code == 202
    confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:confirm"
    )
    assert confirm_resp.status_code == 200
    return confirm_resp.json()


async def generate_confirmed_outline_with_non_visualizable_mark(
    app_client: AsyncClient,
    project_id: str,
) -> None:
    await add_screenplay_source(app_client, project_id)
    understanding_payload = {
        "logline": "A secret in the archive forces Lin Wan to act.",
        "synopsis": "Lin Wan and Chen Mo circle a hidden letter.",
        "themes": ["memory", "trust"],
        "protagonist_goal": "Find the truth behind the letter.",
        "protagonist_fear": "Losing the last trustworthy relationship.",
        "central_conflict": "Truth versus concealment.",
        "mood": "tense",
        "style_fingerprint": "restrained; dialogue-led; tense",
        "narrative": {
            "perspective": "third_person_limited",
            "tense": "past",
            "unreliable": False,
        },
        "non_visualizable": [
            {
                "source_ref": {"chapter": 1, "paragraphs": [1]},
                "note": "Lin Wan realizes the archive has always frightened her.",
            }
        ],
        "strengths": ["Clear dramatic pressure."],
        "difficulties": ["Internal fear needs externalization."],
    }
    put_resp = await app_client.put(
        f"/api/v1/projects/{project_id}/understanding",
        json=understanding_payload,
    )
    assert put_resp.status_code == 200
    confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/understanding:confirm"
    )
    assert confirm_resp.status_code == 200
    characters_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/characters:generate"
    )
    assert characters_resp.status_code == 202
    characters_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/characters:confirm"
    )
    assert characters_confirm_resp.status_code == 200
    outline_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:generate"
    )
    assert outline_resp.status_code == 202
    outline_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:confirm"
    )
    assert outline_confirm_resp.status_code == 200


class TestScreenplayGeneration:
    """API-17/18: confirmed outline generates a structured screenplay draft."""

    async def test_generate_requires_confirmed_outline(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await move_to_confirmed_characters(app_client, project_id)
        outline_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline:generate"
        )
        assert outline_resp.status_code == 202

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "state_gate_blocked"
        assert error["details"]["artifact"] == "outline"

    async def test_generate_screenplay_from_confirmed_outline(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        generated = resp.json()
        assert generated["type"] == "screenplay"
        assert generated["state"] == "draft"
        scenes = generated["data"]["scenes"]
        assert len(scenes) == len(outline["data"]["scenes"])
        for scene in scenes:
            assert scene["heading"]["location"]
            assert scene["source_ref"]["paragraphs"]
            assert scene["beats"]
            assert any(beat["type"] == "action" for beat in scene["beats"])
            assert all(
                beat["source_ref"] and beat["flag"] == "from_source"
                for beat in scene["beats"]
            )

        first_scene = scenes[0]
        assert first_scene["id"] == "sc_001"
        assert first_scene["source_ref"] == {"chapter": 1, "paragraphs": [1, 2]}
        assert first_scene["beats"][0]["source_ref"] == first_scene["source_ref"]

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == generated["version"]

    async def test_non_visualizable_passage_gets_externalization_options(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline_with_non_visualizable_mark(
            app_client, project_id
        )

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        beats = resp.json()["data"]["scenes"][0]["beats"]
        note = next(beat for beat in beats if beat["type"] == "note")
        assert note["flag"] == "ai_inferred"
        assert note["source_ref"] == {"chapter": 1, "paragraphs": [1]}
        assert "externalization" in note["text"]
        assert {option["kind"] for option in note["options"]} == {
            "voice_over",
            "action",
            "dialogue",
            "annotation",
        }

    async def test_get_single_screenplay_scene(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001"
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == "sc_001"
        assert resp.json()["beats"]

    async def test_generate_after_outlined_project_updates_state(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id, set_intent=True)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        assert resp.status_code == 202

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "generated"

    async def test_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay")
        assert resp.status_code == 404

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.post("/api/v1/projects/missing/screenplay:generate")
        assert resp.status_code == 404
