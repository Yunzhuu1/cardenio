# 前端接入后端 M6 接口 — 打磨工作台实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 **M6（打磨工作台：剧本整稿/单场编辑、单场局部重生成、留白清单、单场溯源 trace、按来源过滤节拍、source:resolve 溯源解析）** 接口。本计划把这些接到前端：把当前为 `StagePlaceholder` 的 **`editor`（打磨工作台）** 顶层阶段页升级为可用界面。**全程只改 `frontend/`，不改 `backend/`。**
>
> 本计划延续 [`frontend-m4-m5-backend-integration.md`](./frontend-m4-m5-backend-integration.md) 与 [`frontend-m2-m3-backend-integration.md`](./frontend-m2-m3-backend-integration.md) 的全部约定（默认 `http` 模式、http/mock 双实现经 `VITE_API_MODE` 切换、coss 组件经 shadcn `@coss` registry 安装、统一 envelope 信封、门控只看工件 state、`extra="forbid"` 全量回传、冒号动作段按字面拼接、不发 `If-Match`、两 locale 键同步、Conventional Commits + 纯 ASCII subject、PR 模板五段式）。执行前请通读 M4/M5 计划的「总体方案与不变量」「跨 PR 关键实现细则」「coss 用法红线」，本计划只补充 M6 的差异点。

---

## Context（为什么做、目标、已确认决策）

- 产品主流程在「导入（M0/M1）→ 理解/档案/意图（M2/M3）→ 大纲（M4）→ 剧本初稿（M5）」之后，进入 **M6 打磨工作台**。M5 的 `script` 阶段页（[project-script.tsx](../../frontend/app/routes/project-script.tsx)）已经做了**剧本生成 + 结构化只读查看 + 加戏三态过滤 + AI 新增清单 + 镜头建议开关**，**本计划不动 `script` 页的产品职责**（它仍是「生成 + 只读查看器」）。
- M6 的产品职责落在另一个独立阶段页 **`editor`（打磨工作台，[project-editor.tsx](../../frontend/app/routes/project-editor.tsx) 目前是占位）**。本计划把 `editor` 升级为「打磨工作台」，承载 PRD/路线图里的四项 M6 必做能力：
  - **FR-9.1 双栏对照**：左原文、右剧本，滚动联动 + 互相高亮。
  - **FR-9.2 局部重生成**：选中单场，用自然语言指令只重写该场，不动其他场。
  - **FR-9.5 所见即所得 + 源码双视图**：默认结构化剧本视图（可行内编辑节拍），可切「源码（YAML）」视图手改整稿。
  - **FR-9.6 留白标记**：`todo` 节拍可定位、可筛选。
- 目标产出：作者在剧本初稿生成后，进入 `editor` 阶段——
  1. 看到 **整稿双栏对照**（左：整本原文逐段；右：整稿剧本逐场逐节拍），两栏滚动联动，点剧本场景/节拍能高亮并定位到对应原文段落，反之亦然。
  2. 对**单场**发起 **自然语言局部重生成**（如「这场太平淡，把冲突往前提」），只重写该场，新增内容带 `ai_inferred` 高亮。
  3. **行内直接编辑节拍**（动作/对白/旁白/注释正文、说话人、潜台词、来源 flag；增/删/调序节拍；改场景 heading 与 mood），保存即写回后端。
  4. 切到 **源码（YAML）视图** 手改整稿并应用。
  5. 看到 **留白（TODO）清单**，逐条定位到对应节拍；并能在双栏里只高亮 `todo`。

  全部数据来自真实后端。

- **本次已与用户确认的四项决策（写死，执行 Agent 不得擅自变更）：**
  1. **源码视图格式 = YAML。** 引入一个新的 npm 依赖 **`yaml`**（eemeli/yaml，纯 JS、自带 TS 类型、无原生依赖）做前端序列化/反序列化。后端 `PUT /screenplay` 只收 **JSON**（`GET` 也只支持 `format=json`），所以 YAML 仅用于**前端展示与手改**：展示时 `yaml.stringify(screenplay.data)`，应用时 `yaml.parse(text)` → 转回 JSON 对象 → 调 `PUT /screenplay`。**新增依赖必须按 AGENTS.md 在 README 与 PR 描述披露**（见 PR6）。
  2. **所见即所得编辑粒度 = 节拍行内直接编辑。** 在双栏右侧剧本视图里，点某个节拍即可就地编辑其正文/字段，保存调 `PUT /screenplay/scenes/{id}`（整场全量回传）。
  3. **双栏布局 = 整稿双栏。** 左侧用 `api.source.get` 渲染整本原文（逐章逐段），右侧渲染整稿剧本（逐场逐节拍），全局滚动联动；点击定位用本地 `source_ref` 映射（即时、无抖动），并用 `GET /screenplay/scenes/{id}/trace` 作为「定位原文」按钮的权威数据源（见决策细则）。
  4. **本批范围 = 四项全做（双栏对照 + 局部重生成 + 所见即所得/源码 + 留白），排除「版本与分支」（FR-9.3）。** 后端的 `versions` / `:checkout` / `:diff`（API-22）仍是 `NotImplementedError`，**本期不接**，在相关 PR 描述里如实标注后端缺口。

---

## 后端现状核对（执行前必读，以代码实际行为为准）

> 已逐文件、逐测试核对：[screenplay.py](../../backend/src/cardenio/api/routes/screenplay.py)、[source.py](../../backend/src/cardenio/api/routes/source.py)、[domain/models/screenplay.py](../../backend/src/cardenio/domain/models/screenplay.py)、[domain/models/base.py](../../backend/src/cardenio/domain/models/base.py)、[tests/api/test_screenplay.py](../../backend/tests/api/test_screenplay.py)、[tests/api/test_source.py](../../backend/tests/api/test_source.py)。

### 通用：仍是统一信封（envelope）

剧本工件读写接口返回与 M2–M5 完全相同的 `ArtifactEnvelope`（`type`/`state`/`version`（`v_<hex8>`）/`parent_version`/`etag`（恒 null）/`updated_at`/`needs_recompute`/`data`）。沿用既有处理：`version` 当不透明串、不解析；不发 `If-Match`；门控只看 `state`。前端已有的 `ArtifactEnvelope<T>`/`ArtifactState`/`SourceRef`/`Flag`/`ScreenplayData`/`ScreenplayScene`/`Beat`/`BeatOption`/`ShotHints` 类型直接复用（M5 PR1 已建）。

### M6 新增/已实现的剧本接口（[screenplay.py](../../backend/src/cardenio/api/routes/screenplay.py)，前缀 `/projects/{project_id}/screenplay`）

> 下表只列 **M6 新接的接口**。M5 已接的 `:generate` / `GET ` / `GET /scenes/{id}` / `GET /beats?flag=` 不再赘述（前端 [client.ts](../../frontend/app/lib/api/client.ts) 已有 `screenplay.get/generate/getScene/getBeats`）。

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| **整稿改写** | `PUT ` (前缀根) | `ScreenplayData` **全量**（`{scenes, shot_hints}`） | `200` 信封（`state:"draft"`，`parent_version=` 旧 version，新 version）。尚未生成剧本 → `404 {"detail":"Screenplay not found"}`。非 todo 节拍缺 `source_ref`/`flag` → `422`（见坑 1）。**副作用：把项目 state 置为 `editing`**（坑 4） |
| **单场改写** | `PUT /scenes/{scene_id}` | `ScreenplayScene` **全量** | `200` 信封（整稿，仅替换该场）。`body.id != scene_id` → `422 {"detail":"Scene id in request body must match path scene_id"}`。场景不存在 → `404 {"detail":"Scene not found"}`。trust 字段缺失 → `422`（坑 1）。**副作用：state→`editing`** |
| **单场局部重生成** | `POST /scenes/{scene_id}:rewrite` | `{ "instruction": "把冲突往前提" }`（去空白后非空） | `202` 信封（整稿，仅替换该场；新增节拍多带 `ai_inferred`）。`instruction` 空白 → `422`。场景/剧本不存在 → `404`。**副作用：state→`editing`** |
| **留白清单** | `GET /todos` | — | `200` `{ "items":[{ "scene_id", "beat_index", "source_ref": SourceRef\|null, "beat": Beat }], "count": N }`。无 todo 节拍时 `{items:[],count:0}`。剧本/项目不存在 → `404` |
| **单场溯源 trace** | `GET /scenes/{scene_id}/trace` | — | `200` `{ "scene_id", "source_ref": SourceRef, "paragraphs":[{ "index":int, "text":str }], "beats":[{ "beat_index":int, "source_ref":SourceRef\|null, "flag":str\|null, "type":str }] }`。该场 `source_ref` 段落无法在原文全部命中 → `404 {"detail":{"code":"source_ref_not_found",...}}`。场景/剧本/项目不存在 → `404` |
| **按来源过滤节拍** | `GET /beats?source_chapter=&source_paragraph=` | 查询参（可叠加 `flag`） | `200` `{ "items":[{ "scene_id","beat_index","beat" }], "count" }`。`source_chapter` 与 `source_paragraph` **必须成对出现**，只给一个 → `422`。非法 `flag` → `422` |

