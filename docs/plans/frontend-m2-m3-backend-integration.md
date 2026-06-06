# 前端接入后端 M2/M3 接口 — 实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 **M2（改编前理解层：作品理解 + 人物档案）** 与 **M3（意图与方向锁定：作者意图 + 改编方向 + 冲突校验）** 接口，本计划把这两层接到前端，并把 `analysis` 阶段从单一占位页升级为「作品理解 → 人物档案 → 作者意图与方向」三步可用界面。**全程只改 `frontend/`，不改 `backend/`。**
>
> 本计划延续 [`frontend-m0-m1-backend-integration.md`](./frontend-m0-m1-backend-integration.md) 的约定（Vite 代理联调、默认 `http` 模式、http/mock 双实现、coss 组件经 shadcn registry 安装、信任能力对齐）。执行前请先通读该文档的「总体方案与不变量」「跨 PR 关键实现细则」「coss 用法红线」，本计划只补充 M2/M3 的差异点，不重复其通用规则。

---

## Context（为什么做、目标）

- 产品主流程在「导入（M0/M1，已接通）」之后是 **P1「先理解，再改编」关卡**：必须先产出并经作者确认「作品理解」和「人物档案」，才能进入下游；随后收集「作者意图」并选择「改编方向」，得到冲突提示。后端已把 M2/M3 全部接口实现完毕（见下「后端现状核对」），但前端当前：
  - API 客户端层（`frontend/app/lib/api/`）只有 `projects` 与 `source` 两类资源，**没有 understanding / characters / intent 资源**。
  - `analysis` 路由仍是 [project-analysis.tsx](../../frontend/app/routes/project-analysis.tsx) 的 `StagePlaceholder` 占位，无任何交互。
- 目标产出：作者在导入满足 ≥3 章后，能在 `analysis` 阶段依次完成——
  1. **作品理解**：一键生成 → 逐字段编辑（含 logline / 简介 / 主题 / 目标 / 恐惧 / 矛盾 / 基调 / 风格指纹）→ 查看视角时态与 `non_visualizable` 溯源标记（只读信任信号）→ **确认**。
  2. **人物档案**：在理解已确认后生成 → 按角色分类查看 → 编辑 / 新增 / 删除人物（含 `voice` / `hard_rules` / 关系）→ **确认**。
  3. **作者意图与改编方向**：填写意图约束（保留 / 禁删 / 禁合并 / 必留台词 / 情绪底色 / 三个布尔开关 / 目标类型）→ 选择改编方向（忠实 / 影视化 / 短剧）→ 触发**确定性冲突校验**并展示冲突清单（不阻塞）→ 进入下一阶段。
  全部数据来自真实后端。
- **本次已与用户确认的四项决策**（写死，执行 Agent 不得擅自变更）：
  1. **范围 = M2 + M3 一起完整接入**（作品理解、人物档案、作者意图、改编方向、冲突校验都做）。
  2. **页面组织 = 子路由**：`analysis` 升级为带「子步骤导航」的布局路由，下挂 `理解 / 档案 / 意图` 三个子路由页。
  3. **编辑深度 = 标量全编 + 数组增删**：所有标量字段（字符串/布尔/枚举）可编辑；所有字符串数组字段（themes、strengths、difficulties、keep、no_delete、no_merge、must_keep_lines、hard_rules 等）支持「增加一条 / 删除一条」；`relations` 作为结构化数组支持增删行（选关联人物 + 类型 + 变化）。`non_visualizable` 与 `narrative` 作为**只读信任信号**展示，不可编辑。
  4. **下一步 CTA**：人物档案确认后 CTA 指向同阶段的「意图与方向」子步骤；意图与方向完成后 CTA 指向下一阶段 `/outline`。

---

## 后端现状核对（执行前必读，避免按 api.md 想当然）

`docs/design/api.md` §5/§6/§7 是「全量契约」，但**后端实际行为与 api.md 有若干关键差异**。以下以**代码实际行为为准**（已逐文件、逐测试核对：[understanding.py](../../backend/src/cardenio/api/routes/understanding.py)、[characters.py](../../backend/src/cardenio/api/routes/characters.py)、[intent.py](../../backend/src/cardenio/api/routes/intent.py) 及对应 `backend/tests/api/test_*.py`）。

### 通用：工件信封（envelope）形状

理解 / 档案 / 意图三类工件的读写接口都返回**统一信封**（[base.py](../../backend/src/cardenio/domain/models/base.py) `ArtifactEnvelope`）：

```jsonc
{
  "type": "understanding",          // "understanding" | "characters" | "intent"
  "state": "draft",                  // "draft" | "confirmed" | "needs_recompute"
  "version": "v_3f2a9c1b",           // 形如 v_<hex8>，不是 api.md 示例里的 "v3"
  "parent_version": "v_1a2b3c4d",    // 上一版本，或 null
  "etag": null,                      // 后端当前恒为 null
  "updated_at": "2026-06-06T08:00:00Z",
  "needs_recompute": false,
  "data": { /* 工件正文，按类型不同，见下 */ }
}
```

- **`version` 是 `v_<hex8>` 随机串**，不是递增的 `v2/v3`；前端只把它当不透明字符串，用于显示「已是第 N 版」时**不要**解析它，按需用 `parent_version` 是否为 null 判断「是否首版」。
- **`etag` 恒为 null，后端不校验 `If-Match`**（乐观锁未实现）。前端 PUT/编辑请求**不要**发 `If-Match` 头，也不要依赖版本冲突 409（不会发生）。这是后端缺口，标注但不修。

### M2 · 作品理解（[understanding.py](../../backend/src/cardenio/api/routes/understanding.py)，前缀 `/projects/{project_id}/understanding`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| 生成 | `POST :generate` | 无 | `202` + 信封（`state:"draft"`）。原文不足 3 章 → `409 chapter_threshold_unmet`，`details:{min_chapters:3,current_chapters:N,passed:false}`。项目不存在 → `404` |
| 读取 | `GET ` (前缀根) | — | `200` 信封；尚未生成 → `404 {"detail":"Understanding not found"}` |
| 编辑 | `PUT ` (前缀根) | `UnderstandingData` **全量** | `200` 信封（`state:"draft"`，`parent_version` 指向上一版） |
| 确认 | `POST :confirm` | 无 | `200` 信封（`state:"confirmed"`）。尚未生成 → `404` |

`UnderstandingData`（[understanding.py](../../backend/src/cardenio/domain/models/understanding.py)，**`extra="forbid"` —— 多传任何字段会 422**）：

```jsonc
{
  "logline": "string",            // 必填非空
  "synopsis": "string",           // 必填非空
  "themes": ["string"],            // 可空数组
  "protagonist_goal": "string",    // 必填
  "protagonist_fear": "string",    // 必填
  "central_conflict": "string",    // 必填
  "mood": "string",                // 必填
  "style_fingerprint": "string",   // 必填；同时被回写进 project.meta（全程生成约束）
  "narrative": {                    // 必填对象（只读信任信号）
    "perspective": "first_person", // 自由字符串，常见 first_person / third_person_limited / omniscient
    "tense": "past",               // past / present
    "unreliable": false
  },
  "non_visualizable": [             // 可空数组（只读信任信号，FR-2.1）
    { "source_ref": { "chapter": 1, "paragraphs": [2] }, "note": "string" }
  ],
  "strengths": ["string"],
  "difficulties": ["string"]
}
```

**理解层必须知道的真实行为与坑：**

1. **`PUT` 是「全量替换」且 `extra="forbid"`。** 编辑保存时必须**恰好**回传上面这套字段（不能多、`narrative` 等必填项不能少）。前端编辑器要以「当前 `data` 为基底，浅拷贝后改其中字段，再整体 PUT」，**严禁**附加 `version`/`updated_at`/`type` 等信封字段进 `data`。
2. **`PUT` / `:generate` 都把 `state` 置回 `draft`。** 因此「确认后再编辑 → 回到 draft → 下游档案生成关卡重新关闭」。UI 必须显示当前 `state`，并在「已确认后又编辑」时提示需重新确认。
3. **`non_visualizable` 与 `narrative` 由后端从原文确定性推断**（关键词扫描），是**信任信号**：`non_visualizable[].source_ref` 指回原文章节段落。本期**只读展示**，不进入可编辑表单（即使作者 `PUT` 时改了它们，也属"全量替换"会被保存——但本计划不提供其编辑入口，PUT 时原样回传后端给出的值）。
4. **`style_fingerprint` 写回 project：** 生成/编辑/确认后端都会把 `style_fingerprint` 写进 `project.meta`，前端项目详情 `GET /projects/{id}` 的 `style_fingerprint` 字段会随之更新（http 适配层已映射进 `meta.style_fingerprint`）。UI 可在理解页展示它，但**事实源以理解工件的 `data.style_fingerprint` 为准**。

