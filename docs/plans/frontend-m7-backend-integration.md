# 前端接入后端 M7 接口 — 改编取舍报告实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 **M7（改编取舍报告：报告生成 + 报告统计与剧本 `flag` 标记一致性校验）** 接口。本计划把这些接到前端：把当前为 `StagePlaceholder` 的 **`report`（改编取舍报告）** 顶层阶段页升级为可用界面。**全程只改 `frontend/`，不改 `backend/`。**
>
> 本计划延续 [`frontend-m6-backend-integration.md`](./frontend-m6-backend-integration.md) 与更早各阶段计划的全部约定（默认 `http` 模式、http/mock 双实现经 `VITE_API_MODE` 切换、coss 组件经 shadcn `@coss` registry 安装到 `app/components/ui/`、统一 envelope 信封、门控只看工件存在/state、`extra="forbid"` 全量回传、冒号动作段按字面拼接、不发 `If-Match`、两 locale 键同步、Conventional Commits + 纯 ASCII subject、PR 模板五段式）。执行前请通读 M6 计划的「总体方案与不变量」「跨 PR 关键实现细则」「coss 用法红线」，本计划只补充 M7 的差异点。

---

## Context（为什么做、目标、已确认决策）

- 产品主流程在「导入（M0/M1）→ 理解/档案/意图（M2/M3）→ 大纲（M4）→ 剧本初稿（M5）→ 打磨工作台（M6）」之后，进入 **M7 改编取舍报告**。报告让改编决策**可解释、可交叉核对、可溯源**（PRD FR-10、P3/P5、NFR-4）。
- M7 的产品职责落在独立阶段页 **`report`（[project-report.tsx](../../frontend/app/routes/project-report.tsx) 目前是 `StagePlaceholder` 占位）**。本计划把 `report` 升级为「改编取舍报告」工作台，承载路线图里的两项 M7 必做能力：
  - **M7-T1 报告生成（FR-10）**：从已生成的剧本聚合产出报告——保留 / 删除 / 合并 / 新增 / 心理外化 / 保留的伏笔 / 建议重点复查的场景，并给出原文台词数（`from_source_lines`）与 AI 台词数（`ai_inferred_lines`）统计；每条可定位到场景或原文段落。
  - **M7-T2 与标记一致性校验（FR-10/FR-7.5）**：报告统计必须等于剧本 `flag` 标记计数。**后端已强制**（不一致服务端判生成失败返回 `409 report_flag_mismatch`）；**本计划在前端额外加一个可见的一致性核对面板**，把这层信任保证显式呈现给作者（见决策 2 与 PR3 的额外价值说明）。
- 目标产出：作者在剧本初稿生成（M5）后，进入 `report` 阶段——
  1. 若剧本未生成 → 看到门控空态，引导回 `script` 阶段先生成剧本。
  2. 若剧本已生成但报告未生成 → 看到「生成报告」入口，点击后**异步聚合**产出报告并展示；可「重新生成」。
  3. 看到结构化报告：摘要统计（原文台词数 / AI 台词数）、各分类区块（保留 / 新增 / 删除 / 合并 / 心理外化 / 保留伏笔 / 建议重点复查），每条带来源徽标（`source_ref` 与场景名）与来源/AI 标记。
  4. 看到**一致性核对面板**：前端自行从剧本工件重算 `flag` 计数并与报告统计对比，显式显示「✓ 统计一致」或「⚠ 不一致 / 报告可能已过时」。
  5. 对带 `source_ref` 的条目，可**内联展开预览对应原文段落**（调 `source:resolve`），让「可溯源」真正可读。

  全部数据来自真实后端。

- **本次已与用户确认的三项决策（写死，执行 Agent 不得擅自变更）：**
  1. **定位交互 = 内联原文预览。** 报告每个带 `source_ref` 的条目用 `Collapsible` 内联展开，点开时调既有 `api.source.resolve(projectId, chapter, paragraphs)`（M6 PR1 已建的客户端方法）拉对应原文段落正文展示。**不做跨页跳转到 editor**（不引入 `/editor#scene-x` 之类的跨阶段导航）。场景定位以「场景名徽标 + 原文段落预览」满足 FR-10「可定位到场景或原文段落」。
  2. **加可见的一致性核对面板。** 除后端 409 强制外，前端在报告页加载剧本工件，自行重算非 `todo` 节拍的 `from_source` / `ai_inferred` 计数，与报告 `from_source_lines` / `ai_inferred_lines` 对比，显式展示一致/不一致（呼应 M7-T2，并能在「剧本被编辑后报告过时」时给作者明确提示）。
  3. **本批范围 = 只做报告（report）。** **排除导出（export，API-27/28，属 `M-Should`）**。导出留作后续独立里程碑，不在本期接入。

---

## 后端现状核对（执行前必读，以代码实际行为为准）

> 已逐文件、逐测试核对：[api/routes/report.py](../../backend/src/cardenio/api/routes/report.py)、[domain/models/report.py](../../backend/src/cardenio/domain/models/report.py)、[domain/models/base.py](../../backend/src/cardenio/domain/models/base.py)、[api/errors.py](../../backend/src/cardenio/api/errors.py)、[api/middleware.py](../../backend/src/cardenio/api/middleware.py)、[gateway/providers/stub.py](../../backend/src/cardenio/gateway/providers/stub.py)、[tests/api/test_report.py](../../backend/tests/api/test_report.py)。

### 通用：仍是统一信封（envelope）

报告工件读写接口返回与 M2–M6 完全相同的 `ArtifactEnvelope`（`type`/`state`/`version`（`v_<hex8>`）/`parent_version`/`etag`（恒 null）/`updated_at`/`needs_recompute`/`data`）。沿用既有处理：`version` 当不透明串、不解析；不发 `If-Match`；门控只看工件是否存在。

