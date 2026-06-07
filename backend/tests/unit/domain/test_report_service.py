"""Report service orchestration tests."""

from __future__ import annotations

from typing import Any

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState
from cardenio.domain.services.report_service import ReportService
from cardenio.domain.tools import ToolRegistry
from cardenio.domain.tools.report import ReportGenerateToolInput, ReportGenerateToolOutput
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class FakeStore:
    def __init__(self) -> None:
        self.project: dict[str, Any] = {
            "id": "proj_1",
            "style_fingerprint": "restrained; tense",
        }
        self.artifacts: dict[str, ArtifactEnvelope[Any]] = {
            "screenplay": _artifact("screenplay", "v_screenplay", _screenplay_data()),
            "outline": _artifact("outline", "v_outline", {"scenes": []}),
            "understanding": _artifact(
                "understanding",
                "v_understanding",
                {"style_fingerprint": "restrained; tense"},
            ),
        }
        self.saved: ArtifactEnvelope[Any] | None = None

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


class FakeGateway:
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        raise AssertionError("Tool registry test should not call the gateway directly")


class RecordingReportTool:
    name = "report.generate"
    input_model = ReportGenerateToolInput
    output_model = ReportGenerateToolOutput

    def __init__(self) -> None:
        self.flag_statistics: dict[str, int] | None = None
        self.style_fingerprint: str | None = None
        self.has_outline = False
        self.has_understanding = False

    async def run(self, input_data: ReportGenerateToolInput) -> ReportGenerateToolOutput:
        context = input_data.context
        self.flag_statistics = context.upstream_artifacts["flag_statistics"]
        self.style_fingerprint = context.system_constraints["style_fingerprint"]
        self.has_outline = "outline" in context.upstream_artifacts
        self.has_understanding = "understanding" in context.upstream_artifacts
        return ReportGenerateToolOutput(
            data={
                "kept": [
                    {
                        "item": "Lin Wan opens the archive.",
                        "scene_id": "sc_001",
                        "source_ref": {"chapter": 1, "paragraphs": [1]},
                        "flag": "from_source",
                    }
                ],
                "added": [
                    {
                        "item": "A new bridge beat.",
                        "scene_id": "sc_001",
                        "source_ref": {"chapter": 1, "paragraphs": [2]},
                        "flag": "ai_inferred",
                    }
                ],
                "from_source_lines": 1,
                "ai_inferred_lines": 1,
            },
            status="ok",
            attempts=1,
            usage={},
        )


async def test_report_service_runs_agent_through_tool_registry() -> None:
    store = FakeStore()
    tool = RecordingReportTool()
    service = ReportService(
        gateway=FakeGateway(),
        store=store,
        tools=ToolRegistry([tool]),
    )

    saved = await service.generate_report("proj_1")

    assert tool.flag_statistics == {
        "from_source_lines": 1,
        "ai_inferred_lines": 1,
    }
    assert tool.style_fingerprint == "restrained; tense"
    assert tool.has_outline is True
    assert tool.has_understanding is True
    assert store.saved is not None
    assert store.saved.parent_version == "v_screenplay"
    assert saved["type"] == "report"
    assert saved["data"]["from_source_lines"] == 1
    assert saved["data"]["ai_inferred_lines"] == 1
    assert saved["data"]["kept"][0]["flag"] == "from_source"
    assert saved["data"]["added"][0]["flag"] == "ai_inferred"


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
                "characters": ["lin_wan"],
                "foreshadowing": [],
                "relation_changes": [],
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan opens the archive.",
                        "source_ref": {"chapter": 1, "paragraphs": [1]},
                        "flag": "from_source",
                    },
                    {
                        "type": "action",
                        "text": "A new bridge beat.",
                        "source_ref": {"chapter": 1, "paragraphs": [2]},
                        "flag": "ai_inferred",
                    },
                ],
            }
        ],
        "shot_hints": {"enabled": False},
    }