### M6 溯源解析接口（[source.py](../../backend/src/cardenio/api/routes/source.py)，前缀 `/projects/{project_id}/source`）

| 用途 | 方法 路径 | 查询参 | 返回 / 状态码 |
| --- | --- | --- | --- |
| **解析 source_ref → 原文** | `GET :resolve` | `chapter`（int ≥1，必填）、`paragraphs`（字符串选择器，如 `1-3` 或 `1,3`，必填非空） | `200` `{ "chapter":int, "paragraphs":[{ "index":int, "text":str }] }`。任一段落无法在该章命中 → `404 {"detail":"Source reference not found"}`。选择器非法 → `422`。项目不存在 → `404` |

### 仍是 `NotImplementedError`（本期不接，FR-9.3 版本分支，API-22）

| 用途 | 方法 路径 | 状态 |
| --- | --- | --- |
| 列版本历史 | `GET /scenes/{id}/versions` | **NotImplementedError** |
| 建分支版本 | `POST /scenes/{id}/versions` | **NotImplementedError** |
| 切换/回滚版本 | `POST /scenes/{id}:checkout` | **NotImplementedError** |
| 版本对比 | `GET /scenes/{id}/versions:diff` | **NotImplementedError** |

### 数据形状回顾（前端类型已具备，无需新增 `ScreenplayData` 相关类型）

`ScreenplayScene`：`{ id, heading:{int_ext,location,time}, source_ref:{chapter,paragraphs[]}, synopsis?, goal?, conflict?, mood?, characters[], foreshadowing[], relation_changes[], ending_state?, beats: Beat[] }`（`extra="forbid"`）。

`Beat`（`extra="forbid"`）：`{ type: "action"|"dialogue"|"voice_over"|"off_screen"|"note"|"todo", text?, character?(人物id), parenthetical?, dialogue?, subtext?, source_ref?, flag?("from_source"|"ai_inferred"), options?: {kind,text}[] }`。

`ScreenplayData`：`{ scenes: ScreenplayScene[], shot_hints:{enabled:boolean} }`。

**M6 必须知道的真实行为与坑（执行 Agent 必照）：**

1. **编辑类写入会强制 trust 不变量（`_validate_edit_trust_fields`）。** `PUT /screenplay`、`PUT /scenes/{id}`、`:rewrite` 都会校验：**每个非 `todo` 节拍必须同时带 `source_ref` 与 `flag`**，否则 `422`，错误体走 FastAPI 的 `detail`（**dict，不是 `{error:{...}}` 信封**）：`{"detail":{"code":"missing_trust_fields","message":"...","items":[{"scene_id","beat_index","fields":["source_ref"]}]}}`。**结论：行内编辑/源码改写时绝不能让非 todo 节拍丢掉 `source_ref` 或 `flag`**；`todo` 节拍可不带。`http` 层会把该 `detail`（非字符串时 `JSON.stringify`）塞进 `ApiError.message`，UI 层需把它翻成友好文案（见「关键实现细则」）。
2. **`:rewrite` 是同步 202**（无 Job/SSE），返回整稿信封，**只替换目标场**，其余场与其内容/相对顺序不变（测试 `test_rewrite_scene_only_replaces_target_scene` 断言 `scenes[1:]` 不变）。后端会对重写场做 trust 回填：缺 `source_ref` 的非 todo 节拍回填为该场 `source_ref`、缺 `flag` 的标 `ai_inferred`、对白补 `source_ref`、潜台词/`mood` 补全（测试 `test_rewrite_scene_backfills_missing_trust_fields`）。**前端拿到的重写场每个节拍基本都带 `flag` 与 `source_ref`，可直接渲染信任标记。**
3. **`PUT /scenes/{id}` 与 `:rewrite` 都返回整稿信封**（含全部 scenes + `shot_hints`），不是单个场景。每次写后用返回信封的 `data` 整体刷新即可。
4. **所有 M6 写操作把项目 state 置为 `editing`（`_mark_project_editing`）。** 即剧本生成后项目处于 `generated`，**任何一次编辑/重生成都会把 `project.state` 推进到 `editing`**（测试 `test_update_full_screenplay...` / `test_rewrite_scene...` 断言 `state=="editing"`）。这会让外层「幕步骤条」的 `editor` 幕点亮（`isStageDone("editor")` 看 `state>=editing`，见 [stages.ts](../../frontend/app/lib/stages.ts)），**无需改 stages.ts**。
5. **剧本工件没有 `:confirm`、没有 `needs_recompute` 流程参与门控。** `editor` 页**不需要确认按钮**；下游报告（M7）关卡只要求 screenplay `state=="draft"`，编辑后仍是 `draft`（state 只在 envelope 维度是 `draft`，项目维度变 `editing`），不影响 M7。
6. **`/todos` 的 `source_ref` 在 item 顶层**（与 `beat.source_ref` 同值，可能为 `null`），渲染清单时优先用 item 顶层 `source_ref`。
7. **`trace` 的 `paragraphs` 是「按 source_ref 顺序解析出的原文段落正文」**，可直接作为「该场对应原文」展示；其 `beats` 是轻量溯源（只含 `beat_index`/`source_ref`/`flag`/`type`，**不含正文**），用于校验/定位，不用于渲染正文。
8. **`:resolve` 与 `trace` 的「全命中才返回」语义：** 只要请求的段落里有一个在该章不存在，整体 `404`（后端 `_resolve_source_ref` 要求 `len(resolved)==len(requested)`）。前端把这种 404 当「该引用无法定位」友好提示，不作为崩溃。
9. **`character` / `characters[]` / `relation_changes[].characters[]` 全是人物 id（非姓名）。** 渲染对白/出场人物、行内编辑「说话人」候选项都要用 `characters` 工件做 id→name 映射；映射不到回退显示 id。
10. **`note` 节拍的 `options[]`（心理外化多方案）本期只读展示**，行内编辑**不提供** options 的增删改（后端无对应字段级接口，整场全量回传时原样保留即可）。

### 跨层：`project.state` 推进与门控策略

- 沿用 M4/M5 结论：`outline:generate` 在 `state==intent_set` 时推进 `outlined`；`screenplay:generate` 在 `state==outlined` 时推进 `generated`。**M6 新增：任何剧本编辑/重生成把 `state` 推进 `editing`。**
- **门控策略（写死）：**
  - **`editor` 页能否打磨，一律看 `screenplay` 工件是否存在（`GET /screenplay` 非 404），不看 `project.state`/`gates`。** 剧本未生成 → 空态 + 引导回 `script` 阶段生成。
  - 外层「幕步骤条」继续读 `project.state`：`editor` 幕在 `state>=editing` 点亮。由于编辑会推进 state，幕导航会正确点亮，**无需改 stages.ts**。
  - **`gates` 字段后端不返回**，http 层填假默认值，不可用于判断（沿用既有结论）。

---

## 总体方案与不变量

- **资源契约层沿用既有模式：** 在 [client.ts](../../frontend/app/lib/api/client.ts) 现有 `ScreenplayApi` 上**扩展 M6 方法**，并给 `SourceApi` 增 `resolve`；http 与 mock 双实现，经 `VITE_API_MODE` 切换；组件零分支消费同一接口。
- **唯一新增 npm 依赖：** **`yaml`**（仅 PR6 用于源码视图）。除此之外业务逻辑用原生 `fetch` + React Router v7 内置 `clientLoader`/`useRevalidator`（仓库 `ssr:false`，用 client 版）。**M6 不新装任何 coss 组件**——双栏、行内编辑、源码 Tab、留白清单所需的 `card`/`badge`/`button`/`separator`/`switch`/`scroll-area`/`tabs`/`alert`/`alert-dialog`/`empty`/`dialog`/`menu`/`field`/`input`/`textarea`/`select`/`toggle-group`/`toast`/`collapsible` **全部已装**（见 [app/components/ui/](../../frontend/app/components/ui/)）。
- **路由无需改造：** `editor` 已是 [routes.ts](../../frontend/app/routes.ts) 顶层阶段路由，对应 [project-editor.tsx](../../frontend/app/routes/project-editor.tsx) 占位文件。本计划**直接把该占位替换为可用页**，不新增/嵌套路由、不动 routes.ts、不动 project-layout/stages.ts。
- **复用 M5 只读渲染：** M5 的 `script` 页已写了一套成熟的「节拍/对白/注释/留白只读渲染 + 来源/flag 徽标 + source_ref 文本标记」逻辑（[project-script.tsx](../../frontend/app/routes/project-script.tsx)）。**PR2 先把这套只读渲染抽成共享组件**（行为保持），供 `editor` 双栏右侧复用，避免重复实现与漂移。
- **信任能力对齐：** M6 在编辑层继续兑现 P4/P5/P6——`source_ref`（双栏定位、trace）、`flag`（编辑/重生成后高亮 `ai_inferred`）、`todo`（留白清单与高亮）；编辑写入时**强制不丢 trust 字段**（坑 1）。
- **main 始终可运行：** 每个 PR 自身 `pnpm typecheck`/`build`/`lint`/`format:check` 通过；功能需后端在跑才能手测（mock 模式可离线走流程）。

