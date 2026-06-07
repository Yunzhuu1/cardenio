"""M4-T1 acceptance: outline generation (FR-6)."""

import pytest
from httpx import AsyncClient

from cardenio.gateway.providers.stub import StubLlmGateway


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


async def generate_outline(app_client: AsyncClient, project_id: str) -> dict:
    await move_project_to_confirmed_characters(app_client, project_id)
    resp = await app_client.post(f"/api/v1/projects/{project_id}/outline:generate")
    assert resp.status_code == 202
    return resp.json()


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
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
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
        assert stub_gateway.call_log[-1].task == "outline"
        assert stub_gateway.call_log[-1].output_schema is not None
        context = stub_gateway.call_log[-1].context
        assert context[0]["type"] == "adaptation_direction"
        assert context[1]["chapter_id"]
        assert context[-3]["type"] == "upstream_artifacts"
        assert context[-3]["data"]["understanding"] is not None
        assert context[-3]["data"]["characters"] is not None
        assert "intent" in context[-3]["data"]
        assert context[-2]["type"] == "repair_issues"
        assert context[-1]["type"] == "previous_output"
        constraints = stub_gateway.call_log[-1].system_constraints
        assert constraints.style_fingerprint
        assert constraints.voice
        assert constraints.hard_rules

        resolve_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/source:resolve",
            params={"chapter": 1, "paragraphs": "1-2"},
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["paragraphs"] == [
            {"index": 1, "text": "Lin Wan opened the archive."},
            {"index": 2, "text": "Chen Mo watched Lin Wan hide the letter."},
        ]

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == generated["version"]

    async def test_generated_source_refs_must_resolve_to_existing_paragraphs(
        self,
        app_client: AsyncClient,
        project_id: str,
        stub_gateway: StubLlmGateway,
    ) -> None:
        await move_project_to_confirmed_characters(app_client, project_id)
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "outline": {
                "scenes": [
                    {
                        "id": "sc_bad",
                        "heading": {
                            "int_ext": "INT",
                            "location": "Archive",
                            "time": "DAY",
                        },
                        "source_ref": {"chapter": 1, "paragraphs": [99]},
                        "synopsis": "Invalid source reference.",
                        "goal": "Test validation.",
                        "conflict": "Invalid reference should not be saved.",
                        "mood": "tense",
                        "characters": ["lin_wan"],
                        "foreshadowing": [],
                        "relation_changes": [],
                        "ending_state": "Blocked.",
                    }
                ],
                "merge_suggestions": [],
            },
        }

        resp = await app_client.post(f"/api/v1/projects/{project_id}/outline:generate")

        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "invalid_source_ref"

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        assert get_resp.status_code == 404

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


