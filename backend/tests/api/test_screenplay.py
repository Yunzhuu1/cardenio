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


async def generate_confirmed_outline_with_dark_style(
    app_client: AsyncClient,
    project_id: str,
) -> dict:
    await add_screenplay_source(app_client, project_id)
    understanding_payload = {
        "logline": "A sealed archive forces Lin Wan into a dangerous truth.",
        "synopsis": "Lin Wan and Chen Mo follow a hidden letter through old fear.",
        "themes": ["memory", "betrayal"],
        "protagonist_goal": "Expose the secret behind the letter.",
        "protagonist_fear": "The truth will destroy the last trusted bond.",
        "central_conflict": "Truth versus concealment.",
        "mood": "dark, tense, suspenseful",
        "style_fingerprint": "dark; tense, suspenseful; restrained; secret-driven",
        "narrative": {
            "perspective": "third_person_limited",
            "tense": "past",
            "unreliable": False,
        },
        "non_visualizable": [],
        "strengths": ["Strong suspense pressure."],
        "difficulties": ["Interior dread must stay restrained."],
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
    return outline_confirm_resp.json()


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
        assert stub_gateway.call_log[-1].task == "scene"
        assert stub_gateway.call_log[-1].output_schema is not None
        assert stub_gateway.call_log[-1].system_constraints.shot_hints_enabled is True
        context = stub_gateway.call_log[-1].context
        assert context[0]["type"] == "adaptation_direction"
        assert context[1]["type"] == "request"
        assert context[1]["data"]["shot_hints"] is True
        assert context[-3]["type"] == "upstream_artifacts"
        assert context[-3]["data"]["outline"]["scenes"]
        assert context[-3]["data"]["character_voices"]
        assert "author_intent" in context[-3]["data"]
        assert "non_visualizable" in context[-3]["data"]
        assert context[-2]["type"] == "repair_issues"
        assert context[-1]["type"] == "previous_output"

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

    async def test_style_guard_prevents_light_mood_from_overriding_dark_source(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline_with_dark_style(
            app_client, project_id
        )
        scene = outline["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "scene": {
                "scenes": [
                    {
                        **scene,
                        "mood": "light, humorous",
                        "beats": [
                            {
                                "type": "action",
                                "text": "Lin Wan treats the archive like a joke.",
                                "source_ref": scene["source_ref"],
                                "flag": "from_source",
                            }
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
        assert generated_scene["mood"] != "light, humorous"
        assert "Action carries" in generated_scene["beats"][0]["subtext"]
        assert scene["mood"] in generated_scene["beats"][0]["subtext"]

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

    async def test_update_full_screenplay_saves_new_version_and_preserves_trust_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        data = generated["data"]
        data["scenes"][0]["mood"] = "quiet dread"
        data["scenes"][0]["beats"][0]["text"] = "Lin Wan pauses at the archive door."
        original_source_ref = data["scenes"][0]["beats"][0]["source_ref"]
        original_flag = data["scenes"][0]["beats"][0]["flag"]
        original_subtext = data["scenes"][0]["beats"][0]["subtext"]

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=data,
        )

        assert resp.status_code == 200
        saved = resp.json()
        assert saved["type"] == "screenplay"
        assert saved["state"] == "draft"
        assert saved["parent_version"] == generated["version"]
        assert saved["version"] != generated["version"]
        first_beat = saved["data"]["scenes"][0]["beats"][0]
        assert saved["data"]["scenes"][0]["mood"] == "quiet dread"
        assert first_beat["text"] == "Lin Wan pauses at the archive door."
        assert first_beat["source_ref"] == original_source_ref
        assert first_beat["flag"] == original_flag
        assert first_beat["subtext"] == original_subtext

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "editing"

    async def test_update_single_scene_only_replaces_target_scene(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        original_scenes = generated["data"]["scenes"]
        edited_scene = {**original_scenes[0], "synopsis": "Edited scene synopsis."}
        edited_scene["beats"] = [
            {
                **beat,
                "text": "Edited action beat."
                if beat["type"] == "action" and index == 0
                else beat.get("text"),
            }
            for index, beat in enumerate(edited_scene["beats"])
        ]

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{edited_scene['id']}",
            json=edited_scene,
        )

        assert resp.status_code == 200
        saved = resp.json()
        assert saved["parent_version"] == generated["version"]
        assert saved["data"]["scenes"][0]["synopsis"] == "Edited scene synopsis."
        assert saved["data"]["scenes"][0]["beats"][0]["text"] == "Edited action beat."
        assert saved["data"]["scenes"][1:] == original_scenes[1:]

        scene_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{edited_scene['id']}"
        )
        assert scene_resp.status_code == 200
        assert scene_resp.json()["synopsis"] == "Edited scene synopsis."

    async def test_list_scene_versions_returns_scene_history(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        original_scene = generated["data"]["scenes"][0]
        edited_scene = {**original_scene, "synopsis": "Versioned scene edit."}
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{original_scene['id']}",
            json=edited_scene,
        )
        assert edit_resp.status_code == 200
        edited = edit_resp.json()

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{original_scene['id']}/versions"
        )

        assert resp.status_code == 200
        history = resp.json()
        assert history["count"] == 2
        assert [item["version"] for item in history["items"]] == [
            edited["version"],
            generated["version"],
        ]
        assert history["items"][0]["parent_version"] == generated["version"]
        assert history["items"][0]["scene"]["synopsis"] == "Versioned scene edit."
        assert history["items"][1]["scene"] == original_scene

    async def test_list_scene_versions_skips_versions_without_scene(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        removed_scene = generated["data"]["scenes"][1]
        data = {
            **generated["data"],
            "scenes": [generated["data"]["scenes"][0]],
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=data,
        )
        assert edit_resp.status_code == 200

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{removed_scene['id']}/versions"
        )

        assert resp.status_code == 200
        history = resp.json()
        assert history["count"] == 1
        assert history["items"][0]["version"] == generated["version"]
        assert history["items"][0]["scene"] == removed_scene

    async def test_list_scene_versions_missing_scene_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/missing/versions"
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene not found"

    async def test_list_scene_versions_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001/versions"
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Screenplay not found"

    async def test_list_scene_versions_missing_project_returns_404(
        self, app_client: AsyncClient
    ) -> None:
        resp = await app_client.get(
            "/api/v1/projects/missing/screenplay/scenes/sc_001/versions"
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    async def test_checkout_scene_version_restores_scene_only(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        original_scenes = generated["data"]["scenes"]
        edited_scene = {
            **original_scenes[0],
            "synopsis": "Edited before checkout.",
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{edited_scene['id']}",
            json=edited_scene,
        )
        assert edit_resp.status_code == 200
        edited = edit_resp.json()

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{edited_scene['id']}:checkout",
            json={"version": generated["version"]},
        )

        assert resp.status_code == 200
        checked_out = resp.json()
        assert checked_out["parent_version"] == edited["version"]
        assert checked_out["version"] not in {generated["version"], edited["version"]}
        assert checked_out["data"]["scenes"][0] == original_scenes[0]
        assert checked_out["data"]["scenes"][1:] == edited["data"]["scenes"][1:]

        latest_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{edited_scene['id']}"
        )
        assert latest_resp.status_code == 200
        assert latest_resp.json() == original_scenes[0]

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "editing"

    async def test_checkout_scene_version_missing_version_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001:checkout",
            json={"version": "missing"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene version not found"

    async def test_checkout_scene_version_missing_scene_in_version_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        target_scene = generated["data"]["scenes"][1]
        data = {
            **generated["data"],
            "scenes": [generated["data"]["scenes"][0]],
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=data,
        )
        assert edit_resp.status_code == 200
        version_without_scene = edit_resp.json()
        restore_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=generated["data"],
        )
        assert restore_resp.status_code == 200

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}:checkout",
            json={"version": version_without_scene["version"]},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene version not found"

    async def test_checkout_scene_version_blank_version_returns_422(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001:checkout",
            json={"version": "   "},
        )

        assert resp.status_code == 422

    async def test_diff_scene_versions_reports_structured_changes(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        original_scene = generated["data"]["scenes"][0]
        edited_scene = {
            **original_scene,
            "synopsis": "Diff target synopsis.",
            "mood": "quiet dread",
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{original_scene['id']}",
            json=edited_scene,
        )
        assert edit_resp.status_code == 200
        edited = edit_resp.json()

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{original_scene['id']}/versions:diff",
            params={"a": generated["version"], "b": edited["version"]},
        )

        assert resp.status_code == 200
        diff = resp.json()
        assert diff["scene_id"] == original_scene["id"]
        assert diff["a"]["version"] == generated["version"]
        assert diff["b"]["version"] == edited["version"]
        assert diff["a"]["scene"] == original_scene
        assert diff["b"]["scene"]["synopsis"] == "Diff target synopsis."
        assert diff["changed"] is True
        changes = {item["path"]: item for item in diff["changes"]}
        assert changes["synopsis"]["from"] == original_scene["synopsis"]
        assert changes["synopsis"]["to"] == "Diff target synopsis."
        assert changes["mood"]["from"] == original_scene["mood"]
        assert changes["mood"]["to"] == "quiet dread"

    async def test_diff_scene_versions_same_version_has_no_changes(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        scene_id = generated["data"]["scenes"][0]["id"]

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}/versions:diff",
            params={"a": generated["version"], "b": generated["version"]},
        )

        assert resp.status_code == 200
        diff = resp.json()
        assert diff["changed"] is False
        assert diff["changes"] == []

    async def test_diff_scene_versions_missing_version_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        scene_id = generate_resp.json()["data"]["scenes"][0]["id"]

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}/versions:diff",
            params={"a": generate_resp.json()["version"], "b": "missing"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene version not found"

    async def test_diff_scene_versions_missing_scene_in_version_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        target_scene = generated["data"]["scenes"][1]
        data = {
            **generated["data"],
            "scenes": [generated["data"]["scenes"][0]],
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=data,
        )
        assert edit_resp.status_code == 200
        version_without_scene = edit_resp.json()

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}/versions:diff",
            params={"a": generated["version"], "b": version_without_scene["version"]},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene version not found"

    async def test_update_scene_rejects_path_body_id_mismatch(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        scene = generate_resp.json()["data"]["scenes"][0]
        scene["id"] = "different_scene"

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001",
            json=scene,
        )

        assert resp.status_code == 422

    async def test_update_scene_missing_scene_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        scene = generate_resp.json()["data"]["scenes"][0]
        scene["id"] = "missing"

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay/scenes/missing",
            json=scene,
        )

        assert resp.status_code == 404

    async def test_update_screenplay_rejects_missing_trust_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        data = generate_resp.json()["data"]
        data["scenes"][0]["beats"][0].pop("source_ref")

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=data,
        )

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["code"] == "missing_trust_fields"
        assert detail["items"][0]["scene_id"] == data["scenes"][0]["id"]
        assert detail["items"][0]["fields"] == ["source_ref"]

    async def test_update_screenplay_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json={"scenes": [], "shot_hints": {"enabled": False}},
        )

        assert resp.status_code == 404

    async def test_rewrite_scene_only_replaces_target_scene(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        generated = generate_resp.json()
        original_scenes = generated["data"]["scenes"]
        target_scene = original_scenes[0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "rewrite": {
                **target_scene,
                "synopsis": "The confrontation starts earlier.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan closes the archive door before Chen Mo can leave.",
                        "source_ref": target_scene["source_ref"],
                        "flag": "from_source",
                    },
                    {
                        "type": "dialogue",
                        "character": target_scene["characters"][0],
                        "dialogue": "You hid this from me.",
                        "source_ref": target_scene["source_ref"],
                        "flag": "from_source",
                    },
                ],
            },
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}:rewrite",
            json={"instruction": "Bring the conflict forward."},
        )

        assert resp.status_code == 202
        saved = resp.json()
        assert saved["parent_version"] == generated["version"]
        assert saved["version"] != generated["version"]
        assert saved["data"]["scenes"][0]["id"] == target_scene["id"]
        assert saved["data"]["scenes"][0]["synopsis"] == "The confrontation starts earlier."
        assert saved["data"]["scenes"][0]["beats"][0]["text"].startswith("Lin Wan closes")
        assert saved["data"]["scenes"][1:] == original_scenes[1:]
        assert stub_gateway.call_log[-1].task == "rewrite"
        assert stub_gateway.call_log[-1].output_schema is not None
        context = stub_gateway.call_log[-1].context
        assert context[0]["type"] == "rewrite_request"
        assert context[0]["data"]["instruction"] == (
            "Bring the conflict forward."
        )
        assert context[0]["data"]["scene_id"] == target_scene["id"]
        assert context[-3]["type"] == "upstream_artifacts"
        upstream = context[-3]["data"]
        assert upstream["target_scene"]["id"] == target_scene["id"]
        assert "next" in upstream["adjacent_scenes"]
        assert upstream["source_paragraphs"]
        assert upstream["character_voices"]
        assert "author_intent" in upstream
        assert "understanding" in upstream
        assert context[-2]["type"] == "repair_issues"
        assert context[-1]["type"] == "previous_output"

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "editing"

    async def test_rewrite_scene_backfills_missing_trust_fields(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        target_scene = generate_resp.json()["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "rewrite": {
                **target_scene,
                "beats": [
                    {
                        "type": "action",
                        "text": "A newly sharpened action beat.",
                    },
                    {
                        "type": "dialogue",
                        "character": target_scene["characters"][0],
                        "dialogue": "Not another secret.",
                    },
                ],
            },
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}:rewrite",
            json={"instruction": "Make it sharper."},
        )

        assert resp.status_code == 202
        beats = resp.json()["data"]["scenes"][0]["beats"]
        assert all(beat["source_ref"] == target_scene["source_ref"] for beat in beats)
        assert all(beat["flag"] == "ai_inferred" for beat in beats)

    async def test_rewrite_scene_requires_non_blank_instruction(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        scene_id = generate_resp.json()["data"]["scenes"][0]["id"]

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}:rewrite",
            json={"instruction": "   "},
        )

        assert resp.status_code == 422

    async def test_rewrite_scene_missing_scene_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_outline(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/missing:rewrite",
            json={"instruction": "Make the conflict clearer."},
        )

        assert resp.status_code == 404

    async def test_rewrite_scene_missing_screenplay_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/sc_001:rewrite",
            json={"instruction": "Make the conflict clearer."},
        )

        assert resp.status_code == 404

    async def test_rewrite_scene_keeps_dark_style_anchor(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        outline = await generate_confirmed_outline_with_dark_style(
            app_client, project_id
        )
        scene = outline["data"]["scenes"][0]
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        assert generate_resp.status_code == 202
        target_scene = generate_resp.json()["data"]["scenes"][0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "rewrite": {
                **target_scene,
                "mood": "cheerful comedy",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan laughs off the danger.",
                        "source_ref": target_scene["source_ref"],
                        "flag": "from_source",
                    }
                ],
            },
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}:rewrite",
            json={"instruction": "Make this scene lighter."},
        )

        assert resp.status_code == 202
        rewritten = resp.json()["data"]["scenes"][0]
        assert rewritten["mood"] == scene["mood"]
        assert rewritten["mood"] != "cheerful comedy"

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