---

## PR 拆分（7 个 PR，依次从 `main` 切分支）

> 分支名正则：`<type>/<小写-数字-连字符-点>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore/refactor。
> commit 正则：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**。
> pre-commit 跑 lint、pre-push 跑 build + 分支名校验。每个 PR 合并后 main 可运行，用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。
>
> **依赖顺序：** PR1（客户端）→ PR2（共享只读组件重构）→ PR3（双栏对照壳）→ PR4（局部重生成）/ PR5（行内编辑）/ PR6（YAML 源码）/ PR7（留白）。PR4–PR7 都依赖 PR3（编辑器壳与双栏渲染），且 PR5 复用 PR2 的共享组件。每个 PR 可独立 build/verify。提交时间须落在 2026-06-05 ~ 2026-06-07（北京时间）。

---

### PR 1 — 扩展 screenplay 编辑/溯源 + source 解析的 API 客户端（数据层，无 UI）

- **分支：** `feat/screenplay-editing-api-client`
- **一句话目标：** 按后端真实行为给 `ScreenplayApi` 增加 M6 编辑/溯源/留白方法，给 `SourceApi` 增 `resolve`（types + client 接口 + http 实现 + mock 实现），不接任何 UI。
- **改动文件：**
  - [types.ts](../../frontend/app/lib/api/types.ts)：新增类型（字段严格对齐上文「数据形状」，复用既有 `SourceRef`/`Flag`/`Beat`/`ScreenplayData`/`ScreenplayScene`）：
    - 溯源：`ResolvedParagraph { index:number; text:string }`；`ResolveResponse { chapter:number; paragraphs:ResolvedParagraph[] }`。
    - trace：`TraceBeat { beat_index:number; source_ref:SourceRef|null; flag:Flag|null; type:string }`；`SceneTrace { scene_id:string; source_ref:SourceRef; paragraphs:ResolvedParagraph[]; beats:TraceBeat[] }`。
    - 留白：`TodoItem { scene_id:string; beat_index:number; source_ref:SourceRef|null; beat:Beat }`；`TodosResponse { items:TodoItem[]; count:number }`。
    - 按来源过滤：复用既有 `BeatsFilterResponse`（M5 已建）。
  - [client.ts](../../frontend/app/lib/api/client.ts)：
    - `ScreenplayApi` 增方法（http/mock 两实现都补齐）：
      - `updateScreenplay(projectId, data:ScreenplayData): Promise<ArtifactEnvelope<ScreenplayData>>`
      - `updateScene(projectId, sceneId:string, scene:ScreenplayScene): Promise<ArtifactEnvelope<ScreenplayData>>`
      - `rewriteScene(projectId, sceneId:string, instruction:string): Promise<ArtifactEnvelope<ScreenplayData>>`
      - `getTodos(projectId): Promise<TodosResponse>`
      - `getTrace(projectId, sceneId:string): Promise<SceneTrace>`
      - **扩展 `getBeats`**：保持既有签名 `getBeats(projectId, flag?:Flag)` 向后兼容（M5 已有两处调用 `getBeats(projectId,"ai_inferred")`，**不要改这两处调用**），追加可选第三参 `source?:{ chapter:number; paragraph:number }`，即新签名 `getBeats(projectId, flag?:Flag, source?:{chapter:number;paragraph:number}): Promise<BeatsFilterResponse>`。
    - `SourceApi` 增方法：`resolve(projectId, chapter:number, paragraphs:string): Promise<ResolveResponse>`。
  - [http.ts](../../frontend/app/lib/api/http.ts)：实现上述方法，路径按前缀拼接，**冒号动作段（`:rewrite`、`source:resolve`）按字面拼接，勿 URL-encode 冒号**。要点：
    - `updateScreenplay` = `PUT .../screenplay`，body 为 `ScreenplayData` 全量。
    - `updateScene` = `PUT .../screenplay/scenes/{sceneId}`，body 为 `ScreenplayScene` 全量。
    - `rewriteScene` = `POST .../screenplay/scenes/{sceneId}:rewrite`，body `{ instruction }`。
    - `getTodos` = `GET .../screenplay/todos`（返回 `{items,count}`，**不是信封**，原样返回）。
    - `getTrace` = `GET .../screenplay/scenes/{sceneId}/trace`（**注意是 `/trace` 斜杠子路径，不是冒号**）。
    - `getBeats` 扩展：当传了 `source` 时，在查询串里加 `source_chapter`/`source_paragraph`（两者一起加）；`flag` 仍按既有逻辑加。
    - `source.resolve` = `GET .../source:resolve?chapter={chapter}&paragraphs={paragraphs}`（`source:resolve` 冒号字面拼接；`paragraphs` 直接传形如 `"1-3"` 或 `"1,3"` 的字符串）。
    - **错误体差异**：`missing_trust_fields`（编辑 422）与 `source_ref_not_found`/`invalid` 都走 `detail`（dict/str），既有 `request()` 已把 `detail`（非字符串时 `JSON.stringify`）塞进 `ApiError.message`；本 PR 不必特殊处理，留给 PR5/PR6 在 UI 层翻友好文案（见「关键实现细则」）。
  - [mock.ts](../../frontend/app/lib/api/mock.ts)：给 `screenplay`/`source` mock 加 M6 实现，复刻**关键语义**供离线 UI 开发：
    - 新增内部工具 `setProjectEditing(projectId)`：把项目 state 在 `generated`/`editing` 时置为 `"editing"`（其余 state 不动），更新 `updated_at`。
    - 新增 `saveScreenplay(projectId, data, parentVersion)`：`makeEnvelope("screenplay","draft",data,parentVersion)` 存入 `screenplayStore` 并返回。
    - `updateScreenplay(projectId, data)`：要求 `screenplayStore` 已有（否则 `notFound("Screenplay not found")`）；**最小化复刻 trust 校验**：若存在非 `todo` 节拍缺 `source_ref` 或 `flag`，抛 `ApiError(422,{code:"missing_trust_fields",details:{items:[{scene_id,beat_index,fields}]}})`（便于 UI 联调错误态）；否则 `saveScreenplay`（parent=旧 version）+ `setProjectEditing`。
    - `updateScene(projectId, sceneId, scene)`：要求剧本存在；`scene.id!==sceneId` → `ApiError(422,...)`；找不到场景 → `notFound("Scene not found")`；同上 trust 校验；替换该场后 `saveScreenplay`+`setProjectEditing`，返回整稿信封。
    - `rewriteScene(projectId, sceneId, instruction)`：要求剧本存在；`instruction.trim()` 空 → `ApiError(422,...)`；找不到场景 → 404；**复刻后端 fallback**：取该场，在其 `beats` 末尾追加一个 `note` 节拍 `{ type:"note", text:"重生成指令：{instruction}"（en: "Rewrite instruction: ..."）, character:null, parenthetical:null, dialogue:null, subtext:"这是改编层新增的表达方案。", source_ref: 该场 source_ref, flag:"ai_inferred", options:null }`，替换该场后 `saveScreenplay`+`setProjectEditing`，返回整稿信封。
    - `getTodos(projectId)`：剧本不存在 → 404；遍历全部 `scenes.beats`，挑 `type==="todo"`，返回 `{ items:[{ scene_id, beat_index, source_ref: beat.source_ref ?? null, beat }], count }`。
    - `getTrace(projectId, sceneId)`：剧本不存在/场景不存在 → 404；按该场 `source_ref` 去 `sourceStore` 的对应章（`ch_{chapter}`）逐 index 取段落正文，**任一缺失 → 404**；返回 `{ scene_id, source_ref, paragraphs:[{index,text}], beats: 该场 beats.map((b,i)=>({beat_index:i, source_ref:b.source_ref??null, flag:b.flag??null, type:b.type})) }`。
    - `getBeats` 扩展：在既有 flag 过滤基础上，若传 `source`，再按 `beat.source_ref?.chapter===source.chapter && beat.source_ref.paragraphs.includes(source.paragraph)` 过滤。
    - `source.resolve(projectId, chapter, paragraphs)`：解析选择器（支持 `a-b` 与 `a,b` 混合，去重保序，非法/空抛 `ApiError(422,...)`）→ 去 `sourceStore` 该章逐 index 取正文，**任一缺失 → 404 `notFound("Source reference not found")`**；返回 `{ chapter, paragraphs:[{index,text}] }`。
    - **mock 离线提示（写进 PR 描述，不写进代码）：** seed 里没有现成 screenplay 工件；离线测 `editor` 需先在 mock 模式把某项目跑到「人物确认→意图保存→大纲生成→大纲确认→剧本生成」，再进 `/editor`。
- **不在本 PR：** 任何路由/页面/组件改动。
- **建议 commits：**
  1. `feat(frontend): add screenplay trace todos and source resolve api types`（types.ts）
  2. `feat(frontend): add screenplay editing and source resolve to api client and http`（client.ts + http.ts）
  3. `feat(frontend): add screenplay editing and trace mock adapters`（mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint`/`format:check` 全过；app 行为与本 PR 前一致（`script` 页 `getBeats` 两处调用不受影响）。mock 模式控制台手调 `api.screenplay.rewriteScene(...)`、`api.screenplay.updateScene(...)`、`api.screenplay.getTodos(...)`、`api.screenplay.getTrace(...,"sc_001")`、`api.source.resolve(...,1,"1-2")` 形状/门控/state→editing 正确。

