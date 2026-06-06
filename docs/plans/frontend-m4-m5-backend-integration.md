# 前端接入后端 M4/M5 接口 — 实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 **M4（分场大纲：生成 / 编辑 / 调序 / 溯源校验 / 合并建议）** 与 **M5（剧本生成：媒介翻译 / 心理外化 / 加戏强标注 / 台词溯源 / 潜台词情绪 / 镜头建议开关）** 接口。本计划把这两层接到前端：把 `outline`（分场大纲）和 `script`（剧本）两个当前为 `StagePlaceholder` 的顶层阶段页升级为可用界面。**全程只改 `frontend/`，不改 `backend/`。**
>
> 本计划延续 [`frontend-m2-m3-backend-integration.md`](./frontend-m2-m3-backend-integration.md) 的全部约定（默认 `http` 模式、http/mock 双实现经 `VITE_API_MODE` 切换、coss 组件经 shadcn `@coss` registry 安装、信封 envelope 形状、门控只看工件 state、`extra="forbid"` 全量回传、冒号动作段按字面拼接、不发 `If-Match`、两 locale 键同步、Conventional Commits + 纯 ASCII subject、PR 模板五段式）。执行前请通读 M2/M3 计划的「总体方案与不变量」「跨 PR 关键实现细则」「coss 用法红线」，本计划只补充 M4/M5 的差异点。

---

## Context（为什么做、目标、已确认决策）

- 产品主流程在「导入（M0/M1）→ 理解/档案/意图（M2/M3，均已接通）」之后是 **M4 分场大纲 → M5 剧本初稿**。后端已把 M4/M5 接口实现完毕（见下「后端现状核对」），但前端 `outline` 与 `script` 两个阶段仍是 [project-outline.tsx](../../frontend/app/routes/project-outline.tsx) / [project-script.tsx](../../frontend/app/routes/project-script.tsx) 的占位页，且 API 客户端层（[client.ts](../../frontend/app/lib/api/client.ts)）只有 `projects`/`source`/`understanding`/`characters`/`intent` 五类资源，**没有 outline / screenplay 资源**。
- 目标产出：作者在人物档案确认后，能在 `outline` 阶段——
  1. **生成分场大纲** → 按场卡片查看（标题/地点/时间/人物/目标/冲突/基调/伏笔/关系变化/结尾状态/`source_ref` 文本标记）。
  2. **编辑大纲**：增加 / 删除 / 编辑场景（含场景标题枚举、出场人物、伏笔、关系变化），上/下移动调序。
  3. **合并建议**：查看后端给出的过场合并建议，逐条「采纳 / 忽略」（仅改状态、**绝不自动合并**）。
  4. **确认大纲** → 解锁剧本生成 → CTA 进入 `script`。
  
  随后在 `script` 阶段——
  5. **生成剧本初稿**（可选「生成镜头建议」开关）→ 按场结构化卡片只读查看（场景标题 + 节拍序列，每个节拍显示类型/动作或对白/潜台词/`source_ref`/来源 `flag`）。
  6. **加戏筛选**：用三态分段控件在「全部 / 仅原文 / 仅 AI 新增」之间过滤高亮节拍，并提供一个跨场的「AI 新增内容清单」（FR-7.5 底线信任能力）。
  
  全部数据来自真实后端。
- **本次已与用户确认的三项决策（写死，执行 Agent 不得擅自变更）：**
  1. **M5 范围 = 只读查看器。** 后端剧本的编辑类接口（整稿改写 `PUT /screenplay`、单场重写 `:rewrite`、`/todos`、版本分支 `versions`/`:checkout`/`:diff`）**目前都是 `NotImplementedError`**（属 M6 打磨工作台）。因此本期 `script` 页只做：**生成 + 只读结构化查看 + ai_inferred 过滤 + 镜头建议开关**。不实现任何剧本编辑、局部重生成、YAML 手改、版本分支。
  2. **剧本展示形态 = 结构化卡片。** 每场一张卡片（场景标题 + 节拍列表，每个节拍呈现类型/对白/潜台词/来源标记）。**所见即所得的中文剧本排版（FR-9.5）属 M6，本期不做**，避免与 M6 重叠。
  3. **原文溯源（source_ref → 原文段落）本期不接。** M4/M5 **只展示 `source_ref` 的文本标记**（如 `第2章 · 第45-51段`），**不调用** `GET source:resolve`、不做原文跳转/对照。原文实际拉取与双栏对照统一留给 **M6 双栏编辑器**。

---

## 后端现状核对（执行前必读，以代码实际行为为准）

> 已逐文件、逐测试核对：[outline.py](../../backend/src/cardenio/api/routes/outline.py)、[screenplay.py](../../backend/src/cardenio/api/routes/screenplay.py)、[domain/models/outline.py](../../backend/src/cardenio/domain/models/outline.py)、[domain/models/screenplay.py](../../backend/src/cardenio/domain/models/screenplay.py)、[domain/models/base.py](../../backend/src/cardenio/domain/models/base.py)、[tests/api/test_outline.py](../../backend/tests/api/test_outline.py)、[tests/api/test_screenplay.py](../../backend/tests/api/test_screenplay.py)。

### 通用：仍是统一信封（envelope）

`outline` 与 `screenplay` 工件的读写接口都返回与 M2/M3 完全相同的 `ArtifactEnvelope`（`type`/`state`/`version`（`v_<hex8>`）/`parent_version`/`etag`（恒 null）/`updated_at`/`needs_recompute`/`data`）。沿用 M2/M3 的处理：`version` 当不透明串、不解析；不发 `If-Match`；门控只看 `state`。前端已有的 `ArtifactEnvelope<T>`/`ArtifactState`/`SourceRef` 类型直接复用。

### M4 · 分场大纲（[outline.py](../../backend/src/cardenio/api/routes/outline.py)，前缀 `/projects/{project_id}/outline`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| 生成 | `POST :generate` | 无 | `202` + 信封（`state:"draft"`）。**前置：characters 工件 `state=="confirmed"`**，否则 `409 {"error":{"code":"state_gate_blocked","details":{"artifact":"characters",...}}}`。项目不存在 → `404` |
| 读取 | `GET ` (前缀根) | — | `200` 信封；尚未生成 → `404 {"detail":"Outline not found"}` |
| 新增场景 | `POST /scenes` | `OutlineScene` **全量** | `201` 信封（含全部场景，`state` 置回 `draft`）。`id` 已存在 → `409 {"detail":"Scene already exists"}`。大纲不存在 → `404` |
| 编辑场景 | `PUT /scenes/{scene_id}` | `OutlineScene` **全量** | `200` 信封（`state` 置回 `draft`）。`id` 不存在 → `404` |
| 删除场景 | `DELETE /scenes/{scene_id}` | — | `204`（`state` 置回 `draft`）。不存在 → `404` |
| 调序 | `POST /scenes:reorder` | `{ "order": ["sc_003","sc_001",...] }` | `200` 信封（`state` 置回 `draft`）。order 未恰好覆盖每个场景一次 → `422 {"detail":"Order must include every scene once"}` |
| 确认 | `POST :confirm` | 无 | `200` 信封（`state:"confirmed"`）。尚未生成 → `404` |
| 取合并建议 | `GET /merge-suggestions` | — | `200` `{ "suggestions": [ MergeSuggestion ] }`。大纲不存在 → `404`。**副作用见坑 4** |
| 采纳建议 | `POST /merge-suggestions/{id}:apply` | 无 | `200` 信封（建议 `status:"applied"`，**场景结构不变**）。建议不存在 → `404` |
| 忽略建议 | `POST /merge-suggestions/{id}:dismiss` | 无 | `200` 信封（建议 `status:"dismissed"`，**场景结构不变**）。建议不存在 → `404` |

`OutlineScene`（`extra="forbid"` —— 多传任何字段会 422）：