### M2 · 人物档案（[characters.py](../../backend/src/cardenio/api/routes/characters.py)，前缀 `/projects/{project_id}/characters`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| 生成 | `POST :generate` | 无 | `202` + 信封（`data:{characters:[...]}`，`state:"draft"`）。**前置：理解工件 `state=="confirmed"`**，否则 `409 state_gate_blocked`，`details:{artifact:"understanding",required_state:"confirmed",current_state:"..."}`。项目不存在 → `404` |
| 读取 | `GET ` (前缀根) | — | `200` 信封；尚未生成 → `404 {"detail":"Characters not found"}` |
| 新增人物 | `POST ` (前缀根) | `Character` **全量** | `201` 信封（含全部人物）。`id` 已存在 → `409 {"detail":"Character already exists"}` |
| 编辑人物 | `PUT /{characterId}` | `Character` **全量** | `200` 信封。`id` 不存在 → `404` |
| 删除人物 | `DELETE /{characterId}` | — | `204`。不存在 → `404` |
| 确认 | `POST :confirm` | 无 | `200` 信封（`state:"confirmed"`）。尚未生成 → `404` |

`Character`（[characters.py](../../backend/src/cardenio/domain/models/characters.py)，**`extra="forbid"`**）：

```jsonc
{
  "id": "lin_wan",                  // 必填，唯一；新增时由前端生成（见下坑 3）
  "name": "林晚",                    // 必填
  "role": "protagonist",            // 必填，枚举：protagonist | supporting | mentioned
  "voice": "克制、爱用反问",          // 必填（台词生成硬约束）
  "desire": "找回父亲的真相",         // 必填
  "fear": "再次被抛弃",              // 必填
  "arc": "从回避到直面",             // 可为 null
  "relations": [                     // 可空数组
    { "to": "lin_fu", "type": "父女", "change": "由疏离到和解" }  // change 可为 null
  ],
  "hard_rules": ["从不主动示弱"]      // 可空数组
}
```

**人物档案层必须知道的真实行为与坑：**

1. **新增/编辑/删除都把工件置回 `draft`。** 三个写操作（`POST`/`PUT`/`DELETE`）内部都用 `_save_characters` 重建整份工件为 `state="draft"`。因此**确认人物档案后，任何一次增删改都会让档案回到 draft，需重新 `:confirm`**——否则下游大纲生成关卡（要求 characters confirmed）会再次关闭。UI 必须据此提示。
2. **写操作返回的是整份信封（含全部 characters），不是单个人物。** 前端每次增删改后用返回信封的 `data.characters` 整体刷新列表即可，不要假设返回单条。
3. **新增人物的 `id` 由前端生成。** 后端不自动生成 id（`POST` 直接用请求体的 `id`，重复则 409）。前端在「新增人物」时要本地派生一个稳定 id：建议把 `name` 规范化为 ASCII slug（小写、非字母数字转下划线、去首尾下划线），为空则回退 `character`；若与现有 id 冲突，追加 `-2`/`-3` 等后缀去重。**这是前端职责，后端不兜底。**
4. **`relations[].to` 指向的是另一个人物的 `id`（不是 name）。** 关系编辑器的「关联人物」下拉项 value 用人物 `id`，展示用 `name`。后端生成的关系可能含 `type:"co_occurs"` 这类机器推断值（同段共现），属正常，可编辑覆盖。
5. **`role` 是严格枚举**：只接受 `protagonist|supporting|mentioned`，编辑器用单选控件限制取值，勿用自由文本。

### M3 · 作者意图与改编方向（[intent.py](../../backend/src/cardenio/api/routes/intent.py)，前缀 `/projects/{project_id}/intent`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| 保存意图 | `PUT ` (前缀根) | `IntentConstraints` **全量** | `200` 信封（**`state` 直接为 `confirmed`**）。项目不存在 → `404` |
| 读取意图 | `GET ` (前缀根) | — | `200` 信封；未保存过 → `404 {"detail":"Intent not found"}` |
| 选择方向 | `PUT /direction` | `{ "direction": "faithful" }` | `200` **`{ "direction": "...", "project": <扁平项目对象> }`**（**不是信封！**）。非 MVP 方向 → `422`。项目不存在 → `404` |
| 冲突校验 | `POST :validate` | 无 | `200` `{ "conflicts": [ { code, message, fields } ] }`。**前置：意图工件已存在**，否则 `404 {"detail":"Intent not found"}` |

`IntentConstraints`（[intent.py](../../backend/src/cardenio/domain/models/intent.py)，**`extra="forbid"`**）：

```jsonc
{
  "keep": ["父女对峙"],              // 最想保留的内容
  "no_delete": ["父亲之死"],         // 不能删除的情节
  "no_merge": ["林晚", "林父"],      // 不能合并的人物（自由文本，非 id）
  "must_keep_lines": ["原来你一直都……"], // 必须逐字保留的台词
  "mood_floor": "压抑",              // 情绪底色，可为 null
  "allow_new_plot": false,           // 是否允许新增桥段
  "allow_reorder": false,            // 是否允许调整顺序
  "allow_new_ending": false,         // 是否允许调整结局
  "target_type": "short_drama"       // 目标剧本类型，枚举或 null（见坑 3）
}
```

**意图/方向层必须知道的真实行为与坑（与 api.md 差异最大，务必照此实现）：**

1. **意图没有独立的 `:confirm` 动作——`PUT /intent` 保存即确认。** 后端 `set_intent` 直接以 `state="confirmed"` 落库。所以 UI 上「保存意图」这一个动作 = 提交并确认，**不要**去找/调用 `intent:confirm`（不存在）。
2. **方向接口返回的不是工件信封，而是 `{direction, project}`。** `PUT /intent/direction` 把方向写进 `project.meta.adaptation_direction`（不写进意图工件），返回体里 `project` 是**扁平项目对象**（同 `GET /projects/{id}` 形状）。http 适配层要对这里的 `project` 调用既有的「扁平→嵌套」`normalizeProject` 归一化；前端拿 `direction` 字段更新本地方向选择态即可。
3. **「改编方向」与意图里的 `target_type` 是两个不同的东西，且冲突校验只认前者。**
   - 「方向」存在 `project.meta.adaptation_direction`，由 `PUT /intent/direction` 设置，**取值仅 `faithful|cinematic|short_drama`**（其余 422）。
   - `IntentConstraints.target_type` 是意图工件内的独立字段（枚举可含 tv/film/stage 或 null），不影响冲突校验。
   - `POST :validate` 的冲突判定**只读 `project.adaptation_direction`**（来自 `/direction`）与意图布尔位，**完全不读 `target_type`**。
   - **本计划的处理（写死）**：UI 的「改编方向」单选控件驱动 `PUT /intent/direction`；意图表单内**不再单独暴露 `target_type` 编辑项**，保存意图时把 `target_type` 设为与所选方向相同的值（或 null）——避免两个相似字段让作者困惑。执行 Agent 按此实现，勿自行增设第二个方向选择器。
4. **冲突校验有顺序依赖：** `:validate` 要求意图工件**已存在**（否则 404），且方向**已设置**（否则后端返回空冲突列表 `{conflicts:[]}`）。所以触发校验前，UI 必须保证「先保存过意图 + 已选方向」。推荐交互：作者保存意图、选方向后，自动（或点「检查冲突」按钮）调一次 `:validate` 展示结果；若意图尚未保存则禁用该按钮并提示。
5. **冲突不阻塞、仅提示。** `conflicts` 为空数组表示无冲突。每条 `{code,message,fields}`，`fields` 指出涉及的字段（如 `["direction","allow_new_ending"]`）。展示为警告列表，由作者自行决定是否回头调整，**不拦截进入下一步**。
6. **后端已知冲突规则（用于本地化文案对照，前端只展示后端返回的，不自己算冲突）：** `faithful_vs_new_ending`、`faithful_vs_new_plot`、`faithful_vs_reorder`（忠实方向 + 对应布尔为真）、`short_drama_vs_no_reorder`（短剧方向 + 不允许调序）。前端按 `code` 映射本地化文案；若出现未知 code，回退展示后端 `message`。

### 关键跨层缺口：`project.state` 在 M2/M3 几乎不前进（决定门控策略）

逐路由核对状态机推进逻辑后确认一个**贯穿全程的缺口**：