---

### PR 2 — 重构：抽出剧本只读展示共享组件（行为保持，供 editor 复用）

- **分支：** `refactor/screenplay-shared-components`
- **一句话目标：** 把 M5 `script` 页里「节拍/对白/注释/留白只读渲染 + 来源/flag 徽标 + source_ref 文本标记 + id→name/段落区间工具」抽到共享模块，`script` 页改为消费共享组件（**纯行为保持的重构，UI 与交互零变化**），为 `editor` 双栏右侧复用打底。
- **为什么单独成 PR：** AGENTS.md「不混入无关重构」指的是与目标无关的重构；本重构**直接服务于 M6 编辑器复用**，但为保持每个 PR 单一边界、main 持续可运行，将其作为独立的 `refactor` PR 交付，且严格保证行为不变（不改文案、不改类名语义、不改交互）。
- **改动文件（新增 + 修改）：**
  - 新增 [app/lib/screenplay-format.ts](../../frontend/app/lib/screenplay-format.ts)（纯函数工具，从 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 原样搬迁，签名不变）：`paragraphLabel(paragraphs)`、`sourceRefLabel(t, sourceRef)`、`flagVariant(flag)`、`beatToneClass(beat)`、`optionKindKey(kind)`、`sceneTitle(scene)`、`beatSummary(beat)`、`characterName(map,id)`、`charactersLabel(characters,map,sep)`。
  - 新增 [app/components/screenplay-beat-view.tsx](../../frontend/app/components/screenplay-beat-view.tsx)：只读展示组件——
    - `BeatBadges`（序号 + 类型 Badge + todo Badge + flag Badge + source_ref Badge，来自 M5 `BeatBlock` 头部那段）。
    - `DialogueBeatBody`（说话人 + V.O./O.S. 后缀 + parenthetical + dialogue 正文，来自 M5 `DialogueBeat`）。
    - `NoteBeatBody`（注释正文 + `options[]` 折叠只读，来自 M5 `NoteBeat`）。
    - `BeatBody`（按 type 分派到 dialogue/note/其它正文 + 潜台词行，**不含 filter 高亮逻辑**——filter 高亮是 M5 page 专属，留在 page 层）。
  - 新增 [app/components/screenplay-scene-view.tsx](../../frontend/app/components/screenplay-scene-view.tsx)：只读展示——`SceneHeader`（场景序号 + INT/EXT·location·time 徽标 + source_ref/mood/cast）、`SceneSummary`（synopsis/goal/conflict/ending_state 栅格，来自 M5 `SceneSummary`）。
  - 修改 [project-script.tsx](../../frontend/app/routes/project-script.tsx)：删除被搬走的本地函数/组件，改为从上述模块 import；M5 专属的「filter 高亮 ring/opacity」「`matchingBeatCount`/`noSceneMatches`」逻辑保留在 page 层，包在共享 `BeatBody`/`BeatBadges` 外层。**最终 `script` 页渲染与交互必须与重构前逐像素一致。**
  - i18n：**无新增键**（共享组件继续读现有 `script.*` 键；本 PR 不动 locale）。
- **建议 commits：**
  1. `refactor(frontend): extract screenplay format helpers`（screenplay-format.ts + script 页改用）
  2. `refactor(frontend): extract read only screenplay scene and beat views`（两个 view 组件 + script 页改用）
- **验收：** `script` 页所有既有行为不变（生成/只读卡片/三态过滤高亮/AI 新增清单/镜头开关/重生成）；`build`/`typecheck`/`lint`/`format:check` 过；`git diff` 仅为搬迁与 import 调整，无逻辑/文案变化。

---

### PR 3 — 打磨工作台壳 + 整稿双栏对照（FR-9.1）

- **分支：** `feat/editor-dual-pane`
- **一句话目标：** 把 [project-editor.tsx](../../frontend/app/routes/project-editor.tsx) 从占位升级为「打磨工作台」：门控 + 整稿双栏（左整本原文、右整稿剧本只读）、滚动联动（可开关）、点击互相高亮 + 定位。**不含编辑/重生成/源码/留白**（留 PR4–PR7）。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`button`/`separator`/`switch`/`scroll-area`/`alert`/`empty`/`toast`，均已装；复用 PR2 的 `screenplay-scene-view`/`screenplay-beat-view`/`screenplay-format`）。
- **改动文件：**
  - [project-editor.tsx](../../frontend/app/routes/project-editor.tsx)：
    - `clientLoader`：并行 `getOrNull(api.screenplay.get)` + `api.source.get` + `getOrNull(api.characters.get)`（id→name 映射）。复用 M5 同款 `getOrNull`（404→null）小工具（可从 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 复制，或抽到共享 util；优先与 script 子页同款写法）。返回 `{ screenplay, source, characters, projectId }`。
    - **门控空态**：`screenplay` 为 null（未生成）→ `Empty` + 说明「请先在剧本阶段生成初稿」+ `Button render={<Link to={stagePath(id,"script")}/>}`「去生成剧本」，不展示双栏。
    - **有剧本**：顶部页眉用既有 `pages.editor.*`（milestone/title/description）+ 一个 `Badge` 显示项目级状态（`editing`/`generated`）+ 一行图例（复用 [trust-chips.tsx](../../frontend/app/components/trust-chips.tsx) 的 `TrustChips`，标识 原文/AI 新增/TODO 三色）+ 一个 `Switch`「滚动联动」（默认开）。
    - **双栏容器**：`grid md:grid-cols-2 gap-4`，每栏一个固定高度的 `ScrollArea`（如 `className="h-[calc(100vh-16rem)]"`，两栏等高），各自 `ref` 拿到滚动视口节点。窄屏（`<md`）退化为上下两栏（仍各自可滚）。
      - **左栏（原文）**：遍历 `source.chapters`（按 order）→ 每章标题 + 逐段落；**每段落外层 `div` 加 DOM id `src-{chapter.order}-{paragraph.index}`**，正文 `whitespace-pre-wrap`。段落点击可选中（见高亮）。
      - **右栏（剧本）**：遍历 `screenplay.data.scenes` → 每场用 PR2 的 `SceneHeader` + `SceneSummary` + 逐节拍用 `BeatBadges`+`BeatBody`（只读）；**每场外层加 DOM id `scene-{scene.id}`，每节拍外层加 `beat-{scene.id}-{beatIndex}`**；每个场景头部放一个「定位原文」`Button size="sm" variant="outline"`（图标 `CrosshairIcon`/`MapPinIcon`）。
    - **滚动联动（scroll sync）**：当开关开启时，监听两个 `ScrollArea` 视口的 `scroll` 事件，按比例同步：`other.scrollTop = (this.scrollTop / (this.scrollHeight - this.clientHeight)) * (other.scrollHeight - other.clientHeight)`；用一个 `isSyncing` ref 互斥防止回环（A 触发同步 B 时，B 的 scroll 事件不要再回写 A）。开关关闭时不联动。
    - **互相高亮 + 定位（本地映射为主）**：
      - 维护本地 state `activeSource:{chapter,paragraph}|null` 与 `activeSceneId:string|null`。
      - **点右栏某场（或其「定位原文」按钮）**：取该场 `source_ref`，把 `source_ref.paragraphs` 对应的左栏段落加高亮类（如 `bg-primary/10 ring-1 ring-primary/40`），并 `getElementById('src-{chapter}-{首段}')?.scrollIntoView({behavior:"smooth",block:"center"})`；同时高亮该场。
      - **点左栏某段**：用本地计算找出所有 `scene.source_ref.chapter===chapter && scene.source_ref.paragraphs.includes(p)` 的场景，高亮之并滚动右栏到第一个 `scene-{id}`。
      - 高亮为「短暂 + 可清除」：再次点击别处或点空白清除。
    - **「定位原文」按钮用 `getTrace` 作权威数据源（接入 M6-T1 后端）**：点该按钮时，除了本地高亮，再调 `api.screenplay.getTrace(projectId, scene.id)`，用返回的 `paragraphs[].index` 作为**权威**的高亮段落集合（覆盖本地推断；若 `getTrace` 404 即「该场原文引用无法定位」toast 友好提示）。这样 M6 的 trace 接口被真实接入，且定位比纯本地更准。**常驻的视觉关联仍用本地 `source_ref`**（即时、无请求、无抖动），trace 仅服务于显式「定位」动作。
  - i18n 两 locale [zh-CN/common.json](../../frontend/app/i18n/locales/zh-CN/common.json) 与 [en/common.json](../../frontend/app/i18n/locales/en/common.json)：新增 `editor.*` 命名空间（两 locale 键完全一致）：门控空态标题/说明/CTA、双栏左右栏标题（「原文」/「剧本」）、滚动联动开关标题/说明、「定位原文」按钮与「该场原文引用无法定位」提示、状态徽标、空原文/空剧本占位。复用 `pages.editor.*` 作页眉、`trust.*` 作图例。