### M7 报告接口（[report.py](../../backend/src/cardenio/api/routes/report.py)，前缀 `/projects/{project_id}/report`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| **生成报告** | `POST :generate`（即 `/report:generate`，冒号动作段） | 无 body | `202` **`ArtifactEnvelope<ReportData>`**（`type:"report"`，`state:"draft"`，`parent_version=` 剧本 version）。**不是 Job、无 SSE。** 项目不存在 → `404 {"detail":"Project not found"}`；剧本未生成 → `404 {"detail":"Screenplay not found"}`；报告统计与剧本 `flag` 不一致 → `409 {"error":{"code":"report_flag_mismatch",...}}` |
| **读取报告** | `GET ` (前缀根，即 `/report`) | — | `200` `ArtifactEnvelope<ReportData>`。项目不存在 → `404 {"detail":"Project not found"}`；报告未生成 → `404 {"detail":"Report not found"}` |

> **关键：`:generate` 返回的是工件信封本身（同步 202），不是 Job。** 与 M5 `screenplay:generate`、M6 `:rewrite` 一致——拿到信封后直接 `revalidate` 整体刷新即可，不接 SSE/轮询。

### `ReportData` 数据形状（[models/report.py](../../backend/src/cardenio/domain/models/report.py)，前端需新增类型，复用既有 `SourceRef`/`Flag`）

`ReportData`（`extra="forbid"`）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `kept` | `ReportEntry[]` | 保留自原文的条目（`flag:"from_source"`） |
| `deleted` | `ReportEntry[]` | 删除的条目。**仅 LLM 叙述化时可能填充；stub 模式恒为 `[]`**（见下「stub 行为」） |
| `merged` | `{ scene_ids: string[]; into: string }[]` | 合并的场景。**仅 LLM 时可能填充；stub 恒为 `[]`** |
| `added` | `ReportEntry[]` | AI 新增/改编的条目（`flag:"ai_inferred"`），每条带 `scene_id` 与 `source_ref` |
| `externalized` | `ExternalizationEntry[]` | 心理外化条目（内心独白→V.O./动作等）。**通常为 `[]`**（仅当某 `note`/`voice_over` 节拍正文含 "externalization"/"non-visualizable" 字样才计入） |
| `from_source_lines` | `number` | 原文台词/节拍数（= 剧本非 todo 节拍中 `flag==="from_source"` 的数量） |
| `ai_inferred_lines` | `number` | AI 新增节拍数（= 剧本非 todo 节拍中 `flag==="ai_inferred"` 的数量） |
| `kept_foreshadowing` | `string[]` | 保留的伏笔（从各场 `foreshadowing` 汇总） |
| `review_recommended` | `{ scene_id: string; reason: string }[]` | 建议重点复查的场景（含 AI 新增或 TODO 材料的场景） |

`ReportEntry`（`extra="forbid"`）：`{ item: string; source_ref: SourceRef | null; scene_id: string | null; flag: Flag | null; desc: string | null }`。
- `item`：条目内容标签（取自节拍的 `dialogue`/`text`，超过 96 字符截断加 `...`）。**这是要展示的主文本。**
- `desc`：后端给的**英文**通用描述（如 `"Kept from source material."`、`"Added or adapted by AI and marked for author review."`）。**不可本地化、不建议直接展示**；前端应按 `flag` 自行渲染本地化说明，`desc` 仅作兜底/调试，不作主文案（见坑 4）。

`ExternalizationEntry`（`extra="forbid"`）：`{ scene_id: string; from_type: string; to_type: string }`（`from_type` 如 `"non_visualizable_source"`，`to_type` 如 `"voice_over"`）。

> **注意字段命名差异：** [api.md §11](../../docs/design/api.md) 的示例（`added` 用 `{scene_id, beat_index, flag, desc}`、`externalized` 用 `{from, to}`）与**实际后端模型不一致**。**一律以上表（实际 `models/report.py`）为准**，不要照抄 api.md 的示例字段名。

### M7 必须知道的真实行为与坑（执行 Agent 必照）

1. **报告生成的前置门控是「剧本已生成」，不是「项目 state」。** 后端 `:generate` 只检查 `GET screenplay` 工件存在（否则 `404 "Screenplay not found"`）。**前端报告页门控：剧本工件存在（`GET /screenplay` 非 404）→ 可生成报告；否则空态引导回 `script`。** 不看 `project.state`/`project.gates`。
2. **`:generate` 不推进 `project.state` 到 `report`（后端缺口）。** 报告生成后端**不**调用任何 `_mark_project_*`，项目 state 停在 `generated`/`editing`。因此外层「幕步骤条」里 `report` 幕（[stages.ts](../../frontend/app/lib/stages.ts) 中 `report` 幕在 `state>=report` 点亮）**不会因生成报告而点亮**。**本期不改 stages.ts、不强行点亮**；报告页自身以「报告工件是否存在」驱动展示。在 PR2/PR3 描述里如实标注此缺口。
3. **stub 模式下 `deleted`/`merged`/`externalized` 基本恒为空。** 默认 [StubLlmGateway](../../backend/src/cardenio/gateway/providers/stub.py) 的 fixtures 里**没有 `report` 键**，故 LLM 叙述化返回 `{stub: true}`，后端走**确定性聚合 fallback**（`_deterministic_report`）。fallback 只填 `kept`/`added`/`externalized`/两个计数/`kept_foreshadowing`/`review_recommended`，**`deleted` 与 `merged` 永远是 `[]`**；`externalized` 仅在有特殊文案的 note/voice_over 节拍时才非空（mock 生成的剧本不含此类，故也为空）。**结论：UI 必须把每个分区都按「可能为空」渲染**（空时显示「无」占位），不得假设 `deleted`/`merged`/`externalized` 有数据。
4. **不要直接展示后端 `ReportEntry.desc`（英文、不可本地化）。** 用 `item` 作主文本，按 `flag`（`from_source`/`ai_inferred`）渲染**本地化**的来源说明与徽标（复用既有 `script.flags.*` 文案与 `flagVariant`）。
5. **`409 report_flag_mismatch` 在 stub 模式基本不会发生**（确定性 fallback 自洽），但 UI 仍需捕获：错误体走 **CardenioError 信封** `{"error":{"code":"report_flag_mismatch","message":...,"details":{...}}}`（[middleware.py](../../backend/src/cardenio/api/middleware.py) 把 `CardenioError` 转成 `to_dict()`），故 `ApiError.code === "report_flag_mismatch"` 可判。生成失败时 toast 友好提示（见坑 7 错误体差异）。
6. **`404` 走 FastAPI 默认 `detail`（字符串），`409`/领域错误走 `{error:{...}}` 信封。** 报告的 `404`（项目/剧本/报告不存在）是 `HTTPException`，错误体为 `{"detail":"..."}`；既有 [http.ts](../../frontend/app/lib/api/http.ts) `request()` 已对两种形态做了兜底（`payload.error ?? {message: detailMessage}`）。loader 用既有 `getOrNull`（判 `status===404`→null）即可。
7. **错误体差异（沿用既有结论）：** 领域错误（如 `report_flag_mismatch`）→ `ApiError.code` 可判；`404` → `ApiError.message` 为 detail 字符串。UI 层把 `report_flag_mismatch` 翻成本地化「报告与剧本标记不一致，无法生成」，其余显示 `ApiError.message`。

