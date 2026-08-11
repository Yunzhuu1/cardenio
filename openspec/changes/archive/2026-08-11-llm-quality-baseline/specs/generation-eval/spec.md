## ADDED Requirements

### Requirement: 固定 eval fixture
系统 SHALL 提供一份固定的 3 章中文小说 fixture（`backend/tests/fixtures/novel_sample_3chapters.txt`），内容包含可识别角色名、对话、以及可触发 `non_visualizable` 的内心独白段落，用于保证 eval 结果可复现。

#### Scenario: fixture 存在且可导入
- **WHEN** 运行 eval
- **THEN** 系统使用该 fixture 创建项目并导入 3 章，且章节阈值检查通过

### Requirement: eval 可重复运行且不干扰常规测试
eval SHALL 以 `@pytest.mark.eval` 标记，未配置 `DEEPSEEK_API_KEY` 时自动 skip；常规 `uv run pytest -q` SHALL NOT 执行 eval；显式 `uv run pytest -m eval` SHALL 可重复运行并输出报告。

#### Scenario: 默认测试跳过 eval
- **WHEN** 执行 `uv run pytest -q` 且未配置 API key
- **THEN** eval 用例被跳过，其余测试全部通过

#### Scenario: 显式运行 eval
- **WHEN** 配置 API key 并执行 `uv run pytest -m eval`
- **THEN** eval 用例运行完整流程并生成基线报告

### Requirement: 指标采集
eval SHALL 采集并输出以下指标：schema 一次通过率、非 TODO beat 的 `source_ref` 覆盖率、`must_keep_lines` 命中率、报告统计与剧本 flag 一致性、TODO 降级率、平均延迟与 token 消耗、重试率、确定性兜底触发告警。

#### Scenario: 指标随报告输出
- **WHEN** eval 完成一次完整流程
- **THEN** 报告中包含上述全部指标及其数值

### Requirement: 基线报告落盘
eval SHALL 将结果写入 `docs/eval/baseline-<YYYY-MM-DD>.md`，记录运行日期、模型名与各指标数值，并对每个指标标注「达标 / 待优化」。

#### Scenario: 报告文件生成
- **WHEN** eval 运行成功
- **THEN** 在 `docs/eval/` 下生成带日期的基线报告，且文件包含模型名与达标/待优化标注

#### Scenario: 报告不覆盖历史
- **WHEN** 多次运行 eval
- **THEN** 每次生成独立的日期文件，不覆盖历史基线
