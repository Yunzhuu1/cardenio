"""Rewrite service orchestration tests."""

from __future__ import annotations

from typing import Any

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.services.rewrite_service import RewriteService
from cardenio.domain.tools import ToolRegistry
from cardenio.domain.tools.rewrite import RewriteSceneToolInput, RewriteSceneToolOutput
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class FakeStore:
    def __init__(self) -> None:
        self.project: dict[str, Any] = {
            "id": "proj_1",
            "state": ProjectState.GENERATED,
            "style_fingerprint": "restrained; tense",
        }
        self.artifacts: dict[str, ArtifactEnvelope[Any]] = {
            "screenplay": _artifact("screenplay", "v_screenplay", _screenplay_data()),
        }
        self.saved: ArtifactEnvelope[Any] | None = None
        self.updated_state: ProjectState | None = None

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.project if project_id == "proj_1" else None

    async def get_artifact(
        self,
        project_id: str,
        artifact_type: str,
    ) -> ArtifactEnvelope[Any] | None:
        if project_id != "proj_1":
            return None
        return self.artifacts.get(artifact_type)

    async def save_artifact(
        self,
        project_id: str,
        artifact: ArtifactEnvelope[Any],
    ) -> ArtifactEnvelope[Any]:
        assert project_id == "proj_1"
        self.saved = artifact
        return artifact

    async def update_project_state(self, project_id: str, state: ProjectState) -> None:
        assert project_id == "proj_1"
        self.updated_state = state
        self.project["state"] = state

    async def get_paragraphs(
        self,
        project_id: str,
        chapter_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if project_id != "proj_1" or chapter_id != "ch_1":
            return []
        return [
            {
                "chapter_id": "ch_1",
                "paragraph_index": 1,
                "text": "Lin Wan opened the archive.",
            },
            {
                "chapter_id": "ch_1",
                "paragraph_index": 2,
                "text": "Chen Mo watched her hide the letter.",
            },
        ]


class FakeGateway:
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        raise AssertionError("Runtime test should not call the gateway directly")


class RecordingRewriteTool:
    name = "rewrite.scene"
    input_model = RewriteSceneToolInput
    output_model = RewriteSceneToolOutput

    def __init__(self) -> None:
        self.context_scene_id: str | None = None
        self.request_scene_id: str | None = None

    async def run(self, input_data: RewriteSceneToolInput) -> RewriteSceneToolOutput:
        context = input_data.context
        self.context_scene_id = context.upstream_artifacts["target_scene"]["id"]
        self.request_scene_id = context.source_chunks[0]["data"]["scene_id"]
        return RewriteSceneToolOutput(
            data={
                **context.upstream_artifacts["target_scene"],
                "synopsis": "The confrontation starts earlier.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan closes the archive door.",
                    }
                ],
            },
            status="ok",
            attempts=1,
            usage={},
        )


async def test_rewrite_service_runs_agent_through_runtime() -> None:
    store = FakeStore()
    tool = RecordingRewriteTool()
    service = RewriteService(
        gateway=FakeGateway(),
        store=store,
        tools=ToolRegistry([tool]),
    )

    saved = await service.rewrite_scene(
        "proj_1",
        "sc_001",
        "Bring the conflict forward.",
    )

    assert tool.context_scene_id == "sc_001"
    assert tool.request_scene_id == "sc_001"
    assert store.saved is not None
    assert store.saved.parent_version == "v_screenplay"
    assert store.updated_state == ProjectState.EDITING
    rewritten = saved["data"]["scenes"][0]
    assert rewritten["synopsis"] == "The confrontation starts earlier."
    assert rewritten["beats"][0]["source_ref"] == {"chapter": 1, "paragraphs": [1, 2]}
    assert rewritten["beats"][0]["flag"] == "ai_inferred"


def _artifact(
    artifact_type: str,
    version: str,
    data: dict[str, Any],
) -> ArtifactEnvelope[Any]:
    return ArtifactEnvelope(
        type=artifact_type,
        state=ArtifactState.DRAFT,
        version=version,
        data=data,
    )


def _screenplay_data() -> dict[str, Any]:
    return {
        "scenes": [
            {
                "id": "sc_001",
                "heading": {"int_ext": "INT", "location": "Archive", "time": "NIGHT"},
                "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                "synopsis": "Lin Wan confronts the hidden letter.",
                "goal": "Force the truth into the open.",
                "conflict": "Truth versus concealment.",
                "mood": "tense",
                "characters": ["lin_wan"],
                "foreshadowing": [],
                "relation_changes": [],
                "ending_state": "The letter is exposed.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan opens the archive.",
                        "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                        "flag": "from_source",
                    }
                ],
            }
        ],
        "shot_hints": {"enabled": False},
    }