### 测试已断言的真实语义（来自 [test_report.py](../../backend/tests/api/test_report.py)，可作前端预期）

- 生成成功返回 `202`，`type:"report"`、`state:"draft"`、`parent_version == screenplay.version`。
- `from_source_lines` == 剧本非 todo 节拍中 `flag=="from_source"` 数；`ai_inferred_lines` == `flag=="ai_inferred"` 数。
- `kept` 非空且每条带 `scene_id` 或 `source_ref`；`added` 每条带 `scene_id` + `source_ref` + `flag=="ai_inferred"`；含 AI 节拍的场景出现在 `review_recommended`。
- 生成后 `GET /report` 返回同一 `version`。
- LLM 给出的统计与剧本 `flag` 不符 → `409`，`error.code=="report_flag_mismatch"`，`error.details.statistics.from_source_lines == {expected, actual}`。

---

## 总体方案与不变量

- **资源契约层沿用既有模式：** 在 [client.ts](../../frontend/app/lib/api/client.ts) 新增 `ReportApi`（`get`/`generate`），http 与 mock 双实现，经 `VITE_API_MODE` 切换；组件零分支消费同一接口。**`source.resolve` 已是 M6 PR1 建好的方法，本期直接复用，不需新增客户端方法。**
- **零新增 npm 依赖、零新增 coss 组件：** 报告页所需 `card`/`badge`/`button`/`alert`/`alert-dialog`/`empty`/`separator`/`collapsible`/`spinner`/`scroll-area`/`toast` **全部已装**（见 [app/components/ui/](../../frontend/app/components/ui/)）。业务逻辑用原生 `fetch` + React Router v7 内置 `clientLoader`/`useRevalidator`（仓库 `ssr:false`）。**因此本计划 README 无需更新**（无新依赖、无新外部来源、无运行流程变化）。
- **复用既有溯源与格式工具：** 复用 [screenplay-format.ts](../../frontend/app/lib/screenplay-format.ts) 的 `sourceRefLabel`/`paragraphLabel`/`sceneTitle`/`flagVariant`，复用 [trust-chips.tsx](../../frontend/app/components/trust-chips.tsx) 的 `TrustChips` 作图例。报告条目的「场景名」用剧本工件的 `sceneById` 映射 + `sceneTitle(scene)`，映射不到回退显示 `scene_id`。
- **路由无需改造：** `report` 已是 [routes.ts](../../frontend/app/routes.ts) 顶层阶段路由，对应 [project-report.tsx](../../frontend/app/routes/project-report.tsx) 占位文件。本计划**直接把该占位替换为可用页**，不新增/嵌套路由、不动 routes.ts、不动 project-layout/stages.ts。
- **信任能力对齐：** M7 在报告层继续兑现 P4/P5/NFR-4——`source_ref`（条目溯源 + 内联原文预览）、`flag`（来源/AI 区分徽标）、一致性核对（报告统计 vs 剧本标记，呼应 FR-7.5 加戏交叉核对）。
- **main 始终可运行：** 每个 PR 自身 `pnpm typecheck`/`build`/`lint`/`format:check` 通过；功能需后端在跑才能手测（mock 模式可离线走流程）。

---

## PR 拆分（4 个 PR，依次从 `main` 切分支）