- M1 的 `source` 路由从不把状态置为 `imported`（M0/M1 计划已记录），所以导入后 `project.state` 停在 `"empty"`。
- `understanding:generate`/`:confirm` 只在 `state=="imported"` 时才前进到 `understood`——但 state 是 `"empty"`，**条件不满足，state 不动**。
- `characters:confirm` 只在 `state=="understood"` 时才前进到 `profiled`——同样不满足，**state 不动**。
- 唯一例外：`PUT /intent` 的前进条件是 `state=="profiled"` **或** `characters 工件已 confirmed`。因为后者成立，**保存意图时 state 会跳到 `intent_set`**。

**结论（门控策略，写死）：**

- **子步骤的「完成 / 是否解锁」一律从工件信封 `state` 派生，绝不读 `project.state`：**
  - 理解是否已确认 → `GET /understanding` 的 `state === "confirmed"`。
  - 档案是否已确认 → `GET /characters` 的 `state === "confirmed"`。
  - 意图是否已保存（=已确认）→ `GET /intent` 返回 200（存在即已 confirmed）。
- **外层「幕步骤条」（[project-layout.tsx](../../frontend/app/routes/project-layout.tsx) 的 `isStageDone`）仍读 `project.state`**，`analysis` 在 `state>=intent_set` 时点亮。由于保存意图会把 state 推到 `intent_set`，外层「理解与档案」幕**会在意图保存后正确点亮**——无需改 [stages.ts](../../frontend/app/lib/stages.ts)。但**阶段内部**的三步进度必须用工件 state，不能用 `project.state`（否则前两步永不亮）。
- **`gates` 字段不可信：** `GET /projects/{id}` 后端不返回 `gates`，http 适配层把它填成全 `"empty"` 的默认值。**不要用 `project.gates` 判断子步骤状态**，一律用上面的工件 GET。

---

## 总体方案与不变量

- **资源契约层沿用既有模式：** 按 [client.ts](../../frontend/app/lib/api/client.ts) 现有 `ApiClient`（已含 `projects`/`source`）扩展三类资源 `understanding`/`characters`/`intent`，http 与 mock 双实现，经 `VITE_API_MODE` 切换。组件零分支地消费同一接口。
- **不引入任何新 npm 依赖：** 业务逻辑用原生 `fetch`、React Router v7 内置 `clientLoader`/`clientAction`（仓库 `ssr:false`，必须用 client 版）。UI 用 coss registry 生成的组件（第三方基座，非 npm 包），新装组件须在 README 与 PR 披露（见各 PR）。
- **信封形状归一化只在 http 层做：** 组件消费前端类型（`ArtifactEnvelope<UnderstandingData>` 等），不感知后端细节；`/direction` 返回的 `project` 在 http 层用既有 `normalizeProject` 归一化。mock 直接产出前端形状。
- **门控来自工件 state，不来自 `project.state`/`gates`**（见上「关键跨层缺口」）。
- **main 始终可运行：** 每个 PR 自身可 `pnpm build`/`typecheck`/`lint`/`format:check` 通过；功能需后端在跑才能手测（README 写清）。
- **信任能力对齐：** 本期落地 `non_visualizable`（`source_ref` 溯源）与 `narrative` 的**只读展示**，是 P4/P5 在理解层的体现；`flag`/`ai_inferred` 的可编辑消费在 M5+。

---

## 路由结构改造（单点变更，PR 2 落地）

把 `analysis` 从单页占位升级为**带子步骤导航的布局路由**，下挂三个子路由页（决策 2「子路由」）。

[routes.ts](../../frontend/app/routes.ts) 内，把现有这一行：

```text
route("analysis", "routes/project-analysis.tsx"),
```

改为：

```text
route("analysis", "routes/analysis-layout.tsx", [
  index("routes/analysis-understanding.tsx"),
  route("characters", "routes/analysis-characters.tsx"),
  route("intent", "routes/analysis-intent.tsx"),
]),
```

- **删除** [project-analysis.tsx](../../frontend/app/routes/project-analysis.tsx) 占位文件（其唯一引用是这条路由，删除后无悬挂引用）。
- 新增 4 个文件（全部在 `frontend/app/routes/`）：`analysis-layout.tsx`（子步骤布局 + 共享 loader + `Outlet`）、`analysis-understanding.tsx`、`analysis-characters.tsx`、`analysis-intent.tsx`。
- **子路由路径与语义：**
  - `/projects/:id/analysis`（index）→ 作品理解（第 1 步）。
  - `/projects/:id/analysis/characters` → 人物档案（第 2 步）。
  - `/projects/:id/analysis/intent` → 作者意图与方向（第 3 步）。
- 外层 [project-layout.tsx](../../frontend/app/routes/project-layout.tsx) 的幕导航链接 `stagePath(id,"analysis")` → `/projects/:id/analysis` → 命中 index = 理解页，无需改动 project-layout 或 stages.ts。

**`analysis-layout.tsx` 的职责（执行 Agent 照此实现，勿自行增删）：**

1. **`clientLoader`**：并行拉取并派生门控所需数据——
   - `api.projects.get(projectId)`（取标题等，可选）。
   - `api.source.get(projectId)`（取 `threshold.passed`，用于理解页的 ≥3 章前置提示）。
   - `api.understanding.get(projectId)`、`api.characters.get(projectId)`、`api.intent.get(projectId)`，**各自对 404 做 `catch → null`**（未生成属正常空态，不能让 loader 抛错）。建议封装一个「`getOrNull`」小工具：捕获 `ApiError && status===404` 返回 null，其余错误继续抛。
   - 返回 `{ project, threshold, understanding, characters, intent }`（其中三个工件可能为 null）。
2. **派生子步骤状态**（传给子步骤导航渲染）：
   - 理解：`status = understanding?.state ?? "empty"`（empty/draft/confirmed）；始终可进入，但「生成」按钮在 `threshold.passed===false` 时禁用并提示去导入补章。
   - 档案：`locked = understanding?.state !== "confirmed"`；`status = characters?.state ?? "empty"`。
   - 意图：`locked = characters?.state !== "confirmed"`（**前端施加的顺序约束**——后端 `PUT /intent` 本身不门控，但为贯彻 P1 流程，UI 把意图步骤锁在「档案已确认」之后；在计划与 PR 描述里注明这是前端约束、非后端强制）；`status = intent ? "confirmed" : "empty"`。
3. **子步骤导航条**：横向三步导航（理解 / 档案 / 意图），每步显示序号或「✓」（已确认）、当前态高亮、`locked` 的步骤渲染为禁用（不可点，带锁定提示）。视觉与 project-layout 顶部幕导航一致但层级更轻（次级）。用 `NavLink` + `cn`，禁用步骤用 `span`/`aria-disabled` 而非可点 `NavLink`。
4. 渲染 `<Outlet />`，并把 loader 数据通过 React Router 的 `useRouteLoaderData`（子页用布局 loader 数据）或各子页自身的 `clientLoader` 二选一。**本计划采用：布局 loader 负责门控派生与导航；每个子页另写自己的 `clientLoader` 拉取该步所需工件**（理解页拉 understanding+source、档案页拉 characters+understanding、意图页拉 intent+characters+project），保持子页自治、便于 `revalidate` 局部刷新。布局 loader 与子页 loader 会各自触发，RR 会并行执行，可接受。

> 子步骤之间跳转用 `stagePath` 同款 helper：可在 [stages.ts](../../frontend/app/lib/stages.ts) 新增 `analysisStepPath(projectId, step)`（`step ∈ "understanding"|"characters"|"intent"`，分别拼 `/analysis`、`/analysis/characters`、`/analysis/intent`），或在 layout 内局部定义。优先放进 stages.ts 复用。

---

## PR 拆分（5 个 PR，依次从 `main` 切分支）