```jsonc
{
  "id": "sc_001",                      // 必填，唯一
  "heading": {                          // 必填对象
    "int_ext": "INT",                  // 枚举 INT | EXT
    "location": "旧书店",               // 必填字符串
    "time": "NIGHT"                    // 枚举 DAY | NIGHT | DAWN | DUSK
  },
  "source_ref": {                       // 必填，且段落必须真实存在（见坑 1）
    "chapter": 1,
    "paragraphs": [1, 2]
  },
  "synopsis": "string",                 // 必填非空
  "goal": "string | null",              // 可空
  "conflict": "string | null",          // 可空
  "mood": "string | null",              // 可空
  "characters": ["lin_che"],            // 人物 id 数组（默认 []）
  "foreshadowing": ["父亲的怀表"],       // 字符串数组（默认 []）
  "relation_changes": [                  // 默认 []
    { "characters": ["lin_che","mother"], "change": "信任出现裂缝" }
  ],
  "ending_state": "string | null"       // 可空
}
```

`MergeSuggestion`：`{ "id":"mg_sc_001_sc_002", "scene_ids":["sc_001","sc_002"], "reason":"...", "status":"pending"|"applied"|"dismissed" }`。

`OutlineData`（信封 `data`）：`{ "scenes": OutlineScene[], "merge_suggestions": MergeSuggestion[] }`。

**M4 必须知道的真实行为与坑：**

1. **`source_ref` 严格校验，是新增/编辑场景最大的坑。** 生成、新增、编辑、删除、确认前后端都会逐场调 `_validate_outline_source_refs`：每个场景的 `source_ref.paragraphs` 必须**全部命中** `ch_{chapter}` 章节里真实存在的段落 index，且 `paragraphs` **不能为空**，否则 `422`，错误体走 FastAPI 的 `detail` 字段（**不是** `{error:{...}}` 信封）：`{"detail":{"code":"invalid_source_ref","scene_id":"...","chapter":N,"missing_paragraphs":[...]}}`。**因此前端「新增场景」表单必须让作者选一个真实章节 + 该章真实存在的段落 index（≥1 个）**，否则必 422。实现要点见 PR3 与「关键实现细则」。
2. **所有写操作（add/update/delete/reorder）都把工件置回 `draft`。** 确认大纲后任何一次编辑/调序都会回到 draft，需要重新 `:confirm`，否则下游剧本生成关卡（要求 outline confirmed）会再次关闭。UI 必须据 `state` 提示「需重新确认」。
3. **写操作返回整份信封（含全部 scenes / merge_suggestions），不是单个场景。** 每次增删改调序后用返回信封的 `data` 整体刷新即可。
4. **`GET /merge-suggestions` 有副作用：** 它会重新计算建议并**保存一次大纲**（生成新 `version`，但 `state` 保持不变）。即「查看合并建议」会推进版本号。这是后端行为，前端无需处理，但不要因为版本变化而惊讶或重复请求。
5. **合并建议「永不自动合并」（P2 底线）。** `:apply` / `:dismiss` **只改 `suggestion.status`，绝不改动 `scenes`**（测试 `test_apply/dismiss_..._without_merging` 明确断言场景 id 列表不变）。所以 UI 上「采纳」语义 = **标记为「作者已采纳，待手动合并」**，真正的合并要作者自己用「编辑/删除场景」完成。**文案必须讲清楚这一点**，不要让作者误以为点「采纳」就合并了。
6. **`characters` 是人物 id（非姓名）。** 场景 `characters[]` 和 `relation_changes[].characters[]` 都是人物 id。要展示姓名、要让作者在编辑表单里勾选人物，**outline 页的 loader 需同时拉取 `characters` 工件**做 id→name 映射与候选项来源。
7. **生成是同步 202**（直接返回工件，无 Job/SSE）。`:generate` 期间按钮 `loading` 即可，无需轮询。

### M5 · 剧本生成（[screenplay.py](../../backend/src/cardenio/api/routes/screenplay.py)，前缀 `/projects/{project_id}/screenplay`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| 生成 | `POST :generate` | **可选** `{ "shot_hints": true }`（缺省/无 body = false） | `202` + 信封（`state:"draft"`，`data:{scenes, shot_hints:{enabled}}`）。**前置：outline 工件 `state=="confirmed"`**，否则 `409 state_gate_blocked`，`details.artifact=="outline"`。项目不存在 → `404` |
| 读取整稿 | `GET ` (前缀根) | `?format=json`（默认 json） | `200` 信封。`format!=json` → `422`。尚未生成 → `404 {"detail":"Screenplay not found"}` |
| 读取单场 | `GET /scenes/{scene_id}` | — | `200` **单个 `ScreenplayScene` 对象**（非信封）。场景不存在 → `404` |
| 按 flag 过滤节拍 | `GET /beats?flag=ai_inferred` | `flag` 可选（`from_source`\|`ai_inferred`） | `200` `{ "items": [ { "scene_id", "beat_index", "beat" } ], "count": N }`。非法 flag → `422` |
| ~~整稿改写~~ | `PUT ` | — | **`NotImplementedError`（M6，不接）** |
| ~~单场改写~~ | `PUT /scenes/{id}` | — | **`NotImplementedError`（M6，不接）** |
| ~~单场重写~~ | `POST /scenes/{id}:rewrite` | — | **`NotImplementedError`（M6，不接）** |
| ~~留白清单~~ | `GET /todos` | — | **`NotImplementedError`（M6，不接）** |
| ~~版本分支/对比~~ | `versions` / `:checkout` / `:diff` | — | **`NotImplementedError`（M6，不接）** |

`ScreenplayScene`（信封 `data.scenes[]`）：在 `OutlineScene` 全部字段基础上，把 `synopsis`/`goal`/`conflict`/`mood`/`ending_state` 都放宽为可空，并新增 `beats: Beat[]`。

`Beat`（`extra="forbid"`）：

```jsonc
{
  "type": "action",   // action | dialogue | voice_over | off_screen | note | todo
  "text": "string | null",          // action/note/todo 的正文
  "character": "lin_che | null",     // dialogue/voice_over/off_screen 的人物 id
  "parenthetical": "(声音发抖) | null",
  "dialogue": "string | null",       // 台词正文
  "subtext": "string | null",        // 潜台词（FR-7.6，后端会补全）
  "source_ref": { "chapter":1, "paragraphs":[1,2] } /* | null，后端会为对白补全 */,
  "flag": "from_source | ai_inferred | null",   // P5，后端强制（见坑 2）
  "options": [                        // 仅 note 类型有：心理外化多方案（FR-7.1）
    { "kind": "voice_over", "text": "..." },
    { "kind": "action", "text": "..." },
    { "kind": "dialogue", "text": "..." },
    { "kind": "annotation", "text": "..." }
  ]
}
```

`ScreenplayData`（信封 `data`）：`{ "scenes": ScreenplayScene[], "shot_hints": { "enabled": false } }`。

**M5 必须知道的真实行为与坑：**

1. **生成前后端会强制信任不变量**（`_enforce_screenplay_trust`）：① 凡 `source_ref` 不在大纲来源段落集合内的节拍被强制 `flag:"ai_inferred"`；② 缺 `subtext` 的非 todo 节拍被补 `subtext`；③ 缺 `mood` 的场景被补 `mood`；④ 对白类（dialogue/voice_over/off_screen）若缺 `source_ref` 会回填为该场 `source_ref`，且无来源者标 `ai_inferred`；⑤ 意图 `must_keep_lines` 的台词被逐字注入并标 `from_source`。**结论：前端拿到的每个 beat 基本都带 `flag` 与（对白/动作）`source_ref`，可放心据此渲染信任标记，无需自己补算。**
2. **`flag` 是加戏标注底线（FR-7.5/P5）。** UI 必须能区分并高亮 `ai_inferred`（AI 新增）vs `from_source`（原文已有）。`todo` 类型节拍是留白（P6/FR-9.6），单独高亮为「待补充」。
3. **`character` 是人物 id。** 渲染对白时要把 id 映射成姓名 → **script 页 loader 需同时拉 `characters` 工件**。映射不到时回退显示 id 本身。
4. **`note` 类型携带 `options[]`（心理外化多方案）。** 本期**只读展示**这些备选方案（FR-7.1），不提供「选用某方案」的写操作（后端无此接口）。
5. **剧本没有 `:confirm`，也没有编辑接口。** `script` 页**只有「生成 / 重新生成」**两个写动作；查看为只读。下游报告（M7）的关卡只要求 screenplay `state=="draft"`，生成后即满足，**所以本页不需要确认按钮**。CTA 指向下一幕 `/editor`（占位）。
6. **`:generate` 是覆盖式**（重新生成会覆盖现有剧本、串 `parent_version`、回到 draft）。「重新生成」要用 `AlertDialog` 二次确认。
7. **`shot_hints` 是逐次生成的请求参数**，落在 `data.shot_hints.enabled`，**不是项目级持久设置**（项目级开关是 M8 settings 的事）。本期：生成区放一个 `Switch`「生成镜头建议」，其值决定 `:generate` 的 body `{shot_hints:bool}`；生成后从返回 `data.shot_hints.enabled` 回显当前剧本是否含镜头建议。
8. **`/beats?flag=` 与整稿过滤的关系：** 整稿 `GET` 已包含全部 scenes+beats，**页内过滤高亮一律在前端本地对已加载整稿做**（单一数据源、无闪烁）。`/beats?flag=ai_inferred` 端点用于**独立的「AI 新增内容清单」**（跨场汇总 `{scene_id, beat_index, beat}` + `count`），给作者一个集中复查入口（FR-7.5「UI 可筛选」），与页内高亮互补。