> 分支名正则：`<type>/<小写-数字-连字符-点>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore/refactor。
> commit 正则：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**。
> pre-commit 跑 lint、pre-push 跑 build + 分支名校验。每个 PR 合并后 main 可运行，用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。
>
> **依赖顺序：** PR1（客户端）→ PR2（报告页壳 + 生成 + 渲染）→ PR3（一致性核对面板）/ PR4（内联原文预览）。PR3、PR4 都依赖 PR2，且彼此独立、可各自 build/verify。提交时间须落在 2026-06-05 ~ 2026-06-07（北京时间）。

---

### PR 1 — 报告 API 客户端（数据层，无 UI）

- **分支：** `feat/report-api-client`
- **一句话目标：** 按后端真实行为给 API 客户端新增 `ReportApi`（`get`/`generate`），含 types + client 接口 + http 实现 + mock 实现，不接任何 UI。
- **改动文件：**
  - [types.ts](../../frontend/app/lib/api/types.ts)：新增类型（字段严格对齐上文「`ReportData` 数据形状」，复用既有 `SourceRef`/`Flag`）：
    - `ReportEntry { item: string; source_ref: SourceRef | null; scene_id: string | null; flag: Flag | null; desc: string | null }`
    - `ReportMergedEntry { scene_ids: string[]; into: string }`
    - `ExternalizationEntry { scene_id: string; from_type: string; to_type: string }`
    - `ReviewRecommendation { scene_id: string; reason: string }`
    - `ReportData { kept: ReportEntry[]; deleted: ReportEntry[]; merged: ReportMergedEntry[]; added: ReportEntry[]; externalized: ExternalizationEntry[]; from_source_lines: number; ai_inferred_lines: number; kept_foreshadowing: string[]; review_recommended: ReviewRecommendation[] }`
  - [client.ts](../../frontend/app/lib/api/client.ts)：
    - 新增 `ReportApi` 类型：
      - `get(projectId: ProjectId): Promise<ArtifactEnvelope<ReportData>>`
      - `generate(projectId: ProjectId): Promise<ArtifactEnvelope<ReportData>>`
    - 把 `report: ReportApi` 加入 `ApiClient` 类型，并在 `import type {...}` 里补 `ReportData`。
  - [http.ts](../../frontend/app/lib/api/http.ts)：实现 `report`：
    - `get` = `GET /projects/{projectId}/report`（返回信封，原样返回）。
    - `generate` = `POST /projects/{projectId}/report:generate`（**冒号动作段按字面拼接，勿 URL-encode 冒号**；无 body；返回 `202` 信封，既有 `request()` 对 2xx 统一返回 payload，无需特判 202）。
  - [mock.ts](../../frontend/app/lib/api/mock.ts)：给 `report` mock 加实现，**复刻后端确定性聚合的关键语义**供离线 UI 开发：
    - 新增 `const reportStore = new Map<ProjectId, ArtifactEnvelope<ReportData>>();`（与其它 store 并列）。
    - 在 `projects.remove` 里追加 `reportStore.delete(id);`（与既有 `screenplayStore.delete(id)` 并列，避免脏数据）。
    - 新增内部工具 `buildReportData(screenplay: ScreenplayData): ReportData`，**镜像后端 `_deterministic_report` + `_flag_statistics`**：
      - 遍历 `screenplay.scenes`，对每场：把 `scene.foreshadowing` 累加进 `kept_foreshadowing`；遍历 `scene.beats`：
        - `beat.type === "todo"` → 跳过计数，但标记本场「含复查材料」。
        - 否则按 `flag` 归类：`from_source` → push 进 `kept`；`ai_inferred` → push 进 `added` 且标记本场「含复查材料」。push 的 `ReportEntry` = `{ item: 取 beat.dialogue ?? beat.text ?? beat.type（>96 截断加 "..."）, source_ref: beat.source_ref ?? scene.source_ref, scene_id: scene.id, flag: beat.flag, desc: null }`。
      - `from_source_lines` = 全部非 todo 节拍中 `flag==="from_source"` 计数；`ai_inferred_lines` = `flag==="ai_inferred"` 计数。
      - 本场「含复查材料」（有 ai_inferred 或 todo 节拍）→ push `{ scene_id, reason }` 进 `review_recommended`（reason 用一句中文，如「本场含 AI 新增或待补充内容，建议复查」）。
      - `deleted: []`、`merged: []`、`externalized: []`（与 stub 后端一致，恒空）。
    - `report.generate(projectId)`：`getProjectOrThrow` → 要求 `screenplayStore` 已有（否则 `notFound("Screenplay not found")`）→ `const screenplay = getScreenplayEnvelope(projectId)` → `const data = buildReportData(screenplay.data)` → `const envelope = makeEnvelope("report", "draft", data, screenplay.version)` → `reportStore.set(projectId, envelope)` → 返回 envelope。**不改 project.state**（与后端缺口一致）。
    - `report.get(projectId)`：`getProjectOrThrow` → `reportStore.get(projectId)` 否则 `notFound("Report not found")`。
    - **mock 离线提示（写进 PR 描述，不写进代码）：** seed 里没有现成 screenplay/report 工件；离线测 `report` 需先在 mock 模式把某项目跑到「人物确认→意图保存→大纲生成→大纲确认→剧本生成」，再进 `/report` 点「生成报告」。
- **不在本 PR：** 任何路由/页面/组件改动。
- **建议 commits：**
  1. `feat(frontend): add adaptation report api types`（types.ts）
  2. `feat(frontend): add report api client http and mock`（client.ts + http.ts + mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint`/`format:check` 全过；app 行为与本 PR 前一致。mock 模式控制台手调 `api.report.generate(projectId)`（剧本未生成时抛 404；已生成时返回 `type:"report"` 信封，`from_source_lines`/`ai_inferred_lines` 与剧本节拍计数一致、`parent_version==screenplay.version`）、`api.report.get(projectId)` 形状/门控正确。

---

### PR 2 — 报告工作台壳 + 生成 + 结构化渲染（M7-T1，FR-10）

