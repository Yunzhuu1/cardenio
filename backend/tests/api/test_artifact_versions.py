"""M8-T4 acceptance: artifact version recovery (NFR-6)."""

from httpx import AsyncClient


class TestArtifactVersionRecovery:
    """Saved artifact versions remain recoverable after later edits."""

    async def test_screenplay_versions_can_be_listed_and_recovered(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)
        generated = await generate_screenplay(app_client, project_id)
        original_data = generated["data"]
        edited_data = {
            **original_data,
            "scenes": [
                {
                    **original_data["scenes"][0],
                    "synopsis": "Edited synopsis after interruption.",
                },
                *original_data["scenes"][1:],
            ],
        }
        edit_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/screenplay",
            json=edited_data,
        )
        assert edit_resp.status_code == 200
        edited = edit_resp.json()

        list_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/screenplay/versions"
        )

        assert list_resp.status_code == 200
        history = list_resp.json()
        assert history["count"] == 2
        assert [item["version"] for item in history["items"]] == [
            edited["version"],
            generated["version"],
        ]
        assert history["items"][0]["parent_version"] == generated["version"]

        old_resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/screenplay/versions/{generated['version']}"
        )
        latest_resp = await app_client.get(f"/api/v1/projects/{project_id}/screenplay")

        assert old_resp.status_code == 200
        assert old_resp.json()["version"] == generated["version"]
        assert old_resp.json()["data"]["scenes"][0]["synopsis"] == (
            original_data["scenes"][0]["synopsis"]
        )
        assert latest_resp.status_code == 200
        assert latest_resp.json()["version"] == edited["version"]
        assert latest_resp.json()["data"]["scenes"][0]["synopsis"] == (
            "Edited synopsis after interruption."
        )

    async def test_missing_artifact_version_returns_404(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/screenplay/versions/missing"
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Artifact version not found"

    async def test_unsupported_artifact_type_returns_422(
        self,
        app_client: AsyncClient,
    ) -> None:
        project_id = await create_project(app_client)

        resp = await app_client.get(
            f"/api/v1/projects/{project_id}/artifacts/unknown/versions"
        )

        assert resp.status_code == 422


async def create_project(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "artifact-version-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def generate_screenplay(app_client: AsyncClient, project_id: str) -> dict:
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
    outline_confirm_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/outline:confirm"
    )
    assert outline_confirm_resp.status_code == 200
    screenplay_resp = await app_client.post(
        f"/api/v1/projects/{project_id}/screenplay:generate"
    )
    assert screenplay_resp.status_code == 202
    return screenplay_resp.json()


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