### 跨层：`project.state` 推进与门控策略（沿用并扩展 M2/M3 结论）

- M2/M3 计划已记录：导入未置 `imported`，理解/档案确认不推进 state，**只有保存意图会把 state 跳到 `intent_set`**。
- **从 `intent_set` 起 state 链恢复正常：** `outline:generate` 在 `state==intent_set` 时推进到 `outlined`；`screenplay:generate` 在 `state==outlined` 时推进到 `generated`（测试 `test_generate_after_intent_updates_project_state` / `test_generate_after_outlined_project_updates_state` 确认）。
- **门控策略（写死）：**
  - **阶段内部「能否生成 / 是否已确认」一律看工件 state，不看 `project.state`/`gates`：** outline 能否生成 → `GET /characters` 的 `state==="confirmed"`；剧本能否生成 → `GET /outline` 的 `state==="confirmed"`。
  - **外层「幕步骤条」（[project-layout.tsx](../../frontend/app/routes/project-layout.tsx) 的 `isStageDone`）继续读 `project.state`**：`outline` 幕在 `state>=outlined` 点亮，`script` 幕在 `state>=generated` 点亮。由于 `outline:generate` / `screenplay:generate` 会推进 state（前提是意图已保存使 state 到达 `intent_set`），幕导航会正确点亮，**无需改 [stages.ts](../../frontend/app/lib/stages.ts)**。
  - **已知联动：** 若作者跳过「保存意图」直接到大纲（理论上人物已确认即可生成大纲），大纲能生成但 `project.state` 不会推进到 `outlined`（停在 `profiled`），外层幕不点亮。这是 M2/M3 已记录的 state 缺口的延续，**前端不修**，在相关 PR 描述里标注「建议作者先完成意图阶段」。

---

## 总体方案与不变量

- **资源契约层沿用既有模式：** 按 [client.ts](../../frontend/app/lib/api/client.ts) 现有 `ApiClient` 扩展两类资源 `outline`/`screenplay`，http 与 mock 双实现，经 `VITE_API_MODE` 切换；组件零分支消费同一接口。
- **不引入任何新 npm 依赖：** 业务逻辑用原生 `fetch` + React Router v7 内置 `clientLoader`/`useRevalidator`（仓库 `ssr:false`，用 client 版）。UI 用 coss registry 组件（第三方基座，非 npm 包）；**本计划全程只新装一个 coss 组件 `toggle-group`（PR6），其余全部复用已装组件**。
- **路由无需改造：** `outline` 与 `script` 已是 [routes.ts](../../frontend/app/routes.ts) 里的顶层阶段路由，各对应一个占位文件。本计划**直接把这两个占位文件替换为可用页**，不新增/嵌套路由、不动 routes.ts、不动 project-layout/stages.ts。
- **门控来自工件 state，不来自 `project.state`/`gates`**（见上）。
- **信任能力对齐：** M4 落地 `source_ref` 的**文本标记展示**（每场可见来源章节/段落，但本期不拉原文）；M5 落地 `flag`（`from_source`/`ai_inferred`）与 `todo` 的**可视化高亮 + 过滤 + 跨场清单**，这是 P4/P5/P6 在剧本层的体现，属 MVP 必做、不延后。
- **main 始终可运行：** 每个 PR 自身 `pnpm typecheck`/`build`/`lint`/`format:check` 通过；功能需后端在跑才能手测（mock 模式可离线走流程）。

---

## PR 拆分（6 个 PR，依次从 `main` 切分支）