> 分支名正则（[check-branch-name.sh](../../scripts/hooks/check-branch-name.sh)）：`<type>/<小写-数字-连字符-点>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore。
> commit 正则（[check-commit-msg.sh](../../scripts/hooks/check-commit-msg.sh)）：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**（不得含中文/全角标点）。
> pre-commit 跑 lint；pre-push 跑 `build` + 分支名校验。每个 PR 合并后 main 可运行。每个 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。

**依赖顺序：** PR1（客户端）→ PR2（路由骨架）→ PR3（理解）→ PR4（档案）→ PR5（意图与方向）。PR3/4/5 都依赖 PR1 的客户端与 PR2 的布局，三者之间也有数据前置（理解确认才解锁档案、档案确认才解锁意图），但**代码层面互不耦合**，可分别独立 build/verify。

---

### PR 1 — 新增 analysis 三类资源的 API 客户端（M2/M3 数据层，无 UI）

- **分支：** `feat/analysis-api-client`
- **一句话目标：** 按后端真实行为给 `ApiClient` 增加 `understanding`/`characters`/`intent` 三类资源（types + client 接口 + http 实现 + mock 实现），不接任何 UI。
- **改动文件：**
  - [types.ts](../../frontend/app/lib/api/types.ts)：新增类型（字段严格对齐上文「数据形状」）：
    - 通用：`SourceRef { chapter:number; paragraphs:number[] }`；`ArtifactState = "draft"|"confirmed"|"needs_recompute"`；泛型 `ArtifactEnvelope<T> { type:string; state:ArtifactState; version:string; parent_version:string|null; etag:string|null; updated_at:string; needs_recompute:boolean; data:T }`。
    - 理解：`Narrative { perspective:string; tense:string; unreliable:boolean }`；`NonVisualizableMark { source_ref:SourceRef; note:string }`；`UnderstandingData { logline; synopsis; themes:string[]; protagonist_goal; protagonist_fear; central_conflict; mood; style_fingerprint; narrative:Narrative; non_visualizable:NonVisualizableMark[]; strengths:string[]; difficulties:string[] }`。
    - 档案：`CharacterRole = "protagonist"|"supporting"|"mentioned"`；`CharacterRelation { to:string; type:string; change:string|null }`；`Character { id; name; role:CharacterRole; voice; desire; fear; arc:string|null; relations:CharacterRelation[]; hard_rules:string[] }`；`CharactersData { characters:Character[] }`。
    - 意图：复用既有 `AdaptationDirection`；`IntentConstraints { keep:string[]; no_delete:string[]; no_merge:string[]; must_keep_lines:string[]; mood_floor:string|null; allow_new_plot:boolean; allow_reorder:boolean; allow_new_ending:boolean; target_type:AdaptationDirection|null }`；`IntentConflict { code:string; message:string; fields:string[] }`；`DirectionResponse { direction:AdaptationDirection; project:Project }`；`IntentValidateResponse { conflicts:IntentConflict[] }`。
    - **MVP 方向子类型**（仅用于方向选择控件，避免选到 tv/film/stage 触发 422）：`MvpDirection = "faithful"|"cinematic"|"short_drama"`。
  - [client.ts](../../frontend/app/lib/api/client.ts)：`ApiClient` 增三类资源接口，并在 http/mock 两实现里补齐：
    - `UnderstandingApi`：`get(projectId): Promise<ArtifactEnvelope<UnderstandingData>>`、`generate(projectId): Promise<ArtifactEnvelope<UnderstandingData>>`、`update(projectId, data:UnderstandingData): Promise<ArtifactEnvelope<UnderstandingData>>`、`confirm(projectId): Promise<ArtifactEnvelope<UnderstandingData>>`。
    - `CharactersApi`：`get(projectId): Promise<ArtifactEnvelope<CharactersData>>`、`generate(projectId): Promise<ArtifactEnvelope<CharactersData>>`、`add(projectId, c:Character): Promise<ArtifactEnvelope<CharactersData>>`、`update(projectId, characterId:string, c:Character): Promise<ArtifactEnvelope<CharactersData>>`、`remove(projectId, characterId:string): Promise<void>`、`confirm(projectId): Promise<ArtifactEnvelope<CharactersData>>`。
    - `IntentApi`：`get(projectId): Promise<ArtifactEnvelope<IntentConstraints>>`、`save(projectId, data:IntentConstraints): Promise<ArtifactEnvelope<IntentConstraints>>`（= `PUT /intent`，保存即确认）、`setDirection(projectId, direction:MvpDirection): Promise<DirectionResponse>`、`validate(projectId): Promise<IntentValidateResponse>`。
  - [http.ts](../../frontend/app/lib/api/http.ts)：实现上述方法，路径按前缀拼接，**冒号动作段（`:generate`/`:confirm`/`:validate`）按字面拼接，勿 URL-encode 冒号**。要点：
    - `understanding.generate`/`characters.generate` 是 `POST` 无 body（202 也走既有 `request()`，它对 2xx 一律解析 json）。
    - `understanding.update` = `PUT /projects/{id}/understanding`，body 为 `UnderstandingData` 全量。`characters.update` = `PUT .../characters/{cid}`，body 为 `Character` 全量。
    - `characters.remove` = `DELETE`（204，既有 `request()` 已处理 204→undefined）。
    - `intent.save` = `PUT /projects/{id}/intent`；`intent.setDirection` = `PUT /projects/{id}/intent/direction`，body `{direction}`，**返回 `{direction, project}`，需对 `project` 调 `normalizeProject` 后返回 `{direction, project: normalized}`**；`intent.validate` = `POST .../intent:validate` 无 body。
    - **不要发 `If-Match`**（后端不校验，发了无意义）。
  - [mock.ts](../../frontend/app/lib/api/mock.ts)：加三类资源的内存实现，复刻**关键语义**供离线 UI 开发（mock 不必逐字复刻后端推断算法，但 state 流转、门控、增删改语义必须一致）：
    - 用 `Map<projectId, ArtifactEnvelope<...>>` 分别存 understanding/characters/intent。`generate` 产出一份合理的 draft 假数据（理解给齐所有必填字段 + 至少一条 `non_visualizable` + 一个 `narrative`；档案给 2–3 个不同 `role` 的人物含 relations/hard_rules）。
    - `understanding.update`/`confirm`、`characters.add/update/remove`、`characters.confirm` 按真实语义流转 `state`（update/add/remove → draft；confirm → confirmed），`parent_version` 串起来，`version` 用 mock 计数器生成 `v_mockN`。
    - **门控复刻：** `characters.generate` 在 understanding 非 confirmed 时抛 `ApiError(409, {code:"state_gate_blocked", ...})`；`understanding.generate` 在 mock source <3 章时抛 `ApiError(409,{code:"chapter_threshold_unmet",...})`（沿用 mock source 的 threshold）。
    - `intent.save` 存为 confirmed；`intent.setDirection` 把方向写进 mock 项目的 `meta.adaptation_direction` 并返回 `{direction, project}`；`intent.validate` 用与后端**相同的确定性规则**（上文「后端已知冲突规则」四条）算 `conflicts`，无意图则抛 404。
    - mock 可在内存里把 `style_fingerprint` 同步进 mock 项目 `meta`（与后端行为一致）。
- **不在本 PR：** 任何路由/页面/组件改动（纯扩客户端，app 行为不变）。
- **建议 commits：**
  1. `feat(frontend): add understanding characters intent api types`（types.ts）
  2. `feat(frontend): add analysis resources to api client and http`（client.ts + http.ts）
  3. `feat(frontend): add analysis stage mock adapters`（mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint`/`format:check` 全过；app 运行行为与本 PR 前一致（无新 UI）。mock 模式下浏览器控制台手调 `api.understanding.generate(...)`、`api.characters.generate(...)`、`api.intent.validate(...)` 形状正确、门控/冲突语义正确。

---

### PR 2 — analysis 阶段路由骨架与子步骤导航（布局，子页占位）

- **分支：** `feat/analysis-stage-scaffold`
- **一句话目标：** 按「路由结构改造」一节把 `analysis` 升级为带子步骤导航的布局路由，三个子页先以**轻量占位**渲染（读取 loader 派生的工件 state 显示「未生成 / 草稿 / 已确认」与锁定态），打通导航与门控，不含生成/编辑表单。
- **先安装 coss 组件：** 本 PR 仅用既有已装组件（`card`/`alert`/`button`/`separator`/`badge`/`empty`），**无需新装**。若子步骤导航要用图标，复用 `lucide-react`。
- **改动文件：**
  - [routes.ts](../../frontend/app/routes.ts)：按上文改为 layout + 三子路由；删除 `project-analysis.tsx` 文件。
  - 新增 [analysis-layout.tsx](../../frontend/app/routes/analysis-layout.tsx)：实现「路由结构改造」中 layout 的 `clientLoader` + 子步骤导航条 + `Outlet`。门控派生严格按「关键跨层缺口」结论（工件 state，不读 project.state/gates）。
  - 新增三个子页占位 [analysis-understanding.tsx](../../frontend/app/routes/analysis-understanding.tsx) / [analysis-characters.tsx](../../frontend/app/routes/analysis-characters.tsx) / [analysis-intent.tsx](../../frontend/app/routes/analysis-intent.tsx)：各自 `clientLoader` 拉本步工件（404→null），渲染阶段标题/说明（复用 i18n `pages.analysis.*` 及新增子步骤文案）+ 一个 `Card` 显示「当前状态：未生成 / 草稿 / 已确认」+ 锁定步骤显示「请先完成上一步」提示。**占位不含任何 generate/edit 调用**（留给 PR3/4/5）。
  - [stages.ts](../../frontend/app/lib/stages.ts)：新增 `analysisStepPath(projectId, step)` helper（三步路径拼接）。
  - i18n 两 locale [zh-CN/common.json](../../frontend/app/i18n/locales/zh-CN/common.json) 与 [en/common.json](../../frontend/app/i18n/locales/en/common.json)：新增 `analysis` 命名空间骨架键（两 locale **键完全一致**）：至少 `analysis.steps.understanding`/`analysis.steps.characters`/`analysis.steps.intent`（子步骤名）、`analysis.locked`（「请先完成上一步」）、`analysis.status.empty`/`draft`/`confirmed`、`analysis.stepOf`（如「第 {{current}}/{{total}} 步」）。后续 PR3/4/5 再往 `analysis.*` 下补各自字段文案。
