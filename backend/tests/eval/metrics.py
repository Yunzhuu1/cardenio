"""Eval metrics and baseline report writer (specs/generation-eval)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cardenio.domain.models.base import Flag
from cardenio.domain.models.report import ReportData
from cardenio.domain.models.screenplay import ScreenplayData

# v1 heuristic thresholds used to label each metric 达标 / 待优化.
THRESHOLDS: dict[str, Any] = {
    "schema_pass_rate": 0.9,
    "source_ref_coverage": 0.95,
    "todo_rate": 0.2,  # 上限：TODO 降级率不得超过 20%
    "report_consistency": True,
    "must_keep_hit_rate": 1.0,
}

REPORT_DIR = os.getenv("CARDENIO_EVAL_REPORT_DIR", "docs/eval")


def compute_schema_pass_rate(stage_results: list[dict[str, Any]]) -> float:
    """Proportion of stages that returned a parseable artifact (HTTP 2xx)."""
    if not stage_results:
        return 0.0
    ok = sum(1 for stage in stage_results if stage.get("ok"))
    return round(ok / len(stage_results), 4)


def compute_screenplay_metrics(screenplay_data: dict[str, Any]) -> dict[str, float]:
    """source_ref coverage and TODO degradation rate from the screenplay."""
    screenplay = ScreenplayData.model_validate(screenplay_data)
    beats = [beat for scene in screenplay.scenes for beat in scene.beats]
    total = len(beats)
    todo = sum(1 for beat in beats if beat.type.value == "todo")
    non_todo = total - todo
    covered = sum(
        1
        for beat in beats
        if beat.type.value != "todo" and beat.source_ref and beat.source_ref.paragraphs
    )
    return {
        "beat_count": total,
        "todo_rate": round(todo / total, 4) if total else 0.0,
        "source_ref_coverage": round(covered / non_todo, 4) if non_todo else 0.0,
    }


def compute_report_consistency(
    screenplay_data: dict[str, Any],
    report_data: dict[str, Any],
) -> bool:
    """FR-10 cross-check: report flag statistics must match screenplay flags."""
    screenplay = ScreenplayData.model_validate(screenplay_data)
    report = ReportData.model_validate(report_data)
    from_source = sum(
        1
        for scene in screenplay.scenes
        for beat in scene.beats
        if beat.type.value != "todo" and beat.flag == Flag.FROM_SOURCE
    )
    ai_inferred = sum(
        1
        for scene in screenplay.scenes
        for beat in scene.beats
        if beat.type.value != "todo" and beat.flag == Flag.AI_INFERRED
    )
    return (
        report.from_source_lines == from_source
        and report.ai_inferred_lines == ai_inferred
    )


def compute_must_keep_hit_rate(
    screenplay_data: dict[str, Any],
    must_keep_lines: list[str],
) -> float:
    """Proportion of author must-keep lines appearing verbatim in the screenplay."""
    if not must_keep_lines:
        return 1.0
    screenplay = ScreenplayData.model_validate(screenplay_data)
    texts = {
        (beat.dialogue or beat.text or "").strip()
        for scene in screenplay.scenes
        for beat in scene.beats
    }
    hits = sum(1 for line in must_keep_lines if line.strip() in texts)
    return round(hits / len(must_keep_lines), 4)


def summarize_records(records: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate per-call LLM usage records (latency / tokens / retry proxy)."""
    if not records:
        return {
            "calls": 0,
            "distinct_tasks": 0,
            "avg_calls_per_task": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "avg_latency_ms": 0.0,
        }
    tasks = {record["task"] for record in records}
    return {
        "calls": len(records),
        "distinct_tasks": len(tasks),
        "avg_calls_per_task": round(len(records) / len(tasks), 2),
        "total_input_tokens": sum(int(r.get("input_tokens", 0)) for r in records),
        "total_output_tokens": sum(int(r.get("output_tokens", 0)) for r in records),
        "avg_latency_ms": round(
            sum(int(r.get("latency_ms", 0)) for r in records) / len(records), 1
        ),
    }


