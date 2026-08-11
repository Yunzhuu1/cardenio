"""DeepSeek end-to-end eval (specs/deepseek-e2e-flow, specs/generation-eval).

Run with: ``uv run pytest -m eval`` (requires DEEPSEEK_API_KEY).
Records per-stage results, computes metrics, and writes a baseline report to
``docs/eval/baseline-<date>.md`` without overwriting earlier baselines.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from cardenio.domain.models.characters import CharactersData
from cardenio.domain.models.outline import OutlineData
from cardenio.domain.models.report import ReportData
from cardenio.domain.models.screenplay import ScreenplayData
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.gateway.providers.deepseek import DEFAULT_DEEPSEEK_MODEL

from tests.eval.metrics import write_baseline_report

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "novel_sample_3chapters.txt"
)

# Stage → Pydantic model used to decide whether the artifact is parseable.
_STAGE_MODELS: dict[str, type] = {
    "understanding": UnderstandingData,
    "characters": CharactersData,
    "outline": OutlineData,
    "screenplay": ScreenplayData,
    "report": ReportData,
}


def load_fixture_chapters(path: Path) -> list[dict[str, str]]:
    """Parse the fixture file into chapters using '# 第X章 ...' headings."""
    chapters: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            if current is not None:
                chapters.append(current)
            current = {"title": stripped[2:].strip(), "text": ""}
        elif current is not None and stripped:
            current["text"] += ("\n\n" + stripped) if current["text"] else stripped
    if current is not None:
        chapters.append(current)
    return chapters


async def _run(
    client: AsyncClient,
    method: str,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    model: type | None = None,
) -> dict[str, Any]:
    """Call one stage; ``ok`` means 2xx and (if ``model`` given) parseable data."""
    resp = await getattr(client, method)(url, json=json)
    ok = resp.status_code < 300
    error = ""
    if ok and model is not None:
        try:
            model.model_validate(resp.json()["data"])
        except Exception as exc:  # noqa: BLE001 - record any validation failure
            ok = False
            error = f"artifact 解析失败: {exc}"
    elif not ok:
        try:
            body = resp.json()
            error = body.get("error", {}).get("message", "") or str(body)[:200]
        except Exception:  # noqa: BLE001
            error = resp.text[:200]
    return {"stage": url, "ok": ok, "status": resp.status_code, "error": error, "resp": resp}


@pytest.mark.eval
async def test_deepseek_e2e_generates_baseline(deepseek_client: tuple[AsyncClient, Any]) -> None:
    client, recorder = deepseek_client
    stages: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, Any]] = {}

    project_id = await _create_project(client)
    chapters = load_fixture_chapters(FIXTURE_PATH)
    assert len(chapters) == 3, "fixture must contain exactly 3 chapters"
    for index, chapter in enumerate(chapters, start=1):
        resp = await client.post(
            f"/api/v1/projects/{project_id}/source/chapters",
            json={"title": chapter["title"], "text": chapter["text"], "order": index},
        )
        assert resp.status_code == 201
    stages.append({"stage": "source:import", "ok": True, "status": 201, "error": ""})

    # -- understanding -------------------------------------------------------
    s = await _run(client, "post", f"/api/v1/projects/{project_id}/understanding:generate",
                   model=_STAGE_MODELS["understanding"])
    stages.append(s)
    if s["ok"]:
        artifacts["understanding"] = s["resp"].json()
        await client.post(f"/api/v1/projects/{project_id}/understanding:confirm")

    # -- characters ----------------------------------------------------------
    s = await _run(client, "post", f"/api/v1/projects/{project_id}/characters:generate",
                   model=_STAGE_MODELS["characters"])
    stages.append(s)
    if s["ok"]:
        artifacts["characters"] = s["resp"].json()
        await client.post(f"/api/v1/projects/{project_id}/characters:confirm")

    # -- intent + direction --------------------------------------------------
    payload = intent_payload()
    s = await _run(client, "put", f"/api/v1/projects/{project_id}/intent", json=payload)
    stages.append(s)
    s = await _run(
        client,
        "put",
        f"/api/v1/projects/{project_id}/intent/direction",
        json={"direction": "short_drama"},
    )
    stages.append(s)

    # -- outline -------------------------------------------------------------
    s = await _run(client, "post", f"/api/v1/projects/{project_id}/outline:generate",
                   model=_STAGE_MODELS["outline"])
    stages.append(s)
    if s["ok"]:
        artifacts["outline"] = s["resp"].json()
        await client.post(f"/api/v1/projects/{project_id}/outline:confirm")

    # -- screenplay ----------------------------------------------------------
    s = await _run(client, "post", f"/api/v1/projects/{project_id}/screenplay:generate",
                   model=_STAGE_MODELS["screenplay"])
    stages.append(s)
    if s["ok"]:
        artifacts["screenplay"] = s["resp"].json()

    # -- report --------------------------------------------------------------
    s = await _run(client, "post", f"/api/v1/projects/{project_id}/report:generate",
                   model=_STAGE_MODELS["report"])
    stages.append(s)
    if s["ok"]:
        artifacts["report"] = s["resp"].json()

    # -- baseline report -----------------------------------------------------
    report_path = write_baseline_report(
        stage_results=stages,
        screenplay_data=artifacts.get("screenplay", {}).get("data"),
        report_data=artifacts.get("report", {}).get("data"),
        must_keep_lines=[],
        records=recorder.records,
        model_name=os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
    )

    # Structural assertions: the baseline must at least capture the first
    # generative stage; the report file must exist.
    assert report_path.exists()
    assert any("understanding" in stage["stage"] for stage in stages)
    assert artifacts.get("understanding") is not None, (
        "understanding 阶段失败：见基线报告「分阶段结果」"
    )


async def _create_project(client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/projects",
        json={
            "title": "eval-deepseek-baseline",
            "ui_language": "zh-CN",
            "source_language": "zh-CN",
            "output_language": "zh-CN",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def intent_payload() -> dict:
    """Author intent for the baseline run.

    ``must_keep_lines`` is intentionally empty for the first baseline:
    enabling it can hard-fail screenplay generation when the model does not
    reproduce a line verbatim (see `enforce_must_keep_lines`). The capability
    is covered by unit tests; re-enable in a later optimization pass.
    """
    return {
        "keep": ["father-daughter confrontation"],
        "no_delete": ["the sealed letter"],
        "no_merge": ["林晚", "沈知远"],
        "must_keep_lines": [],
        "mood_floor": "tense",
        "allow_new_plot": True,
        "allow_reorder": True,
        "allow_new_ending": False,
        "target_type": "short_drama",
    }
