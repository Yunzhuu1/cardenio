"""Outline service orchestration tests."""

from __future__ import annotations

from typing import Any

from cardenio.domain.agents.base import AgentContext, AgentProtocol
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.runtime import AgentRuntimeResult
from cardenio.domain.services.outline_service import OutlineService
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class FakeStore:
    def __init__(self) -> None:
        self.project: dict[str, Any] = {
            "id": "proj_1",
            "state": ProjectState.INTENT_SET,
            "adaptation_direction": "short_drama",
            "style_fingerprint": "restrained; tense",
        }
        self.artifacts: dict[str, ArtifactEnvelope[Any]] = {
            "characters": _artifact(
                "characters",
                "v_characters",
                _characters_data(),
                state=ArtifactState.CONFIRMED,
            ),
            "understanding": _artifact(
                "understanding",
                "v_understanding",
                {"style_fingerprint": "restrained; tense"},
                state=ArtifactState.CONFIRMED,
            ),
            "intent": _artifact(
                "intent",
                "v_intent",
                {"keep": ["sealed letter"], "allow_new_plot": False},
            ),
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

    async def list_chapters(self, project_id: str) -> list[dict[str, Any]]:
        if project_id != "proj_1":
            return []
        return [
            {
                "id": "ch_1",
                "title": "Chapter 1",
                "order": 1,
                "paragraphs": [
                    {"index": 1, "text": "Lin Wan opened the archive."},
                    {"index": 2, "text": "Chen Mo watched her hide the letter."},
                ],
            }
        ]

    async def get_paragraphs(
        self,
        project_id: str,
        chapter_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if project_id != "proj_1" or chapter_id != "ch_1":
            return []
        return [
            {"chapter_id": "ch_1", "paragraph_index": 1, "text": "Lin Wan opened."},
            {"chapter_id": "ch_1", "paragraph_index": 2, "text": "Chen Mo watched."},
        ]

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


class FakeGateway:
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        raise AssertionError("Runtime test should not call the gateway directly")


class RecordingRuntime:
    def __init__(self) -> None:
        self.agent_task: str | None = None
        self.context: AgentContext | None = None

    async def run(
        self,
        *,
        agent: AgentProtocol,
        context: AgentContext,
    ) -> AgentRuntimeResult:
        self.agent_task = agent.task_name
        self.context = context
        return AgentRuntimeResult(
            data={
                "scenes": [
                    {
                        "id": "sc_001",
                        "heading": {
                            "int_ext": "INT",
                            "location": "Archive",
                            "time": "NIGHT",
                        },
                        "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                        "synopsis": "Lin Wan confronts the hidden letter.",
                        "goal": "Force the truth into the open.",
                        "conflict": "Truth versus concealment.",
                        "mood": "tense",
                        "characters": ["lin_wan"],
                        "foreshadowing": ["The letter remains traceable."],
                        "relation_changes": [],
                        "ending_state": "The letter is exposed.",
                    }
                ],
                "merge_suggestions": [],
            },
            status="ok",
            attempts=1,
            usage={},
        )


async def test_outline_service_runs_agent_through_runtime() -> None:
    store = FakeStore()
    runtime = RecordingRuntime()
    service = OutlineService(
        gateway=FakeGateway(),
        store=store,
        runtime=runtime,
    )

    saved = await service.generate_outline("proj_1")

    assert runtime.agent_task == "outline"
    assert runtime.context is not None
    assert runtime.context.source_chunks[0] == {
        "type": "adaptation_direction",
        "data": "short_drama",
    }
    assert runtime.context.source_chunks[1]["chapter_id"] == "ch_1"
    assert runtime.context.upstream_artifacts["characters"] == _characters_data()
    assert runtime.context.upstream_artifacts["intent"] == {
        "keep": ["sealed letter"],
        "allow_new_plot": False,
    }
    assert runtime.context.system_constraints == {
        "style_fingerprint": "restrained; tense",
        "voice": {"lin_wan": "Quiet, clipped."},
        "hard_rules": ["Do not make Lin Wan cheerful."],
        "author_intent": {"keep": ["sealed letter"], "allow_new_plot": False},
    }
    assert store.saved is not None
    assert store.saved.type == "outline"
    assert store.updated_state == ProjectState.OUTLINED
    assert saved["data"]["scenes"][0]["id"] == "sc_001"


def _artifact(
    artifact_type: str,
    version: str,
    data: dict[str, Any],
    *,
    state: ArtifactState = ArtifactState.DRAFT,
) -> ArtifactEnvelope[Any]:
    return ArtifactEnvelope(
        type=artifact_type,
        state=state,
        version=version,
        data=data,
    )


def _characters_data() -> dict[str, Any]:
    return {
        "characters": [
            {
                "id": "lin_wan",
                "name": "Lin Wan",
                "role": "protagonist",
                "voice": "Quiet, clipped.",
                "desire": "Expose the truth.",
                "fear": "Being betrayed again.",
                "arc": "From avoidance to confrontation.",
                "relations": [],
                "hard_rules": ["Do not make Lin Wan cheerful."],
            }
        ]
    }
