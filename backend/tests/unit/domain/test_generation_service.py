"""Generation service orchestration tests."""

from __future__ import annotations

from typing import Any

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.services.generation_service import GenerationService
from cardenio.domain.tools import ToolRegistry
from cardenio.domain.tools.scene import SceneGenerateToolInput, SceneGenerateToolOutput
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class FakeStore:
    def __init__(self) -> None:
        self.project: dict[str, Any] = {
            "id": "proj_1",
            "state": ProjectState.OUTLINED,
            "adaptation_direction": "short_drama",
            "style_fingerprint": "restrained; tense",
            "output_language": "zh-CN",
        }
        self.artifacts: dict[str, ArtifactEnvelope[Any]] = {
            "outline": _artifact(
                "outline",
                "v_outline",
                _outline_data(),
                state=ArtifactState.CONFIRMED,
            ),
            "characters": _artifact("characters", "v_characters", _characters_data()),
            "intent": _artifact("intent", "v_intent", _intent_data()),
            "understanding": _artifact("understanding", "v_understanding", _understanding_data()),
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


class FakeGateway:
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        raise AssertionError("Tool registry test should not call the gateway directly")


class RecordingSceneTool:
    name = "scene.generate"
    input_model = SceneGenerateToolInput
    output_model = SceneGenerateToolOutput

    def __init__(self) -> None:
        self.source_chunk_types: list[str] = []
        self.outline_scene_ids: list[str] = []
        self.shot_hints_enabled: bool | None = None
        self.voice: dict[str, str] | None = None
        self.output_language: str | None = None
        self.hard_rules: list[str] | None = None

    async def run(self, input_data: SceneGenerateToolInput) -> SceneGenerateToolOutput:
        context = input_data.context
        self.source_chunk_types = [chunk["type"] for chunk in context.source_chunks]
        self.outline_scene_ids = [
            scene["id"] for scene in context.upstream_artifacts["outline"]["scenes"]
        ]
        self.shot_hints_enabled = context.system_constraints["shot_hints_enabled"]
        self.voice = context.system_constraints["voice"]
        self.output_language = context.system_constraints["output_language"]
        self.hard_rules = context.system_constraints["hard_rules"]
        return SceneGenerateToolOutput(
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
                        "foreshadowing": [],
                        "relation_changes": [],
                        "ending_state": "The letter is exposed.",
                        "beats": [
                            {
                                "type": "action",
                                "text": "Lin Wan closes the archive door.",
                                "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                                "flag": "from_source",
                            }
                        ],
                    }
                ],
                "shot_hints": {"enabled": True},
            },
            status="ok",
            attempts=1,
            usage={},
        )


async def test_generation_service_runs_scene_agent_through_tool_registry() -> None:
    store = FakeStore()
    tool = RecordingSceneTool()
    service = GenerationService(
        gateway=FakeGateway(),
        store=store,
        tools=ToolRegistry([tool]),
    )

    saved = await service.generate_screenplay("proj_1", body={"shot_hints": True})

    assert tool.source_chunk_types == ["adaptation_direction", "request"]
    assert tool.outline_scene_ids == ["sc_001"]
    assert tool.shot_hints_enabled is True
    assert tool.voice == {"lin_wan": "Quiet, clipped."}
    assert tool.output_language == "zh-CN"
    assert tool.hard_rules == [
        "All user-visible generated content must be written in Simplified Chinese."
    ]
    assert store.saved is not None
    assert store.saved.type == "screenplay"
    assert store.updated_state == ProjectState.GENERATED
    assert saved["data"]["shot_hints"]["enabled"] is True
    assert saved["data"]["scenes"][0]["beats"][0]["flag"] == "from_source"


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


def _outline_data() -> dict[str, Any]:
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
            }
        ],
        "merge_suggestions": [],
    }


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
                "hard_rules": [],
            }
        ]
    }


def _intent_data() -> dict[str, Any]:
    return {
        "keep": [],
        "no_delete": [],
        "no_merge": [],
        "must_keep_lines": [],
        "mood_floor": "tense",
        "allow_new_plot": False,
        "allow_reorder": False,
        "allow_new_ending": False,
        "target_type": "short_drama",
    }


def _understanding_data() -> dict[str, Any]:
    return {
        "logline": "A sealed letter forces Lin Wan to confront Chen Mo.",
        "synopsis": "Archive secrets pull two characters into open conflict.",
        "themes": ["trust"],
        "protagonist_goal": "Expose the letter.",
        "protagonist_fear": "Losing the last bond.",
        "central_conflict": "Truth versus concealment.",
        "mood": "tense",
        "style_fingerprint": "restrained; tense",
        "narrative": {
            "perspective": "third_person_limited",
            "tense": "past",
            "unreliable": False,
        },
        "non_visualizable": [],
        "strengths": [],
        "difficulties": [],
    }