- **建议 commits：**
  1. `feat(frontend): add editor workbench i18n keys`（两 locale）
  2. `feat(frontend): scaffold editor workbench with screenplay gate`（门控 + 空态 + 页眉 + 图例）
  3. `feat(frontend): render source and screenplay dual pane with scroll sync`（双栏 + 滚动联动 + 高亮/定位 + trace 接入）
- **验收：** 已生成剧本的项目：进 `/editor` → 左整本原文、右整稿剧本并排；开「滚动联动」拖动任一栏，另一栏按比例跟随；点某场「定位原文」→ 左栏对应段落高亮并滚到视野（与 trace 返回段落一致）；点左栏某段 → 右栏对应场景高亮并滚到视野；未生成剧本时显示门控空态并可跳回 `script`。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 4 — 局部重生成（FR-9.2，核心交互）

- **分支：** `feat/editor-local-rewrite`
- **一句话目标：** 在双栏右侧每个场景头部加「局部重生成」入口：弹 `Dialog` 输入自然语言指令 → 调 `:rewrite` 只重写该场 → 刷新 → 新增节拍带 `ai_inferred` 高亮。
- **先安装 coss 组件：** 无需新装（用 `dialog`/`field`/`textarea`/`button`/`badge`/`alert`，均已装）。
- **改动文件：**
  - [project-editor.tsx](../../frontend/app/routes/project-editor.tsx)：
    - 每个场景头部加「局部重生成」`Button size="sm"`（图标 `SparklesIcon`/`WandSparklesIcon`），点击打开一个**受控 `Dialog`**（按当前场景 id 受控；用 `open`/`onOpenChange` + `useState<string|null>` 持有「正在重生成哪场」）：
      - `DialogHeader`：标题「局部重生成：第 N 场 · {location}」+ 说明「用自然语言描述想要的改动，只会重写本场，其他场不变」。
      - `DialogPanel`：一个 `Field`+`FieldLabel`+`Textarea`（指令，必填非空）+ `FieldDescription` 举例（「如：这场太平淡，把冲突往前提 / 口语化一点 / 把内心戏改成动作」）。
      - `DialogFooter`：`DialogClose render={<Button variant="ghost"/>}`「取消」+ 一个**普通** `Button type="button" loading`「重生成」。
    - 提交：`instruction.trim()` 为空时本地拦截（禁用按钮 + Field 错误），否则调 `api.screenplay.rewriteScene(projectId, sceneId, instruction)`（202）→ 成功 `toastManager.add(success)` + 关闭 Dialog + `revalidator.revalidate()`；失败 toast 显示 `ApiError.message`（含 422 空指令的友好回退）。重生成期间按钮 `loading` 且禁用。
    - **刷新后的「新增内容」提示**：重生成会让该场新节拍多为 `ai_inferred`；双栏右侧已有 flag 徽标与 `beatToneClass` 高亮（来自 PR2 共享组件），无需额外处理；可在该场头部加一个轻提示「本场刚被重生成，请重点复查 AI 新增内容」（用 `Alert variant="info"` 或一次性 Badge，基于「刚重生成的 sceneId」本地 state）。
  - i18n 两 locale：`editor.rewrite.*`（按钮、Dialog 标题/说明、指令标签/占位/举例、取消/重生成、成功/失败 toast、空指令提示、刚重生成提示）。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add local rewrite i18n keys`（两 locale）
  2. `feat(frontend): rewrite a single screenplay scene from instruction`（Dialog + :rewrite + 刷新 + 复查提示）
- **验收：** 已生成剧本的项目：点某场「局部重生成」→ 输入「把冲突往前提」→ 提交后**仅该场**内容变化、其余场不变、项目 state 变 `editing`（外层 `editor` 幕点亮）、该场出现带 `ai_inferred` 高亮的新节拍；空指令被拦截/得友好提示。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 5 — 节拍行内编辑（FR-9.5 所见即所得部分）

- **分支：** `feat/editor-inline-beat-editing`
- **一句话目标：** 在双栏右侧剧本视图里就地编辑节拍（正文/字段）、增/删/调序节拍、改场景 heading 与 mood，保存调 `PUT /screenplay/scenes/{id}`（整场全量回传），**强制保留 trust 字段**。
- **先安装 coss 组件：** 无需新装（用 `field`/`input`/`textarea`/`select`/`toggle-group`/`menu`/`button`/`alert-dialog`/`badge`，均已装）。
- **改动文件：**
  - [project-editor.tsx](../../frontend/app/routes/project-editor.tsx)：在 PR3 的右栏只读渲染基础上，引入**「场景编辑态」本地 state**（`editingSceneId:string|null` + 该场草稿 `draftScene:ScreenplayScene|null`）：
    - **进入编辑**：每场头部一个「编辑本场」`Button`（图标 `PencilIcon`）或行操作 `Menu`（「编辑本场 / 局部重生成」）。点「编辑本场」→ 以 loader 该场为初值深拷贝进 `draftScene`，该场切到编辑布局。**同一时刻只允许一个场处于编辑态**（避免多场并发写冲突）。
    - **场景级字段（轻量）**：`heading.int_ext`（`Select` INT/EXT）、`heading.time`（`Select` DAY/NIGHT/DAWN/DUSK）、`heading.location`（`Field`+`Input type="text"`）、`mood`（`Field`+`Input`，可空）。`synopsis`/`goal`/`conflict`/`ending_state`/`characters`/`foreshadowing`/`relation_changes`/`source_ref` **本 PR 不在编辑表单暴露，原样回传**（`extra="forbid"`，见坑）。
    - **节拍列表编辑**：`draftScene.beats` 逐条渲染为可编辑行，按 `type`：
      - `action`/`note`/`todo`：`Textarea` 编辑 `text`。`note` 的 `options[]` **只读展示、原样保留**（不编辑）。
      - `dialogue`/`voice_over`/`off_screen`：`Select`（说话人 `character`，items = `characters` 工件，value=id、label=name）+ `Input`（`parenthetical`，可空）+ `Textarea`（`dialogue`）。
      - **所有非 `todo` 节拍**：额外一个 `subtext` `Textarea`（可空）+ 一个 `flag` **`ToggleGroup type="single"`**（两项 `from_source`/`ai_inferred`，本地化「原文 / AI 新增」，**必选**）。
      - **`source_ref` 只读展示、不可编辑**（用文本标记展示），保存时原样回传——避免产生非法引用（后端编辑接口不校验 source_ref 段落真实性，但保留原值最安全）。
      - **节拍类型 `type` 本 PR 固定不可改**（改类型涉及字段重构，留未来增强）。
    - **增节拍**：节拍列表底部「添加节拍」按钮，弹一个小 `Menu`/`Select` 选类型（action/dialogue/voice_over/off_screen/note/todo）→ 追加一个该类型空节拍到 `draftScene.beats`：非 `todo` 默认 `source_ref = 该场 source_ref`、`flag = "ai_inferred"`（满足坑 1）；`todo` 默认 `source_ref=null,flag=null`。
    - **删节拍**：每行一个删除 `Button size="icon" variant="ghost"`（图标 `Trash2Icon`，补 `aria-label`），直接从 `draftScene.beats` 移除（本地，未保存前可撤销=取消编辑）。
    - **调序节拍**：每行「上移/下移」`Button size="icon"`（首/末禁用，补 `aria-label`），在 `draftScene.beats` 交换相邻项。**用上/下按钮而非拖拽**（无新依赖、键盘可达）。
    - **保存/取消**：该场编辑区底部「保存本场」（普通 `Button loading`）+「取消」（`Button variant="ghost"`，丢弃 `draftScene`）。
      - 保存前**本地兜底校验**：每个非 `todo` 节拍必须有非空 `source_ref` 与 `flag`，否则不发请求、给行级/场级错误提示（对齐坑 1，避免必然 422）。
      - 保存：以 loader 原始该场为基底浅拷贝、用 `draftScene` 覆盖被编辑字段，组装**完整 `ScreenplayScene`**（仅 `ScreenplayScene` 合法字段、**绝不混入信封字段**），调 `api.screenplay.updateScene(projectId, sceneId, fullScene)` → 成功 toast + 退出编辑态 + `revalidate`；失败：若 `ApiError.message` 含 `missing_trust_fields` → 友好「本场有节拍缺少来源/AI 标记，请补全后再保存」；其余显示 `ApiError.message`。
    - **未保存离开提醒**：当某场处于编辑态且用户点别处「编辑本场」或「局部重生成」时，用 `AlertDialog` 提示「当前有未保存的修改，是否放弃？」（破坏性=放弃用 destructive）。
  - i18n 两 locale：`editor.edit.*`（编辑/保存/取消、字段标签 location/int_ext/time/mood、节拍字段标签 character/parenthetical/dialogue/text/subtext/flag、flag 两态本地化、添加/删除/上移/下移 aria-label、节拍类型选项、缺 trust 字段提示、放弃未保存确认、成功/失败 toast）。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add inline beat editing i18n keys`（两 locale）
  2. `feat(frontend): edit screenplay beats inline and save scene`（场景/节拍字段编辑 + 全量回传 + trust 兜底）
  3. `feat(frontend): add reorder and add remove beats in editor`（增/删/调序 + 放弃未保存确认）
