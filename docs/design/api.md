# Cardenio 入戏 API 接口文档（API Specification）

> 把 [PRD](../product/requirements.md) 与 [技术设计](./design.md) 的能力落为可调用的 HTTP/JSON 接口契约。本文是 [design.md §8「API 契约（高层）」](./design.md#8-api-契约高层框架无关) 的具体化。

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档类型 | API 接口规格（面向前后端联调） |
| 文档状态 | Draft（评审中） |
| 协议 | HTTP/1.1 · JSON · 生成类接口用 SSE 流式 |
| 关联文档 | [`requirements.md`](../product/requirements.md)（需求与 §7 YAML Schema）、[`design.md`](./design.md)（分层架构 / LLM 网关）、[`agent-workflow.md`](./agent-workflow.md)（编排与信任强制） |
| 最近更新 | 2026-06-07 |

本文给出**契约层**接口定义。设计文档明确「框架无关、provider 无关」（design.md §11），故此处只约定**资源、动作、报文与状态语义**，不绑定具体后端框架；字段命名沿用 PRD §7 的最终契约。接口编号采用 `API-x`，每条接口标注其对应的 `FR-x` / `NFR-x` 与里程碑（M0–M8）。

> 本文与 PRD §7 Schema、agent-workflow.md 的「信任强制」对齐。当本文与 PRD 不一致时，**以 PRD 为准**，并提 Issue 复审。

---

## 1. 通用约定

### 1.1 基础

| 约定 | 值 |
| --- | --- |
| Base URL | `/api/v1` |
| 版本策略 | 路径前缀 `v1`；破坏性变更升 `v2`，旧版并行一段时间 |
| 请求/响应体 | `application/json; charset=utf-8`（导入/导出用 `multipart/form-data` 或二进制流） |
| 时间格式 | ISO-8601 UTC（如 `2026-06-06T08:00:00Z`） |
| 标识符 | 资源 ID 带类型前缀：`prj_` 项目、`ch_` 章节、`sc_` 场景、`ver_` 版本、`job_` 任务、`exp_` 导出 |

### 1.2 鉴权

- 公开接口仅包括健康检查、注册、登录；其余接口需 `Authorization: Bearer <access_token>`。
- `access_token` 由本服务签发，`token_type` 固定为 `bearer`，过期时间由 `expires_at` 表达。
- 项目级数据隔离（NFR-1）：token 主体只能访问其拥有/被授权的 `prj_*`；越权返回 `403 forbidden`。
- 缺失、过期、撤销或无法验证的 token 返回 `401 unauthenticated`。
- 登出会撤销当前会话；已撤销会话对应的 access token 不得继续访问受保护接口。

### 1.3 语言三分（NFR-7）

UI / Source / Output Language 三者解耦，**不硬编码**：

- `source_language` / `output_language` 存于项目 `meta`，创建项目时设定、可改。
- UI 语言（错误文案、提示）由请求头 `Accept-Language` 决定，默认 `zh-CN`。
- 服务端不得假设三者相同。

### 1.4 幂等与并发

- 写入/生成类接口接受可选 `Idempotency-Key` 头：同 key 重复请求返回首次结果，避免重复生成与扣费。
- 工件更新用乐观锁：请求带 `If-Match: <etag>`（来自工件 `version`/`updated_at`）；冲突返回 `409 version_conflict`。

### 1.5 分页

列表接口统一游标分页：

```
GET /api/v1/projects?limit=20&cursor=<opaque>
→ { "items": [...], "next_cursor": "<opaque|null>" }
```

### 1.6 统一错误模型

所有非 2xx 返回：

```json
{
  "error": {
    "code": "state_gate_blocked",
    "message": "作品理解尚未确认，无法生成人物档案。",
    "retryable": false,
    "details": { "required_state": "understood", "current_state": "imported" }
  }
}
```

- `code`：稳定机读错误码（见 §16），`message` 为可读文案（按 `Accept-Language` 本地化）。
- `retryable`：客户端是否可原样重试（如 LLM 限流为 `true`）。
- LLM 厂商错误在网关收敛为结构化错误，**不向上泄露 provider 细节**（design.md §9）。

### 1.7 信任字段（贯穿所有工件）

以下字段语义全局一致，定义见 PRD §7 与 [agent-workflow.md §6](./agent-workflow.md#6-信任能力的编排级强制关键)：

| 字段 | 含义 | 关联 |
| --- | --- | --- |
| `source_ref` | `{ chapter:int, paragraphs:int[] }` 溯源锚点，**生成类工件必填** | P4 / FR-8.1 |
| `flag` | `from_source`（原文已有）\| `ai_inferred`（AI 推断/新增） | P5 / FR-7.5 |
| `todo` 节拍 | 留白标记，可检索可筛选 | P6 / FR-9.6 |

服务端在编排层**强制**这些字段，校验不通过的产物不落库（不靠提示词自觉）。

---

## 2. 资源模型与状态机

### 2.1 资源概览

一次改编是一个 **Project**，下挂一组有序、可编辑、可版本化的**工件（artifact）**：

```text
Project (prj_*)
├── source          导入原文（章节[] + 段落索引）        ← 溯源根 · FR-1
├── understanding   作品理解（需确认）                    ← FR-2
├── characters      人物档案[]（需确认）                  ← FR-3
├── intent          作者意图约束（+ 改编方向）            ← FR-4/FR-5
├── outline         分场大纲（场景[]，每场含 source_ref） ← FR-6
├── screenplay      剧本 YAML（场景/节拍，可版本/分支）   ← FR-7/FR-8
└── report          改编取舍报告                          ← FR-10
```

每个工件携带 `state`、`version`、`parent_version`、`updated_at`，支持自动保存与中断恢复（NFR-6）。

### 2.2 流程状态机（强制「先理解，再改编」P1）

```text
imported → understood(✓) → profiled(✓) → intent_set → outlined(✓)
        → generated → [editing ⇄ report] → exported
```

- 标 `(✓)` 的关卡需作者**显式确认**（`:confirm` 动作）才能进入下一阶段。
- 在前置关卡未满足时调用下游生成接口，返回 `409 state_gate_blocked`（见 §16 门控表）。
- `editing` 与 `report` 可反复往返；回到上游工件编辑会把受影响下游标记 `needs_recompute`。

项目当前阶段可随时查询：

```
GET /api/v1/projects/{projectId}
→ { "id": "prj_x", "state": "outlined", "gates": { "understanding": "confirmed", "characters": "confirmed", "outline": "draft" }, ... }
```

### 2.3 工件信封（envelope）

所有工件 GET 返回统一外层：

```json
{
  "type": "understanding",
  "state": "draft",
  "version": "v2",
  "parent_version": "v1",
  "etag": "W/\"a1b2\"",
  "updated_at": "2026-06-06T08:00:00Z",
  "needs_recompute": false,
  "data": { /* 工件正文，结构见各章节 */ }
}
```

### 2.4 异步生成与流式（NFR-5）

LLM 生成接口（`:generate` / `:rewrite` / `report:generate`）为**长任务**，统一返回 **Job**，并支持 SSE 进度/流式：

```
POST .../understanding:generate
→ 202 Accepted
{ "job": { "id": "job_x", "kind": "understand", "status": "running", "events_url": "/api/v1/projects/prj_x/jobs/job_x/events" } }
```

订阅事件流：

```
GET /api/v1/projects/{projectId}/jobs/{jobId}/events     (text/event-stream)

event: progress
data: {"phase":"scene","done":3,"total":12,"scene_id":"sc_003"}

event: delta
data: {"path":"scenes[2].beats[1].dialogue","text":"原来你一直都……"}

event: done
data: {"artifact_version":"v3"}

event: error
data: {"code":"llm_unavailable","retryable":true}
```

- 同步轮询备选：`GET /api/v1/projects/{projectId}/jobs/{jobId}`。
- 取消：`POST /api/v1/projects/{projectId}/jobs/{jobId}:cancel`。
- 场景生成为**场景级并行 fan-out**（agent-workflow §4.2）；`progress` 按场景上报，单场失败不影响其余场景与既有版本（NFR-6）。

---

## 3. 认证（Auth）· NFR-1 · `M0`

### API-A1 注册 · `POST /api/v1/auth/register`

公开接口。用于创建作者账号并返回当前登录态。

请求：

```json
{
  "email": "author@example.com",
  "password": "correct horse battery staple",
  "display_name": "林晚"
}
```

约束：

- `email` 全局唯一，服务端按规范化后的邮箱判断重复。
- `password` 明文只出现在请求体中，服务端必须以不可逆哈希保存，不得落日志。
- `display_name` 可选；为空时客户端可展示邮箱前缀或服务端返回的默认名。

响应 `201`：

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_at": "2026-06-07T10:30:00Z",
  "user": {
    "id": "usr_12345678",
    "email": "author@example.com",
    "display_name": "林晚"
  }
}
```

错误：

- `400 invalid_request`：邮箱格式非法、密码不满足策略或请求体非法。
- `409 version_conflict`：邮箱已注册。

### API-A2 登录 · `POST /api/v1/auth/login`

公开接口。使用邮箱和密码换取 Bearer access token。

请求：

```json
{
  "email": "author@example.com",
  "password": "correct horse battery staple"
}
```

响应 `200`：同 API-A1 的登录态响应。

错误：

- `401 unauthenticated`：邮箱不存在、密码错误、账号不可用。为避免账号枚举，错误文案不得区分具体原因。

### API-A3 当前用户 · `GET /api/v1/auth/me`

受保护接口。返回当前 token 主体。

响应 `200`：

```json
{
  "id": "usr_12345678",
  "email": "author@example.com",
  "display_name": "林晚"
}
```

错误：

- `401 unauthenticated`：缺失、过期、撤销或无效 token。

### API-A4 登出 · `POST /api/v1/auth/logout`

受保护接口。撤销当前会话。

响应 `204`：无响应体。

错误：

- `401 unauthenticated`：缺失、过期、撤销或无效 token。

### 3.1 用户与项目归属

- `User.id` 是 token 主体，也是项目归属判断的最小单位。
- 创建项目时，服务端必须把项目绑定到当前 `User.id`。
- `GET /projects` 只返回当前用户拥有或被授权的项目。
- 任意 `projects/{projectId}` 作用域接口在进入业务逻辑前必须校验当前用户是否拥有或被授权访问该项目。
- 项目不存在、已删除时返回 `404 not_found`；项目存在但当前用户无权访问时返回 `403 forbidden`。
- 多人协作和项目共享边界暂不在 MVP 中开放，但权限模型必须保留“被授权访问”的扩展语义。

---

## 4. 项目管理（Projects）· `M0`

### API-1 创建项目 · `POST /api/v1/projects`

请求：

```json
{
  "title": "旧书店的信",
  "ui_language": "zh-CN",
  "source_language": "zh-CN",
  "output_language": "zh-CN",
  "adaptation_direction": null
}
```

响应 `201`：返回项目对象（`state: "empty"`，`meta` 含语言三分与 `style_fingerprint`（生成理解后回填））。

| 关联 | NFR-6 / NFR-7 / M0 |
| --- | --- |

### API-2 项目读写

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 列表 | `GET /projects` | 游标分页，返回 `id/title/state/updated_at` |
| 详情 | `GET /projects/{projectId}` | 含 `state`、各工件 `gates` 状态 |
| 改 meta | `PATCH /projects/{projectId}` | 改标题、语言、`adaptation_direction` |
| 删除 | `DELETE /projects/{projectId}` | 软删除；级联工件 |

---

## 5. 导入与预处理（Source）· FR-1 · `M1`

### API-3 录入章节（粘贴/按章）· `POST /projects/{projectId}/source/chapters`

```json
{ "title": "第二章 旧书店", "text": "林晚推开门……" }
```

响应 `201`：返回章节对象（`ch_*`、`order`、`char_count`、段落索引区间）。对应 FR-1.1。

### API-4 文件导入 · `POST /projects/{projectId}/source/import`

- `multipart/form-data`，字段 `file`（TXT/DOCX；RTF/PDF/EPUB 为未来 `Could`）。
- 服务端解析 + 字符清洗（全/半角统一、去乱码与多余空白，**保留换行语义**，FR-1.4），返回自动切分的章节预览（FR-1.2）。
- 验收：导入后「原文视图」与源文件一致，无字符丢失（FR-1 验收）。

响应 `200`：

```json
{
  "chapters": [{ "id": "ch_1", "title": "第一章", "char_count": 3120, "paragraphs": [1, 58] }],
  "warnings": []
}
```

### API-5 获取原文 · `GET /projects/{projectId}/source`

返回章节数组 + 段落索引（**溯源根**）+ 计数与门槛校验：

```json
{
  "chapters": [ /* ... */ ],
  "stats": { "chapter_count": 3, "char_count": 9460 },
  "threshold": { "min_chapters": 3, "passed": true }
}
```

- `threshold.passed=false` 时（不足 3 章）下游 `:generate` 返回 `409 chapter_threshold_unmet`（FR-1.3）。

### API-6 章节编辑与切分调整

| 接口 | 方法 路径 | 关联 |
| --- | --- | --- |
| 编辑章节 | `PUT /source/chapters/{chapterId}` | FR-1.1 |
| 删除章节 | `DELETE /source/chapters/{chapterId}` | FR-1.2 |
| 合并/拆分 | `POST /source/chapters:resegment` | FR-1.2 |

`:resegment` 请求示例（手动调整切分点，作者拍板）：

```json
{ "op": "split", "chapter_id": "ch_2", "at_paragraph": 47 }
```

> 重新切分会重建段落索引；已存在的下游 `source_ref` 由服务端做区间重映射并标记受影响工件 `needs_recompute`。

---

## 6. 作品理解（Understanding）· FR-2 · `M2`

> 对应 P1：必须先产出并经作者确认，才能进入下游。

### API-7 生成作品理解 · `POST /projects/{projectId}/understanding:generate`

- 前置：`source` 满足 ≥3 章门槛。
- 异步 Job（见 §2.4）。输出字段与 PRD §7 / FR-2 对齐：

```json
{
  "logline": "一个女孩在父亲的旧书店里追查他的死亡真相。",
  "synopsis": "...",
  "themes": ["记忆与和解"],
  "protagonist_goal": "找回父亲的真相",
  "protagonist_fear": "再次被抛弃",
  "central_conflict": "真相与逃避的撕扯",
  "mood": "压抑、悬而未决",
  "style_fingerprint": "克制、冷硬、意象密集",
  "narrative": { "perspective": "first_person", "tense": "past", "unreliable": false },
  "non_visualizable": [
    { "source_ref": { "chapter": 1, "paragraphs": [12, 18] }, "note": "大段内心独白，需外化" }
  ],
  "strengths": ["意象集中"],
  "difficulties": ["心理戏多"]
}
```

- **FR-2.1 强制**：含大段心理描写的章节，`non_visualizable` 至少一处（校验不过则重试，最终降级标 `needs_attention`）。
- `style_fingerprint` 写入项目 `meta`，作为**全程生成约束**（NFR-2 / P7）。

### API-8 读取 / 编辑 / 确认

| 接口 | 方法 路径 | 说明 | 关联 |
| --- | --- | --- | --- |
| 读取 | `GET /understanding` | 工件信封 | FR-2 |
| 编辑 | `PUT /understanding` | 全字段可编辑；编辑版本成为下游**事实源** | FR-2.3 |
| 确认 | `POST /understanding:confirm` | 通过 P1 关卡；未确认下游被门控 | FR-2 验收 |

`PUT` 需带 `If-Match`；确认后 `state=confirmed`。

---

## 7. 人物档案（Characters）· FR-3 · `M2`

### API-9 生成人物档案 · `POST /projects/{projectId}/characters:generate`

- 前置：`understanding` 已确认。
- 输出人物数组，对齐 PRD §7 `characters[]`：

```json
{
  "characters": [
    {
      "id": "lin_wan",
      "name": "林晚",
      "role": "protagonist",
      "voice": "克制、爱用反问",
      "desire": "找回父亲的真相",
      "fear": "再次被抛弃",
      "arc": "从回避到直面",
      "relations": [{ "to": "lin_fu", "type": "父女", "change": "由疏离到和解" }],
      "hard_rules": ["从不主动示弱"]
    }
  ]
}
```

- FR-3.1 分类：`protagonist | supporting | mentioned`。
- 校验：覆盖原文全部具名主要人物；`voice` / `hard_rules` 非空（FR-3 验收）。

### API-10 档案读写与确认

| 接口 | 方法 路径 | 说明 | 关联 |
| --- | --- | --- | --- |
| 读取 | `GET /characters` | 全部人物 + 关系图 | FR-3.2 |
| 新增 | `POST /characters` | 手动补人物 | FR-3 |
| 编辑 | `PUT /characters/{characterId}` | 全字段可编辑 | FR-3.3 |
| 删除 | `DELETE /characters/{characterId}` | — | FR-3 |
| 确认 | `POST /characters:confirm` | 通过 P1 关卡 | FR-3 |

> 确认后，`voice` / `hard_rules` 成为台词生成与一致性检查的**硬约束**（引用于 FR-7.3 / FR-9.4）。修改 `hard_rules` 后，下游引用的是修改后的值（FR-3 验收）。

---

## 8. 作者意图与改编方向（Intent）· FR-4 / FR-5 · `M3`

### API-11 设置作者意图 · `PUT /projects/{projectId}/intent`

意图编译为下游**硬约束**（agent-workflow §5.3）：

```json
{
  "keep": ["父女对峙"],
  "no_delete": ["父亲之死"],
  "no_merge": ["林晚", "林父"],
  "must_keep_lines": ["原来你一直都……"],
  "mood_floor": "压抑",
  "allow_new_plot": false,
  "allow_reorder": true,
  "allow_new_ending": false,
  "target_type": "short_drama"
}
```

对应 FR-4 收集项。`PUT` 后 `state → intent_set`。

### API-12 选择改编方向 · `PUT /projects/{projectId}/intent/direction`

```json
{ "direction": "faithful" }
```

- MVP 值：`faithful | cinematic | short_drama`（`Must`）；`tv | film | stage`（`Should`/`Could`）。
- 写入 `meta.adaptation_direction`，影响下游生成策略与节奏（FR-5）。

### API-13 意图—方向冲突校验 · `POST /projects/{projectId}/intent:validate`

确定性校验，返回冲突清单由作者裁决（FR-5 验收）：

```json
{
  "conflicts": [
    { "code": "faithful_vs_new_ending", "message": "「忠实改编」与「允许调整结局」冲突。", "fields": ["direction", "allow_new_ending"] }
  ]
}
```

- 无冲突返回 `{ "conflicts": [] }`。冲突不阻塞，仅提示；是否调整由作者决定。

> **意图门控（编排级强制）**：`allow_new_plot=false` 时，后续剧本生成将从约束侧**拒绝**带 `ai_inferred` 的新增**剧情节点**（仅允许媒介翻译层面的外化），见 §8 与 agent-workflow §6。

---

## 9. 分场大纲（Outline）· FR-6 · `M4`

### API-14 生成大纲 · `POST /projects/{projectId}/outline:generate`

- 前置：`understanding`、`characters` 已确认（`intent` 可并行，未设时用默认方向）。
- 每场字段对齐 PRD §7 与 FR-6：

```json
{
  "scenes": [
    {
      "id": "sc_012",
      "heading": { "int_ext": "INT", "location": "旧书店", "time": "NIGHT" },
      "source_ref": { "chapter": 2, "paragraphs": [45, 51] },
      "synopsis": "林晚发现父亲的信",
      "goal": "揭示父亲秘密",
      "conflict": "真相与逃避的撕扯",
      "mood": "压抑、悬而未决",
      "characters": ["lin_wan", "lin_fu"],
      "foreshadowing": ["父亲的怀表"],
      "relation_changes": [{ "characters": ["lin_wan", "lin_fu"], "change": "信任出现裂缝" }],
      "ending_state": "林晚握紧日记，决定追查"
    }
  ]
}
```

- **FR-6.3 / 8.1 强制**：每场 `source_ref` 非空且段落落在原文索引内（校验不过则重试）。

### API-15 大纲编辑（FR-6.2）

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 读取 | `GET /outline` | 场景数组 |
| 新增场景 | `POST /outline/scenes` | — |
| 编辑场景 | `PUT /outline/scenes/{sceneId}` | 改字段 |
| 删除场景 | `DELETE /outline/scenes/{sceneId}` | — |
| 调整顺序 | `POST /outline/scenes:reorder` | `{ "order": ["sc_001","sc_012",...] }` |
| 确认 | `POST /outline:confirm` | 通过关卡，进入剧本生成 |

### API-16 合并建议（FR-6.1，建议而非擅自删）

```
GET  /projects/{projectId}/outline/merge-suggestions
→ { "suggestions": [ { "id":"mg_1", "scene_ids":["sc_003","sc_004"], "reason":"两场均为过场，可合并", "status":"pending" } ] }

POST /projects/{projectId}/outline/merge-suggestions/{suggestionId}:apply     # 作者采纳
POST /projects/{projectId}/outline/merge-suggestions/{suggestionId}:dismiss    # 作者拒绝
```

> 验收：合并/删除以**建议**形式呈现，未经作者确认不改变大纲结构（FR-6 验收 / P2）。

---

## 10. 剧本生成（Screenplay）· FR-7 / FR-8 · `M5`

> 产品价值核心：把小说语言「翻译」为剧本语言（P3）。生成在编排层强制信任能力（agent-workflow §6）。

### API-17 生成剧本初稿 · `POST /projects/{projectId}/screenplay:generate`

- 前置：`outline` 已确认。
- 按场景 fan-out 并行生成；异步 Job + `progress` 按场景上报。
- 可选请求体：`{ "scene_ids": ["sc_012"], "shot_hints": false }`（不传则全量生成；`shot_hints` 默认按项目设置，FR-7.2 / NG4）。

生成结果即 PRD §7 `screenplay` 结构，节拍 `beats[]` 关键约束：

| 约束 | 接口语义 | 关联 |
| --- | --- | --- |
| 来源回填 | 每个 beat 必带 `source_ref`，缺失重试不落库 | FR-8.1 / P4 |
| 加戏强标注 | 无对应源片段的 beat 一律 `flag: ai_inferred`（**底线**） | FR-7.5 / P5 |
| 心理外化 | `non_visualizable` 段产出 `note` + `options[]` 多方案（V.O./动作/对话/注释），默认主推+备选，标 `ai_inferred` | FR-7.1 |
| 对白剧本化 | 保留人物 `voice` 指纹 | FR-7.3 |
| 潜台词/情绪 | beat 带 `subtext`，场景带 `mood` | FR-7.6 |
| 留白 | 置信不足产出 `type: todo` 节拍，不编造 | FR-9.6 / P6 |
| 必留台词 | `intent.must_keep_lines` 逐字出现并标 `from_source` | FR-4 验收 |
| 意图门控 | `allow_new_plot=false` 时拒绝 `ai_inferred` 剧情节点 | FR-4 / §7 |

节拍片段示例（完整 Schema 见 [PRD §7](../product/requirements.md#7-数据模型--yaml-schema-规范)）：

```json
{
  "id": "sc_012",
  "beats": [
    { "type": "action", "text": "林晚拂去书脊的灰，抽出一本日记。", "subtext": "她其实早就知道它在这里。",
      "source_ref": { "chapter": 2, "paragraphs": [46] }, "flag": "from_source" },
    { "type": "note", "text": "原文为大段内心独白，建议用画外音处理。", "flag": "ai_inferred",
      "options": [ { "kind": "voice_over", "text": "（V.O.）这一次，我不会再回头。" },
                   { "kind": "action", "text": "林晚合上日记，吹熄了灯。" } ] },
    { "type": "todo", "text": "此处需作者补充父女对峙的关键台词。" }
  ]
}
```

### API-18 读取剧本（所见即所得 + 源码双视图，FR-9.5）

```
GET /projects/{projectId}/screenplay?format=json        # 结构化（默认，供编辑器渲染中文剧本排版）
GET /projects/{projectId}/screenplay?format=yaml        # 原始 YAML 手改视图
GET /projects/{projectId}/screenplay/scenes/{sceneId}   # 单场
```

- 两种表示**往返一致**（parse → edit → serialize 不丢字段，FR-8.4）。

### API-19 回写剧本（YAML 手改不破坏结构，FR-8.4）

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 整稿回写 | `PUT /screenplay` | 接受 `format=yaml\|json`；服务端 Schema 校验，不合格返回 `422 schema_invalid` 并指明字段 |
| 单场回写 | `PUT /screenplay/scenes/{sceneId}` | 同上，仅该场 |

### API-20 信任筛选视图（编辑器高亮/筛选）

| 接口 | 返回 | 关联 |
| --- | --- | --- |
| `GET /screenplay/beats?flag=ai_inferred` | 全部 AI 新增节拍（供高亮筛选） | FR-7.5 验收 |
| `GET /screenplay/todos` | 全部 `todo` 留白（可定位、可筛选） | FR-9.6 验收 |

---

## 11. 打磨工作台（Editing）· FR-9 · `M6`

### API-21 局部重生成（核心交互）· `POST /screenplay/scenes/{sceneId}:rewrite`

```json
{ "instruction": "这场太平淡，把冲突往前提；口语化一点。" }
```

- 输入装配：目标场景当前版本 + 前后场景摘要 + 人物档案 + 意图 + 整体剧情（agent-workflow §5.6）。
- 异步 Job + 流式返回；产物为**该场景的新版本节点**，契约同 API-17。
- **保证**：只改动选中块，其余场景内容与版本指针不变（FR-9.2 验收）。

响应（done 事件）：`{ "scene_id": "sc_012", "new_version": "ver_8", "parent_version": "ver_7" }`

### API-22 版本与分支（FR-9.3，`Should`）

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 版本列表 | `GET /screenplay/scenes/{sceneId}/versions` | 版本树（`version`/`parent_version`/label） |
| 建分支 | `POST /screenplay/scenes/{sceneId}/versions` | `{ "from": "ver_7", "label": "冷峻版" }` |
| 切换/回滚 | `POST /screenplay/scenes/{sceneId}:checkout` | `{ "version": "ver_5" }`（回滚=指向旧版本，不破坏历史） |
| 版本对比 | `GET /screenplay/scenes/{sceneId}/versions:diff?a=ver_5&b=ver_7` | 结构化 diff |

> 同一场戏可并存多个方向（「温情版」「冷峻版」），可分支、对比、回滚。版本节点不可变，局部操作不破坏版本数据（NFR-6）。

### API-23 一致性守护（FR-9.4，`Should`）

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 全局改名 | `POST /consistency:rename` | `{ "character_id": "lin_wan", "new_name": "林万" }`；确定性全局替换（`id` 稳定，仅替换显示名），破坏性操作需 `confirm:true` |
| 冲突检测 | `POST /consistency:check` | 按 `hard_rules` 扫描台词/动作，返回冲突**建议**清单（非自动改） |

`:check` 响应：

```json
{ "conflicts": [ { "scene_id":"sc_020", "beat_index":3, "rule":"从不主动示弱", "excerpt":"我求你了……", "severity":"high" } ] }
```

> 改名后全剧本对白与动作中的指代同步更新（FR-9.4 验收）；改人设后检测并提示冲突台词，由作者决定是否修改。

### API-24 溯源解析（双栏对照，FR-9.1 / P4）· `GET /projects/{projectId}/source:resolve`

```
GET /projects/{projectId}/source:resolve?chapter=2&paragraphs=45-51
→ { "chapter": 2, "paragraphs": [
      { "index": 45, "text": "..." }, { "index": 46, "text": "林晚拂去书脊的灰……" } ] }
```

- 供双栏视图「点击剧本场景 → 高亮对应原文段落」与滚动联动使用（FR-9.1 验收）。
- 反向定位（原文段落 → 引用它的场景/节拍）：`GET /screenplay/beats?source_chapter=2&source_paragraph=46`。

---

## 12. 改编取舍报告（Report）· FR-10 · `M7`

### API-25 生成报告 · `POST /projects/{projectId}/report:generate`

- 前置：`screenplay` 已生成。
- 确定性聚合（从 `flag` 与版本/大纲 diff）+ LLM 叙述化（agent-workflow §5.8）。

```json
{
  "kept": [{ "item": "父女对峙", "source_ref": { "chapter": 2, "paragraphs": [48] } }],
  "deleted": [{ "item": "邻居闲谈", "source_ref": { "chapter": 1, "paragraphs": [30, 34] } }],
  "merged": [{ "scene_ids": ["sc_003", "sc_004"], "into": "sc_003" }],
  "added": [{ "scene_id": "sc_018", "beat_index": 2, "flag": "ai_inferred", "desc": "新增过渡动作" }],
  "externalized": [{ "scene_id": "sc_012", "from": "内心独白", "to": "voice_over" }],
  "from_source_lines": 42,
  "ai_inferred_lines": 7,
  "kept_foreshadowing": ["父亲的怀表"],
  "review_recommended": [{ "scene_id": "sc_018", "reason": "AI 新增桥段，建议复查" }]
}
```

- **一致性校验（FR-10 验收）**：报告统计与剧本 `flag` 标记**必须一致**；不一致服务端判生成失败并返回 `409 report_flag_mismatch`（交叉核对 FR-7.5）。
- 每条「删除/合并/新增/改写」均可定位到场景或原文段落。

### API-26 读取报告 · `GET /projects/{projectId}/report`

返回报告工件信封。

---

## 13. 导出（Export）· FR-11 · `M-Should`

### API-27 创建导出 · `POST /projects/{projectId}/export`

```json
{ "format": "fountain", "version": "v3", "shot_hints": false }
```

- MVP 优先：`fountain`（优先打通）、`docx`、`pdf`（`Should`）；`fdx | rtf | markdown` 未来（`Could`）。
- 中文剧本默认中文创作排版；英文对齐传统 screenplay（FR-11）。
- 异步 Job，完成后产出下载链接。

响应 `202`：`{ "export": { "id": "exp_x", "status": "running" } }`

### API-28 导出状态/下载

| 接口 | 方法 路径 | 说明 |
| --- | --- | --- |
| 状态 | `GET /export/{exportId}` | `status` + `download_url`（完成后） |
| 下载 | `GET /export/{exportId}/file` | 二进制流，带 `Content-Disposition` |

> 验收：导出的 Fountain/DOCX 在目标软件可正常打开，场景标题、人物、对白、动作层级正确（FR-11 验收 / NFR-8 不锁定生态）。

---

## 14. 设置与隐私（Settings）· NFR-1 · `M8`

### API-29 项目设置读写

```
GET  /projects/{projectId}/settings
PUT  /projects/{projectId}/settings
```

```json
{
  "no_training": true,
  "shot_hints_default": false,
  "storage_region": "...",
  "data_usage_notice_ack": true
}
```

- `no_training`：明确「不用于训练」承诺与开关（NFR-1）。
- 告知数据存储位置；传输/存储加密、项目级隔离为平台保证，不在此暴露密钥（NFR-1）。

---

## 15. 通用对象 Schema（机读契约）

字段命名为最终契约，新增字段需走 Schema 评审（PRD §7）。完整剧本结构以 [PRD §7](../product/requirements.md#7-数据模型--yaml-schema-规范) 为准，下表为 API 高频对象：

| 对象 | 形状 |
| --- | --- |
| `SourceRef` | `{ "chapter": int, "paragraphs": int[] }` |
| `Flag` | `"from_source" \| "ai_inferred"` |
| `Beat` | `{ "type": "action\|dialogue\|voice_over\|off_screen\|note\|todo", "text"?, "character"?, "parenthetical"?, "dialogue"?, "subtext"?, "source_ref"?, "flag"?, "options"? }` |
| `Job` | `{ "id", "kind", "status": "queued\|running\|succeeded\|failed\|canceled", "events_url", "error"? }` |
| `Artifact<T>` | §2.3 信封 |
| `Error` | §1.6 |

---

## 16. 错误码与状态门控

### 16.1 通用错误码

| HTTP | `code` | 含义 |
| --- | --- | --- |
| 400 | `invalid_request` | 报文/参数非法 |
| 401 | `unauthenticated` | 缺失/无效 token |
| 403 | `forbidden` | 越权访问他人项目 |
| 404 | `not_found` | 资源不存在 |
| 409 | `version_conflict` | 乐观锁 `If-Match` 不匹配 |
| 409 | `state_gate_blocked` | 前置确认关卡未满足（见 16.2） |
| 409 | `chapter_threshold_unmet` | 原文不足 3 章 |
| 409 | `report_flag_mismatch` | 报告统计与剧本 `flag` 不一致（FR-10） |
| 422 | `schema_invalid` | YAML/工件回写不合 Schema，`details` 指明字段 |
| 429 | `rate_limited` | 限流，`retryable:true` |
| 503 | `llm_unavailable` | LLM 网关超时/降级，`retryable:true` |

### 16.2 状态门控表（state_gate_blocked）

| 调用动作 | 要求前置状态 | 关联 |
| --- | --- | --- |
| `characters:generate` | `understanding = confirmed` | P1 / FR-2 |
| `outline:generate` | `characters = confirmed` | P1 / FR-3 |
| `screenplay:generate` | `outline = confirmed` 且原文 ≥3 章 | FR-6 / FR-1.3 |
| `report:generate` | `screenplay` 已生成 | FR-10 |
| `export` | `screenplay` 已生成 | FR-11 |

> 门控由编排层状态机强制（design.md §7.1）；前置未满足一律拒绝，不进入 LLM 调用。

---

## 17. 接口 ↔ 需求 ↔ 里程碑映射

| 接口组 | API | 关联需求 | 里程碑 |
| --- | --- | --- | --- |
| 认证 | API-A1~A4 | NFR-1 | M0 |
| 项目管理 | API-1/2 | NFR-6/7 | M0 |
| 导入预处理 | API-3~6 | FR-1.1~1.4 | M1 |
| 作品理解 | API-7/8 | FR-2、FR-2.1/2.3、NFR-2 | M2 |
| 人物档案 | API-9/10 | FR-3、FR-3.1~3.3 | M2 |
| 意图/方向 | API-11~13 | FR-4、FR-5 | M3 |
| 分场大纲 | API-14~16 | FR-6、FR-6.1~6.3 | M4 |
| 剧本生成 | API-17~20 | FR-7、FR-7.1~7.6、FR-8 | M5 |
| 打磨工作台 | API-21~24 | FR-9.1~9.6 | M6 |
| 改编报告 | API-25/26 | FR-10 | M7 |
| 导出 | API-27/28 | FR-11、NFR-8 | Should |
| 设置/隐私 | API-29 | NFR-1 | M8 |

---

## 18. 开放问题（待 ADR）

- **A1 项目共享边界**：多人协作与项目授权模型细节（当前 NG5 不做多人实时协作）。
- **A2 流式协议**：SSE vs WebSocket；断线重连与事件序号（`Last-Event-ID`）补发策略。
- **A3 Job 生命周期**：任务保留时长、重试与幂等键过期、取消语义的精确边界。
- **A4 版本树存储**：场景级版本/分支在关系型 vs 文档型的查询形态（呼应 design.md O3）。
- **A5 大文件导入**：分块上传与超长原文（NFR-3）超限时的降级与如实提示。

> 与 design.md / agent-workflow.md 一致：关键契约决策（流式、版本、门控）进入对应里程碑前以 ADR 记录。
