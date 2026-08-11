## 1. Eval 骨架与 fixture

- [x] 1.1 新增 fixture `backend/tests/fixtures/novel_sample_3chapters.txt`（3 章中文小说，含角色名、对话、可触发 non_visualizable 的内心独白段落）
- [x] 1.2 在 `backend/tests/eval/` 新增 `conftest.py`：复用 API conftest 的 app_client 思路，注入真实 DeepSeekGateway（未配置 `DEEPSEEK_API_KEY` 时自动 skip）
- [x] 1.3 新增 `backend/tests/eval/test_e2e_deepseek.py`（`@pytest.mark.eval`）：用 fixture 跑通导入 → 理解 → 人物 → 意图 → 大纲 → 剧本 → 报告，断言各阶段 artifact 可被对应 Pydantic model 解析

## 2. DeepSeek 端到端跑通与修复

- [x] 2.1 配置 `DEEPSEEK_API_KEY` 本地运行 eval，记录每个阶段的实际失败点
- [x] 2.2 修复 `ControlledAgent` 校验-重试循环在真模型下的行为（repair_issues 反馈、max_attempts、needs_attention 降级）
- [x] 2.3 修复各 agent `validate_domain` 业务规则在真模型输出下的误报/漏报
- [x] 2.4 验证并修复信任强制：source_ref 回填、ai_inferred 标注、意图门控、must_keep_lines、报告统计与剧本 flag 交叉校验（409）
- [x] 2.5 检查 `with_xxx_defaults` 兜底是否静默吞掉坏输出，必要时增加兜底触发告警路径

## 3. 指标与基线报告

- [x] 3.1 实现指标采集：schema 一次通过率、非 TODO beat 的 source_ref 覆盖率、must_keep_lines 命中率、报告统计一致性、TODO 降级率、平均延迟与 token 消耗、重试率、兜底触发告警
- [x] 3.2 实现基线报告写入 `docs/eval/baseline-<YYYY-MM-DD>.md`（含运行日期、模型名、各指标数值与达标/待优化标注，不覆盖历史）
- [x] 3.3 运行 eval 生成首份基线报告，标注达标与待优化指标

## 4. 文档与收尾

- [x] 4.1 README 补充 DeepSeek 模式端到端运行说明与 eval 使用说明
- [x] 4.2 确认 `uv run pytest -q` 全绿（stub 模式无回归），`pnpm run build` 通过
- [x] 4.3 归档 openspec change（`openspec archive`），确认归档后 specs 进入 `openspec/specs/`
