## Why

Cardenio 后端默认运行在 stub 模式，真实 LLM（DeepSeek）链路从未被端到端验证：ControlledAgent 的校验-重试循环、各 agent 的 `validate_domain` 业务规则、信任强制（`source_ref` / `ai_inferred` / 意图门控 / `must_keep_lines` / 报告统计交叉校验）在真模型下的行为未知，且生成质量没有任何可度量的基线。不先打通真实链路并建立 eval，后续所有生成类优化都无从谈起，项目的核心差异化（确定性编排 + 信任机制）也只是未经证实的设计。

## What Changes

- 打通 DeepSeek 模式端到端流程：导入 → 作品理解 → 人物档案 → 作者意图 → 分场大纲 → 剧本 → 改编报告。
- 修复真模型下暴露的问题：ControlledAgent 重试与 `needs_attention` 降级路径、各 agent 的 `validate_domain` 规则、信任强制是否被正确执行、`with_xxx_defaults` 兜底是否会静默吞掉坏输出。
- 新增可重复运行的生成质量评估（eval）：固定中文小说 fixture、指标采集、基线报告输出。
- 明确记录基线数字，标注达标与待优化指标。
- 不破坏 stub 模式；现有 `backend/tests` 全部保持通过。

## Capabilities

### New Capabilities
- `deepseek-e2e-flow`: DeepSeek 模式下端到端改编流程可运行，生成产物通过 schema 校验与信任强制，失败可降级为 `needs_attention` / TODO。
- `generation-eval`: 可重复运行的生成质量评估基线，包含固定 fixture、指标定义与基线报告输出。

### Modified Capabilities
<!-- 无既有 specs，本变更不修改既有能力 -->

## Impact

- 后端代码：`gateway/providers/deepseek.py`、`domain/agents/*`（base + 各 agent）、`domain/services/*`（analysis / outline / generation / rewrite / report）、`domain/validation/trust.py`、`orchestrator/trust_enforcer.py`、`api/app.py`（网关工厂）。
- 新增：eval fixture 与 eval 脚本（`backend/scripts/eval` 或 `backend/tests/eval`）、基线报告（位置待 design 确定）。
- 依赖：DeepSeek API 为外部服务（已有 `DEEPSEEK_API_KEY` 环境变量契约，不新增代码依赖）。
- 文档：README 需补充「DeepSeek 模式运行与 eval 说明」。
