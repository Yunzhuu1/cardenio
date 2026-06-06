"""M3-T1 acceptance: author intent constraints (FR-4)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(app_client: AsyncClient) -> str:
    resp = await app_client.post(
        "/api/v1/projects",
        json={
            "title": "intent-test",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def move_project_to_profiled(app_client: AsyncClient, project_id: str) -> None:
    chapters = [
        "Lin Wan opened the archive.\n\nChen Mo watched Lin Wan hide the letter.",
        "Lin Wan found another clue.\n\nOld Master Qiao warned Chen Mo.",
        "Chen Mo returned at dawn.\n\nLin Wan chose to confront the secret.",
    ]
    for index, text in enumerate(chapters):
        create_resp = await app_client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": f"Chapter {index + 1}", "text": text, "order": index + 1},
        )
        assert create_resp.status_code == 201

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


class TestAuthorIntent:
    """API-11: author intent is saved as a hard-constraint artifact."""

    async def test_set_and_get_intent_constraints(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=intent_payload(),
        )

        assert resp.status_code == 200
        saved = resp.json()
        assert saved["type"] == "intent"
        assert saved["state"] == "confirmed"
        assert saved["data"] == intent_payload()

        get_resp = await app_client.get(f"/api/v1/projects/{project_id}/intent")
        assert get_resp.status_code == 200
        assert get_resp.json()["version"] == saved["version"]
        assert get_resp.json()["data"]["must_keep_lines"] == ["You hid this from me."]

    async def test_updating_intent_creates_new_version(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        first_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=intent_payload(),
        )
        updated_payload = intent_payload()
        updated_payload["allow_new_plot"] = True
        updated_payload["keep"] = ["archive reveal"]

        second_resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=updated_payload,
        )

        assert second_resp.status_code == 200
        updated = second_resp.json()
        assert updated["parent_version"] == first_resp.json()["version"]
        assert updated["data"]["allow_new_plot"] is True
        assert updated["data"]["keep"] == ["archive reveal"]

    async def test_setting_intent_after_profiles_updates_project_state(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        await move_project_to_profiled(app_client, project_id)

        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent",
            json=intent_payload(),
        )
        assert resp.status_code == 200

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["state"] == "intent_set"

    async def test_missing_intent_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.get(f"/api/v1/projects/{project_id}/intent")
        assert resp.status_code == 404

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.put(
            "/api/v1/projects/missing/intent",
            json=intent_payload(),
        )
        assert resp.status_code == 404


class TestAdaptationDirection:
    """API-12: MVP adaptation direction can be selected and stored."""

    @pytest.mark.parametrize("direction", ["faithful", "cinematic", "short_drama"])
    async def test_set_mvp_direction_updates_project_meta(
        self, app_client: AsyncClient, project_id: str, direction: str
    ) -> None:
        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": direction},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["direction"] == direction
        assert data["project"]["adaptation_direction"] == direction

        project_resp = await app_client.get(f"/api/v1/projects/{project_id}")
        assert project_resp.status_code == 200
        assert project_resp.json()["adaptation_direction"] == direction

    async def test_non_mvp_direction_is_rejected(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": "tv"},
        )

        assert resp.status_code == 422

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.put(
            "/api/v1/projects/missing/intent/direction",
            json={"direction": "faithful"},
        )
        assert resp.status_code == 404


class TestIntentDirectionValidation:
    """API-13: direction-intent conflicts are surfaced without blocking."""

    async def test_faithful_direction_conflicts_with_new_ending(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        payload = intent_payload()
        payload["allow_new_ending"] = True
        await app_client.put(f"/api/v1/projects/{project_id}/intent", json=payload)
        await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": "faithful"},
        )

        resp = await app_client.post(f"/api/v1/projects/{project_id}/intent:validate")

        assert resp.status_code == 200
        conflicts = resp.json()["conflicts"]
        assert any(
            conflict["code"] == "faithful_vs_new_ending"
            and conflict["fields"] == ["direction", "allow_new_ending"]
            for conflict in conflicts
        )

    async def test_no_conflicts_returns_empty_list(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        payload = intent_payload()
        payload["allow_reorder"] = True
        payload["allow_new_ending"] = False
        payload["allow_new_plot"] = False
        await app_client.put(f"/api/v1/projects/{project_id}/intent", json=payload)
        await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": "cinematic"},
        )

        resp = await app_client.post(f"/api/v1/projects/{project_id}/intent:validate")

        assert resp.status_code == 200
        assert resp.json()["conflicts"] == []

    async def test_short_drama_conflicts_when_reorder_is_disallowed(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        payload = intent_payload()
        payload["allow_reorder"] = False
        await app_client.put(f"/api/v1/projects/{project_id}/intent", json=payload)
        await app_client.put(
            f"/api/v1/projects/{project_id}/intent/direction",
            json={"direction": "short_drama"},
        )

        resp = await app_client.post(f"/api/v1/projects/{project_id}/intent:validate")

        assert resp.status_code == 200
        assert resp.json()["conflicts"][0]["code"] == "short_drama_vs_no_reorder"

    async def test_missing_intent_returns_404(
        self, app_client: AsyncClient, project_id: str
    ) -> None:
        resp = await app_client.post(f"/api/v1/projects/{project_id}/intent:validate")
        assert resp.status_code == 404

    async def test_missing_project_returns_404(self, app_client: AsyncClient) -> None:
        resp = await app_client.post("/api/v1/projects/missing/intent:validate")
        assert resp.status_code == 404