> 分支名正则：`<type>/<小写-数字-连字符-点>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore。
> commit 正则：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**。
> pre-commit 跑 lint、pre-push 跑 build + 分支名校验。每个 PR 合并后 main 可运行，用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。
>
> **依赖顺序：** PR1（客户端）→ PR2（大纲查看/生成/确认）→ PR3（大纲编辑/调序）→ PR4（合并建议）→ PR5（剧本生成/查看）→ PR6（加戏筛选）。PR2–4 都依赖 PR1；PR5–6 依赖 PR1，且功能上需大纲已确认（数据前置，代码不耦合）。每个 PR 可独立 build/verify。

---

### PR 1 — 新增 outline / screenplay 两类资源的 API 客户端（数据层，无 UI）

- **分支：** `feat/outline-screenplay-api-client`
- **一句话目标：** 按后端真实行为给 `ApiClient` 增加 `outline`/`screenplay` 两类资源（types + client 接口 + http 实现 + mock 实现），不接任何 UI。
- **改动文件：**
  - [types.ts](../../frontend/app/lib/api/types.ts)：新增类型（字段严格对齐上文「数据形状」）：
    - 通用：`Flag = "from_source" | "ai_inferred"`（新增；复用既有 `SourceRef`/`ArtifactEnvelope`/`ArtifactState`）。
    - 大纲：`IntExt = "INT"|"EXT"`；`TimeOfDay = "DAY"|"NIGHT"|"DAWN"|"DUSK"`；`SceneHeading { int_ext:IntExt; location:string; time:TimeOfDay }`；`RelationChange { characters:string[]; change:string }`；`OutlineScene { id:string; heading:SceneHeading; source_ref:SourceRef; synopsis:string; goal:string|null; conflict:string|null; mood:string|null; characters:string[]; foreshadowing:string[]; relation_changes:RelationChange[]; ending_state:string|null }`；`MergeSuggestionStatus = "pending"|"applied"|"dismissed"`；`MergeSuggestion { id:string; scene_ids:string[]; reason:string; status:MergeSuggestionStatus }`；`OutlineData { scenes:OutlineScene[]; merge_suggestions:MergeSuggestion[] }`；`MergeSuggestionsResponse { suggestions:MergeSuggestion[] }`。
    - 剧本：`BeatType = "action"|"dialogue"|"voice_over"|"off_screen"|"note"|"todo"`；`BeatOption { kind:string; text:string }`；`Beat { type:BeatType; text:string|null; character:string|null; parenthetical:string|null; dialogue:string|null; subtext:string|null; source_ref:SourceRef|null; flag:Flag|null; options:BeatOption[]|null }`；`ShotHints { enabled:boolean }`；`ScreenplayScene { id:string; heading:SceneHeading; source_ref:SourceRef; synopsis:string|null; goal:string|null; conflict:string|null; mood:string|null; characters:string[]; foreshadowing:string[]; relation_changes:RelationChange[]; ending_state:string|null; beats:Beat[] }`；`ScreenplayData { scenes:ScreenplayScene[]; shot_hints:ShotHints }`；`BeatsFilterItem { scene_id:string; beat_index:number; beat:Beat }`；`BeatsFilterResponse { items:BeatsFilterItem[]; count:number }`。
  - [client.ts](../../frontend/app/lib/api/client.ts)：`ApiClient` 增两类资源接口（http/mock 两实现都补齐）：
    - `OutlineApi`：`get(projectId): Promise<ArtifactEnvelope<OutlineData>>`、`generate(projectId): Promise<ArtifactEnvelope<OutlineData>>`、`addScene(projectId, scene:OutlineScene): Promise<ArtifactEnvelope<OutlineData>>`、`updateScene(projectId, sceneId:string, scene:OutlineScene): Promise<ArtifactEnvelope<OutlineData>>`、`deleteScene(projectId, sceneId:string): Promise<void>`、`reorder(projectId, order:string[]): Promise<ArtifactEnvelope<OutlineData>>`、`confirm(projectId): Promise<ArtifactEnvelope<OutlineData>>`、`getMergeSuggestions(projectId): Promise<MergeSuggestionsResponse>`、`applyMergeSuggestion(projectId, suggestionId:string): Promise<ArtifactEnvelope<OutlineData>>`、`dismissMergeSuggestion(projectId, suggestionId:string): Promise<ArtifactEnvelope<OutlineData>>`。
    - `ScreenplayApi`：`get(projectId): Promise<ArtifactEnvelope<ScreenplayData>>`、`generate(projectId, options?:{ shot_hints?:boolean }): Promise<ArtifactEnvelope<ScreenplayData>>`、`getScene(projectId, sceneId:string): Promise<ScreenplayScene>`、`getBeats(projectId, flag?:Flag): Promise<BeatsFilterResponse>`。
  - [http.ts](../../frontend/app/lib/api/http.ts)：实现上述方法，路径按前缀拼接，**冒号动作段（`:generate`/`:confirm`/`/scenes:reorder`/`:apply`/`:dismiss`）按字面拼接，勿 URL-encode 冒号**。要点：
    - `outline.generate`/`outline.confirm` = `POST` 无 body；`outline.get` = `GET` 前缀根。
    - `outline.addScene` = `POST .../outline/scenes`，body 为 `OutlineScene` 全量；`outline.updateScene` = `PUT .../outline/scenes/{sceneId}`；`outline.deleteScene` = `DELETE`（204，既有 `request()` 已处理 204→undefined）；`outline.reorder` = `POST .../outline/scenes:reorder`，body `{order}`。
    - `outline.getMergeSuggestions` = `GET .../outline/merge-suggestions`（返回 `{suggestions}`，**不是信封**，原样返回）；`applyMergeSuggestion`/`dismissMergeSuggestion` = `POST .../merge-suggestions/{id}:apply`/`:dismiss` 无 body（返回信封）。
    - `screenplay.generate` = `POST .../screenplay:generate`，**仅当传了 `options?.shot_hints` 才带 body** `{shot_hints: options.shot_hints}`，否则无 body（后端缺省 false）。`screenplay.get` = `GET .../screenplay`（不带 `format`，默认 json）。`screenplay.getScene` = `GET .../screenplay/scenes/{sceneId}`（返回裸场景对象）。`screenplay.getBeats` = `GET .../screenplay/beats`，`flag` 有值时加查询参数 `?flag=...`。
    - **`invalid_source_ref` 错误体走 `detail`（dict），不是 `error` 信封**：既有 `request()` 已把 `detail`（非字符串时 `JSON.stringify`）塞进 `ApiError.message`。本 PR 不必特殊处理，留给 PR3 在 UI 层把这种 422 翻成友好文案（见「关键实现细则」）。
  - [mock.ts](../../frontend/app/lib/api/mock.ts)：加两类资源的内存实现，复刻**关键语义**供离线 UI 开发：
    - 用 `Map<projectId, ArtifactEnvelope<OutlineData>>` 和 `Map<projectId, ArtifactEnvelope<ScreenplayData>>` 分别存。
    - `outline.generate`：在 `charactersStore` 非 confirmed 时抛 `ApiError(409,{code:"state_gate_blocked",details:{artifact:"characters",...}})`；否则产出 2–3 个完整场景（每场 heading 含合法枚举、`source_ref` 指向 `{chapter:1..3, paragraphs:[1,2]}`、含 synopsis/goal/conflict/mood/characters（取自 charactersStore 的 id）/foreshadowing/relation_changes/ending_state），`merge_suggestions` 给 1 条 pending（scene_ids 取相邻两场），`state:"draft"`。
    - `outline.addScene/updateScene/deleteScene/reorder`：按真实语义改 `scenes` 并把 `state` 置回 `draft`，串 `parent_version`，`version` 用既有 `v_mockN` 计数器；`addScene` 对重复 id 抛 409、reorder 对 order 集合不一致抛 422、找不到场景/大纲抛 404。**mock 可省略 source_ref 真实校验**（仅做最小化：paragraphs 为空时抛 422 invalid_source_ref，便于 UI 联调错误态）。
    - `outline.confirm`：置 `state:"confirmed"`；`getMergeSuggestions` 返回当前 `merge_suggestions`（mock 可不每次重算、不必复刻保存副作用）；`apply/dismiss` 改对应建议 `status`、`scenes` 不变。
    - `screenplay.generate`：在 outlineStore 非 confirmed 时抛 409（artifact:"outline"）；否则从大纲场景派生剧本：每场生成 `beats`——至少 1 个 `action`（flag from_source、带 source_ref、带 subtext）、1 个 `dialogue`（character 取该场首个人物 id、带 dialogue/parenthetical/subtext/source_ref/flag from_source）、**1 个 `note`（flag ai_inferred、带 4 个 options）**、**1 个 `todo`（留白）**；`shot_hints.enabled` 回显入参（默认 false）。`state:"draft"`，覆盖式重写串 parent_version。
    - `screenplay.get`：404 若未生成；`getScene`：遍历找 id；`getBeats`：遍历全部 scenes.beats，按 `flag` 过滤，返回 `{items:[{scene_id,beat_index,beat}],count}`。
    - mock 推进项目 state：`outline.generate` 把 `state==="intent_set"` 的项目推进到 `"outlined"`；`screenplay.generate` 把 `"outlined"` 推进到 `"generated"`（与后端一致，便于外层幕导航联调）。seed 的 `prj_demo_outlined` 已有 confirmed characters，可直接生成大纲。
- **不在本 PR：** 任何路由/页面/组件改动。
- **建议 commits：**
  1. `feat(frontend): add outline and screenplay api types`（types.ts）
  2. `feat(frontend): add outline and screenplay resources to api client and http`（client.ts + http.ts）
  3. `feat(frontend): add outline and screenplay mock adapters`（mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint`/`format:check` 全过；app 行为与本 PR 前一致。mock 模式控制台手调 `api.outline.generate(...)`、`api.outline.reorder(...)`、`api.screenplay.generate({shot_hints:true})`、`api.screenplay.getBeats("ai_inferred")` 形状/门控正确。

---

### PR 2 — 分场大纲：生成 / 卡片查看 / 确认 / 门控（读路径）

- **分支：** `feat/outline-stage`
- **一句话目标：** 把 [project-outline.tsx](../../frontend/app/routes/project-outline.tsx) 从占位升级为可用页：在人物档案已确认后一键生成大纲、按场卡片只读展示全部字段（含 `source_ref` 文本标记）、确认进入剧本步、处理门控与「需重新确认」提示。**不含场景编辑/调序/合并建议**（留 PR3/PR4）。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`alert`/`alert-dialog`/`button`/`separator`/`empty`/`collapsible`/`toast`，均已装）。
- **改动文件：**
  - [project-outline.tsx](../../frontend/app/routes/project-outline.tsx)：
    - `clientLoader`：并行 `getOrNull(api.outline.get)` + `getOrNull(api.characters.get)` + `api.source.get`（取章节列表用于段落计数显示，可选）。沿用 M2/M3 的 `getOrNull`（404→null）小工具（可在本文件内复制，或抽到共享 util；优先与 analysis 子页同款写法）。返回 `{ outline, characters, source }`。
    - **门控空态**：`characters` 未 confirmed → `Alert variant="warning"` + 标题/说明（「请先确认人物档案」）+ `Link` 回 `analysisStepPath(id,"characters")`，不展示生成按钮。
    - **无大纲且人物已确认**：`Empty` + 「生成分场大纲」`Button`（`loading`）→ `api.outline.generate`；若 409 `state_gate_blocked` 则 toast 提示并引导回档案步。
    - **已有大纲**：顶部 `Badge`/`Alert` 显示当前 `state`（草稿/已确认）+ 操作区（重新生成 / 确认）。下面按场渲染**只读卡片**（每场一个 `Card`）：
      - `CardHeader`：场景序号 + 标题（用 `heading.location` + `synopsis` 首句）+ 一组 `Badge`：`int_ext`（INT/EXT）、`time`（DAY/NIGHT/DAWN/DUSK 本地化）、`source_ref` 文本标记（如「第 1 章 · 第 1-2 段」，用工具函数把 `paragraphs` 压成区间/列表）。
      - `CardPanel`：分行展示 `synopsis`/`goal`/`conflict`/`mood`/`ending_state`（空字段不渲染或显示占位）；`characters` 用 `Badge` 列表（**经 characters 工件把 id 映射成 name**，映射不到回退 id）；`foreshadowing` 用 `Badge` 列表；`relation_changes` 用文本行（「关联人物 A、B：change」，人物用 name）。可用 `Collapsible` 把次要字段折叠。
      - **本 PR 卡片为纯只读**（无行内编辑、无菜单）。
    - **确认**：draft 时显示「确认分场大纲」`Button` → `api.outline.confirm` → 成功 toast + `revalidate`，并提供「进入剧本生成」CTA（`Link` → `stagePath(id,"script")`）。已确认后若 PR3 引入编辑导致回 draft，用 `Alert variant="info"` 提示「编辑后需重新确认才能进入下一步」（本 PR 先放好这个 state→提示的渲染分支）。
    - **重新生成**：已有大纲时提供「重新生成」按钮，用 `AlertDialog` 二次确认（会覆盖当前全部场景、若已确认会回 draft）后再调 `generate`。
  - i18n 两 locale [zh-CN/common.json](../../frontend/app/i18n/locales/zh-CN/common.json) 与 [en/common.json](../../frontend/app/i18n/locales/en/common.json)：新增 `outline.*` 命名空间（两 locale 键完全一致）：标题/说明、门控文案、空态、生成/重新生成/确认按钮与 toast、状态 `outline.status.empty/draft/confirmed`、`int_ext`/`time` 枚举本地化、`source_ref` 展示模板（含 `{{chapter}}`/`{{paragraphs}}`）、字段标签（synopsis/goal/conflict/mood/characters/foreshadowing/relation_changes/ending_state）、「需重新确认」提示、CTA。复用既有 `pages.outline.*`（已存在 milestone/title/description）作为页眉。
