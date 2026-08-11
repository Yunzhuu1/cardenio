## Context

Cardenio 后端是 FastAPI + 确定性 Agent 编排（routes → services → ToolRegistry → AgentRuntime → ControlledAgent → LlmGateway），LlmGateway 支持 stub 与 DeepSeek 双 provider。当前默认 stub，服务层用 `with_xxx_defaults` 从原文做确定性降级，真实 DeepSeek 链路从未端到端验证。目标：先打通真模型全流程，再建立可重复的质量基线，为后续生成质量优化提供量化依据。

约束：不破坏 stub 模式；现有 `backend/tests` 必须通过；solo fork 工作流（feat/ 分支、Conventional Commits、无 PR）。

## Goals / Non-Goals

**Goals:**
- DeepSeek 模式下「导入 → 理解 → 人物 → 意图 → 大纲 → 剧本 → 报告」端到端可运行。
- 修复真模型暴露的校验/重试/信任强制问题。
- 建立可重复运行的 eval：固定 fixture、指标、基线报告。

**Non-Goals:**
- 不重写编排架构（services / agents / runtime / gateway 分层保持不变）。
- 不做 prompt 效果优化竞赛（先有基线，优化留到后续变更）。
- 不做前端改动、不引入新外部依赖（DeepSeek 为既有契约）。
- 不把 eval 接入 CI 强制门禁（无 API key 时跳过）。

## Decisions

**D1. eval 形态：pytest 标记 `@pytest.mark.eval`，无 key 自动 skip**
- 与现有测试体系一致、可复用 `test_e2e_demo_flow.py` 的流程骨架；默认 `uv run pytest -q` 不跑（不花钱、不失败），显式 `uv run pytest -m eval` 才跑。
- 备选（独立 CLI 脚本）被否：会偏离既有测试工具链，且难以复用 fixture/conftest。

**D2. eval 通过真实 HTTP 流程驱动，指标从 artifact + usage 采集**
- 复用 conftest 的 `app_client` 思路，但 gateway 换成真实 `DeepSeekGateway`（通过 `create_gateway_from_env()` 注入 app.state）。
- schema 通过率 = 各阶段 artifact 能被对应 Pydantic model 解析的比例；source_ref 覆盖率、must_keep 命中率、报告一致性直接对 artifact 数据计算；延迟/token 从 agent `usage`（ControlledAgent 已返回）汇总。
- 备选（侵入业务代码埋点）被否：污染业务层，指标应作为外部观测。

**D3. fixture：`backend/tests/fixtures/novel_sample_3chapters.txt`**
- 固定 3 章中文小说，包含可识别角色名（用于人物抽取）、对话、内心独白段落（触发 `non_visualizable`）、可被 `must_keep_lines` 引用的原句。
- 固定内容保证基线可复现。

**D4. 基线报告落盘 `docs/eval/`**
- 每次运行输出 `docs/eval/baseline-<date>.md`，含全部指标与达标/待优化标注；长期保留，便于对比后续优化。
- 备选（只放 openspec change 目录）被否：change 会归档，基线需要长期存在。

**D5. 修复策略：先跑通、记录问题、按问题修复**
- 用 eval 驱动发现真模型问题；修复围绕 ControlledAgent 重试、validate_domain、信任强制、兜底告警，不做大重构。

## Risks / Trade-offs

- [每次 eval 消耗 API 额度与时间] → fixture 仅 3 章、固定场景、`max_tokens` 受控；eval 标记为可选测试。
- [DeepSeek JSON 输出偶发不符合 schema] → 依赖既有 ControlledAgent 重试（≤3 次）+ `needs_attention` 降级；基线记录重试率与降级率。
- [`with_xxx_defaults` 可能静默掩盖坏输出] → eval 增加「兜底触发告警」：真模型输出为空/needs_attention 且落入 defaults 时在报告中显式标注。
- [不同时间跑 eval 结果波动] → 基线报告记录运行日期与模型名，明确为「快照」而非硬性断言。

## Migration Plan

1. 分支 `feat/llm-quality-baseline`；先加 fixture 与 eval 骨架（skip 模式）。
2. 用 DEEPSEEK_API_KEY 本地跑通，修复问题并逐步放开 eval 断言。
3. 记录基线报告，更新 README（DeepSeek 模式 + eval 使用说明）。
4. 合并回 main；后续优化在 `generation-eval` 能力上迭代。
- 回滚：eval 与修复均为增量，无迁移；stub 模式始终可用。

## Open Questions

- 基线报告中是否纳入「人工抽检评分」（1-5 分）？→ 初版只做客观指标，人工评分留到后续。
- `must_keep_lines` fixture 的原文行选取由谁定？→ 初版由 fixture 作者（开发者在 propose 后补充）确定，eval 只校验命中率。
