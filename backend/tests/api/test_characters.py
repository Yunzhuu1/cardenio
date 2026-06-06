"""M2-T4 acceptance: character profile extraction and editing (FR-3)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "characters-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def add_character_source(app_client: AsyncClient, project_id: str) -> None:
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


async def generate_confirmed_understanding(
    app_client: AsyncClient,
    project_id: str,
) -> None:
    await add_character_source(app_client, project_id)
    generate_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/understanding:generate"
    )
    assert generate_resp.status_code == 202
    confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/understanding:confirm"
    )
    assert confirm_resp.status_code == 200


class TestCharacterProfiles:
    """API-9/10: character profiles are generated, editable, and confirmable."""

    async def test_generate_requires_confirmed_understanding(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:generate"
        )

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "state_gate_blocked"
        assert error["details"]["artifact"] == "understanding"

    async def test_generate_and_get_character_profiles(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_understanding(app_client, project_id)

        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:generate"
        )
        assert generate_resp.status_code == 202
        generated = generate_resp.json()
        assert generated["type"] == "characters"
        assert generated["state"] == "draft"
        characters = generated["data"]["characters"]
        assert len(characters) >= 2
        assert {character["name"] for character in characters} >= {"Lin Wan", "Chen Mo"}
        roles = {character["name"]: character["role"] for character in characters}
        assert roles["Lin Wan"] == "protagonist"
        assert roles["Chen Mo"] == "supporting"
        assert roles["Old Master Qiao"] == "mentioned"
        assert all(character["voice"] for character in characters)
        assert all(character["desire"] for character in characters)
        assert all(character["fear"] for character in characters)
        assert all(character["hard_rules"] for character in characters)
        lin_wan = next(character for character in characters if character["name"] == "Lin Wan")
        assert any(
            relation["to"] == "chen_mo" and relation["type"] == "co_occurs"
            for relation in lin_wan["relations"]
        )

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/characters")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == generated["version"]

    async def test_update_character_persists_editable_fields(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_understanding(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:generate"
        )
        character = generate_resp.json()["data"]["characters"][0]
        character["voice"] = "Quiet, clipped, avoids direct answers."
        character["hard_rules"] = ["Never volunteers the whole truth."]

        update_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/characters/{character['id']}",
            json=character,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["parent_version"] == generate_resp.json()["version"]
        edited = updated["data"]["characters"][0]
        assert edited["voice"] == "Quiet, clipped, avoids direct answers."
        assert edited["hard_rules"] == ["Never volunteers the whole truth."]

    async def test_add_and_delete_character(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_understanding(app_client, project_id)
        await app_client.post(f"/api/v1/projects/{project_id}/characters:generate")

        add_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters",
            json={
                "id": "archivist_ren",
                "name": "Archivist Ren",
                "role": "supporting",
                "voice": "Slow, formal warnings.",
                "desire": "Protect the old secret.",
                "fear": "The secret becoming public.",
                "arc": "Moves from warning to confession.",
                "relations": [],
                "hard_rules": ["Speaks indirectly."],
            },
        )
        assert add_resp.status_code == 201
        assert any(
            character["id"] == "archivist_ren"
            for character in add_resp.json()["data"]["characters"]
        )

        delete_resp = await app_client.delete(
            f"/api/v1/projects/{project_id}/characters/archivist_ren"
        )
        assert delete_resp.status_code == 204
        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/characters")
        assert all(
            character["id"] != "archivist_ren"
            for character in get_resp.json()["data"]["characters"]
        )

    async def test_confirm_characters_marks_gate_confirmed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await generate_confirmed_understanding(app_client, project_id)
        generate_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:generate"
        )

        confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:confirm"
        )
        assert confirm_resp.status_code == 200
        confirmed = confirm_resp.json()
        assert confirmed["state"] == "confirmed"
        assert confirmed["parent_version"] == generate_resp.json()["version"]

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/characters")
        assert get_resp.json()["state"] == "confirmed"

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.post("/api/v1/projects/missing/characters:generate")
        assert resp.status_code == 404
