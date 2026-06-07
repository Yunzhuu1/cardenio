"""M7-T1 acceptance: adaptation tradeoff report generation (FR-10)."""

from httpx import AsyncClient

from cardenio.gateway.providers.stub import StubLlmGateway


async def create_project(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "report-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def add_source(app_client: AsyncClient, project_id: str) -> None:
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


async def generate_confirmed_outline(app_client: AsyncClient, project_id: str) -> dict:
    await add_source(app_client, project_id)
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
    confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:confirm"
    )
    assert confirm_resp.status_code == 200
    return confirm_resp.json()


async def generate_screenplay(app_client: AsyncClient, project_id: str) -> dict:
    await generate_confirmed_outline(app_client, project_id)
    resp = await app_client.post(f"/api/v1/projects/{project_id}/screenplay:generate")
    assert resp.status_code == 202
    return resp.json()


class TestReportGeneration:
    """API-25/26: report can be generated from a screenplay artifact."""

    async def test_generate_report_from_screenplay_artifact(
        self,
        app_client: AsyncClient,
        stub_gateway: StubLlmGateway,
    ) -> None:
        project_id = await create_project(app_client)
        screenplay = await generate_screenplay(app_client, project_id)
        screenplay_beats = [
            beat
            for scene in screenplay["data"]["scenes"]
            for beat in scene["beats"]
            if beat["type"] != "todo"
        ]

        resp = await app_client.post(f"/api/v1/projects/{project_id}/report:generate")

        assert resp.status_code == 202
        report = resp.json()
        assert report["type"] == "report"
        assert report["state"] == "draft"
        assert report["parent_version"] == screenplay["version"]
        data = report["data"]
        assert data["from_source_lines"] == len(
            [beat for beat in screenplay_beats if beat["flag"] == "from_source"]
        )
        assert data["ai_inferred_lines"] == len(
            [beat for beat in screenplay_beats if beat["flag"] == "ai_inferred"]
        )
        assert data["kept"]
        assert all(item["scene_id"] or item["source_ref"] for item in data["kept"])
        assert stub_gateway.call_log[-1].task == "report"
        context = {item["type"]: item["data"] for item in stub_gateway.call_log[-1].context}
        assert context["flag_statistics"] == {
            "from_source_lines": data["from_source_lines"],
            "ai_inferred_lines": data["ai_inferred_lines"],
        }

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/report")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == report["version"]

    async def test_report_tracks_ai_inferred_items_for_review(
        self,
        app_client: AsyncClient,
        stub_gateway: StubLlmGateway,
    ) -> None:
        project_id = await create_project(app_client)
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
                                "source_ref": scene["source_ref"],
                                "flag": "ai_inferred",
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
        screenplay_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/screenplay:generate"
        )
        assert screenplay_resp.status_code == 202

        resp = await app_client.post(f"/api/v1/projects/{project_id}/report:generate")

        assert resp.status_code == 202
        data = resp.json()["data"]
        assert data["from_source_lines"] == 1
        assert data["ai_inferred_lines"] == 1
        assert data["added"][0]["scene_id"] == scene["id"]
        assert data["added"][0]["source_ref"] == scene["source_ref"]
        assert data["added"][0]["flag"] == "ai_inferred"
        assert data["review_recommended"][0]["scene_id"] == scene["id"]

    async def test_report_rejects_generated_flag_count_mismatch(
        self,
        app_client: AsyncClient,
        stub_gateway: StubLlmGateway,
    ) -> None:
        project_id, scene = await generate_screenplay_with_ai_inferred_beat(
            app_client,
            stub_gateway,
        )
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "report": {
                "kept": [],
                "added": [],
                "from_source_lines": 99,
                "ai_inferred_lines": 0,
            },
        }

        resp = await app_client.post(f"/api/v1/projects/{project_id}/report:generate")

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "report_flag_mismatch"
        assert error["details"]["statistics"]["from_source_lines"] == {
            "expected": 1,
            "actual": 99,
        }
        assert scene["id"]

    async def test_report_rejects_missing_ai_inferred_report_items(
        self,
        app_client: AsyncClient,
        stub_gateway: StubLlmGateway,
    ) -> None:
        project_id, scene = await generate_screenplay_with_ai_inferred_beat(
            app_client,
            stub_gateway,
        )
        stub_gateway.fixtures = {
            **stub_gateway.fixtures,
            "report": {
                "kept": [
                    {
                        "item": "You hid this from me.",
                        "scene_id": scene["id"],
                        "source_ref": scene["source_ref"],
                        "flag": "from_source",
                    }
                ],
                "added": [],
                "from_source_lines": 1,
                "ai_inferred_lines": 1,
            },
        }

        resp = await app_client.post(f"/api/v1/projects/{project_id}/report:generate")

        assert resp.status_code == 409
        error = resp.json()["error"]
        assert error["code"] == "report_flag_mismatch"
        assert error["details"]["added"] == {
            "expected_ai_inferred_items": 1,
            "actual_ai_inferred_items": 0,
        }

    async def test_report_generation_requires_screenplay(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)

        resp = await app_client.post(f"/api/v1/projects/{project_id}/report:generate")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Screenplay not found"

    async def test_get_report_missing_report_returns_404(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)

        resp = await app_client.get(f"/api/v1/projects/{project_id}/report")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Report not found"

    async def test_report_missing_project_returns_404(
        self,
        app_client: AsyncClient,
    ) -> None:
        resp = await app_client.post("/api/v1/projects/missing/report:generate")

        assert resp.status_code == 404


async def generate_screenplay_with_ai_inferred_beat(
    app_client: AsyncClient,
    stub_gateway: StubLlmGateway,
) -> tuple[str, dict]:
    project_id = await create_project(app_client)
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
                            "source_ref": scene["source_ref"],
                            "flag": "ai_inferred",
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
    screenplay_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/screenplay:generate"
    )
    assert screenplay_resp.status_code == 202
    return project_id, scene