- **建议 commits：**
  1. `feat(frontend): add outline stage i18n keys`（两 locale）
  2. `feat(frontend): generate and view scene outline`（生成 + 卡片只读展示 + 门控 + 空态）
  3. `feat(frontend): confirm outline and gate screenplay step`（确认 + CTA + 重生成确认 + 需重新确认提示）
- **验收：** 后端在跑、某项目人物档案已确认：进 `/outline` 空态 → 生成 → 出现 ≥1 场卡片（字段非空、`source_ref` 文本标记可见、人物显示姓名）→ 确认后状态变「已确认」且「进入剧本生成」可点。人物未确认时显示门控提示并引导回档案步。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 3 — 分场大纲编辑：新增 / 编辑 / 删除场景 + 调序（含 source_ref 合法性）

- **分支：** `feat/outline-editing`
- **一句话目标：** 给大纲卡片加上行操作（编辑 / 删除）、列表上方「新增场景」、每张卡片的上/下移动调序；新增/编辑用 `Dialog` 表单，**强制产出合法 `source_ref`**（章节 + 真实段落），删除用 `AlertDialog` 二次确认。
- **先安装 coss 组件：** 无需新装（用 `dialog`/`alert-dialog`/`menu`/`select`/`field`/`input`/`textarea`/`input-group`/`number-field`/`button`/`badge`，均已装；字符串数组复用既有 [string-list-editor.tsx](../../frontend/app/components/string-list-editor.tsx)）。
- **改动文件：**
  - [project-outline.tsx](../../frontend/app/routes/project-outline.tsx)：在 PR2 卡片基础上补：
    - **行操作 `Menu`**（每张卡片头部 ghost icon 触发）：「编辑场景 / 删除场景」。删除项跳 `AlertDialog` 二次确认 → `api.outline.deleteScene` → 成功 toast + `revalidate`，并提示「删除会让大纲回到草稿，需重新确认」（见后端坑 2）。
    - **调序**：每张卡片头部一对「上移 / 下移」`Button size="icon"`（首张禁用上移、末张禁用下移）。点击 → 在本地把场景 id 数组交换相邻项 → 调 `api.outline.reorder(projectId, newOrderIds)`（**传全部场景 id 的完整新顺序**）→ `revalidate`。（**用上/下按钮而非拖拽**：无新依赖、键盘可达；拖拽留作未来增强。）
    - **新增场景**：列表上方「新增场景」`Button` → `Dialog`（本地受控 state）。表单字段：
      - `heading.int_ext` 用 **`Select`**（INT/EXT 两项）；`heading.time` 用 `Select`（DAY/NIGHT/DAWN/DUSK 四项）；`heading.location` 用 `Field`+`Input`。
      - **`source_ref`（关键）**：`chapter` 用 `Select`（items = 当前 `source.chapters` 的 order，label 用章节标题）；`paragraphs` 用「段落多选」——基于所选章节的真实段落 index 列表渲染一组可勾选项（`Checkbox` 列表或 `Select multiple`），**至少选 1 段**。换章节时清空已选段落。**禁止自由输入任意段号**（避免 422 invalid_source_ref）。
      - `synopsis` 用 `Field`+`Textarea`（必填非空）；`goal`/`conflict`/`mood`/`ending_state` 用 `Field`+`Input`（可空）。
      - `characters` 用 **`Select multiple`**（items = characters 工件的人物，value=id、label=name）。
      - `foreshadowing` 用 `StringListEditor`。
      - `relation_changes` 用一个轻量「关系变化编辑器」（内联子组件）：每行 = `Select multiple`（关联人物，取自 characters 工件）+ `Input`（change）+ 删除行；底部「添加一行」。**可选地，若工期紧可在本 PR 先把 relation_changes 设为只读、留空新增**——但编辑既有场景时要原样回传（`extra="forbid"`，见坑）。**推荐实现为可编辑行编辑器**以满足 FR-6.2。
      - 确认时**本地派生 `id`**：`sc_` + 递增序号或基于现有最大 `sc_NNN` +1（与后端 `sc_001` 风格一致），与现有 id 冲突则再加后缀去重；组装完整 `OutlineScene` 调 `api.outline.addScene`。成功 toast + `revalidate`；409（id 冲突）或 422（source_ref 非法）兜底为友好提示（见「关键实现细则」第 2 条）。
    - **编辑场景**：`Menu`「编辑」→ 同款 `Dialog`，以该场景为初值（`id` 固定不可改），保存调 `api.outline.updateScene(projectId, scene.id, fullScene)`。**全量 `OutlineScene`、严禁多字段**（`extra="forbid"`）；未在表单暴露的字段（如本 PR 若未做 relation_changes 编辑）必须以 loader 原值原样回传。
  - i18n 两 locale：`outline.*` 下补新增/编辑/删除对话框文案、字段标签与占位、章节/段落选择文案、调序按钮 aria-label、关系变化编辑器文案、删除二次确认、id 冲突与 `source_ref` 非法的友好提示、「编辑后需重新确认」。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add outline editing i18n keys`（两 locale）
  2. `feat(frontend): add and edit outline scenes`（Dialog 表单 + Select 枚举/章节 + 段落多选 + 人物多选 + StringListEditor + 本地 id 派生 + 全量回传）
  3. `feat(frontend): delete and reorder outline scenes`（Menu 删除 + AlertDialog + 上/下移调序）
- **验收：** 已生成大纲的项目：新增一个场景（选 INT/NIGHT、选章节 1 + 第 1 段、填 synopsis、勾 2 个人物、加 1 条伏笔、加 1 行关系变化）→ 保存后出现新卡片且持久；编辑某场 synopsis/goal/location → 保存生效；上移/下移改变顺序并持久；删除某场（二次确认）后仅该场消失；每次写操作后状态回「草稿」且提示需重新确认；故意把段落选成空（若 UI 允许）应得友好「原文引用无效」提示而非裸 JSON。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 4 — 分场大纲：合并建议（查看 / 采纳 / 忽略）

- **分支：** `feat/outline-merge-suggestions`
- **一句话目标：** 在大纲页加一个「合并建议」区块：拉取后端建议、逐条展示涉及的两场 + 理由 + 状态，提供「采纳 / 忽略」（**仅标状态、不自动合并**，文案讲清这一点）。
- **先安装 coss 组件：** 无需新装（用 `card`/`alert`/`badge`/`button`/`separator`，均已装）。
- **改动文件：**
  - [project-outline.tsx](../../frontend/app/routes/project-outline.tsx)：
    - `clientLoader` 增拉 `getOrNull(api.outline.getMergeSuggestions)`（仅在大纲存在时拉；404→null/空）。**注意后端坑 4**：该接口有保存副作用会推进 version，属正常，无需处理。
    - 在大纲卡片列表下方加「合并建议」`Card` 区块：
      - 顶部一句说明 + `Alert variant="info"`：**「这些是建议，采纳只是标记你的决定，系统不会自动合并；如需合并请用编辑/删除场景手动完成」**（P2 底线，措辞务必清楚）。
      - 每条建议一行/一小卡：展示 `scene_ids` 对应的两场标题（用大纲场景 id→标题映射）+ `reason` + 当前 `status`（`Badge`：pending/applied/dismissed 本地化）。
      - `status==="pending"` 时显示「采纳」「忽略」两个 `Button` → `api.outline.applyMergeSuggestion` / `dismissMergeSuggestion` → `revalidate`（场景列表不会变，仅状态变）。已采纳/已忽略显示状态徽标，可允许撤回（再调对侧动作）或只读，二选一（推荐：允许在 applied/dismissed 间切换）。
      - 无建议时显示「当前没有可合并的过场建议」空文案。
  - i18n 两 locale：`outline.merge.*` 下补区块标题/说明、底线提示、采纳/忽略按钮、三种 status 本地化、空态。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add outline merge suggestion i18n keys`（两 locale）
  2. `feat(frontend): review and resolve outline merge suggestions`（拉取 + 采纳/忽略 + 底线提示）