- **验收：** 已生成剧本的项目：编辑某场——改一句对白、改说话人、把某节拍 flag 从 `from_source` 切到 `ai_inferred`、加一个 `action` 节拍、删一个节拍、上移一个节拍 → 保存后该场持久更新、其余场不变、state 变 `editing`；把某非 todo 节拍 flag 清掉（若 UI 允许）→ 本地拦截或得「缺少来源/AI 标记」友好提示而非裸 JSON；取消编辑丢弃改动；编辑中切到别场触发未保存确认。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 6 — 源码（YAML）双视图（FR-9.5 源码部分）

- **分支：** `feat/editor-yaml-source-view`
- **一句话目标：** 在编辑器顶部加 `Tabs`「所见即所得 / 源码 (YAML)」；源码视图用 `yaml` 把整稿序列化为 YAML 文本供手改，应用时解析回 JSON 调 `PUT /screenplay`；引入并披露 `yaml` 依赖。
- **先安装依赖：** `pnpm --filter frontend add yaml`（在 frontend workspace 装 `yaml`）。装完 `git diff frontend/package.json pnpm-lock.yaml` 确认只新增 `yaml` 一个 runtime 依赖。**这是本计划唯一的新 npm 依赖，必须更新 README（见下）并在 PR 描述披露。**
- **先安装 coss 组件：** 无需新装（用 `tabs`/`textarea`/`button`/`alert`/`badge`，均已装）。
- **改动文件：**
  - [project-editor.tsx](../../frontend/app/routes/project-editor.tsx)：
    - 用受控 `Tabs`（`TabsList`>`TabsTab value="wysiwyg"`/`value="yaml"`，`TabsPanel` 对应）包住主体：`wysiwyg` 面板 = PR3–PR5 的双栏；`yaml` 面板 = 源码编辑区。用本地 `useState` 持 tab 值。
    - **源码（YAML）面板**：
      - 进入或点「从当前剧本载入」时，用 `yaml.stringify(screenplay.data)`（`screenplay.data` 即 `ScreenplayData`）生成 YAML，灌入一个受控 `Textarea`（大号、等宽、`whitespace-pre`，`type` 不适用于 textarea）。
      - 「应用更改」`Button loading`：`try { const parsed = yaml.parse(text) } catch → 行内 Alert variant="error" 显示「YAML 语法错误：{message}」`，不发请求；解析成功后**最小形状校验**（`parsed` 是对象且 `Array.isArray(parsed.scenes)` 且有 `shot_hints`，缺 `shot_hints` 时补 `screenplay.data.shot_hints` 兜底）→ 调 `api.screenplay.updateScreenplay(projectId, parsed)` → 成功 toast + 切回 `wysiwyg` + `revalidate`；失败：`missing_trust_fields` → 友好「有节拍缺少来源/AI 标记」，其余显示 `ApiError.message`。
      - 「重置」`Button variant="ghost"`：用当前 loader 的 `screenplay.data` 重新 `yaml.stringify` 覆盖 Textarea（丢弃手改）。
      - 顶部 `Alert variant="info"`：说明「源码视图直接编辑整稿结构，应用后会覆盖整份剧本；非 TODO 节拍必须保留 source_ref 与 flag（来源/AI 标记），否则无法保存」（对齐坑 1）。
    - **往返一致提醒**：`yaml.stringify`→编辑→`yaml.parse`→`PUT` 的链路依赖 `ScreenplayData` 全字段；不要在序列化前裁字段（直接序列化整个 `data`）。
  - [README.md](../../README.md)：
    - 在「依赖与来源」追加运行时依赖 **`yaml`**（用途：编辑器源码视图的 YAML 序列化/反序列化；来源：npm `yaml`，第三方库）。
    - 在「原创边界」段说明：编辑器的双栏对照、局部重生成、行内节拍编辑、YAML 源码视图、留白清单等交互与数据流为本项目业务实现；`yaml` 仅作文本序列化基座，coss 组件为 registry 生成的第三方基座。
  - i18n 两 locale：`editor.source.*`（Tab 标签「所见即所得」/「源码 (YAML)」、应用更改/重置、YAML 语法错误模板 `{{message}}`、形状非法提示、缺 trust 字段提示、覆盖整稿说明、成功/失败 toast）。两 locale 键一致。
- **建议 commits：**
  1. `chore(frontend): add yaml dependency and document source view`（package.json + lockfile + README）
  2. `feat(frontend): add yaml source view i18n keys`（两 locale）
  3. `feat(frontend): edit screenplay as yaml source and apply`（Tabs + 序列化/解析/应用/重置 + 错误处理）
- **验收：** 已生成剧本的项目：切「源码 (YAML)」→ 看到当前整稿 YAML → 改某场 synopsis/某节拍 dialogue → 应用 → 切回所见即所得看到生效、state 变 `editing`；故意写坏缩进 → 得「YAML 语法错误」行内提示且不发请求；删掉某非 todo 节拍的 flag 后应用 → 得「缺少来源/AI 标记」友好提示。`git diff frontend/package.json` 只多 `yaml`；README 已披露。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 7 — 留白（TODO）清单与高亮（FR-9.6）

- **分支：** `feat/editor-todo-markers`
- **一句话目标：** 在编辑器加「留白清单」：用 `GET /screenplay/todos` 拉取全部 `todo` 节拍，逐条定位到右栏对应节拍；并在双栏加一个「只看留白」开关高亮 todo 节拍。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`button`/`switch`/`separator`/`scroll-area`/`empty`，均已装）。
- **改动文件：**
  - [project-editor.tsx](../../frontend/app/routes/project-editor.tsx)：
    - `clientLoader` 增并行 `getOrNull(api.screenplay.getTodos)`（剧本存在时拉；404→null）。返回里加 `todos`。
    - **留白清单区块**（独立 `Card`，可放 `wysiwyg` 面板顶部或右栏上方）：
      - 标题 + `Badge` 显示 `count`（`{{count}}`）；下面逐条：场景标题（用右栏 `sceneById` 映射 id→`sceneTitle`，映射不到回退 id）+ 节拍序号 + `source_ref` 文本标记（用 item 顶层 `source_ref`，可能为 null → 显示「无来源」）+ `beat.text` 摘要。
      - 每条一个「定位」`Button size="sm" variant="outline"`：调用 PR3 已有的 `scrollToBeat(sceneId, beatIndex)`（按 `beat-{sceneId}-{index}` 锚点滚动并高亮），把作者带到该 todo 节拍。
      - 无 todo 时显示「当前没有留白，剧本暂无待补充内容」空文案。
      - 一个「刷新清单」`Button`（重新 `getTodos`，或直接 `revalidate`）——因为编辑/重生成可能改变 todo 集合。
    - **双栏「只看留白」开关**：在双栏控制区加一个 `Switch`「只看留白」（与 PR3 的「滚动联动」开关并列）。开启时：右栏 `todo` 节拍高亮（已有 `beatToneClass` 给 todo warning 色），非 todo 节拍弱化（降透明度，如 `opacity-40`），整场无 todo 时整场弱化；关闭复原。**纯本地过滤高亮，不发请求**（与 M5 加戏过滤同策略）。
  - i18n 两 locale：`editor.todo.*`（清单标题/说明、计数 `{{count}}`、定位按钮、刷新、空态、「只看留白」开关标题/说明、无来源标记）。两 locale 键一致。