- **不在本 PR：** 生成/编辑/确认任何工件；表单与数组编辑器。
- **建议 commits：**
  1. `feat(frontend): nest analysis sub-routes with step layout`（routes.ts + analysis-layout.tsx + 删 project-analysis.tsx + stages.ts helper）
  2. `feat(frontend): add analysis scaffold sub-pages and gating`（三个占位子页 + loader 404 兜底）
  3. `feat(frontend): add analysis stage i18n scaffold keys`（两 locale）
- **验收：** 后端在跑、且某项目已导入 ≥3 章：进入 `/projects/:id/analysis` 命中理解占位页，子步骤导航显示三步；理解步可进入，档案/意图步因未确认而锁定（不可点、有提示）；手动在控制台或后续步骤确认理解后 `revalidate`，档案步解锁。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 3 — 作品理解子页（生成 / 编辑 / 确认 + 信任信号展示）

- **分支：** `feat/understanding-stage`
- **一句话目标：** 把 [analysis-understanding.tsx](../../frontend/app/routes/analysis-understanding.tsx) 从占位升级为可用页：一键生成作品理解、逐字段编辑（标量全编 + themes/strengths/difficulties 数组增删）、只读展示 `narrative` 与 `non_visualizable` 溯源、确认进入档案步。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/input-group`（字符串数组编辑器要用）。其余（`field`/`input`/`textarea`/`card`/`badge`/`alert`/`button`/`separator`/`alert-dialog`/`toast`/`collapsible`）PR1/导入期已装，复用。装完 `git diff package.json` 确认无新增 npm 依赖。
- **新增可复用组件 [string-list-editor.tsx](../../frontend/app/components/string-list-editor.tsx)（本 PR 引入，PR4/PR5 复用）：**
  - **用途：** 编辑一个 `string[]` 字段（themes/strengths/difficulties/hard_rules/keep/no_delete/no_merge/must_keep_lines）。
  - **Props（写死契约）：** `label:string`、`values:string[]`、`onChange:(next:string[])=>void`、可选 `placeholder`、可选 `description`、可选 `inputType`（默认 `"text"`）。
  - **结构（coss 映射见组件表）：** `Field`>`FieldLabel`（+ 可选 `FieldDescription`）；下方一个 `InputGroup`：`InputGroupInput`（受控本地输入态，回车或点「添加」addon 追加非空去重项）+ `InputGroupAddon`（在 input **之后**，放一个 `Button size="icon" variant="ghost" aria-label`「添加」+ `PlusIcon`）；再下方把 `values` 渲染为一排 `Badge variant="secondary"`，每个 Badge 末尾带一个小「×」`Button`（`aria-label`「删除」）调用 `onChange(values.filter(...))`。
  - **行为：** 追加时 trim、忽略空串、去重（已存在则不加）。删除按值或按下标均可（按下标更稳，允许重复值时也安全）。本组件**纯受控**，不自持 `values` 状态，只持「当前输入框文本」局部态。
- **改动文件：**
  - [analysis-understanding.tsx](../../frontend/app/routes/analysis-understanding.tsx)：
    - `clientLoader`：`api.understanding.get`（404→null）+ `api.source.get`（取 `threshold.passed`）。
    - **空态（无理解工件）：** 渲染 `Empty` + 「生成作品理解」`Button`（`loading`）。`threshold.passed===false` 时禁用按钮并用 `Alert variant="warning"` 提示「需先在导入阶段补足 3 章」，附 `Link` 回 `/projects/:id/import`。点击生成 → `api.understanding.generate` → 成功 toast + `revalidate`。生成是长任务，按钮 `loading` 期间禁用；失败 toast 展示 `ApiError.message`（如 409 门槛）。
    - **已有工件：** 进入「编辑态」表单（本地 React state，以 `data` 为初值；非 react-router Form 提交，用受控组件 + 「保存」按钮调 `api.understanding.update`）：
      - 标量字段用 `Field`+`Input`：`logline`、`protagonist_goal`、`protagonist_fear`、`central_conflict`、`mood`、`style_fingerprint`。`synopsis` 用 `Field`+`Textarea size="lg"`。
      - 数组字段 `themes`/`strengths`/`difficulties` 用 `StringListEditor`。
      - **只读信任区**（不可编辑）：`narrative`（perspective/tense/unreliable 用 `Badge` 展示）；`non_visualizable` 用 `Card`/列表展示每条 `note` + `source_ref`（如「第 2 章 · 第 2 段」），可用 `Collapsible` 折叠；区域顶部放一句说明「以下为系统从原文识别的信任信号（视角/时态、需外化的心理段落），仅供参考，不可在此编辑」。复用 [trust-chips.tsx](../../frontend/app/components/trust-chips.tsx) 的视觉风格但此处是具体数据，建议单独渲染。
      - **保存**：把当前表单态合并回完整 `UnderstandingData`（**保留 loader 里原样的 `narrative`/`non_visualizable`**，只覆盖可编辑标量与三个数组），调 `api.understanding.update` → 成功 toast + `revalidate`。**严禁多传信封字段**（`extra="forbid"`）。
      - **状态与确认**：页面顶部用 `Badge`/`Alert` 显示当前 `state`（草稿/已确认）。
        - 未确认（draft）：显示「确认作品理解」`Button` → `api.understanding.confirm` → 成功后 toast + `revalidate`，并提供「进入人物档案」CTA（`Link` → `analysisStepPath(id,"characters")`）。
        - 已确认（confirmed）后若作者再次编辑保存 → 后端回 draft；UI 据返回 state 重新显示「需重新确认」。用 `Alert variant="info"` 提示「编辑后需重新确认才能进入下一步」。
        - 「重新生成」入口：已有工件时提供「重新生成」按钮，但因会覆盖当前内容（且若已确认会回到 draft），用 `AlertDialog` 二次确认后再调 `generate`。
  - i18n 两 locale：在 `analysis.understanding.*` 下补齐所有字段标签、按钮、提示文案、`narrative`/`non_visualizable` 说明、`source_ref` 展示模板（如 `analysis.understanding.sourceRef` 含 `{{chapter}}`/`{{paragraphs}}`）。两 locale 键一致。
- **建议 commits：**
  1. `chore(frontend): add coss input-group for analysis stage`（input-group + README 组件清单追加）
  2. `feat(frontend): add reusable string list editor`（string-list-editor.tsx）
  3. `feat(frontend): add understanding i18n keys`（两 locale）
  4. `feat(frontend): generate and edit work understanding`（生成 + 标量/数组编辑 + 保存）
  5. `feat(frontend): show narrative and non-visualizable trust signals`（只读信任区）
  6. `feat(frontend): confirm understanding and gate next step`（确认 + CTA + 重生成确认）
- **验收：** 后端在跑、项目已导入 ≥3 章：进理解页空态 → 生成 → 出现各字段（logline 等非空）→ 编辑某标量与 themes 增删 → 保存后刷新持久 → 只读区显示视角/时态与至少一条 `non_visualizable`（含 source_ref）→ 确认后状态变「已确认」且「进入人物档案」可点；再次编辑保存后回到「需重新确认」。<3 章项目进入时生成按钮禁用并提示去导入。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 4 — 人物档案子页（生成 / 增删改 / 确认 + 角色分类 + 关系编辑）

- **分支：** `feat/characters-stage`
- **一句话目标：** 把 [analysis-characters.tsx](../../frontend/app/routes/analysis-characters.tsx) 从占位升级为可用页：在理解已确认后生成人物档案、按角色分类卡片展示、编辑/新增/删除人物（含 voice/hard_rules/relations）、确认进入意图步。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/select`（关系编辑器的「关联人物」下拉、角色单选用）。`input-group`（PR3 已装，关系/hard_rules 复用）、`dialog`/`menu`/`alert-dialog`/`card`/`badge`/`field`/`input`/`textarea`/`button`/`empty`/`alert`/`toast`（导入期/PR3 已装）复用。若 PR4 先于 PR3 合并，则本 PR 需补装 `input-group`。装完 `git diff package.json` 确认依赖。
- **改动文件：**
  - [analysis-characters.tsx](../../frontend/app/routes/analysis-characters.tsx)：
    - `clientLoader`：`api.characters.get`（404→null）+ `api.understanding.get`（取其 state，用于门控提示）。
    - **门控空态**：若 understanding 未 confirmed（理论上 layout 已锁定此步，但子页要自兜底）→ `Alert variant="warning"`「请先确认作品理解」+ `Link` 回理解步，不展示生成按钮。
    - **无档案且理解已确认**：`Empty` + 「生成人物档案」`Button`（`loading`）→ `api.characters.generate`；若后端因门控返回 409 `state_gate_blocked` 则 toast 提示并引导回理解步。
    - **已有档案**：按 `role` 分组渲染（主角 / 配角 / 仅提及三组，每组一个小标题 + 该组人物卡片）。每个人物一个 `Card`：
      - `CardHeader`：`name` + `role` 用 `Badge`（三种 role 不同 `variant`/语义色）+ 行操作 `Menu`（`MenuTrigger` 为 ghost icon 按钮）含「编辑 / 删除」。
      - `CardPanel`：展示 `voice`/`desire`/`fear`/`arc` + `hard_rules`（`Badge` 列表）+ `relations`（每条展示「→ 关联人物 name（type）：change」）。
      - 删除走 `AlertDialog` 二次确认 → `api.characters.remove` → 成功 toast + `revalidate`。**提示：删除/编辑会让档案回到 draft，需重新确认**（见后端坑 1）。
    - **新增人物**：列表上方「新增人物」`Button` → `Dialog`（编辑态本地 state）：`Field`+`Input`（name）、角色用 **`Select`**（三枚举项）、`Field`+`Input`（voice/desire/fear/arc）、`hard_rules` 用 `StringListEditor`、`relations` 用「关系编辑器」（见下）。确认时**本地派生 `id`**（name → ASCII slug，去重，见后端坑 3），组装完整 `Character` 调 `api.characters.add`；id 冲突的 409 兜底为再加后缀重试或提示。成功 toast + `revalidate`。
    - **编辑人物**：`Menu`「编辑」→ `Dialog`，以该人物为初值，同新增表单（但 `id` 固定不可改，name 可改）。保存调 `api.characters.update(projectId, character.id, fullCharacter)`。**全量 `Character`、严禁多字段**（`extra="forbid"`）。
    - **关系编辑器（内联子组件，可放本文件内或 `app/components/relation-editor.tsx`）：** 编辑 `CharacterRelation[]`。每行：`Select`（关联人物，items = 当前档案里**除自己外**的其他人物，value=`id`、label=`name`）+ `Input`（type，如「父女」）+ `Input`（change，可空）+ 删除行按钮；底部「添加关系」按钮追加空行。**关联人物列表来自当前编辑会话已知的人物集合**（新增人物尚未落库时，至少能选已存在的人物；自己不可选自己）。纯受控，`onChange(next:CharacterRelation[])`。
    - **状态与确认**：顶部 `Badge`/`Alert` 显示 `state`。draft 时显示「确认人物档案」`Button` → `api.characters.confirm` → 成功后 CTA「进入作者意图」（`Link` → `analysisStepPath(id,"intent")`）。已确认后任一增删改回 draft，`Alert variant="info"` 提示需重新确认。
    - **重新生成**：同理解页，`AlertDialog` 二次确认（会覆盖现有全部人物）后再调 `generate`。
  - i18n 两 locale：`analysis.characters.*` 下补角色名（protagonist/supporting/mentioned 的本地化）、字段标签、关系编辑器文案、新增/编辑/删除对话框文案、确认与 CTA、需重新确认提示、id 冲突提示。两 locale 键一致。