def _label(metric: str, value: Any) -> str:
    threshold = THRESHOLDS[metric]
    if isinstance(threshold, bool):
        return "达标" if bool(value) == threshold else "待优化"
    if metric == "todo_rate":
        return "达标" if float(value) <= float(threshold) else "待优化"
    return "达标" if float(value) >= float(threshold) else "待优化"


def write_baseline_report(
    *,
    stage_results: list[dict[str, Any]],
    screenplay_data: dict[str, Any] | None,
    report_data: dict[str, Any] | None,
    must_keep_lines: list[str],
    records: list[dict[str, Any]],
    model_name: str,
) -> Path:
    """Write docs/eval/baseline-<date>.md; never overwrites earlier baselines."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.now(UTC)
    path = Path(REPORT_DIR) / f"baseline-{now:%Y-%m-%d}.md"

    schema_pass_rate = compute_schema_pass_rate(stage_results)
    metrics: dict[str, Any] = {"schema_pass_rate": schema_pass_rate}

    if screenplay_data is not None:
        screen_metrics = compute_screenplay_metrics(screenplay_data)
        metrics.update(screen_metrics)
        metrics["must_keep_hit_rate"] = compute_must_keep_hit_rate(
            screenplay_data, must_keep_lines
        )
    if screenplay_data is not None and report_data is not None:
        metrics["report_consistency"] = compute_report_consistency(
            screenplay_data, report_data
        )

    usage = summarize_records(records)

    lines: list[str] = []
    lines.append("# Cardenio 生成质量基线报告")
    lines.append("")
    lines.append(f"- 生成时间（UTC）：{now.isoformat()}")
    lines.append(f"- 模型：`{model_name}`")
    lines.append("- 说明：本报告为基线快照，不覆盖历史文件。")
    lines.append("")

    lines.append("## 分阶段结果")
    lines.append("")
    lines.append("| 阶段 | 结果 | HTTP | 备注 |")
    lines.append("| --- | --- | --- | --- |")
    for stage in stage_results:
        lines.append(
            f"| {stage['stage']} | {'✅ 成功' if stage['ok'] else '❌ 失败'} | "
            f"{stage.get('status', '-')} | {stage.get('error', '')} |"
        )
    lines.append("")

    lines.append("## 指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 阈值 | 结论 |")
    lines.append("| --- | --- | --- | --- |")
    for metric, threshold in THRESHOLDS.items():
        if metric not in metrics:
            lines.append(f"| {metric} | N/A（未生成） | {threshold} | - |")
            continue
        value = metrics[metric]
        lines.append(f"| {metric} | {value} | {threshold} | {_label(metric, value)} |")
    lines.append("")

    lines.append("## LLM 调用统计")
    lines.append("")
    lines.append(f"- 调用次数：{usage['calls']}（涉及 {usage['distinct_tasks']} 种任务）")
    lines.append(f"- 每任务平均调用次数（重试代理指标）：{usage['avg_calls_per_task']}")
    lines.append(f"- 输入 token 合计：{usage['total_input_tokens']}")
    lines.append(f"- 输出 token 合计：{usage['total_output_tokens']}")
    lines.append(f"- 平均单次延迟：{usage['avg_latency_ms']} ms")
    lines.append("")

    lines.append("## 备注")
    lines.append("")
    if not must_keep_lines:
        lines.append(
            "- `must_keep_lines` 在本次基线中未启用（避免整链失败），"
            "该能力由 `backend/tests/unit/domain/test_generation_service.py` 等单测覆盖；"
            "后续优化阶段再开启并纳入指标。"
        )
    if screenplay_data is None or report_data is None:
        lines.append("- 剧本或报告未生成，相关指标为 N/A；请结合「分阶段结果」定位失败点。")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