- **建议 commits：**
  1. `feat(frontend): add todo markers i18n keys`（两 locale）
  2. `feat(frontend): list and locate screenplay todo markers`（清单 + getTodos + 定位 + 刷新）
  3. `feat(frontend): add todo only highlight toggle in dual pane`（只看留白开关 + 本地高亮）
- **验收：** 含 `todo` 节拍的剧本（可在 PR5 行内加一个 todo，或 mock 生成的剧本本就含 todo）：进 `/editor` → 留白清单显示 ≥1 条（场景标题 + 节拍序号 + 摘要）→ 点「定位」滚到右栏该节拍并高亮；开「只看留白」→ 仅 todo 节拍突出、其余弱化；编辑后点「刷新清单」数目更新。`build`/`typecheck`/`lint`/`format:check` 过。

---

## coss UI 组件映射（每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`。导入 `~/components/ui/<name>` 的**已样式化导出**优先于 `*Primitive`。**M6 不新装任何 coss 组件**（所需组件全部已装）；唯一新增依赖是 `yaml`（PR6）。下表组件用法已对照 coss skill 各 primitive 指南。

| 界面元素 | coss 组件（已装） | 关键 composition / 注意点 | 所属 PR |
| --- | --- | --- | --- |
| 工作台门控/状态/提示 | `alert` / `badge` / `empty` | 未生成剧本用 `Empty`>`EmptyHeader`(`EmptyMedia variant="icon"`)+`EmptyTitle`/`EmptyDescription`+`Button render={<Link/>}`；状态徽标用 `Badge`；重生成/缺 trust 提示用 `Alert variant`（info/warning/error） | PR3/PR4/PR5/PR6 |
| 信任图例 | 复用 `trust-chips`（已有组件） | 直接渲染 `<TrustChips/>`（原文/AI 新增/TODO 三色），读 `trust.*` | PR3 |
| 双栏滚动容器 | `scroll-area` | 左右各一个 `ScrollArea`，**必须给显式高度**（如 `h-[calc(100vh-16rem)]`）；拿视口节点做滚动联动；勿在内部再套竞争滚动的 ScrollArea | PR3 |
| 联动/只看留白 开关 | `switch` | 「带描述」结构：`Label htmlFor`+说明在左、`Switch id` 在右（用 `useId`）；偏好开关用 `Switch`（不用 ToggleGroup） | PR3/PR7 |
| 场景卡片头/字段（只读） | `card`/`badge`/`separator`（经 PR2 共享组件） | 复用 `screenplay-scene-view`/`screenplay-beat-view`；INT/EXT·time·flag·source_ref 各一个 `Badge`；ai_inferred/todo 用警示色 | PR3 |
| 行操作菜单（编辑/重生成） | `menu` | `Menu`>`MenuTrigger render={<Button size="icon" variant="ghost"/>}`+`MenuItem`；或直接两个并列 Button。图标按钮补 `aria-label` | PR4/PR5 |
| 局部重生成弹窗 | `dialog` | `Dialog` 受控（`open`/`onOpenChange`）>`DialogPopup`>`DialogHeader`(在 form 外)+`DialogPanel`(指令表单)+`DialogFooter`(取消 `DialogClose`/重生成普通 Button `type="button"`) | PR4 |
| 指令输入 | `field`+`textarea` | `Field`>`FieldLabel`+`Textarea`（`Textarea` 已内置 `Field.Control`，直接放进 `Field`）+`FieldDescription`(举例)+`FieldError`(空指令) | PR4 |
| 节拍正文行内编辑 | `field`+`textarea`/`input` | action/note/todo 用 `Textarea` 编辑 `text`；对白用 `Input`(parenthetical)+`Textarea`(dialogue)；潜台词用 `Textarea`。`Input` 必显式 `type="text"` | PR5 |
| 说话人 / heading 枚举 单选 | `select` | items-first：`Select items=[...]`>`SelectTrigger`>`SelectValue`+`SelectPopup`>`SelectItem`；说话人 items=characters(value=id,label=name)，int_ext/time 用枚举 items | PR5 |
| flag 二选一（原文/AI 新增） | `toggle-group` | `ToggleGroup type="single"` 两项 `from_source`/`ai_inferred`，受控、互斥；图标/文本项补可达标签。**互斥分段选择用 ToggleGroup，不用 Switch/Checkbox** | PR5 |
| 增/删/调序 节拍 | `button` | 添加(选类型可配 `Menu`/`Select`)、删除 `Button size="icon" variant="ghost"`(+aria-label)、上/下移 `Button size="icon"`(首/末禁用)。无拖拽依赖 | PR5 |
| 放弃未保存 / 破坏性确认 | `alert-dialog` | **破坏性操作用 AlertDialog**：footer `AlertDialogClose`（取消 ghost / 放弃 destructive） | PR5 |
| 所见即所得 / 源码 切换 | `tabs` | `Tabs`(受控 `value`/`onValueChange`)>`TabsList`>`TabsTab value="wysiwyg"/"yaml"`+`TabsPanel`；`TabsTab` 与 `TabsPanel` 的 value 必须配对 | PR6 |
| YAML 源码编辑 | `textarea`+`alert`/`button` | 大号 `Textarea`（等宽 `font-mono`、`whitespace-pre`）；语法错误用 `Alert variant="error"`；应用/重置用 `Button` | PR6 |
| 留白清单 | `card`/`badge`/`button`/`scroll-area` | 每条场景标题+节拍序号+source_ref+摘要+定位按钮；`count` 用 `Badge`；多条用 `ScrollArea` 包裹 | PR7 |
| 操作成功/失败反馈 | `toast` | `toastManager.add({title,description,type})`；root 已接 provider | PR3–PR7 |

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **门控只看工件存在/state，不看 `project.state`/`project.gates`。** `editor` 能否打磨 → `GET /screenplay` 是否 404（404=未生成→空态引导回 `script`）。`project.gates` 是 http 层假默认值，不可用。
2. **trust 字段是编辑/源码改写的头号坑（PR5/PR6）。** `PUT /screenplay`、`PUT /scenes/{id}`、`:rewrite` 都要求**非 `todo` 节拍必须带 `source_ref` 与 `flag`**，否则 `422`，错误体在 `detail`（dict，`code:"missing_trust_fields"`，含 `items:[{scene_id,beat_index,fields}]`）；http 层把它 `JSON.stringify` 进 `ApiError.message`。**前端：① 行内编辑/源码应用前本地兜底校验，缺失即拦截给友好提示；② 仍捕获 422 翻成本地化「本场/某些节拍缺少来源(source_ref)或 AI 标记(flag)」，不要把裸 JSON 弹给用户。** 新增节拍默认补 `source_ref=该场 source_ref`、`flag="ai_inferred"`。
3. **`extra="forbid"` 全量回传：** `ScreenplayScene`、`Beat` 禁止多字段。行内编辑以 loader 原始该场为基底浅拷贝改字段，**绝不**把信封字段（`version`/`state`/`updated_at`/`type`/`parent_version`/`etag`/`needs_recompute`）混进 `data`；表单未暴露的字段（synopsis/goal/conflict/ending_state/characters/foreshadowing/relation_changes/source_ref/note.options 等）**原样回传**。源码（YAML）应用时直接 `yaml.parse` 整个 `ScreenplayData` 回传，不裁字段。
4. **所有 M6 写操作把项目 state 推进 `editing`（后端行为）。** 前端写后 `revalidate`，外层 `editor` 幕会自动点亮（无需改 stages.ts）。剧本工件 envelope 仍是 `draft`，**editor 页无确认按钮**。
5. **`:rewrite`/`updateScene` 返回整稿信封**（仅替换目标场）。写后用返回信封 `data` 或直接 `revalidate` 整体刷新；不要只局部 patch 单场以免与服务端 trust 回填不一致。
6. **双栏定位优先本地、显式定位用 trace。** 常驻视觉关联（点场→高亮原文段、点段→高亮场）用本地 `source_ref` 映射（即时、无请求、无抖动）；每场「定位原文」按钮额外调 `getTrace` 作权威段落集合并兜 404 友好提示——这是真实接入 M6-T1 后端。`source:resolve` 与 `/beats?source_*` 端点已在 client 备好，本期可不在 UI 主路径调用（保留给未来按段反查增强）。
7. **滚动联动防回环：** 用 `isSyncing` ref 互斥；按 `scrollTop/(scrollHeight-clientHeight)` 比例同步；开关关闭时解绑/跳过。
8. **`character`/`characters[]`/`relation_changes[].characters[]` 全是人物 id：** editor loader 拉 `characters` 工件做 id→name 映射（只读展示与「说话人」候选项）；映射不到回退显示 id。
9. **本地过滤高亮（只看留白）不发请求**（对已加载整稿处理），`getTodos` 仅驱动「留白清单」区块；二者应一致（可作自检）。
10. **冒号动作段按字面拼接**（`:rewrite`、`source:resolve`），`/scenes/{id}/trace` 是斜杠子路径；都不要 URL-encode 冒号。
11. **404 = 空态/友好提示而非崩溃：** loader 里对 `screenplay.get`/`getTodos`/`getTrace` 的 404 `catch→null`（沿用 `getOrNull`，判 `ApiError && status===404`）；`getTrace`/`source.resolve` 的 404（引用无法定位）在交互层 toast 友好提示；其余错误继续抛。
12. **写操作是同步任务：** `updateScreenplay`/`updateScene`/`:rewrite` 期间按钮 `loading` 且禁用；失败 toast 展示（翻译后的）`ApiError.message`。本期不接 SSE/Job。
13. **i18n 两 locale 同步：** 每个新增键在 `zh-CN` 与 `en` 完全一致；插值占位一致。新增统一挂在 `editor.*` 命名空间（`editor.rewrite.*`/`editor.edit.*`/`editor.source.*`/`editor.todo.*`），复用 `pages.editor.*` 作页眉、`trust.*` 作图例，避免与既有 `script.*`/`outline.*` 冲突。
14. **coss 用法红线**（照 coss skill）：① 导入 `~/components/ui/<name>` 已样式化导出优先于 `*Primitive`；② Dialog/AlertDialog/Menu/Select/Tabs/ToggleGroup 各按其文档层级，不跨组件混用 trigger/popup（`TabsTab`↔`TabsPanel` value 配对、`SelectValue` 放进 `SelectTrigger`、`Select` items-first、`Dialog` 表单时 header 在 form 外 / `Form className="contents"` 包 panel+footer）；③ `Input` 必显式 `type`，`Textarea` 直接放进 `Field`（已内置 control）；④ `Switch` 用于偏好开关（联动/只看留白）、`ToggleGroup type="single"` 用于互斥分段（flag 二选一）、`Select` 用于枚举单选——不混用；⑤ 图标按钮补 `aria-label`，`Alert` 语义图标不要 `aria-hidden`；⑥ 破坏性确认（放弃未保存）用 `AlertDialog`，普通输入（重生成指令）用 `Dialog`；⑦ `ScrollArea` 必给显式高度、勿嵌套竞争滚动；⑧ Toast 直接 `toastManager.add`。

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- **版本与分支（FR-9.3，API-22）未实现：** `GET/POST /scenes/{id}/versions`、`POST /scenes/{id}:checkout`、`GET /scenes/{id}/versions:diff` 均 `NotImplementedError`。本期 editor **不做版本分支/对比/回滚**；在 PR3/PR5 描述里标注。
- **`PUT /screenplay` 仅接受 JSON：** `GET` 也只支持 `format=json`（`format!=json`→422）。YAML 纯前端序列化（PR6 经 `yaml` 库），后端不产/不收 YAML。
- **编辑接口不校验 `source_ref` 段落真实性：** `PUT`/`:rewrite` 只校验「非 todo 节拍带 source_ref+flag」，不校验段落 index 是否在原文存在（与 outline 的 `invalid_source_ref` 严格校验不同）。前端行内编辑把 `source_ref` 设为只读、原样回传，避免引入坏引用。
- **`gates` 字段后端不返回**，http 层填假默认值，不可用于判断阶段状态。
- **`etag` 恒 null、不校验 `If-Match`**（乐观锁未实现），不发 `If-Match`；**多场并发编辑无冲突保护**——前端用「同一时刻只允许一个场处于编辑态」规避（PR5）。
- **`project.state` 仅从 `intent_set` 起正常推进**（M2/M3 已记录缺口延续）：跳过保存意图直接生成，state 可能停在更早态，外层幕不点亮；建议作者按流程走。M6 编辑会把 state 推到 `editing`（前提是剧本已生成）。