- **建议 commits：**
  1. `chore(frontend): add coss select for character profiles`（select + README 组件清单追加）
  2. `feat(frontend): add character i18n keys`（两 locale）
  3. `feat(frontend): generate and list character profiles by role`（生成 + 分组卡片 + 角色 Badge）
  4. `feat(frontend): add and edit character profiles`（Dialog 表单 + Select 角色 + StringListEditor + 关系编辑器 + 本地 id 派生）
  5. `feat(frontend): delete characters and confirm profiles`（AlertDialog 删除 + 确认 + CTA + 重生成确认）
- **验收：** 理解已确认的项目：进档案页 → 生成 → 按角色分组显示人物（含 voice/hard_rules/relations）→ 新增一个人物（name 派生 id、选 role、加 hard_rules、加一条指向已有人物的关系）→ 编辑某人物 hard_rules → 删除某人物（二次确认）→ 每次增删改后档案回 draft 且需重新确认 → 确认后「进入作者意图」可点。理解未确认时进入此页显示门控提示。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 5 — 作者意图与改编方向子页（意图约束 + 方向选择 + 冲突校验）

- **分支：** `feat/intent-direction-stage`
- **一句话目标：** 把 [analysis-intent.tsx](../../frontend/app/routes/analysis-intent.tsx) 从占位升级为可用页：填写并保存（=确认）作者意图约束、选择改编方向、触发确定性冲突校验展示冲突清单、完成后进入 `/outline`。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/switch @coss/radio-group`（三个布尔开关用 `switch`；三选一方向用 `radio-group`）。`input-group`（PR3）、`field`/`input`/`card`/`badge`/`alert`/`button`/`separator`/`toast`（已装）复用。装完 `git diff package.json` 确认无新增 npm 依赖。
- **改动文件：**
  - [analysis-intent.tsx](../../frontend/app/routes/analysis-intent.tsx)：
    - `clientLoader`：`api.intent.get`（404→null）+ `api.characters.get`（取 state 门控）+ `api.projects.get`（取 `meta.adaptation_direction` 当前方向）。
    - **门控**：characters 未 confirmed → `Alert variant="warning"`「请先确认人物档案」+ `Link` 回档案步，不展示表单（前端施加的顺序约束，PR 描述注明非后端强制）。
    - **意图表单**（本地受控 state，初值取 intent?.data 或全空默认）：
      - 字符串数组 `keep`/`no_delete`/`no_merge`/`must_keep_lines` 各用一个 `StringListEditor`（PR3 引入）。
      - `mood_floor` 用 `Field`+`Input`（可空）。
      - `allow_new_plot`/`allow_reorder`/`allow_new_ending` 各用一个 **`Switch`**（带 `Label` + 说明文案，按 switch.md 的「带描述」结构：左标题+说明、右 `Switch`，用 `id`/`htmlFor` 关联）。
      - **不单独提供 `target_type` 编辑项**（见 M3 坑 3）：保存意图时把 `target_type` 设为当前所选方向（`faithful|cinematic|short_drama`）或在尚未选方向时设 null。
      - 「保存意图」`Button` → `api.intent.save(projectId, intent)`（**保存即确认**）→ 成功 toast + `revalidate`。
    - **改编方向选择**（独立区块）：用 **`RadioGroup`**（三项卡片式：忠实改编 / 影视化增强 / 短剧模式，各带一句说明）。`value` 来自 `project.meta.adaptation_direction`（可能为 null → 不选中）。`onValueChange` → `api.intent.setDirection(projectId, value)` → 成功后用返回的 `{direction, project}` 更新本地方向态 + toast。**只允许三个 MVP 值**（`MvpDirection`），控件本身就只渲染这三项，天然规避 422。
    - **冲突校验**：一个「检查意图与方向冲突」`Button`：
      - **可用前提**：意图已保存（`intent` 非 null）**且**已选方向。任一不满足则禁用并提示「请先保存意图并选择方向」。
      - 点击 → `api.intent.validate(projectId)` → 把 `conflicts` 存入本地 state 展示。
      - **冲突展示**：`conflicts` 为空 → `Alert variant="success"`「未发现冲突」；非空 → 每条一个 `Alert variant="warning"`（或一个列表），按 `code` 映射本地化文案（四个已知 code，见 M3 坑 6），未知 code 回退 `message`；标注「冲突不阻塞，是否调整由你决定」。
      - 建议：保存意图或切换方向后**自动触发一次** `validate`（若前提满足），让作者即时看到冲突；亦保留手动按钮。
    - **完成与 CTA**：意图已保存后（无论是否有冲突），底部 `Alert variant="success"` + 「进入分场大纲」`Button`（`Link` → `stagePath(id,"outline")`）。提示：保存意图会把项目推进到 `intent_set`，外层「理解与档案」幕随之点亮（见跨层缺口说明）。`/outline` 当前可能仍是占位页，可正常跳转。
  - i18n 两 locale：`analysis.intent.*` 下补意图各字段标签与说明、三个 switch 的标题/说明、三个方向的名称与说明、四个冲突 code 的本地化文案 + 未知回退、按钮与 CTA、门控与「保存即确认」提示。两 locale 键一致。
- **建议 commits：**
  1. `chore(frontend): add coss switch and radio-group for intent stage`（switch + radio-group + README 组件清单追加）
  2. `feat(frontend): add intent and direction i18n keys`（两 locale，含冲突 code 文案）
  3. `feat(frontend): edit and save author intent constraints`（StringListEditor + Switch 表单 + 保存即确认）
  4. `feat(frontend): select adaptation direction`（RadioGroup + setDirection + 返回项目归一化）
  5. `feat(frontend): validate intent direction conflicts and gate outline`（validate + 冲突展示 + CTA）
- **验收：** 档案已确认的项目：进意图页 → 填 keep/no_delete 等数组、切三个开关、填 mood_floor → 保存意图（状态变已保存/已确认）→ 选「忠实改编」方向 → 点检查冲突，若同时开了「允许调整结局/新增桥段/调序」则出现对应 `faithful_vs_*` 冲突警告（不阻塞）；改选「短剧模式」且未开调序则出现 `short_drama_vs_no_reorder`；无冲突时显示成功 → 「进入分场大纲」可点跳 `/outline`。档案未确认时进入显示门控提示。`build`/`typecheck`/`lint`/`format:check` 过。

---

## coss UI 组件映射（每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`（见 [components.json](../../frontend/components.json) 的 `registries["@coss"]`）。安装命令统一 `pnpm dlx shadcn@latest add @coss/<name>`。安装后从 `~/components/ui/<name>` 导入**已样式化导出**（如 `Switch`/`RadioGroup`/`Select`），仅在需要自定义组合时才用 `*Primitive` 导出。
> coss 组件文件由 registry 生成，属第三方基座（非原创业务），**每个引入新组件的 PR 必须在 README「依赖与来源」coss 段追加所装组件清单，并在 PR 描述据实披露**。安装后务必 `git diff package.json` 检查是否带入新 npm 依赖（预期不会，`@base-ui/react` 已在依赖中；若有则一并披露）。

