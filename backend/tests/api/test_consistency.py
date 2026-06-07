"""FR-9.4 acceptance: deterministic character rename consistency."""

from __future__ import annotations

import json

from httpx import AsyncClient


class TestCharacterRenameConsistency:
    """Global rename keeps character ids stable and updates text artifacts."""

    async def test_rename_requires_confirm_true(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)
        await generate_screenplay_flow(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/consistency:rename",
            json={"character_id": "lin_wan", "new_name": "Lin Yue"},
        )

        assert resp.status_code == 409
        assert resp.json()["detail"] == "Rename requires confirm=true"

    async def test_rename_character_updates_profiles_and_text_artifacts(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)
        generated = await generate_screenplay_flow(app_client, project_id)
        assert "Lin Wan" in json.dumps(generated["data"], ensure_ascii=False)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/consistency:rename",
            json={
                "character_id": "lin_wan",
                "new_name": "Lin Yue",
                "confirm": True,
            },
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["old_name"] == "Lin Wan"
        assert payload["new_name"] == "Lin Yue"
        changed = {item["type"]: item for item in payload["changed_artifacts"]}
        assert {"characters", "outline", "screenplay"} <= set(changed)
        assert changed["characters"]["replacements"] >= 1
        assert changed["screenplay"]["replacements"] >= 1

        characters_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/characters"
        )
        assert characters_resp.status_code == 200
        characters = characters_resp.json()
        renamed = next(
            character
            for character in characters["data"]["characters"]
            if character["id"] == "lin_wan"
        )
        assert renamed["name"] == "Lin Yue"
        assert "lin_wan" in {
            character["id"] for character in characters["data"]["characters"]
        }
        assert "Lin Wan" not in json.dumps(characters["data"], ensure_ascii=False)

        screenplay_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay"
        )
        assert screenplay_resp.status_code == 200
        screenplay_text = json.dumps(screenplay_resp.json()["data"], ensure_ascii=False)
        assert "Lin Yue" in screenplay_text
        assert "Lin Wan" not in screenplay_text
        assert screenplay_resp.json()["parent_version"] == generated["version"]

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "editing"

    async def test_rename_missing_character_returns_404(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)
        await generate_screenplay_flow(app_client, project_id)

        resp = await app_client.post(
            f"/api/v1/projects/{project_id}/consistency:rename",
            json={
                "character_id": "missing",
                "new_name": "Lin Yue",
                "confirm": True,
            },
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Character not found"

    async def test_rename_missing_project_returns_404(
        self,
        app_client: AsyncClient,
    ) -> None:
        resp = await app_client.post(
            "/api/v1/projects/missing/consistency:rename",
            json={
                "character_id": "lin_wan",
                "new_name": "Lin Yue",
                "confirm": True,
            },
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"


async def create_project(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "consistency-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def generate_screenplay_flow(app_client: AsyncClient, project_id: str) -> dict:
    await add_three_chapters(app_client, project_id)
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
    outline_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:generate"
    )
    assert outline_resp.status_code == 202
    outline_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:confirm"
    )
    assert outline_confirm_resp.status_code == 200
    screenplay_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/screenplay:generate"
    )
    assert screenplay_resp.status_code == 202
    return screenplay_resp.json()


async def add_three_chapters(app_client: AsyncClient, project_id: str) -> None:
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
