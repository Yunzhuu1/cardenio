"""M8-T1 acceptance: backend MVP demo flow (PRD 10.3)."""

from httpx import AsyncClient

from cardenio.gateway.providers.stub import StubLlmGateway


class TestBackendDemoFlow:
    """Import -> understand -> profile -> intent -> outline -> screenplay -> report."""

    async def test_mvp_demo_flow_with_local_rewrite_and_recovery(
        self,
        app_client: AsyncClient,
        stub_gateway: StubLlmGateway,
    ) -> None:
        project_id = await create_project(app_client)
        await add_three_chapters(app_client, project_id)

        source_resp = await app_client.get(f"/api/v1/projects/{project_id}/source")
        assert source_resp.status_code == 200
        assert len(source_resp.json()["chapters"]) == 3

        understanding_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:generate"
        )
        assert understanding_resp.status_code == 202
        understanding = understanding_resp.json()
        assert understanding["type"] == "understanding"
        assert understanding["data"]["style_fingerprint"]
        understanding_confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/understanding:confirm"
        )
        assert understanding_confirm_resp.status_code == 200

        characters_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:generate"
        )
        assert characters_resp.status_code == 202
        characters = characters_resp.json()
        assert characters["type"] == "characters"
        characters_confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/characters:confirm"
        )
        assert characters_confirm_resp.status_code == 200

        intent_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=intent_payload(),
        )
        assert intent_resp.status_code == 200
        direction_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": "short_drama"},
        )
        assert direction_resp.status_code == 200

        outline_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline:generate"
        )
        assert outline_resp.status_code == 202
        outline = outline_resp.json()
        assert outline["data"]["scenes"]
        assert all(scene["source_ref"]["paragraphs"] for scene in outline["data"]["scenes"])
        outline_confirm_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/outline:confirm"
        )
        assert outline_confirm_resp.status_code == 200

        screenplay_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        assert screenplay_resp.status_code == 202
        screenplay = screenplay_resp.json()
        scenes = screenplay["data"]["scenes"]
        assert scenes
        assert all(scene["source_ref"]["paragraphs"] for scene in scenes)
        assert all(
            beat["source_ref"] and beat["flag"]
            for scene in scenes
            for beat in scene["beats"]
            if beat["type"] != "todo"
        )

        trace_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{scenes[0]['id']}/trace"
        )
        assert trace_resp.status_code == 200
        assert trace_resp.json()["paragraphs"]

        report_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/report:generate"
        )
        assert report_resp.status_code == 202
        report = report_resp.json()
        assert report["type"] == "report"
        assert report["parent_version"] == screenplay["version"]
        assert report["data"]["kept"]
        assert all(item["scene_id"] or item["source_ref"] for item in report["data"]["kept"])

        target_scene = scenes[0]
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "rewrite": {
                **target_scene,
                "synopsis": "The first conflict is pulled forward.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan shuts the archive door before Chen Mo can leave.",
                        "source_ref": target_scene["source_ref"],
                        "flag": "from_source",
                    }
                ],
            },
        }
        rewrite_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay/scenes/{target_scene['id']}:rewrite",
            json={"instruction": "Bring the first conflict forward."},
        )
        assert rewrite_resp.status_code == 202
        rewritten = rewrite_resp.json()
        assert rewritten["parent_version"] == screenplay["version"]
        assert rewritten["data"]["scenes"][0]["synopsis"] == (
            "The first conflict is pulled forward."
        )
        assert rewritten["data"]["scenes"][1:] == scenes[1:]

        versions_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/screenplay/versions"
        )
        assert versions_resp.status_code == 200
        assert versions_resp.json()["count"] == 2
        old_version_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/screenplay/versions/{screenplay['version']}"
        )
        assert old_version_resp.status_code == 200
        assert old_version_resp.json()["data"]["scenes"][0] == target_scene

        settings_resp = await app_client.get(f"/api/v1/projects/{project_id}/settings")
        assert settings_resp.status_code == 200
        assert settings_resp.json()["data"]["allow_model_training"] is False

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "editing"


async def create_project(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "e2e-demo-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


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


def intent_payload() -> dict:
    return {
        "keep": ["father-daughter confrontation"],
        "no_delete": ["the sealed letter"],
        "no_merge": ["Lin Wan", "Chen Mo"],
        "must_keep_lines": ["You hid this from me."],
        "mood_floor": "tense",
        "allow_new_plot": True,
        "allow_reorder": True,
        "allow_new_ending": False,
        "target_type": "short_drama",
    }