| 界面元素 | coss 组件（安装名） | 关键 composition / 注意点 | 参考 particle | 所属 PR |
| --- | --- | --- | --- | --- |
| 子步骤导航条（理解/档案/意图） | 无需新组件（`NavLink`+`cn`+`lucide`） | 次级导航，禁用步骤用 `span aria-disabled` 而非 `NavLink`；已确认步显示 `CheckIcon` | — | PR2 |
| 阶段/子步骤状态显示 | `alert` / `badge`（已装） | 「未生成/草稿/已确认」用 `Badge`；门控/提示用 `Alert variant` | p-badge-3 / p-alert-4 | PR2+ |
| 空态（未生成工件） | `empty`（已装） | `Empty`>`EmptyHeader`(`EmptyMedia variant="icon"`)+`EmptyTitle`/`EmptyDescription`，内放「生成」按钮 | p-empty-1 | PR3/4 |
| 生成/重生成/确认/保存 按钮 | `button`（已装） | `type="button"` + `loading`；长任务期间禁用。**这些是命令式调用（非 react-router Form 提交）** | — | PR3/4/5 |
| 标量文本字段（logline/voice/mood_floor 等） | `field` + `input`（已装） | `Field`>`FieldLabel`+`Input type="text"`。**始终显式 `type`** | p-field-1 / p-input-6 | PR3/4/5 |
| 多行文本（synopsis） | `textarea`+`field`（已装） | `Field`>`FieldLabel`+`Textarea size="lg"`。Textarea 已含 Field 控件语义，勿叠 `FieldControl render` | p-textarea-5 | PR3 |
| 字符串数组编辑（themes/strengths/hard_rules/keep/...） | `input-group` + `badge` + `button`（input-group 新装于 PR3） | 封装为可复用 `StringListEditor`：`Field`>`InputGroup`(`InputGroupInput`+ 其后 `InputGroupAddon` 内「添加」icon 按钮) + 下方 `Badge` 列表带「×」删除。**Addon 必须在 Input 之后**（DOM 顺序不变量） | p-input-group-7 / p-input-group-1 | PR3（PR4/5 复用） |
| 角色分类显示（主角/配角/仅提及） | `badge`（已装） | 三种 role 用不同 `variant`/语义色的 `Badge`；分组小标题用纯文本 | p-badge-3 | PR4 |
| 人物卡片 | `card`（已装） | 每人一个 `Card`：`CardHeader`(name+role Badge+操作 Menu)/`CardPanel`(voice/欲望/恐惧/弧光/hard_rules/relations) | p-card-1 | PR4 |
| 角色单选（新增/编辑人物时） | `select`（PR4 新装） | `Select items=[3 枚举]`>`SelectTrigger`>`SelectValue`+`SelectPopup`>`SelectItem`。items-first 模式，避免 SSR 不匹配 | p-select-1 / p-select-23 | PR4 |
| 关系编辑器「关联人物」下拉 | `select`（PR4 新装） | items=其他人物（value=`id`、label=`name`，排除自己）；每行 + type/change `Input` + 删除按钮；底部「添加关系」 | p-select-10 | PR4 |
| 行操作菜单（编辑/删除人物） | `menu`（已装） | `Menu`>`MenuTrigger render={<Button size="icon" variant="ghost"/>}`+`MenuItem`；删除项跳 `AlertDialog` | p-menu-1 | PR4 |
| 新增/编辑人物弹窗 | `dialog`（已装） | `Dialog`>`DialogPopup`>`DialogHeader`(在 form 外)+`DialogPanel`(表单，长内容在此滚动)+`DialogFooter`(确认/取消)。如内嵌 react-router Form 则 `<Form className="contents">` 只包 panel+footer；本页表单为受控本地态，用普通按钮提交即可 | p-dialog-1 / p-dialog-5 | PR4 |
| 删除人物 / 覆盖式重生成 二次确认 | `alert-dialog`（已装） | **破坏性操作用 AlertDialog（非 Dialog）**：footer 两个 `AlertDialogClose`（取消 ghost / 确认 destructive） | p-alert-dialog-1 | PR3/4 |
| 布尔开关（allow_new_plot/reorder/new_ending） | `switch`（PR5 新装） | 「带描述」结构：左 `Label htmlFor`+说明 `<p>`、右 `Switch id`。**用 Switch 而非 Checkbox**（这是偏好开关，非表单同意项） | p-switch-3 / p-switch-5 | PR5 |
| 改编方向三选一 | `radio-group`（PR5 新装） | `RadioGroup value onValueChange`>每项 `Label`>`Radio value`+标题/说明（卡片式）。**3 个互斥短选项用 RadioGroup（而非 Select）**；只渲染 faithful/cinematic/short_drama 三项，天然规避 422 | p-radio-group-3 / p-radio-group-4 | PR5 |
| 只读信任信号（narrative/non_visualizable） | `card`/`badge`/`collapsible`（已装） | `narrative` 三项用 `Badge`；`non_visualizable` 用列表/`Card` 展示 note+source_ref，可 `Collapsible` 折叠。**不可编辑**，区域顶部说明其来源 | p-card-1 / p-collapsible-1 | PR3 |
| 冲突清单 | `alert`（已装） | 无冲突 `Alert variant="success"`；每条冲突 `Alert variant="warning"`，按 code 本地化，标注「不阻塞」 | p-alert-6 / p-alert-5 | PR5 |
| 操作成功/失败反馈 | `toast`（已装） | `toastManager.add({title,description,type})`；root 已接 `ToastProvider`+`AnchoredToastProvider`（M0/M1 期完成），直接用 | p-toast-2 | PR3/4/5 |