- **验收：** 已生成大纲（含相邻同人物过场）的项目：合并建议区出现 ≥1 条 pending 建议（显示两场标题 + 理由）→ 点「采纳」状态变 applied、**场景列表不变**；点「忽略」状态变 dismissed；提示文案明确说明不会自动合并。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 5 — 剧本生成与结构化只读查看器（含镜头建议开关）

- **分支：** `feat/screenplay-stage`
- **一句话目标：** 把 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 从占位升级为可用页：在大纲已确认后（可带「生成镜头建议」开关）生成剧本、按场结构化卡片只读展示场景与节拍（动作/对白/潜台词/来源标记/心理外化方案/留白）、重新生成、门控。**不含加戏过滤**（留 PR6）。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`switch`/`alert`/`alert-dialog`/`empty`/`button`/`separator`/`collapsible`/`scroll-area`/`toast`，均已装）。
- **改动文件：**
  - [project-script.tsx](../../frontend/app/routes/project-script.tsx)：
    - `clientLoader`：并行 `getOrNull(api.screenplay.get)` + `getOrNull(api.outline.get)`（取其 state 做门控）+ `getOrNull(api.characters.get)`（id→name 映射）。返回 `{ screenplay, outline, characters }`。
    - **门控空态**：`outline` 未 confirmed → `Alert variant="warning"`「请先确认分场大纲」+ `Link` 回 `stagePath(id,"outline")`，不展示生成按钮。
    - **无剧本且大纲已确认**：`Empty` + 生成区——一个 `Switch`「生成镜头建议」（`id`/`Label` 关联，默认关，附说明「景别/运镜仅作建议，可关闭，对应 NG4」）+ 「生成剧本初稿」`Button`（`loading`）→ `api.screenplay.generate({shot_hints: switchValue})`；409 `state_gate_blocked` → toast 引导回大纲步。
    - **已有剧本**：顶部 `Badge` 显示 `state`（草稿）+ 「当前镜头建议：开/关」（读 `data.shot_hints.enabled`）+ 操作区（重新生成）。按场渲染**结构化只读卡片**（每场一个 `Card`）：
      - `CardHeader`：场景序号 + `heading`（INT/EXT · location · time 用 `Badge`）+ `source_ref` 文本标记 + `mood`（`Badge`）。
      - `CardPanel`：渲染 `beats` 序列，每个 beat 一行/一块，按 `type` 不同样式：
        - `action`：动作正文 `text`；尾部 `Badge` 显示 `flag`（from_source 中性 / ai_inferred 警示高亮）；有 `subtext` 时用次要文字展示「潜台词：…」。
        - `dialogue`/`voice_over`/`off_screen`：人物名（id→name）+ `parenthetical`（括号提示）+ `dialogue` 正文；`voice_over` 标注「(V.O.)」、`off_screen` 标注「(O.S.)」；尾部 `flag` Badge + 「潜台词」。
        - `note`：以信息卡样式展示 `text`（「改编注释」），并把 `options[]`（心理外化多方案）用 `Collapsible`/列表**只读**展示（每条 `kind` 本地化 + `text`）；`flag` 通常 ai_inferred，高亮。
        - `todo`：以醒目「留白 TODO」样式展示 `text`（P6/FR-9.6），用 warning 色 `Badge`「待补充」。
      - 每个 beat 的 `source_ref` 以文本标记展示（不拉原文，决策 3）。长剧本可把每场 `CardPanel` 内容放进 `ScrollArea` 或整页自然滚动。
    - **重新生成**：`AlertDialog` 二次确认（覆盖现有剧本）后再调 `generate`（沿用当前开关值）。
    - **CTA**：剧本已生成后底部「进入打磨工作台」`Button`（`Link` → `stagePath(id,"editor")`，占位页可正常跳转）。**无确认按钮**（剧本无 `:confirm`，见坑 5）。
  - i18n 两 locale：`script.*` 下补标题/说明、门控、空态、镜头建议开关标题/说明、生成/重新生成按钮与 toast、`state`/`shot_hints` 状态文案、beat 类型本地化（action/dialogue/voice_over/off_screen/note/todo）、flag 本地化（原文/AI 新增）、潜台词/留白/改编注释/心理外化方案 `kind` 文案、`source_ref` 模板、CTA。复用既有 `pages.script.*` 作页眉。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add screenplay stage i18n keys`（两 locale）
  2. `feat(frontend): generate screenplay with shot hints toggle`（生成 + Switch + 门控 + 空态 + 重生成）
  3. `feat(frontend): render screenplay scenes and beats read only`（结构化卡片 + 节拍/潜台词/来源标记/外化方案/留白渲染）
- **验收：** 大纲已确认的项目：进 `/script` 空态 → 开/关「镜头建议」→ 生成 → 出现按场卡片，每场含动作/对白节拍，对白显示人物姓名，节拍带来源 `flag` 标记，至少一条 `note`（含心理外化多方案）与（若有）`todo` 留白被醒目展示；重新生成走二次确认；「进入打磨工作台」可点。大纲未确认时显示门控提示。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 6 — 剧本加戏筛选：三态过滤高亮 + AI 新增内容清单

- **分支：** `feat/screenplay-ai-inferred-filter`
- **一句话目标：** 在剧本页加「全部 / 仅原文 / 仅 AI 新增」三态分段过滤（本地对已加载整稿过滤高亮），并加一个用 `GET /screenplay/beats?flag=ai_inferred` 驱动的跨场「AI 新增内容清单」，把 FR-7.5 的「可高亮筛选」底线能力落到 UI。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/toggle-group`（三态分段控件）。装完 `git diff package.json` 确认无新增 npm 依赖。
- **改动文件：**
  - [project-script.tsx](../../frontend/app/routes/project-script.tsx)：
    - 在剧本卡片列表上方加一个 **`ToggleGroup`**（单选、三项：`all` / `from_source` / `ai_inferred`，本地化「全部 / 仅原文 / 仅 AI 新增」），用本地 state 持有当前过滤值。
    - **本地过滤高亮**（不发请求，对已加载 `screenplay.data.scenes` 处理）：
      - `all`：全部 beat 正常显示。
      - `from_source`/`ai_inferred`：与所选 flag 不符的 beat **弱化（降透明度/折叠）或隐藏**（推荐弱化，保留场景上下文）；命中的 beat 高亮。空场景（该场无命中 beat）可整场弱化或隐藏并显示「本场无匹配节拍」。
    - **「AI 新增内容清单」面板**（独立 `Card`，可放页尾或侧栏）：进入时或点「刷新清单」时调 `api.screenplay.getBeats(projectId, "ai_inferred")`，展示 `count` 与逐条 `{scene_id（→场景标题）, beat_index, beat 摘要}`，每条可作为「复查锚点」（点击滚动定位到对应场景卡片，用 `id`/`ref` 锚点；定位为增强项，最简实现可仅列出）。这是给作者集中复查 AI 加戏的入口（P5/R1）。
    - 用 `useState` 管过滤值即可，不需要额外 loader 改动（清单可用一个独立的轻量请求或并入 loader；推荐进入页面时在 loader 里并行 `getOrNull(api.screenplay.getBeats(projectId,"ai_inferred"))`，剧本不存在时为 null）。
  - i18n 两 locale：`script.filter.*`（三态标签）、`script.aiList.*`（清单标题/说明/计数 `{{count}}`/空态/复查提示）。两 locale 键一致。
  - [README.md](../../README.md)：在「依赖与来源」coss 组件清单里**追加 `toggle-group`**，并在「原创边界」段说明剧本阶段的生成/只读查看/加戏筛选/信任标记展示逻辑为本项目业务实现，coss 组件为 registry 生成的第三方基座。