- **分支：** `feat/report-workbench`
- **一句话目标：** 把 [project-report.tsx](../../frontend/app/routes/project-report.tsx) 从占位升级为「改编取舍报告」：门控空态 + 生成/重新生成 + 摘要统计 + 各分类区块只读渲染（保留/新增/删除/合并/心理外化/保留伏笔/建议复查），每条带来源徽标。**不含一致性面板与内联原文预览**（留 PR3/PR4）。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`button`/`alert`/`alert-dialog`/`empty`/`separator`/`toast`，均已装；复用 `trust-chips`/`screenplay-format`）。
- **改动文件：**
  - [project-report.tsx](../../frontend/app/routes/project-report.tsx)：
    - 复制 M5/M6 同款 `getOrNull`（404→null）小工具（从 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 复制即可，保持同款写法）。
    - `clientLoader`：并行 `getOrNull(api.report.get)` + `getOrNull(api.screenplay.get)`。返回 `{ report, screenplay, projectId }`。（**不需要 characters**——报告条目展示的是节拍内容文本与场景名，场景名由剧本 `sceneById` 提供。）
    - **门控空态（两级）：**
      - `screenplay` 为 null（剧本未生成）→ `Empty`：`EmptyHeader`>`EmptyMedia variant="icon"`(`ScrollTextIcon`)+`EmptyTitle`/`EmptyDescription`「请先在剧本阶段生成初稿」+ `EmptyContent`>`Button render={<Link to={stagePath(id,"script")}/>}`「去生成剧本」。不展示报告区。
      - `screenplay` 存在但 `report` 为 null（报告未生成）→ `Empty`：标题/说明「尚未生成改编取舍报告」+ `EmptyContent`>「生成报告」`Button loading`（点击调 `api.report.generate`）。
    - **有报告：** 顶部页眉用既有 `pages.report.*`（milestone/title/description）+ 一个 `Badge` 显示工件 state（`draft`，复用 `statusVariant` 同款映射）+ 一行图例（`<TrustChips/>`，原文/AI 新增/TODO 三色）+ 右上「重新生成」入口（`AlertDialog` 确认，**镜像 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 的 regenerate 弹窗结构**：`AlertDialogTrigger render={<Button size="sm" variant="outline"/>}` + `AlertDialogPopup`>`AlertDialogHeader`(标题/说明)+`AlertDialogFooter`(取消 `AlertDialogClose render={<Button variant="ghost"/>}` / 确认 `AlertDialogClose render={<Button variant="destructive" loading onClick={generateReport}/>}`)）。
    - **摘要统计卡**（`Card`>`CardHeader`(title/description)+`CardPanel`）：两个醒目 `Badge`/数字块——「原文台词数 `from_source_lines`」（`variant="success"`）、「AI 新增数 `ai_inferred_lines`」（`variant="warning"`）。
    - **分类区块**（每类一个 `Card`，标题 + `Badge` 计数 + 列表；空类显示 dashed 占位文案「无」）：
      - **保留（kept）**：逐条 `item` 文本 + 场景名徽标（`sceneTitle` 映射）+ `sourceRefLabel(t, source_ref)` 徽标 + 来源徽标（`script.flags.from_source` 文案，`Badge variant="success"`）。
      - **新增（added）**：同上，来源徽标用 `script.flags.ai_inferred`（`Badge variant="warning"`），整条用 `bg-warning/8` 弱底强调「需重点复查」。
      - **删除（deleted）**：`item` + `sourceRefLabel`（stub 恒空 → 显示「无删除条目」占位）。
      - **合并（merged）**：每条「`scene_ids` 合并入 `into`」（用场景名映射）（stub 恒空 → 占位）。
      - **心理外化（externalized）**：每条「场景名：`from_type` → `to_type`」（`from_type`/`to_type` 用本地化映射，未知回退原值）（通常空 → 占位）。
      - **保留的伏笔（kept_foreshadowing）**：`string[]` 渲染为一组 `Badge variant="secondary"`；空→占位。
      - **建议重点复查（review_recommended）**：每条「场景名 + reason」（`reason` 直接展示后端文本；mock 用中文，真实后端可能英文——可接受，作为非主路径提示）。
    - **生成/重新生成逻辑**：`generateReport()` → `setWorking(true)` → `api.report.generate(projectId)` → 成功 `toastManager.add(success)` + `revalidator.revalidate()`；失败 toast：`ApiError.code === "report_flag_mismatch"` → 本地化「报告与剧本标记不一致，无法生成」；剧本不存在 404 → 本地化「请先生成剧本初稿」；其余显示 `ApiError.message`。生成期间按钮 `loading` 且禁用。
  - i18n 两 locale [zh-CN/common.json](../../frontend/app/i18n/locales/zh-CN/common.json) 与 [en/common.json](../../frontend/app/i18n/locales/en/common.json)：新增 `report.*` 命名空间（两 locale 键完全一致）：状态徽标、两级门控空态（标题/说明/CTA）、生成/重新生成（按钮、AlertDialog 标题/说明/确认/取消）、摘要统计标签（原文台词数/AI 新增数）、各分区标题与空占位（kept/added/deleted/merged/externalized/foreshadowing/review）、`from_type`/`to_type` 本地化映射键、成功/失败 toast、`report_flag_mismatch` 友好文案。复用 `pages.report.*` 作页眉、`trust.*` 作图例、`script.flags.*`/`script.sourceRef`/`script.noSourceRef` 作来源/溯源文案（避免重复造键）。
- **建议 commits：**
  1. `feat(frontend): add report workbench i18n keys`（两 locale）
  2. `feat(frontend): generate and render adaptation report`（门控 + 生成/重生成 + 摘要 + 分区渲染）
- **验收：** 已生成剧本的项目：进 `/report` → 看到「生成报告」入口 → 点击后展示报告（摘要统计与剧本节拍计数一致、保留/新增分区有条目、删除/合并/外化分区显示空占位、伏笔与建议复查可见）；「重新生成」走 AlertDialog 确认后刷新；未生成剧本时显示门控空态并可跳回 `script`。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 3 — 一致性核对面板（M7-T2，FR-10/FR-7.5）

- **分支：** `feat/report-consistency-check`
- **一句话目标：** 在报告页加一个可见的一致性核对面板：前端从剧本工件重算非 todo 节拍的 `from_source`/`ai_inferred` 计数，与报告 `from_source_lines`/`ai_inferred_lines` 对比，显式展示「✓ 一致」或「⚠ 不一致 / 报告可能已过时」。
- **额外价值（写进 PR 描述）：** 后端已在生成时强制一致（409）。但**作者在 M6 编辑器改过剧本后，旧报告会过时**——此面板用「当前剧本」重算并对比「已存报告」的统计，能在过时时给作者明确的「请重新生成报告」信号，是真实的信任增益（呼应 FR-7.5 加戏交叉核对、P5）。
- **先安装 coss 组件：** 无需新装（用 `alert`/`badge`/`button`，均已装）。
- **改动文件：**
  - [project-report.tsx](../../frontend/app/routes/project-report.tsx)：
    - 复用 PR2 已加载的 `report` 与 `screenplay`。新增本地纯函数 `countFlags(screenplay: ScreenplayData)`：遍历 `scenes.beats`，对非 `todo` 节拍按 `flag` 计数，返回 `{ from_source, ai_inferred }`（**复刻后端 `_flag_statistics` 语义**：只数非 todo 节拍）。
    - 计算 `consistent = recomputed.from_source === report.data.from_source_lines && recomputed.ai_inferred === report.data.ai_inferred_lines`。
    - 在摘要统计卡下方/报告顶部渲染一个 `Alert`：
      - `consistent` → `Alert variant="success"` + `CheckCircle2Icon`（**语义图标，不加 `aria-hidden`**）+ `AlertTitle`「报告统计与剧本标记一致」+ `AlertDescription`（展示「原文 X 条 / AI 新增 Y 条，与剧本标记一致」）。
      - 不一致 → `Alert variant="warning"` + `AlertTriangleIcon` + `AlertTitle`「报告可能已过时」+ `AlertDescription`（逐项展示「原文：报告 A / 剧本 B」「AI 新增：报告 C / 剧本 D」差异）+ `AlertAction`>「重新生成报告」`Button size="sm"`（复用 PR2 的 `generateReport`）。
    - **仅在 `report` 存在时渲染该面板**（无报告时是空态，不显示面板）。
  - i18n 两 locale：`report.consistency.*`（一致标题/说明、不一致标题/说明、逐项差异模板 `{{reported}}`/`{{actual}}`、重新生成按钮）。两 locale 键一致，插值占位一致。