**安装清单汇总：**
- **PR1/PR2：** 不装任何 coss 组件。
- **PR3 安装：** `input-group`。
- **PR4 安装：** `select`。（`input-group` 若 PR3 已装则复用；否则本 PR 补装。）
- **PR5 安装：** `switch`、`radio-group`。
- 其余（`field`/`input`/`textarea`/`card`/`badge`/`alert`/`button`/`separator`/`empty`/`collapsible`/`menu`/`dialog`/`alert-dialog`/`toast`/`label`）均在导入阶段已装，直接复用。

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **门控只看工件 state，不看 `project.state`/`project.gates`。** 三步解锁/完成判定一律用 `GET /understanding|/characters|/intent` 的 `state`/存在性。`project.state` 在 M2/M3 几乎不前进（只有保存意图会跳 `intent_set`），`gates` 是 http 层填的假默认值（见「关键跨层缺口」）。
2. **所有写操作让工件回 `draft`（意图除外）。** 理解 `PUT`、档案 `add/update/remove` 都把 state 置回 draft；确认后再编辑需**重新确认**才解锁下游。意图 `PUT` 直接是 confirmed、无独立 confirm。UI 必须如实反映这些 state 流转，并在「已确认后又编辑」时提示重新确认。
3. **`extra="forbid"` 全量回传：** 理解 `UnderstandingData`、人物 `Character`、意图 `IntentConstraints` 三个模型都禁止多字段。编辑保存时以 loader 原始 `data` 为基底浅拷贝改字段，**绝不**把信封字段（`version`/`state`/`updated_at`/`type`/`parent_version`/`etag`）混进 `data`。理解的 `narrative`/`non_visualizable` 即使只读，PUT 时也要**原样回传**（不能丢，否则必填 `narrative` 缺失 422）。
4. **冒号动作段按字面拼接**（`:generate`/`:confirm`/`:validate`），不要 URL-encode 成 `%3A`。
5. **方向接口特例：** `PUT /intent/direction` 返回 `{direction, project}` 非信封；http 层对 `project` 调 `normalizeProject`。方向值只允许 `faithful|cinematic|short_drama`（控件只渲染这三项）。方向存 `project.meta.adaptation_direction`，与意图 `target_type` 是两回事，冲突校验只认前者。
6. **冲突校验前置：** `:validate` 需意图已存在（否则 404）+ 方向已设（否则空冲突）。按钮在前提不满足时禁用并提示。前端**不自己计算冲突**，只展示后端返回的 `conflicts`，按 `code` 本地化、未知 code 回退 `message`。
7. **新增人物 id 前端派生：** name→ASCII slug（小写、非字母数字转 `_`、去首尾 `_`、空则 `character`），与现有 id 冲突则加 `-2`/`-3` 去重。后端不自动生成 id。
8. **404 = 空态而非错误：** loader 里对三类工件 `GET` 的 404 一律 `catch→null`（用 `ApiError && status===404` 判定），渲染空态；其余错误继续抛给 RR 错误边界或 toast。
9. **不发 `If-Match`、不依赖乐观锁：** 后端 `etag` 恒 null、不校验版本，发了无意义。
10. **生成是长任务：** `:generate`/`:confirm` 期间按钮 `loading` 且禁用，避免重复提交；失败 toast 展示 `ApiError.message`（含 409 门槛/门控的可读文案）。本期不接 SSR/Job 轮询（后端 `:generate` 同步返回 202 + 工件，无需订阅 events_url）。
11. **i18n 两 locale 同步：** 每个新增键在 `zh-CN` 与 `en` **完全一致**；插值占位（`{{n}}`/`{{chapter}}` 等）两边一致。新增统一挂在 `analysis.*` 命名空间下，避免与既有 `import.*`/`pages.*` 冲突。
12. **coss 用法红线**（照 coss skill，与 M0/M1 计划一致）：① 安装名 `@coss/<name>`，导入 `~/components/ui/<name>` 已样式化导出优先于 `*Primitive`。② trigger/popup 组合不跨组件混用（Dialog/AlertDialog/Menu/Select/RadioGroup 各按其文档层级）。③ `Input` 必显式 `type`；`Textarea` 直接放进 `Field`，勿叠 `FieldControl render`。④ `InputGroupAddon` 必须在 `InputGroupInput` **之后**（焦点行为不变量）。⑤ `Select` 用 items-first 模式、`SelectValue` 放进 `SelectTrigger`。⑥ `Switch` 用于偏好开关、`RadioGroup` 用于互斥单选、`Checkbox` 用于表单同意项——**不要混用**。⑦ 图标按钮/无可见标签控件补 `aria-label`；`Alert` 语义图标不要 `aria-hidden`。⑧ 破坏性确认（删除/覆盖式重生成）用 `AlertDialog`，普通编辑/新增弹窗用 `Dialog`。⑨ Toast 是 Base UI（root 已接 provider），直接 `toastManager.add`。

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- **`project.state` 在 M2/M3 不正常前进**：因导入未置 `imported`，理解/档案确认都不推进 state；只有保存意图（经 characters-confirmed 分支）会跳 `intent_set`。→ 前端门控改用工件 state。
- **`gates` 字段后端不返回**，http 层填假默认值，不可用于判断子步骤状态。
- **`etag` 恒 null、不校验 `If-Match`**（乐观锁未实现）。
- **理解 `non_visualizable`/`narrative` 为关键词启发式推断**，可能不完美；本期只读展示，不做编辑/纠错入口。
- **意图无独立 `:confirm`、方向独立于 `target_type`、`:validate` 需前置**：属契约与 api.md 描述的差异，已在「后端现状核对·M3」逐条标注。
- **生成为同步 202（非真异步 Job）**：后端 `:generate` 直接返回工件，无 `job`/SSE；前端本期不接进度流。

> 这些只标注、不修改后端。若后端后续补齐 state 前进、`gates`、乐观锁或异步 Job，前端可据此简化门控/增加进度反馈，属后续小改。

---

## 验证方式（端到端）

1. **起后端：** 在 `backend/` 按其工具启动 dev 服务（[dev_server.py](../../backend/scripts/dev_server.py)，监听 `:8000`）。
2. **起前端：** 仓库根 `pnpm install`（无新 npm 依赖）→ `pnpm dev`（默认 http，经 Vite 代理打 `:8000`）。
3. **冒烟（按 PR 累积）：**
   - PR1：`typecheck`/`build` 过；mock 模式控制台手调三类资源方法，形状/门控/冲突语义正确。
   - PR2：导入 ≥3 章的项目进 `/analysis`，三步导航出现，理解步可进、档案/意图步锁定。
   - PR3：理解空态→生成→编辑标量与 themes 增删→保存持久→只读区显示 narrative + 至少一条 non_visualizable→确认→「进入人物档案」可点；<3 章项目生成禁用并引导去导入。
   - PR4：理解确认后→生成档案→按角色分组→新增/编辑/删除人物（含关系/hard_rules）→每次增删改回 draft 需重新确认→确认→「进入作者意图」可点。
   - PR5：档案确认后→填意图+切开关→保存（即确认）→选方向→检查冲突（构造 faithful+allow_new_ending 看到 `faithful_vs_new_ending`；short_drama+不调序看到 `short_drama_vs_no_reorder`）→无冲突显示成功→「进入分场大纲」跳 `/outline`。
   - 离线：任一 PR 后 `VITE_API_MODE=mock pnpm dev` 仍可走完三步（mock 复刻门控与冲突）。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。装完 coss 组件后 `git diff package.json` 核对依赖，并人工点检 Dialog/AlertDialog/Menu/Select/RadioGroup/Switch 的键盘与焦点返回（Base UI overlay/选择交互）。
5. **窗口与规范：** 提交时间落在 2026-06-05 ~ 2026-06-07（北京时间）；分支名/commit 经 hooks 校验（commit subject 纯 ASCII）；每 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。

---

## AGENTS.md 合规要点

- **单一边界：** PR1 客户端、PR2 路由骨架、PR3 理解、PR4 档案、PR5 意图与方向——每个 PR 一个清晰边界，互不混入无关重构/样式。
- **README 更新（依赖与来源 / 运行说明）：**
  - **PR3/PR4/PR5** 各自在 [README.md](../../README.md) §依赖与来源的 coss 组件清单里**追加本次 `shadcn add` 的新组件**（PR3：`input-group`；PR4：`select`；PR5：`switch`、`radio-group`），并在「原创边界」段说明这些是 registry 生成的第三方基座、非原创业务；analysis 阶段的录入/编辑/门控/冲突展示逻辑为本项目业务实现。
  - PR1/PR2 不新增依赖、不改运行流程，**README 无需更新**（在 PR 「来源与依赖」段写「无新增第三方依赖」即可）。
- **PR 描述据实披露：** 复用既有 API 客户端模式与 coss 基座；新增 coss 组件标明为第三方生成资产；后端缺口（state 不前进、gates 不可用、意图无独立 confirm、方向特例等）如实说明，**不得把后端能力写成前端原创**。
- main 每次合并后可 `pnpm build` 通过、可启动。
- 提交在开发窗口内（2026-06-05~06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。