- **建议 commits：**
  1. `chore(frontend): add coss toggle-group for screenplay filter`（toggle-group + README 组件清单追加）
  2. `feat(frontend): add screenplay beat flag filter i18n keys`（两 locale）
  3. `feat(frontend): filter screenplay beats by flag and list ai inferred`（ToggleGroup 三态过滤高亮 + AI 新增清单）
- **验收：** 已生成剧本的项目：切「仅 AI 新增」→ 仅 ai_inferred 节拍高亮、其余弱化；切「仅原文」→ 反之；切「全部」→ 复原；「AI 新增内容清单」显示与高亮一致的条数与逐条摘要；构造一份含明显 AI 新增 note 的剧本时清单与高亮数目一致（与后端 `flag` 标记一致，FR-10/R1 交叉核对）。`git diff package.json` 无新增 npm 依赖。`build`/`typecheck`/`lint`/`format:check` 过。

---

## coss UI 组件映射（每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`。安装命令 `pnpm dlx shadcn@latest add @coss/<name>`。导入 `~/components/ui/<name>` 的**已样式化导出**优先于 `*Primitive`。**本计划仅 PR6 新装 `toggle-group`，其余全部复用已装组件。** 每个引入新组件的 PR 须在 README「依赖与来源」追加清单并在 PR 描述披露。

| 界面元素 | coss 组件（安装名） | 关键 composition / 注意点 | 所属 PR |
| --- | --- | --- | --- |
| 阶段标题/状态/门控提示 | `badge` / `alert`（已装） | 状态「未生成/草稿/已确认」用 `Badge`；门控/需重新确认用 `Alert variant`（warning/info） | PR2/PR5 |
| 空态（未生成大纲/剧本） | `empty`（已装） | `Empty`>`EmptyHeader`(`EmptyMedia variant="icon"`)+`EmptyTitle`/`EmptyDescription`，内放生成按钮（剧本空态再并入镜头建议 `Switch`） | PR2/PR5 |
| 生成/重生成/确认 按钮 | `button`（已装） | `type="button"`+`loading`；长任务期间禁用。命令式调用（非 RR Form） | PR2/PR5 |
| 场景卡片（大纲/剧本） | `card`（已装） | 每场一个 `Card`：`CardHeader`(序号/标题/heading Badge/source_ref 标记/行操作)+`CardPanel`(字段或 beats) | PR2/PR5 |
| heading 枚举 Badge / 来源标记 | `badge`（已装） | `int_ext`(INT/EXT)、`time`(DAY/NIGHT/DAWN/DUSK)、`flag`(原文/AI 新增)、`source_ref` 文本标记各一个 `Badge`；ai_inferred 用警示色高亮 | PR2/PR5 |
| 字段折叠（次要字段/外化方案） | `collapsible`（已装） | `Collapsible`>`CollapsibleTrigger`+`CollapsiblePanel`；剧本 note 的 `options[]` 折叠只读展示 | PR2/PR5 |
| 行操作菜单（编辑/删除场景） | `menu`（已装） | `Menu`>`MenuTrigger render={<Button size="icon" variant="ghost"/>}`+`MenuItem`；删除项跳 `AlertDialog` | PR3 |
| 新增/编辑场景弹窗 | `dialog`（已装） | `Dialog`>`DialogPopup`>`DialogHeader`(form 外)+`DialogPanel`(表单滚动)+`DialogFooter`(确认/取消)。受控本地态，普通按钮提交 | PR3 |
| 场景标量字段（location/synopsis/goal...） | `field`+`input`/`textarea`（已装） | `Field`>`FieldLabel`+`Input type="text"`；synopsis 用 `Textarea`。`Input` 必显式 `type` | PR3 |
| heading 枚举单选（int_ext/time） | `select`（已装） | `Select items=[枚举]`>`SelectTrigger`>`SelectValue`+`SelectPopup`>`SelectItem`，items-first | PR3 |
| source_ref 章节选择 | `select`（已装） | items = 真实章节（value=order、label=标题） | PR3 |
| source_ref 段落多选 | `checkbox`（已装）或 `select`（multiple） | 仅渲染所选章节的真实段落 index；至少选 1；换章清空。**禁止自由输入任意段号**（防 422） | PR3 |
| 出场人物多选 / 关系变化人物 | `select`（已装，`multiple`） | items = characters 工件（value=id、label=name）；关系变化每行一个多选 | PR3 |
| 字符串数组（foreshadowing） | `input-group`+`badge`（已装，复用 `StringListEditor`） | 复用既有 [string-list-editor.tsx](../../frontend/app/components/string-list-editor.tsx)；`InputGroupAddon` 必在 `InputGroupInput` 之后 | PR3 |
| 场景调序 | `button`（已装） | 上/下移 `Button size="icon"`（首/末禁用）→ 调 `reorder` 传完整新顺序。无拖拽依赖 | PR3 |
| 删除场景 / 覆盖式重生成 二次确认 | `alert-dialog`（已装） | **破坏性操作用 AlertDialog**：footer `AlertDialogClose`（取消 ghost / 确认 destructive） | PR2/PR3/PR5 |
| 合并建议区块 | `card`/`alert`/`badge`/`button`（已装） | 每条建议展示两场标题+理由+status Badge+采纳/忽略按钮；顶部 `Alert info` 讲清「不自动合并」 | PR4 |
| 镜头建议开关 | `switch`（已装） | 「带描述」结构：左 `Label htmlFor`+说明、右 `Switch id`。值决定 `:generate` 的 `{shot_hints}` | PR5 |
| beat 类型/潜台词/留白 渲染 | `card`/`badge`/`separator`（已装） | action/dialogue/voice_over/off_screen/note/todo 分样式；潜台词次要文字；todo 用 warning Badge | PR5 |
| 加戏三态过滤 | `toggle-group`（**PR6 新装**） | `ToggleGroup`（单选）三项 all/from_source/ai_inferred；对已加载整稿本地过滤高亮 | PR6 |
| AI 新增内容清单 | `card`/`badge`/`scroll-area`（已装） | `getBeats("ai_inferred")` 驱动；`count`+逐条摘要，可作复查锚点 | PR6 |
| 长列表滚动 | `scroll-area`（已装） | 剧本节拍多时包裹 `CardPanel`/清单 | PR5/PR6 |
| 操作成功/失败反馈 | `toast`（已装） | `toastManager.add({title,description,type})`；root 已接 provider | PR2–6 |

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **门控只看工件 state，不看 `project.state`/`project.gates`。** 大纲能否生成 → `GET /characters` 的 `state==="confirmed"`；剧本能否生成 → `GET /outline` 的 `state==="confirmed"`。`project.gates` 是 http 层填的假默认值，不可用。
2. **`source_ref` 合法性是大纲编辑的头号坑（PR3）。** 新增/编辑场景必须产出 `source_ref={chapter, paragraphs}` 且 `paragraphs` 非空、全部命中该章真实段落 index。**表单用「章节 Select + 该章真实段落多选」强约束**，不让作者填任意段号。若仍收到 `422`，错误体在 `detail`（dict，`code:"invalid_source_ref"`）：http 层会把它 `JSON.stringify` 进 `ApiError.message`；UI 层捕获后判断（`error instanceof ApiError && error.message.includes("invalid_source_ref")`，或解析 `error.details`）→ 显示本地化「该场景的原文引用无效（章节/段落不存在）」，**不要把裸 JSON 弹给用户**。
3. **`extra="forbid"` 全量回传：** `OutlineScene`、`ScreenplayScene`、`Beat` 都禁止多字段。编辑大纲场景时以 loader 原始场景为基底浅拷贝改字段，**绝不**把信封字段（`version`/`state`/`updated_at`/`type`/`parent_version`/`etag`）混进 `data`；表单未暴露的字段（如某些 PR 阶段未做的 relation_changes）原样回传。
4. **所有大纲写操作让工件回 `draft`（add/update/delete/reorder），merge apply/dismiss 保持原 state，confirm 置 confirmed。** 确认后再编辑/调序需重新确认才解锁剧本生成。UI 据 `state` 如实提示。
5. **合并建议永不自动合并（P2 底线）：** `:apply`/`:dismiss` 只改 `status`，UI 文案必须讲清「采纳=标记决定，需手动合并」。`GET /merge-suggestions` 有保存副作用（推进 version），属正常。
6. **剧本只读、无 confirm、无编辑接口：** `script` 页只有生成/重新生成两个写动作；`PUT`/`:rewrite`/`/todos`/versions 是后端 NotImplementedError，**不要调用**。CTA 指向 `/editor`。
7. **`shot_hints` 是逐次生成参数**，不是项目持久设置；仅当用户开启时给 `:generate` 带 body `{shot_hints:true}`，生成后从 `data.shot_hints.enabled` 回显。
8. **`character` / `characters[]` / `relation_changes[].characters[]` 全是人物 id：** outline 页与 script 页 loader 都要拉 `characters` 工件做 id→name 映射与（编辑表单）候选项；映射不到回退显示 id。
9. **加戏过滤在前端本地做**（对已加载整稿），`getBeats` 仅驱动独立的「AI 新增清单」；二者数目应一致（可作为与后端 `flag` 标记一致性的自检）。
10. **冒号动作段按字面拼接**（`:generate`/`:confirm`/`/scenes:reorder`/`:apply`/`:dismiss`），不要 URL-encode 成 `%3A`。
11. **404 = 空态而非错误：** loader 里对 `outline.get`/`screenplay.get`/`getMergeSuggestions`/`getBeats` 的 404 一律 `catch→null`（沿用 M2/M3 `getOrNull`，判 `ApiError && status===404`）；其余错误继续抛。
12. **生成是同步长任务：** `:generate`/`:confirm` 期间按钮 `loading` 且禁用；失败 toast 展示 `ApiError.message`（含 409 门控可读文案）。本期不接 SSE/Job。
13. **i18n 两 locale 同步：** 每个新增键在 `zh-CN` 与 `en` 完全一致；插值占位一致。新增统一挂在 `outline.*` / `script.*` 命名空间，避免与既有 `analysis.*`/`import.*`/`pages.*` 冲突。
14. **coss 用法红线**（照 coss skill）：① 导入 `~/components/ui/<name>` 已样式化导出优先于 `*Primitive`；② Dialog/AlertDialog/Menu/Select/ToggleGroup 各按其文档层级，不跨组件混用 trigger/popup；③ `Input` 必显式 `type`，`Textarea` 直接放进 `Field`；④ `InputGroupAddon` 必在 `InputGroupInput` 之后；⑤ `Select` 用 items-first、`SelectValue` 放进 `SelectTrigger`；⑥ `Switch` 用于偏好开关、`ToggleGroup` 用于互斥分段过滤、`Checkbox` 用于多选项——不混用；⑦ 图标按钮补 `aria-label`，`Alert` 语义图标不要 `aria-hidden`；⑧ 破坏性确认（删除/覆盖式重生成）用 `AlertDialog`，普通新增/编辑用 `Dialog`；⑨ Toast 直接 `toastManager.add`。

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- **剧本编辑全链路未实现：** `PUT /screenplay`、`PUT /scenes/{id}`、`POST /scenes/{id}:rewrite`、`GET /todos`、`versions`/`:checkout`/`:diff` 均 `NotImplementedError`（属 M6）。本期 M5 只读。
- **`project.state` 仅从 `intent_set` 起正常推进：** 跳过保存意图直接生成大纲，大纲可生成但 state 不推进到 `outlined`，外层幕不点亮（M2/M3 已记录的 state 缺口延续）。建议作者先完成意图阶段。
- **`gates` 字段后端不返回**，http 层填假默认值，不可用于判断阶段状态。
- **`etag` 恒 null、不校验 `If-Match`**（乐观锁未实现），不发 `If-Match`。
- **`GET /merge-suggestions` 有保存副作用**（重算并保存，推进 version），属设计如此。
- **`source:resolve` 本期不接**（决策 3）：原文实际拉取/对照统一留给 M6 双栏编辑器；本期仅展示 `source_ref` 文本标记。

