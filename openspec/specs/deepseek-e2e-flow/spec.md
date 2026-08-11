# deepseek-e2e-flow Specification

## Purpose
TBD - created by archiving change llm-quality-baseline. Update Purpose after archive.
## Requirements
### Requirement: DeepSeek 模式下端到端改编流程可运行
系统 SHALL 在配置 `DEEPSEEK_API_KEY` 后，支持使用 DeepSeek provider 完成从小说导入到改编报告的完整流程：导入 → 作品理解 → 人物档案 → 作者意图 → 分场大纲 → 剧本 → 改编报告。

#### Scenario: 完整流程成功
- **WHEN** 配置 DeepSeek provider 且项目满足 3 章门槛
- **THEN** 各阶段生成接口返回成功，且每阶段 artifact 均可被对应 Pydantic 模型解析

#### Scenario: 未配置 API key 时保持 stub 模式
- **WHEN** 未设置 `DEEPSEEK_API_KEY`
- **THEN** 系统默认使用 `StubLlmGateway`，现有测试与功能不受影响

### Requirement: 生成产物通过 schema 校验，失败可降级
每个生成阶段 SHALL 对 LLM 输出执行 Pydantic schema 校验与业务规则校验（`validate_domain`）；校验失败时 SHALL 使用既有重试循环（携带 repair issues 重试，最多 3 次）；重试耗尽 SHALL 返回 `needs_attention` 降级结果，且 SHALL NOT 把未通过校验的脏数据写入 artifact store。

#### Scenario: 校验失败触发重试
- **WHEN** LLM 输出未通过 schema 或业务校验且错误可重试
- **THEN** 系统携带错误反馈重试，最终返回通过校验的结果或 `needs_attention`

#### Scenario: 重试耗尽不写脏数据
- **WHEN** 多次重试后仍无法通过校验
- **THEN** 结果标记为 `needs_attention`，且 artifact store 中不出现校验失败的原始数据

### Requirement: 信任强制保持生效
剧本与大纲等生成产物 SHALL 继续执行信任强制：非 TODO beat 必须有有效 `source_ref`，无源段落内容标记为 `ai_inferred`；作者 `must_keep_lines` 必须原样出现并标记 `from_source`；改编报告统计 SHALL 与剧本 flag 计数一致，不一致时 SHALL 返回 409。

#### Scenario: source_ref 缺失被标记
- **WHEN** 生成的 beat 没有可匹配源段落的 `source_ref`
- **THEN** 该 beat 被标记为 `ai_inferred`（TODO beat 除外）

#### Scenario: 报告统计不一致被拒绝
- **WHEN** 报告中的 `from_source_lines` / `ai_inferred_lines` 与剧本 flag 计数不一致
- **THEN** 报告生成失败并返回 409 `report_flag_mismatch`

### Requirement: 兜底不静默掩盖坏输出
当真实 LLM 输出为空或降级时，系统 SHALL 在 eval 报告中显式记录 `needs_attention` 与确定性兜底（`with_xxx_defaults`）的触发情况，SHALL NOT 将降级输出静默当作正常成功结果。

#### Scenario: 兜底触发被记录
- **WHEN** DeepSeek 输出为空或标记 `needs_attention` 且服务落入确定性兜底
- **THEN** eval 报告显式标注该阶段的兜底触发与原因

