"""M5-T1 acceptance: screenplay generation from outline (FR-7/FR-8)."""

import pytest
from httpx import AsyncClient

from cardenio.gateway.providers.stub import StubLlmGateway


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


async def generate_confirmed_outline_with_custom_voice(
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
    character = characters_resp.json()["data"]["characters"][0]
    character["voice"] = "Quiet, clipped, avoids direct answers."
    update_resp = await app_client.put(
        f"/api/v1/projects/{project_id}/characters/{character['id']}",
        json=character,
    )
    assert update_resp.status_code == 200
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
        assert generated["data"]["shot_hints"]["enabled"] is False

    async def test_shot_hints_can_be_enabled_per_generation(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate",
            json={"shot_hints": True},
        )

        assert resp.status_code == 202
        assert resp.json()["data"]["shot_hints"]["enabled"] is True
        assert stub_gateway.call_log[-1].system_constraints.shot_hints_enabled is True
        request_context = {
            item["type"]: item["data"] for item in stub_gateway.call_log[-1].context
        }
        assert request_context["request"]["shot_hints"] is True

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

    async def test_dialogue_uses_character_voice_fingerprint(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline_with_custom_voice(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        beats = resp.json()["data"]["scenes"][0]["beats"]
        dialogue = next(beat for beat in beats if beat["type"] == "dialogue")
        assert dialogue["parenthetical"] == "(quiet, clipped)"
        assert dialogue["dialogue"].startswith("Enough.")
        assert len(dialogue["dialogue"]) <= 88
        assert "Voice: Quiet, clipped, avoids direct answers." in dialogue["subtext"]

    async def test_ai_inferred_beats_are_forced_and_filterable(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)
        scene = outline["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "scene": {
                "scenes": [
                    {
                        **scene,
                        "beats": [
                            {
                                "type": "action",
                                "text": "A new bridge beat not anchored in the source.",
                            },
                            {
                                "type": "dialogue",
                                "character": scene["characters"][0],
                                "dialogue": "You hid this from me.",
                                "source_ref": scene["source_ref"],
                                "flag": "from_source",
                            },
                        ],
                    }
                ],
                "shot_hints": {"enabled": False},
            },
        }

        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        assert generate_resp.status_code == 202
        beats = generate_resp.json()["data"]["scenes"][0]["beats"]
        assert beats[0]["flag"] == "ai_inferred"
        assert beats[1]["flag"] == "from_source"

        filter_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/beats",
            params={"flag": "ai_inferred"},
        )

        assert filter_resp.status_code == 200
        payload = filter_resp.json()
        assert payload["count"] == 1
        assert payload["items"][0]["scene_id"] == scene["id"]
        assert payload["items"][0]["beat_index"] == 0
        assert payload["items"][0]["beat"]["flag"] == "ai_inferred"

    async def test_must_keep_lines_are_verbatim_from_source_dialogue(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id, set_intent=True)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        dialogues = [
            beat
            for scene in resp.json()["data"]["scenes"]
            for beat in scene["beats"]
            if beat["type"] == "dialogue"
        ]
        kept = [
            beat
            for beat in dialogues
            if beat["dialogue"] == intent_payload()["must_keep_lines"][0]
        ]
        assert kept
        assert kept[0]["source_ref"]["paragraphs"]
        assert kept[0]["flag"] == "from_source"

    async def test_dialogue_without_source_ref_gets_scene_trace_and_ai_flag(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)
        scene = outline["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "scene": {
                "scenes": [
                    {
                        **scene,
                        "beats": [
                            {
                                "type": "dialogue",
                                "character": scene["characters"][0],
                                "dialogue": "This line is newly inferred.",
                            },
                        ],
                    }
                ],
                "shot_hints": {"enabled": False},
            },
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        dialogue = resp.json()["data"]["scenes"][0]["beats"][0]
        assert dialogue["type"] == "dialogue"
        assert dialogue["source_ref"] == scene["source_ref"]
        assert dialogue["flag"] == "ai_inferred"

    async def test_filter_beats_by_source_reference(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)
        source_ref = outline["data"]["scenes"][0]["source_ref"]
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/beats",
            params={
                "source_chapter": source_ref["chapter"],
                "source_paragraph": source_ref["paragraphs"][0],
            },
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["count"] > 0
        assert {item["scene_id"] for item in payload["items"]} == {
            outline["data"]["scenes"][0]["id"]
        }
        assert all(
            item["beat"]["source_ref"]["chapter"] == source_ref["chapter"]
            and source_ref["paragraphs"][0]
            in item["beat"]["source_ref"]["paragraphs"]
            for item in payload["items"]
        )

    async def test_source_reference_filter_requires_complete_pair(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/beats",
            params={"source_chapter": 1},
        )

        assert resp.status_code == 422

    async def test_todos_empty_when_screenplay_has_no_todo_beats(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay/todos")

        assert resp.status_code == 200
        assert resp.json() == {"items": [], "count": 0}

    async def test_todos_return_scene_and_beat_locations(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)
        first_scene = outline["data"]["scenes"][0]
        second_scene = outline["data"]["scenes"][1]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "scene": {
                "scenes": [
                    {
                        **first_scene,
                        "beats": [
                            {
                                "type": "action",
                                "text": "Lin Wan opens the archive.",
                                "source_ref": first_scene["source_ref"],
                                "flag": "from_source",
                            },
                            {
                                "type": "todo",
                                "text": "TODO: author should supply the exact confrontation line.",
                                "source_ref": first_scene["source_ref"],
                            },
                        ],
                    },
                    {
                        **second_scene,
                        "beats": [
                            {
                                "type": "todo",
                                "text": "TODO: clarify whether Chen Mo notices the clue.",
                            }
                        ],
                    },
                ],
                "shot_hints": {"enabled": False},
            },
        }
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay/todos")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["count"] == 2
        assert payload["items"][0]["scene_id"] == first_scene["id"]
        assert payload["items"][0]["beat_index"] == 1
        assert payload["items"][0]["source_ref"] == first_scene["source_ref"]
        assert payload["items"][0]["beat"]["type"] == "todo"
        assert payload["items"][1]["scene_id"] == second_scene["id"]
        assert payload["items"][1]["beat_index"] == 0
        assert payload["items"][1]["source_ref"] is None
        assert payload["items"][1]["beat"]["source_ref"] is None

    async def test_todos_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay/todos")

        assert resp.status_code == 404

    async def test_todos_missing_project_returns_404(
        self, app_client: AsyncClient
    ) -> None:
        resp = await app_client.get("/api/v1/projects/missing/screenplay/todos")

        assert resp.status_code == 404

    async def test_missing_subtext_and_mood_are_annotated(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline(app_client, project_id)
        scene = outline["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "scene": {
                "scenes": [
                    {
                        **scene,
                        "mood": None,
                        "beats": [
                            {
                                "type": "action",
                                "text": "Lin Wan stops at the archive door.",
                                "source_ref": scene["source_ref"],
                                "flag": "from_source",
                            },
                            {
                                "type": "dialogue",
                                "character": scene["characters"][0],
                                "dialogue": "Not yet.",
                                "source_ref": scene["source_ref"],
                                "flag": "from_source",
                            },
                        ],
                    }
                ],
                "shot_hints": {"enabled": False},
            },
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )

        assert resp.status_code == 202
        generated_scene = resp.json()["data"]["scenes"][0]
        assert generated_scene["mood"] == scene["mood"]
        assert all(beat["subtext"] for beat in generated_scene["beats"])
        assert "Action carries" in generated_scene["beats"][0]["subtext"]
        assert "Underlying intent" in generated_scene["beats"][1]["subtext"]

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

    async def test_get_scene_trace_resolves_source_paragraphs(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001/trace"
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["scene_id"] == "sc_001"
        assert payload["source_ref"] == {"chapter": 1, "paragraphs": [1, 2]}
        assert payload["paragraphs"] == [
            {"index": 1, "text": "Lin Wan opened the archive."},
            {"index": 2, "text": "Chen Mo watched Lin Wan hide the letter."},
        ]
        assert payload["beats"]
        assert all("beat_index" in item for item in payload["beats"])
        assert payload["beats"][0]["source_ref"] == payload["source_ref"]
        assert payload["beats"][0]["flag"] in {"from_source", "ai_inferred"}

    async def test_get_scene_trace_missing_scene_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/missing/trace"
        )

        assert resp.status_code == 404

    async def test_get_scene_trace_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001/trace"
        )

        assert resp.status_code == 404

    async def test_get_scene_trace_missing_project_returns_404(
        self, app_client: AsyncClient
    ) -> None:
        resp = await app_client.get(
            "/api/v1/projects/missing/screenplay/scenes/sc_001/trace"
        )

        assert resp.status_code == 404

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