> 这些只标注、不改后端。若后端后续补齐编辑接口、state 推进或乐观锁，前端可据此在 M6 扩展编辑能力。

---

## 验证方式（端到端）

1. **起后端：** `backend/` 按其工具启动 dev 服务（[dev_server.py](../../backend/scripts/dev_server.py)，`:8000`）。
2. **起前端：** 仓库根 `pnpm install`（PR1–5 无新 npm 依赖；PR6 装 coss `toggle-group` 也不应带新 npm 依赖）→ `pnpm dev`（默认 http，经 Vite 代理打 `:8000`）。
3. **冒烟（按 PR 累积，需先把某项目跑到「人物档案已确认 + 意图已保存」）：**
   - PR1：`typecheck`/`build` 过；mock 控制台手调 outline/screenplay 各方法，形状/门控正确。
   - PR2：人物确认后进 `/outline` → 生成 → 卡片展示（字段非空、source_ref 标记、人物姓名）→ 确认 → 「进入剧本生成」可点；人物未确认显示门控。
   - PR3：新增/编辑/删除场景（章节+段落强约束产出合法 source_ref）、上下调序均持久；写操作后回草稿需重新确认；非法 source_ref 得友好提示。
   - PR4：合并建议显示 pending 条目 → 采纳/忽略仅改状态、场景不变、提示不自动合并。
   - PR5：大纲确认后进 `/script` → 开/关镜头建议 → 生成 → 按场卡片 + 节拍（对白显姓名、来源 flag、潜台词、note 外化方案、todo 留白）；重新生成走二次确认；「进入打磨工作台」可点；大纲未确认显示门控。
   - PR6：三态过滤高亮正确、AI 新增清单与高亮数目一致。
   - 离线：任一 PR 后 `VITE_API_MODE=mock pnpm dev` 仍可走完大纲→剧本流程（mock 复刻门控/加戏/留白）。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。PR6 装完 `toggle-group` 后 `git diff package.json` 核对无新增 npm 依赖，并人工点检 Dialog/AlertDialog/Menu/Select/ToggleGroup 的键盘与焦点返回。
5. **窗口与规范：** 提交时间落在 2026-06-05 ~ 2026-06-07（北京时间）；分支名/commit 经 hooks 校验（subject 纯 ASCII）；每 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式并勾选合规项。

---

## AGENTS.md 合规要点

- **单一边界：** PR1 客户端、PR2 大纲查看、PR3 大纲编辑、PR4 合并建议、PR5 剧本生成查看、PR6 加戏筛选——每个 PR 一个清晰边界，互不混入无关重构/样式。
- **README 更新（依赖与来源 / 原创边界）：**
  - **仅 PR6** 在 [README.md](../../README.md) §依赖与来源的 coss 组件清单里**追加 `toggle-group`**，并在「原创边界」段说明剧本阶段的生成/只读查看/加戏筛选/信任标记展示逻辑为本项目业务实现，coss 组件为 registry 生成的第三方基座。
  - **PR1–PR5 不新增依赖、不改运行流程，README 无需更新**（在 PR「来源与依赖」段写「无新增第三方依赖；复用既有 API 客户端模式与已装 coss 组件」）。
- **PR 描述据实披露：** 复用既有 API 客户端模式与 coss 基座；PR6 新增 coss 组件标明为第三方生成资产；后端缺口（剧本编辑未实现、state 推进缺口、gates 不可用、合并不自动、source:resolve 本期不接等）如实说明，不得把后端能力写成前端原创。
- main 每次合并后可 `pnpm build` 通过、可启动。
- 提交在开发窗口内（2026-06-05~06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。