> 这些只标注、不改后端。若后端后续补齐版本分支/乐观锁/YAML 导出，前端可据此扩展。

---

## 验证方式（端到端）

1. **起后端：** `backend/` 按其工具启动 dev 服务（[dev_server.py](../../backend/scripts/dev_server.py)，`:8000`）。
2. **起前端：** 仓库根 `pnpm install`（PR1–PR5、PR7 无新 npm 依赖；PR6 装 `yaml`，`pnpm install` 后生效）→ `pnpm dev`（默认 http，经 Vite 代理打 `:8000`）。
3. **冒烟（按 PR 累积，需先把某项目跑到「剧本初稿已生成」）：**
   - 前置：人物确认 → 意图保存 → 大纲生成并确认 → 剧本生成（`/script`）。
   - PR1：`typecheck`/`build` 过；mock 控制台手调 `rewriteScene`/`updateScene`/`updateScreenplay`/`getTodos`/`getTrace`/`source.resolve`，形状/门控/state→editing 正确。
   - PR2：`script` 页行为逐项与重构前一致（生成/只读/三态过滤/AI 清单/镜头开关/重生成）。
   - PR3：进 `/editor` → 双栏并排、滚动联动、点场定位原文（与 trace 一致）、点段定位场、未生成剧本显示门控。
   - PR4：某场局部重生成 → 仅该场变、其余不变、出现 ai_inferred 高亮、state 变 editing；空指令被拦截。
   - PR5：行内改对白/说话人/flag、增/删/调序节拍、改 heading/mood → 保存持久、其余场不变；缺 trust 字段得友好提示；取消丢弃、切场触发未保存确认。
   - PR6：源码 YAML 视图序列化/改写/应用生效；语法错误行内提示；缺 trust 字段友好提示；`git diff frontend/package.json` 仅多 `yaml`，README 已披露。
   - PR7：留白清单显示与定位、只看留白高亮、刷新更新。
   - 离线：任一 PR 后 `VITE_API_MODE=mock pnpm dev` 仍可走完「生成→进 editor→双栏/重生成/编辑/源码/留白」流程（mock 复刻门控/编辑/留白/trace；需先在 mock 跑到剧本已生成）。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。PR6 装完 `yaml` 后 `git diff frontend/package.json` 核对仅新增 `yaml`，并人工点检 Dialog/AlertDialog/Menu/Select/Tabs/ToggleGroup 的键盘与焦点返回。
5. **窗口与规范：** 提交时间落在 2026-06-05 ~ 2026-06-07（北京时间）；分支名/commit 经 hooks 校验（subject 纯 ASCII）；每 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式并勾选合规项。

---

## AGENTS.md 合规要点

- **单一边界：** PR1 客户端、PR2 共享组件重构、PR3 双栏壳、PR4 局部重生成、PR5 行内编辑、PR6 YAML 源码、PR7 留白——每个 PR 一个清晰边界，互不混入无关重构/样式。PR2 是**与 M6 直接相关**的行为保持重构，单独成 PR 以保边界与 main 可运行。
- **README 更新（依赖与来源 / 原创边界）：**
  - **仅 PR6** 在 [README.md](../../README.md) §依赖与来源追加运行时依赖 **`yaml`**（用途：编辑器源码视图 YAML 序列化/反序列化；第三方 npm 库），并在「原创边界」段说明 M6 编辑器各能力为本项目业务实现、`yaml` 与 coss 为第三方基座。
  - **PR1–PR5、PR7 不新增依赖、不改运行流程，README 无需更新**（在 PR「来源与依赖」段写「无新增第三方依赖；复用既有 API 客户端模式与已装 coss 组件」）。
- **PR 描述据实披露：** 复用既有 API 客户端模式与 coss 基座；PR6 新增 `yaml` 依赖标明为第三方库；后端缺口（版本分支未实现、仅 JSON、编辑不校验 source_ref 真实性、gates 不可用、无乐观锁等）如实说明，不得把后端能力写成前端原创。
- **main 每次合并后可 `pnpm build` 通过、可启动；提交在开发窗口内（2026-06-05~06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。**