- **建议 commits：**
  1. `feat(frontend): add report consistency check i18n keys`（两 locale）
  2. `feat(frontend): cross check report stats against screenplay flags`（重算 + 对比 + Alert 面板）
- **验收：** 已生成报告的项目：进 `/report` → 看到绿色「统计一致」面板（数字与剧本节拍计数吻合）；**到 `/editor` 对某场局部重生成或增删一个非 todo 节拍后回到 `/report`**（报告未重生成）→ 面板变黄色「报告可能已过时」并列出差异，点「重新生成报告」后回到一致。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 4 — 报告条目内联原文预览（FR-10 可溯源，P4）

- **分支：** `feat/report-source-preview`
- **一句话目标：** 给报告各条目（带非空 `source_ref` 的 kept/added/deleted）加 `Collapsible` 内联展开，点开时调既有 `api.source.resolve` 拉对应原文段落正文展示，让「可定位到原文段落」真正可读。
- **先安装 coss 组件：** 无需新装（用 `collapsible`/`spinner`/`alert`/`badge`，均已装）。**`source.resolve` 客户端方法 M6 PR1 已建，本期直接消费，不改客户端。**
- **改动文件：**
  - [project-report.tsx](../../frontend/app/routes/project-report.tsx)：
    - 把 PR2 里「保留/新增/删除」条目的渲染抽成一个内部 `ReportEntryRow` 组件，在 `source_ref` 非空时，在条目底部加一个 `Collapsible`：
      - `CollapsibleTrigger render={<Button size="sm" variant="ghost"/>}`「查看原文」（带 `ChevronRight`/`ChevronDown` 图标，按 `open` 切换；图标补 `aria-hidden`）。
      - 受控 `Collapsible`（`open`/`onOpenChange`）：**首次展开时**才发请求（懒加载），调 `api.source.resolve(projectId, source_ref.chapter, paragraphLabel(source_ref.paragraphs))`。
        - `paragraphLabel(source_ref.paragraphs)` 产出形如 `"45-51"` 或 `"45, 47"` 的选择器字符串，与 `source:resolve`/`parseParagraphSelector` 的「显式索引 + 区间」语义**精确往返**（已核对：逗号分隔与 `a-b` 区间均被后端/mock 接受）。
      - `CollapsiblePanel` 内三态：
        - 加载中 → `Spinner aria-label` + 「加载原文…」。
        - 成功 → 逐段渲染 `paragraphs[].index` + `paragraphs[].text`（`whitespace-pre-wrap`，弱底 `bg-muted/32 rounded`）。
        - 失败（`source.resolve` 404「该引用无法定位」或其它错误）→ `Alert variant="warning"` 行内提示「该引用无法定位到原文」（不崩溃、不弹全局 toast）。
      - **每条目独立缓存已解析结果**（本地 `useState`/`Map`，键用 `scene_id+source_ref` 或条目索引），避免重复折叠时重复请求。
    - `source_ref` 为 null 的条目（理论上 added 都有，kept 可能个别没有）→ 不渲染「查看原文」触发器，仅展示 `noSourceRef` 徽标。
  - i18n 两 locale：`report.preview.*`（「查看原文」/「收起」触发文案、「加载原文…」、「该引用无法定位到原文」、段落序号模板 `{{index}}`）。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add report source preview i18n keys`（两 locale）
  2. `feat(frontend): preview source paragraphs for report entries`（Collapsible + source.resolve 懒加载 + 三态 + 缓存）
- **验收：** 已生成报告的项目：进 `/report` → 某「保留/新增」条目点「查看原文」→ 内联展开显示该 `source_ref` 对应的原文段落正文；再点收起；故意构造一个段落不存在的引用（或对一个 mock 中越界引用）→ 得「无法定位」行内提示而非崩溃；重复折叠不重复请求。`build`/`typecheck`/`lint`/`format:check` 过。

---

## coss UI 组件映射（每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`。导入 `~/components/ui/<name>` 的**已样式化导出**优先于 `*Primitive`。**M7 不新装任何 coss 组件**（所需组件全部已装），也无新增 npm 依赖。下表组件用法已对照 coss skill 各 primitive 指南（collapsible/alert/empty/card/alert-dialog/spinner）。