class TestOutlineEditing:
    """API-15: outline scenes are editable and saved as stable versions."""

    async def test_add_scene_appends_and_persists(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        new_scene = {
            "id": "sc_manual",
            "heading": {"int_ext": "INT", "location": "Archive", "time": "NIGHT"},
            "source_ref": {"chapter": 1, "paragraphs": [1]},
            "synopsis": "Lin Wan studies the first clue again.",
            "goal": "Clarify the clue before the next turn.",
            "conflict": "She wants certainty but only has fragments.",
            "mood": "tense",
            "characters": ["lin_wan"],
            "foreshadowing": ["The letter remains unresolved."],
            "relation_changes": [],
            "ending_state": "The clue points back to Chen Mo.",
        }

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/scenes",
            json=new_scene,
        )

        assert resp.status_code == 201
        saved = resp.json()
        assert saved["parent_version"] == generated["version"]
        assert saved["data"]["scenes"][-1]["id"] == "sc_manual"

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == saved["version"]

    async def test_update_scene_replaces_editable_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        scene = generated["data"]["scenes"][0]
        scene["synopsis"] = "Edited synopsis for the opening scene."
        scene["goal"] = "Edited scene goal."
        scene["heading"]["location"] = "Edited Archive"

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/outline/scenes/{scene['id']}",
            json=scene,
        )

        assert resp.status_code == 200
        saved = resp.json()
        assert saved["parent_version"] == generated["version"]
        edited = saved["data"]["scenes"][0]
        assert edited["synopsis"] == "Edited synopsis for the opening scene."
        assert edited["goal"] == "Edited scene goal."
        assert edited["heading"]["location"] == "Edited Archive"

    async def test_delete_scene_removes_only_target_scene(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        deleted_id = generated["data"]["scenes"][1]["id"]

        resp = await app_client.delete(
            f"/api/v1/projects/{project_id}/outline/scenes/{deleted_id}"
        )

        assert resp.status_code == 204
        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        scenes = get_resp.json()["data"]["scenes"]
        assert [scene["id"] for scene in scenes] == ["sc_001", "sc_003"]

    async def test_reorder_scenes_persists_exact_order(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/scenes:reorder",
            json={"order": ["sc_003", "sc_001", "sc_002"]},
        )

        assert resp.status_code == 200
        saved = resp.json()
        assert saved["parent_version"] == generated["version"]
        assert [scene["id"] for scene in saved["data"]["scenes"]] == [
            "sc_003",
            "sc_001",
            "sc_002",
        ]

    async def test_reorder_requires_every_scene_once(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_outline(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/scenes:reorder",
            json={"order": ["sc_001", "sc_001"]},
        )

        assert resp.status_code == 422

    async def test_confirm_outline_marks_latest_edit_confirmed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        scene = generated["data"]["scenes"][0]
        scene["synopsis"] = "Confirmed edited synopsis."
        update_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/outline/scenes/{scene['id']}",
            json=scene,
        )
        assert update_resp.status_code == 200

        confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline:confirm"
        )

        assert confirm_resp.status_code == 200
        confirmed = confirm_resp.json()
        assert confirmed["state"] == "confirmed"
        assert confirmed["parent_version"] == update_resp.json()["version"]
        assert confirmed["data"]["scenes"][0]["synopsis"] == "Confirmed edited synopsis."

    async def test_editing_missing_outline_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/scenes",
            json={
                "id": "sc_manual",
                "heading": {"int_ext": "INT", "location": "Archive", "time": "DAY"},
                "source_ref": {"chapter": 1, "paragraphs": [1]},
                "synopsis": "No outline exists yet.",
            },
        )

        assert resp.status_code == 404


class TestOutlineMergeSuggestions:
    """API-16: merge candidates are suggestions and never auto-merge scenes."""

    async def test_get_merge_suggestions_does_not_change_outline_structure(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        scene_ids_before = [
            scene["id"] for scene in generated["data"]["scenes"]
        ]

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions"
        )

        assert resp.status_code == 200
        suggestions = resp.json()["suggestions"]
        assert suggestions
        assert suggestions[0]["status"] == "pending"
        assert len(suggestions[0]["scene_ids"]) == 2

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/outline")
        scene_ids_after = [
            scene["id"] for scene in get_resp.json()["data"]["scenes"]
        ]
        assert scene_ids_after == scene_ids_before

    async def test_apply_merge_suggestion_marks_status_without_merging(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        suggestions_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions"
        )
        suggestion_id = suggestions_resp.json()["suggestions"][0]["id"]

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions/{suggestion_id}:apply"
        )

        assert resp.status_code == 200
        saved = resp.json()
        suggestion = saved["data"]["merge_suggestions"][0]
        assert suggestion["id"] == suggestion_id
        assert suggestion["status"] == "applied"
        assert [scene["id"] for scene in saved["data"]["scenes"]] == [
            scene["id"] for scene in generated["data"]["scenes"]
        ]

    async def test_dismiss_merge_suggestion_marks_status_without_merging(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        generated = await generate_outline(app_client, project_id)
        suggestions_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions"
        )
        suggestion_id = suggestions_resp.json()["suggestions"][0]["id"]

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions/{suggestion_id}:dismiss"
        )

        assert resp.status_code == 200
        saved = resp.json()
        suggestion = saved["data"]["merge_suggestions"][0]
        assert suggestion["id"] == suggestion_id
        assert suggestion["status"] == "dismissed"
        assert [scene["id"] for scene in saved["data"]["scenes"]] == [
            scene["id"] for scene in generated["data"]["scenes"]
        ]

    async def test_get_merge_suggestions_missing_outline_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions"
        )

        assert resp.status_code == 404

    async def test_missing_merge_suggestion_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_outline(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline/merge-suggestions/missing:apply"
        )

        assert resp.status_code == 404