| 界面元素 | coss 组件（已装） | 关键 composition / 注意点 | 所属 PR |
| --- | --- | --- | --- |
| 两级门控空态（无剧本 / 无报告） | `empty` | `Empty`>`EmptyHeader`(`EmptyMedia variant="icon"`+`EmptyTitle`/`EmptyDescription`)+`EmptyContent`(无剧本→`Button render={<Link/>}` 跳 script；无报告→「生成报告」`Button loading`)。**EmptyContent 必含可执行下一步** | PR2 |
| 工件状态徽标 | `badge` | `Badge variant={statusVariant(state)}`（复用 script 页同款映射，`draft`→warning/secondary） | PR2 |
| 信任图例 | 复用 `trust-chips`（已有组件） | 直接渲染 `<TrustChips/>`（原文/AI 新增/TODO 三色），读 `trust.*` | PR2 |
| 重新生成确认 | `alert-dialog` | **破坏性/重算确认用 AlertDialog**：`AlertDialogTrigger render={<Button size="sm" variant="outline"/>}`+`AlertDialogPopup`>`AlertDialogHeader`(标题/说明)+`AlertDialogFooter`(取消 `AlertDialogClose render={<Button variant="ghost"/>}` / 确认 `AlertDialogClose render={<Button variant="destructive" loading onClick={...}/>}`)。无 `AlertDialogPanel`，body 内容直接放 header/footer 之间 | PR2 |
| 摘要统计 / 分区计数 / 来源·溯源·伏笔徽标 | `badge` | `from_source_lines`→`variant="success"`、`ai_inferred_lines`→`variant="warning"`；来源徽标读 `script.flags.*` + `flagVariant`；`sourceRefLabel`/场景名/伏笔用 `variant="secondary"` | PR2 |
| 报告分区容器（保留/新增/删除/合并/外化/伏笔/复查） | `card`/`separator` | 每类一个 `Card`>`CardHeader`(`CardTitle`+计数 `Badge`)+`CardPanel`(列表)；保持 `CardHeader`/`CardPanel` 为 `Card` 直接子级；分区内分隔用 `Separator` | PR2 |
| 空分区占位 | 文本（无组件） | dashed 边框 + `text-muted-foreground` 文案（镜像 script 页 `noSceneMatches` 写法），**不要用 Empty**（Empty 留给整页门控） | PR2 |
| 一致性核对面板 | `alert` | 一致→`Alert variant="success"`+`CheckCircle2Icon`；不一致→`Alert variant="warning"`+`AlertTriangleIcon`+`AlertAction`(「重新生成」`Button size="sm"`)。**语义图标不加 `aria-hidden`**（图标传达状态） | PR3 |
| 条目内联原文预览 | `collapsible`+`spinner`+`alert` | `Collapsible`(受控 `open`/`onOpenChange`)>`CollapsibleTrigger render={<Button size="sm" variant="ghost"/>}`+`CollapsiblePanel`；trigger/panel 必在同一 `Collapsible` 根内；加载用 `Spinner aria-label`；失败用 `Alert variant="warning"`；**懒加载**（首次展开才请求） | PR4 |
| 操作成功/失败反馈 | `toast` | `toastManager.add({title,description,type})`；root 已接 provider | PR2–PR4 |

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **门控只看工件存在，不看 `project.state`/`project.gates`。** 报告页能否生成 → `GET /screenplay` 是否 404（404=剧本未生成→空态引导回 `script`）；是否展示报告 → `GET /report` 是否 404（404=报告未生成→「生成报告」空态）。`project.gates` 是 http 层假默认值、`project.state` 不会被报告生成推进，**两者都不可用于报告页门控**。
2. **`:generate` 返回工件信封、同步 202、无 Job/SSE。** 拿到信封后直接 `revalidator.revalidate()` 整体刷新，不接轮询/流式。生成期间按钮 `loading` 且禁用。
3. **stub 模式下 `deleted`/`merged`/`externalized` 恒空 → 每个分区都按「可能为空」渲染**，空时显示本地化「无」占位，绝不假设有数据、绝不因空数组崩溃（`?? []` 兜底 + `.length === 0` 分支）。
4. **不展示后端 `ReportEntry.desc`（英文）。** 主文本用 `item`；来源说明/徽标按 `flag` 用既有 `script.flags.*` 本地化文案 + `flagVariant`。`review_recommended[].reason`、`externalized` 的类型字段属次要提示，可直接展示后端文本（真实后端可能英文，作为非主路径可接受），但**统计、徽标、主要交互文案一律本地化**。
5. **场景名映射用剧本工件。** 报告条目的 `scene_id` → 用剧本 `sceneById`（`new Map(screenplay.data.scenes.map(s=>[s.id,s]))`）+ `sceneTitle(scene)` 渲染；映射不到回退显示原始 `scene_id`。
6. **一致性重算只数非 todo 节拍**（与后端 `_flag_statistics` 一致）：`from_source` = 非 todo 且 `flag==="from_source"` 计数，`ai_inferred` = 非 todo 且 `flag==="ai_inferred"` 计数。把这两个值与报告的 `from_source_lines`/`ai_inferred_lines` 对比。
7. **内联预览的选择器字符串用 `paragraphLabel(source_ref.paragraphs)`**（产出 `"45-51"` / `"45, 47"`），它与 `source:resolve` 的「显式索引 + 区间」语义精确往返；**懒加载**（首次展开才请求）并**按条目缓存**结果避免重复请求；`source.resolve` 的 404/错误在面板内 `Alert variant="warning"` 友好提示，不弹全局 toast、不崩溃。
8. **`extra="forbid"` 不影响报告（报告是只读消费）。** 本期不回写报告工件（无 `PUT /report`），无须担心多字段；但若未来加报告编辑，仍须遵守全量回传/不混信封字段的既有红线。
9. **错误处理分流：** `ApiError.code === "report_flag_mismatch"`（409，`{error:{...}}` 信封）→ 本地化「报告与剧本标记不一致，无法生成」；剧本不存在 404（`detail` 字符串）→ 本地化「请先生成剧本初稿」；`source.resolve` 404 → 面板内「该引用无法定位到原文」；其余显示 `ApiError.message`。loader 的 404 一律 `getOrNull`→null。
10. **冒号动作段按字面拼接**（`report:generate`、`source:resolve`），不要 URL-encode 冒号。`GET /report` 是前缀根、`GET /screenplay` 是前缀根，均无尾段。
11. **i18n 两 locale 同步：** 每个新增键在 `zh-CN` 与 `en` 完全一致；插值占位一致。新增统一挂在 `report.*` 命名空间（`report.gate.*`/`report.generate.*`/`report.summary.*`/`report.sections.*`/`report.consistency.*`/`report.preview.*`），复用 `pages.report.*` 作页眉、`trust.*` 作图例、`script.flags.*`/`script.sourceRef`/`script.noSourceRef` 作来源/溯源文案，避免与既有命名空间冲突或重复造键。
12. **coss 用法红线**（照 coss skill）：① 导入 `~/components/ui/<name>` 已样式化导出优先于 `*Primitive`；② `AlertDialog` 无 `AlertDialogPanel`，header/footer 直接作 `AlertDialogPopup` 子级，动作用 `AlertDialogClose render={<Button/>}`；③ `Empty` 的 `EmptyContent` 必含可执行下一步，loading/error 不要用 Empty（用 Spinner/Alert）；④ `Collapsible` 的 trigger 与 panel 必在同一根内，受控懒加载；⑤ `Alert` 语义图标（成功/警告）**不加 `aria-hidden`**，装饰性图标（折叠箭头）加 `aria-hidden`；⑥ `Card` 保持 `CardHeader`/`CardPanel` 为直接子级以维持间距；⑦ 图标按钮补 `aria-label`；⑧ Toast 直接 `toastManager.add`。

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- **`report:generate` 不推进 `project.state` 到 `report`：** 报告生成后端不调用 `_mark_project_*`，项目 state 停在 `generated`/`editing`。外层「幕步骤条」的 `report` 幕（`state>=report` 点亮）因此**不会因生成报告而点亮**。本期报告页以「报告工件是否存在」自驱，不改 stages.ts、不强行点亮；在 PR2/PR3 描述标注。
- **stub provider 不产 `deleted`/`merged`/`externalized`：** 默认 StubLlmGateway 无 `report` fixture，后端走确定性 fallback，这三类恒空。UI 已按「可能为空」渲染。真实 LLM provider 接入后这些分区会有数据，前端渲染无需改动。
- **`ReportData` 字段命名与 [api.md §11](../../docs/design/api.md) 示例不一致：** 以实际 `models/report.py` 为准（见「数据形状」表）。api.md 示例的 `added.beat_index`、`externalized.{from,to}` 等字段名**不存在于实际响应**。
- **`ReportEntry.desc` 为英文、不可本地化：** 前端不展示，按 `flag` 自行本地化。`review_recommended[].reason` 文案语言取决于 provider（stub/mock 为中文，真实后端可能英文）。
- **无 `PUT /report`（报告不可编辑）：** 报告是只读工件，仅 `:generate`（重算覆盖）+ `GET`。本期不做报告内联编辑。
- **导出（export，API-27/28）属 `M-Should`、本期不接：** 报告页不提供导出入口。后端导出端点状态需后续独立里程碑核对。

> 这些只标注、不改后端。若后端后续补齐 state 推进 / 真实 LLM 叙述化 / 导出，前端可据此扩展。

---

## 验证方式（端到端）

1. **起后端：** `backend/` 按其工具启动 dev 服务（[dev_server.py](../../backend/scripts/dev_server.py)，`:8000`）。
2. **起前端：** 仓库根 `pnpm install`（本计划**无任何新 npm 依赖**）→ `pnpm dev`（默认 http，经 Vite 代理打 `:8000`）。
3. **冒烟（按 PR 累积，需先把某项目跑到「剧本初稿已生成」）：**
   - 前置：人物确认 → 意图保存 → 大纲生成并确认 → 剧本生成（`/script`）。
   - PR1：`typecheck`/`build` 过；mock 控制台手调 `api.report.generate`（剧本未生成抛 404；已生成返回 `type:"report"` 信封，统计与节拍计数一致、`parent_version==screenplay.version`）、`api.report.get`，形状/门控正确。
   - PR2：进 `/report` → 「生成报告」→ 摘要统计与剧本节拍计数一致、保留/新增分区有条目、删除/合并/外化分区显示空占位、伏笔与建议复查可见；「重新生成」AlertDialog 确认后刷新；未生成剧本时门控空态可跳回 `script`。
   - PR3：报告页见绿色「统计一致」面板；到 `/editor` 对某场局部重生成或增删一个非 todo 节拍后回 `/report`（报告未重生成）→ 面板变黄「报告可能已过时」并列差异，点「重新生成报告」后回到一致。
   - PR4：某「保留/新增」条目点「查看原文」→ 内联展开对应原文段落；收起；越界引用得「无法定位」行内提示而非崩溃；重复折叠不重复请求。
   - 离线：任一 PR 后 `VITE_API_MODE=mock pnpm dev` 仍可走完「生成剧本→进 report→生成报告→看分区/一致性/原文预览」流程（mock 复刻确定性聚合/门控/resolve；需先在 mock 跑到剧本已生成）。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。人工点检 AlertDialog/Collapsible 的键盘与焦点返回、Alert 语义图标可读性。
5. **窗口与规范：** 提交时间落在 2026-06-05 ~ 2026-06-07（北京时间）；分支名/commit 经 hooks 校验（subject 纯 ASCII）；每 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式并勾选合规项。

---

## AGENTS.md 合规要点

- **单一边界：** PR1 客户端、PR2 报告页壳+生成+渲染、PR3 一致性面板、PR4 内联原文预览——每个 PR 一个清晰边界，互不混入无关重构/样式。PR4 把 PR2 的条目渲染抽成 `ReportEntryRow` 属**与本功能直接相关**的就地小重构（仅服务于内联预览复用），不算无关重构。
- **README 更新：** **本计划无新增第三方依赖、无新增外部来源、无运行/测试流程变化、无 coss 新组件**，故 **README 无需更新**。每个 PR 的「来源与依赖」段写「无新增第三方依赖；复用既有 API 客户端模式、已装 coss 组件与既有 `source:resolve` 端点」。
- **PR 描述据实披露：** 复用既有 API 客户端模式与 coss 基座；后端缺口（state 不推进 report、stub 不产 deleted/merged/externalized、api.md 字段名不一致、desc 英文、无 PUT /report、导出不接）如实说明，不得把后端能力写成前端原创。
- **main 每次合并后可 `pnpm build` 通过、可启动；提交在开发窗口内（2026-06-05~06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。**
