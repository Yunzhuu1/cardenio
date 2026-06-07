# 前端接入后端 M8 接口 — 设置与隐私（Settings）实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 **M8 的设置与隐私能力（API-29：项目级隐私/训练承诺/镜头默认/语言设置读写）** 接口。本计划把它接到前端：把当前为 `StagePlaceholder` 的 **`settings`（项目设置）** 阶段页升级为可用界面，落地路线图 **M8-T2 隐私与训练承诺（NFR-1）** 与 **M5-T7 镜头建议默认开关** 的前端职责。**全程只改 `frontend/`，不改 `backend/`。**
>
> 本计划延续 [`frontend-m7-backend-integration.md`](./frontend-m7-backend-integration.md) 与更早各阶段计划的全部约定（默认 `http` 模式、http/mock 双实现经 `VITE_API_MODE` 切换、coss 组件经 shadcn `@coss` registry 安装到 `app/components/ui/`、统一 envelope 信封、门控只看工件存在/state、`extra="forbid"` 全量回传、冒号动作段按字面拼接、不发 `If-Match`、两 locale 键同步、Conventional Commits + 纯 ASCII subject、PR 模板五段式）。执行前请通读 M7 计划的「总体方案与不变量」「跨 PR 关键实现细则」「coss 用法红线」，本计划只补充 M8 设置页的差异点。

---

## Context（为什么做、目标、已确认决策）

- 产品主流程「导入（M0/M1）→ 理解/档案/意图（M2/M3）→ 大纲（M4）→ 剧本初稿（M5）→ 打磨工作台（M6）→ 改编取舍报告（M7）」已全部接入。**`settings`（项目设置）是目前唯一仍为 `StagePlaceholder` 的页面**（[project-settings.tsx](../../frontend/app/routes/project-settings.tsx)），后端 [settings.py](../../backend/src/cardenio/api/routes/settings.py)（API-29）已完整实现，本期把它接成可用页。
- M8 的产品职责落在独立阶段页 **`settings`**，承载路线图里两项能力：
  - **M8-T2 隐私与训练承诺（NFR-1）**：明确数据存储位置、「不用于训练」承诺、本地/私有处理保留路径，并把这些信任文案与开关**显式呈现给作者**。后端把 `allow_model_training` **强制锁死为 `false`**（PUT 传 `true` 会 422 校验失败），UI 须把它做成**只读、已关闭**的展示，不可让作者误以为能开启。
  - **M5-T7 镜头建议默认开关**：`shot_hints_enabled` 作为**项目级默认值**，作者在设置页持久化后，**驱动 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 剧本生成的镜头建议默认值**。
- 目标产出：作者进入 `settings` 阶段——
  1. 看到**隐私与训练承诺**面板：数据存储位置说明、「不用于训练」承诺（只读 `Switch` 恒关 + 说明）、本地/私有处理保留说明。文案优先展示后端返回的 `*_notice` 字段。
  2. 看到**镜头建议默认**开关（`shot_hints_enabled`），可切换并保存；该默认值被剧本页生成时采用。
  3. 看到**语言三分**（界面 / 源 / 输出语言）**只读展示**（数据取 `project.meta`），本期不提供编辑（见决策 1 与后端缺口）。
  4. 「保存设置」把可编辑项（仅 `shot_hints_enabled`）经 `PUT settings` 持久化；保存成功 toast + `revalidate`。

  全部数据来自真实后端。

- **本次已与用户确认的三项决策（写死，执行 Agent 不得擅自变更）：**
  1. **语言三分 = 只读展示，不在设置页编辑。** 后端 `PATCH /projects`（API-2）**尚未实现**（`raise NotImplementedError`），语言无法同步回 `project.meta`；为避免 settings 与 project.meta 漂移，本期语言三分**从 `project.meta` 读取并只读展示**。语言编辑待后端补 API-2 后单独一期。**已就此向后端提 issue（见文末「已知后端缺口」）。**
  2. **镜头建议 = 设置页默认值驱动剧本生成。** 设置页持久化 `shot_hints_enabled` 后，剧本页（[project-script.tsx](../../frontend/app/routes/project-script.tsx)）生成时的镜头建议**默认值改为「优先用既有剧本工件值，否则用设置默认值」**（PR3）。
  3. **本批范围 = 只做设置（settings）。** **排除导出（export，API-27/28）**：后端 [export.py](../../backend/src/cardenio/api/routes/export.py) 仍为 `raise NotImplementedError`，前端无法接，留待后端实现后单独一期。

---

## 后端现状核对（执行前必读，以代码实际行为为准）

> 已逐文件核对：[api/routes/settings.py](../../backend/src/cardenio/api/routes/settings.py)、[domain/models/base.py](../../backend/src/cardenio/domain/models/base.py)、[api/routes/projects.py](../../backend/src/cardenio/api/routes/projects.py)、[api/routes/export.py](../../backend/src/cardenio/api/routes/export.py)、[docs/design/api.md §13](../../docs/design/api.md)。

### M8 设置接口（[settings.py](../../backend/src/cardenio/api/routes/settings.py)，前缀 `/projects/{project_id}/settings`）

| 用途 | 方法 路径 | 请求体 | 返回 / 状态码 |
| --- | --- | --- | --- |
| **读取设置** | `GET ` (前缀根，即 `/settings`) | — | `200`。**项目已存 settings 工件 → 完整 `ArtifactEnvelope`**（`state:"confirmed"`）；**未存 → 一个「裁剪过」的默认信封**（仅 `type`/`state`/`version:null`/`parent_version:null`/`data`，**缺 `etag`/`updated_at`/`needs_recompute`**，见坑 1）。项目不存在 → `404 {"detail":"Project not found"}` |
| **写入设置** | `PUT ` (前缀根) | `ProjectSettings`（`extra="forbid"`，见下「数据形状」） | `200` 完整 `ArtifactEnvelope<ProjectSettings>`（`state:"confirmed"`，`parent_version=` 上一版本）。项目不存在 → `404 {"detail":"Project not found"}`；`allow_model_training=true` → **`422`（Pydantic 校验失败）** |

> **关键：`settings` 工件 `state` 恒为 `confirmed`**（不是 draft），且**无 `:generate`/`:confirm` 动作**——直接 `GET`/`PUT`，是纯读写工件（类似 intent 的 `get`/`save`，但 intent 有 direction/validate 子动作，settings 没有）。

### `ProjectSettings` 数据形状（[settings.py](../../backend/src/cardenio/api/routes/settings.py) `class ProjectSettings`，前端需新增类型）

`ProjectSettings`（`extra="forbid"`）：

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `ui_language` | `string` | `"zh-CN"` | 界面语言。默认从 `project.ui_language` 取。**本期只读展示** |
| `source_language` | `string` | `"zh-CN"` | 源语言。默认从 `project.source_language` 取。**本期只读展示** |
| `output_language` | `string` | `"zh-CN"` | 输出语言。默认从 `project.output_language` 取。**本期只读展示** |
| `data_storage_location` | `"configured_sqlite_database"`（字面量） | 同左 | 数据存储位置枚举（PUT 时被后端**强制**回写此值，作者改不了） |
| `data_storage_notice` | `string` | 见后端常量 | 数据存储位置说明文案（**英文**，PUT 时被强制回写） |
| `allow_model_training` | `boolean` | `false` | 「不用于训练」开关。**后端强制 `false`**（PUT 传 `true` → 422）。**UI 做只读「已关闭」展示** |
| `training_notice` | `string` | 见后端常量 | 不用于训练承诺文案（**英文**，PUT 时被强制回写） |
| `local_processing_reserved` | `boolean` | `true` | 是否保留本地/私有处理路径（PUT 时被强制回写 `true`） |
| `local_processing_notice` | `string` | 见后端常量 | 本地处理说明文案（**英文**，PUT 时被强制回写） |
| `shot_hints_enabled` | `boolean` | `false` | **镜头建议项目级默认开关。本期唯一可编辑字段** |

> **`*_notice` 三个字段是后端给的英文文案。** 与 M7 报告的 `ReportEntry.desc` 同理：**展示时优先用前端本地化文案**（按字段语义写中/英 i18n），把后端 `*_notice` 作为**兜底/补充**（可作为副文本或在本地化键缺失时回退）。`data_storage_location` 是枚举，用本地化映射展示。

### M8 必须知道的真实行为与坑（执行 Agent 必照）

1. **`GET settings` 在「未存工件」时返回的是裁剪信封（缺 `etag`/`updated_at`/`needs_recompute`，`version:null`）。** 前端 `ArtifactEnvelope<T>` 类型要求这些字段为非空（[types.ts](../../frontend/app/lib/api/types.ts) `version: string`）。**http 客户端 `settings.get` 必须把默认响应规整成完整信封**（补 `etag:null`、`needs_recompute:false`、`updated_at` 用当前时间、`version` 用空串或原值），否则下游消费 `envelope.version` 等字段会拿到 `undefined`/`null`。PUT 返回的是完整信封，无需特判。**规整逻辑放 http 客户端，组件零分支。**
2. **`settings` 不进 `project.state`、不在「幕步骤条」里。** `settings` 不在 [stages.ts](../../frontend/app/lib/stages.ts) 的 `stages[]` 中（它经 [project-layout.tsx](../../frontend/app/routes/project-layout.tsx) 侧栏入口进入，不是阶段流的一环）。**门控：只要项目存在即可进入设置页**（无前置工件门控）。不看 `project.state`/`project.gates`，不动 stages.ts。
3. **`allow_model_training` 后端强制 `false`，UI 不得提供可开启的开关。** 做成 **`disabled` 的 `Switch`（恒 `checked={false}`）+ 承诺说明**，或纯文本「已关闭（不可开启）」。**绝不**发 `allow_model_training:true` 的 PUT（会 422）。
4. **PUT body 必须是完整 `ProjectSettings`（`extra="forbid"`）。** 保存时 payload = **「当前 GET 到的 settings.data」整体回传，仅改 `shot_hints_enabled`**；锁定/notice/location 字段照原样带上（后端会再强制规整，但少传字段不会报错——所有字段有默认值——为稳妥仍全量回传，避免 `extra="forbid"` 误伤未来字段）。
5. **语言三分有两份且本期不同步（后端缺口）。** `project.meta.{ui,source,output}_language`（建项目时设、本期**唯一**真实来源）与 `settings.data.*_language`（默认从 project 取，但 PUT settings **不回写 project**）各自独立。**本期语言只读，数据一律取 `project.meta`**（保证显示的是生成实际用的值）；PUT 时 `settings.data` 里的语言字段照原值带上即可，不作为编辑项。
6. **`PATCH /projects`（API-2）与 `DELETE /projects` 后端未实现（`NotImplementedError`，会 500）。** 故语言「同步回项目」本期不可做（见决策 1）。前端 `projects.patch`/`projects.remove` 客户端方法虽存在，但打真实后端会 500——**本计划不调用它们**。
7. **api.md §13 的字段名与实际后端模型不一致。** [api.md §13](../../docs/design/api.md) 示例用 `no_training`/`shot_hints_default`/`storage_region`/`data_usage_notice_ack`，**实际 `settings.py` 模型不是这些名字**（见上表）。**一律以实际 `ProjectSettings` 为准**，不要照抄 api.md 示例字段名。
8. **`404` 走 FastAPI 默认 `detail`（字符串）。** 项目不存在的 `404` 是 `{"detail":"Project not found"}`；既有 [http.ts](../../frontend/app/lib/api/http.ts) `request()` 已兜底（`payload.error ?? {message: detailMessage}`）。但**设置页基本不会遇到 404**（能进项目页说明项目存在）；仍按既有方式处理。

---

## 总体方案与不变量

- **资源契约层沿用既有模式：** 在 [client.ts](../../frontend/app/lib/api/client.ts) 新增 `SettingsApi`（`get`/`update`），http 与 mock 双实现，经 `VITE_API_MODE` 切换；组件零分支消费同一接口。**默认信封规整在 http 客户端内完成（坑 1）。**
- **零新增 npm 依赖、零新增 coss 组件：** 设置页所需 `card`/`badge`/`button`/`switch`/`field`/`label`/`separator`/`alert`/`empty`/`toast` **全部已装**（见 [app/components/ui/](../../frontend/app/components/ui/)）。业务逻辑用原生 `fetch` + React Router v7 内置 `clientLoader`/`useRevalidator`（仓库 `ssr:false`）。**因此本计划 README 无需更新**。
- **复用既有页面范式：** 设置页是「读工件 → 表单编辑 → PUT 保存 → revalidate」，**结构镜像 [analysis-intent.tsx](../../frontend/app/routes/analysis-intent.tsx)**（`getOrNull` loader、`useState` 表单、`Switch` + `Field`/`Label` 行、`toastManager` + `revalidator`、`Card`>`CardHeader`(`CardAction` 放保存按钮)+`CardPanel`）。复用其 `IntentSwitch` 同款「label/description + Switch 行」布局（可在本页内重写一个等价的小组件，不跨文件抽公共件，保持 PR 边界）。
- **信任能力对齐：** M8-T2 在设置层兑现 NFR-1——把「数据存储位置 / 不用于训练承诺 / 本地处理保留」从隐式平台保证变成**作者可见**的显式声明。
- **main 始终可运行：** 每个 PR 自身 `pnpm typecheck`/`build`/`lint`/`format:check` 通过；功能需后端在跑才能手测（mock 模式可离线走流程）。

---

## PR 拆分（3 个 PR，依次从 `main` 切分支）

> 分支名正则：`<type>/<小写-数字-连字符-点>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore/refactor。
> commit 正则：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**。
> pre-commit 跑 lint、pre-push 跑 build + 分支名校验。每个 PR 合并后 main 可运行，用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式填写并勾选合规项。
>
> **依赖顺序：** PR1（客户端）→ PR2（设置页）→ PR3（剧本页采用设置默认）。PR3 依赖 PR1（要读 settings），与 PR2 逻辑独立但建议排在 PR2 后。提交时间须落在 2026-06-07（北京时间）。

---

### PR 1 — 设置 API 客户端（数据层，无 UI）

- **分支：** `feat/settings-api-client`
- **一句话目标：** 按后端真实行为给 API 客户端新增 `SettingsApi`（`get`/`update`），含 types + client 接口 + http 实现（**含默认信封规整**）+ mock 实现，不接任何 UI。
- **改动文件：**
  - [types.ts](../../frontend/app/lib/api/types.ts)：新增类型（字段严格对齐上文「`ProjectSettings` 数据形状」）：
    - `ProjectSettingsData { ui_language: string; source_language: string; output_language: string; data_storage_location: "configured_sqlite_database"; data_storage_notice: string; allow_model_training: boolean; training_notice: string; local_processing_reserved: boolean; local_processing_notice: string; shot_hints_enabled: boolean }`
  - [client.ts](../../frontend/app/lib/api/client.ts)：
    - 新增 `SettingsApi` 类型：
      - `get(projectId: ProjectId): Promise<ArtifactEnvelope<ProjectSettingsData>>`
      - `update(projectId: ProjectId, data: ProjectSettingsData): Promise<ArtifactEnvelope<ProjectSettingsData>>`
    - 把 `settings: SettingsApi` 加入 `ApiClient` 类型，并在 `import type {...}` 里补 `ProjectSettingsData`。
  - [http.ts](../../frontend/app/lib/api/http.ts)：实现 `settings`：
    - `get` = `GET /projects/{projectId}/settings`，**对响应规整成完整信封**（坑 1）：`{ type:"settings", state: payload.state ?? "confirmed", version: payload.version ?? "", parent_version: payload.parent_version ?? null, etag: payload.etag ?? null, updated_at: payload.updated_at ?? new Date().toISOString(), needs_recompute: payload.needs_recompute ?? false, data: payload.data }`。写一个小 `normalizeSettingsEnvelope(payload)` 局部函数完成，**只在缺字段时补默认**。
    - `update` = `PUT /projects/{projectId}/settings`（body = `JSON.stringify(data)`；返回完整信封，原样返回）。
  - [mock.ts](../../frontend/app/lib/api/mock.ts)：给 `settings` mock 加实现，**复刻后端默认值/锁定语义**供离线 UI 开发：
    - 新增 `const settingsStore = new Map<ProjectId, ArtifactEnvelope<ProjectSettingsData>>();`（与其它 store 并列）。
    - 在 `projects.remove` 里追加 `settingsStore.delete(id);`（与 `reportStore.delete(id)` 并列）。
    - 新增内部工具 `defaultSettings(project: Project): ProjectSettingsData`：从 `project.meta` 取三语言，其余字段用后端同款默认（`data_storage_location:"configured_sqlite_database"`、三个 `*_notice` 用与后端一致的英文常量、`allow_model_training:false`、`local_processing_reserved:true`、`shot_hints_enabled:false`）。
    - `settings.get(projectId)`：`getProjectOrThrow` → `settingsStore.get(projectId)` 否则用 `makeEnvelope("settings","confirmed", defaultSettings(project))`（**不写回 store**，仅返回默认，镜像后端「未存即返回默认」）。
    - `settings.update(projectId, data)`：`getProjectOrThrow` → **强制规整锁定字段**（`allow_model_training:false`、`data_storage_location`/三 `*_notice`/`local_processing_reserved` 回写为默认常量），`const envelope = makeEnvelope("settings","confirmed", normalized, settingsStore.get(projectId)?.version ?? null)` → `settingsStore.set` → 返回。**若入参 `allow_model_training===true`，按后端语义 `throw new ApiError(422, {...})`**（保证 mock 与后端一致，UI 永不会触发，但保留对称）。**不改 project.state / project.meta**（与后端缺口一致）。
    - **mock 离线提示（写进 PR 描述，不写进代码）：** 设置页无前置工件门控，mock 模式下任意 seed 项目直接进 `/settings` 即可测；首次 GET 返回默认设置，PUT 后再 GET 取到持久化值。
  - **不在本 PR：** 任何路由/页面/组件改动。
- **建议 commits：**
  1. `feat(frontend): add project settings api types`（types.ts）
  2. `feat(frontend): add settings api client http and mock`（client.ts + http.ts + mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint`/`format:check` 全过；app 行为与本 PR 前一致。mock 模式控制台手调 `api.settings.get(projectId)`（返回完整信封、`data` 含全部字段、语言来自 project）、`api.settings.update(projectId, {...data, shot_hints_enabled:true})`（返回信封、`shot_hints_enabled:true`、锁定字段被规整、`allow_model_training` 恒 false）；http 模式确认默认响应被规整为完整信封（无 `undefined` 字段）。

---

### PR 2 — 设置页（M8-T2 隐私与训练承诺 + 镜头默认 + 只读语言）

- **分支：** `feat/settings-workbench`
- **一句话目标：** 把 [project-settings.tsx](../../frontend/app/routes/project-settings.tsx) 从占位升级为「项目设置」：隐私与训练承诺面板（只读）+ 镜头建议默认开关（可编辑、可保存）+ 语言三分只读展示 + 保存。
- **先安装 coss 组件：** 无需新装（用 `card`/`badge`/`button`/`switch`/`field`/`label`/`separator`/`alert`/`toast`，均已装）。
- **改动文件：**
  - [project-settings.tsx](../../frontend/app/routes/project-settings.tsx)：
    - 复制 M5/M7 同款 `getOrNull`（404→null）小工具。
    - `clientLoader`：并行 `getOrNull(api.settings.get)` + `api.projects.get`。返回 `{ settings, project, projectId }`（`settings` 理论上恒非 null——后端无工件也返回默认；仍用 `getOrNull` 兜底，null 时本地构造默认对象渲染）。
    - 页眉用既有 `pages.settings.*`（milestone/title/description）+ `Badge` 显示工件 state（`confirmed`，复用 `statusVariant` 同款映射）。
    - **隐私与训练承诺卡**（`Card`>`CardHeader`(title/description)+`CardPanel`，**只读**）：
      - **不用于训练**：一行「label + 说明 + 只读 `Switch`」——`Switch checked={false} disabled`（坑 3，不可开启）+ `Badge variant="success"`「已关闭」+ 本地化承诺文案（副文本可附后端 `settings.data.training_notice`）。
      - **数据存储位置**：`data_storage_location` 用本地化映射展示（如「本后端环境配置的 SQLite 数据库」）+ 本地化说明（副文本可附 `data_storage_notice`）。
      - **本地/私有处理**：本地化说明（副文本可附 `local_processing_notice`）+ `Badge`「已保留」。
    - **生成偏好卡**（`Card`，可编辑）：
      - **镜头建议默认**：一行「label + 说明 + `Switch`」——`Switch checked={form.shot_hints_enabled} onCheckedChange={...}`，受控本地 state。说明文案点明「作为剧本生成的镜头建议默认值」。
      - `CardAction`/底部放「保存设置」`Button loading={working} onClick={saveSettings}`。
    - **语言卡**（`Card`，**只读**）：界面/源/输出语言三项,各用 `Field`>`FieldLabel`+只读值（`Badge variant="secondary"` 或纯文本，值取 `project.meta.{ui,source,output}_language`，经本地化映射如 `zh-CN→简体中文`），并附一行说明「语言在创建项目时设定，暂不支持在此修改」（呼应后端缺口）。
    - **保存逻辑**：`saveSettings()` → `setWorking(true)` → `const payload: ProjectSettingsData = { ...settings.data, shot_hints_enabled: form.shot_hints_enabled }`（坑 4：全量回传，仅改可编辑项）→ `api.settings.update(projectId, payload)` → 成功 `toastManager.add(success)` + `revalidator.revalidate()`；失败 toast 显示 `ApiError.message`。保存期间按钮 `loading` 且禁用。
    - **本地表单 state**：`const [form, setForm] = useState({ shot_hints_enabled: settings?.data.shot_hints_enabled ?? false })`（仅承载唯一可编辑字段）。
  - i18n 两 locale [zh-CN/common.json](../../frontend/app/i18n/locales/zh-CN/common.json) 与 [en/common.json](../../frontend/app/i18n/locales/en/common.json)：新增 `settings.*` 命名空间（两 locale 键完全一致）：状态徽标、隐私卡（标题/说明、不用于训练 label/说明/「已关闭」、数据存储 label/位置枚举映射/说明、本地处理 label/说明/「已保留」）、生成偏好卡（标题、镜头默认 label/说明）、语言卡（标题、三语言 label、语言代码→名称映射 `zh-CN`/`en`/`mixed`/`unknown`、不可编辑说明）、保存按钮、成功/失败 toast。复用 `pages.settings.*` 作页眉、`language.*`（若已有语言名映射）避免重复造键——**先查 [language](../../frontend/app/i18n/locales/zh-CN/common.json) 命名空间是否已有语言名**，有则复用，无则在 `settings.languages.*` 下建。
- **建议 commits：**
  1. `feat(frontend): add settings page i18n keys`（两 locale）
  2. `feat(frontend): build project settings and privacy page`（隐私卡 + 镜头默认 + 只读语言 + 保存）
- **验收：** 任意项目进 `/settings` → 看到隐私与训练承诺（不用于训练 `Switch` 禁用且为关、数据存储与本地处理说明可读）、镜头建议默认开关可切换、语言三分只读展示；切换镜头开关并「保存设置」→ 成功 toast、刷新后值保持（再进页仍为新值）；`allow_model_training` 无任何可开启入口。`build`/`typecheck`/`lint`/`format:check` 过。

---

### PR 3 — 剧本生成采用设置页镜头默认（决策 2，M5-T7）

- **分支：** `feat/script-shot-hints-default`
- **一句话目标：** 让 [project-script.tsx](../../frontend/app/routes/project-script.tsx) 剧本生成的镜头建议默认值改为「优先用既有剧本工件值，否则用设置页 `shot_hints_enabled`」，使设置页的项目级默认真正驱动首次生成。
- **先安装 coss 组件：** 无需新装。
- **改动文件：**
  - [project-script.tsx](../../frontend/app/routes/project-script.tsx)：
    - `clientLoader` 并行请求里追加 `getOrNull(api.settings.get(projectId))`，返回值加入 `settings`。
    - 镜头开关初始化（当前 `useState(screenplay?.data.shot_hints.enabled ?? false)`）改为 **`useState(screenplay?.data.shot_hints.enabled ?? settings?.data.shot_hints_enabled ?? false)`**——已有剧本时仍以剧本工件值为准（不破坏既有行为），**仅在尚未生成剧本时采用设置默认**。
    - 其余生成逻辑不变（`generateScreenplay` 仍按当前 `shotHints` 本地 state 传 `shot_hints`）。
    - **不**在剧本页写回 settings（设置页才是 `shot_hints_enabled` 的写入点）；剧本页只「读默认」。
  - i18n：无新增键（本 PR 不加文案；若想在剧本页镜头开关旁加一句「默认来自项目设置」提示，则两 locale 同步加一个 `script.shotHintsDefaultHint` 键，可选）。
- **建议 commits：**
  1. `feat(frontend): seed script shot hints from project settings`（loader + 初始化默认）
- **验收：** 在设置页把镜头默认设为「开」并保存 → 进入**尚未生成剧本**的项目 `/script` → 镜头开关默认呈「开」（来自设置）；对**已生成剧本**的项目，开关仍反映剧本工件既有值（不被设置默认覆盖）。`build`/`typecheck`/`lint`/`format:check` 过。

---

## coss UI 组件映射（每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`。导入 `~/components/ui/<name>` 的**已样式化导出**优先于 `*Primitive`。**M8 不新装任何 coss 组件**，也无新增 npm 依赖。

| 界面元素 | coss 组件（已装） | 关键 composition / 注意点 | 所属 PR |
| --- | --- | --- | --- |
| 卡片容器（隐私 / 生成偏好 / 语言） | `card`/`separator` | 每组一个 `Card`>`CardHeader`(`CardTitle`+`CardDescription`)+`CardPanel`；保存按钮放 `CardAction` 或 `CardPanel` 底部；组内分隔用 `Separator`。保持 `CardHeader`/`CardPanel` 为 `Card` 直接子级 | PR2 |
| 工件状态徽标 / 「已关闭」「已保留」/ 语言只读值 | `badge` | `Badge variant={statusVariant(state)}`（`confirmed`→success）；「已关闭」用 `variant="success"`、语言只读值用 `variant="secondary"` | PR2 |
| 不用于训练（只读开关）/ 镜头建议默认（可编辑开关） | `switch`+`field`/`label` | 镜像 intent 页 `IntentSwitch`：`<div className="flex items-start justify-between ... border p-3">` 内左 `Label`+说明、右 `Switch`。**不用于训练：`Switch disabled checked={false}`（坑 3）**；镜头默认：受控 `Switch checked onCheckedChange` | PR2 |
| 语言三分只读项 | `field`/`label`+`badge` | `Field`>`FieldLabel`+只读值（`Badge`/文本），附 `FieldDescription` 说明不可编辑 | PR2 |
| 保存设置 | `button` | `Button loading={working} onClick={saveSettings}`，保存期禁用 | PR2 |
| 操作成功/失败反馈 | `toast` | `toastManager.add({title,description,type})`；root 已接 provider | PR2 |
| （PR3）无新 UI | — | 仅 loader + 默认值初始化；可选加一句默认来源提示文案 | PR3 |

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **默认信封规整在 http 客户端完成（坑 1）。** `settings.get` 对「未存工件」的裁剪响应补齐 `etag:null`/`needs_recompute:false`/`updated_at`/`version`，保证组件拿到的恒是完整 `ArtifactEnvelope`。组件不做缺字段分支。
2. **`allow_model_training` 永远只读、恒 false、永不 PUT true（坑 3）。** UI 用 `disabled` Switch + 「已关闭」徽标；保存 payload 里照原值（false）带上，绝不构造 true。
3. **PUT 全量回传（坑 4）。** payload = `{ ...settings.data, shot_hints_enabled }`；锁定/notice/location/语言字段照原值带上（后端会再强制规整），不漏字段、不混入信封字段。
4. **语言只读、数据取 `project.meta`（坑 5、决策 1）。** 展示用 `project.meta.{ui,source,output}_language` 经本地化映射；本期不提供编辑、不调 `projects.patch`（后端未实现，坑 6）。
5. **门控：项目存在即可进设置页（坑 2）。** 无前置工件门控，不看 `project.state`/`project.gates`，不动 stages.ts、不进幕步骤条。
6. **不展示后端英文 `*_notice` 作主文案。** 主文案用本地化键；`*_notice`/枚举值作兜底副文本或本地化缺失回退（与 M7 `desc` 同处理）。
7. **PR3 不破坏既有剧本页行为。** 镜头默认仅在「尚无剧本工件」时采用设置值；已有剧本仍以剧本工件 `shot_hints.enabled` 为准。剧本页只读设置、不写设置。
8. **i18n 两 locale 同步：** 每个新增键在 `zh-CN` 与 `en` 完全一致；新增统一挂 `settings.*` 命名空间（`settings.privacy.*`/`settings.generation.*`/`settings.languages.*`/`settings.save.*`），复用 `pages.settings.*` 作页眉、已有 `language.*`（若有）作语言名，避免重复造键。
9. **coss 用法红线**（照 coss skill）：① 导入已样式化导出优先于 `*Primitive`；② `Switch` 受控用 `checked`/`onCheckedChange`，只读用 `disabled`；③ `Card` 保持 `CardHeader`/`CardPanel` 为直接子级；④ `Field`/`Label` 配对、`Label htmlFor` 对应控件 `id`；⑤ 图标按钮补 `aria-label`；⑥ Toast 直接 `toastManager.add`。
10. **冒号动作段不涉及（settings 只有前缀根 `GET`/`PUT`，无 `:action`）。** 路径直接 `/projects/{id}/settings`。

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- **`PATCH /projects`（API-2）与 `DELETE /projects` 未实现（`NotImplementedError`，500）：** 故语言三分本期只读、无法在设置页编辑并同步回 `project.meta`。**已就此提 issue（API-2 项目元数据更新），** 后端补齐后前端可把语言三分改为可编辑（设置页保存时同时 `PUT settings` + `PATCH /projects` 保持一致）。
- **`GET settings` 未存工件时返回裁剪信封（缺 `etag`/`updated_at`/`needs_recompute`、`version:null`）：** 前端 http 客户端已规整。后端如后续统一返回完整默认信封，前端规整逻辑可简化（无须改组件）。
- **`settings.data` 语言与 `project.meta` 语言两份不同步：** `PUT settings` 不回写 project。本期以 `project.meta` 为唯一展示来源规避。
- **`*_notice` 为英文、不可本地化：** 前端按字段语义本地化，`*_notice` 仅作兜底副文本。
- **导出（export，API-27/28）后端为 `NotImplementedError`、本期不接：** 设置页不提供导出入口。后端实现后单独一期接入。

> 这些只标注、不改后端。若后端补齐 API-2 / 完整默认信封 / 导出，前端可据此扩展。

---

## 验证方式（端到端）

1. **起后端：** `backend/` 按其工具启动 dev 服务（[dev_server.py](../../backend/scripts/dev_server.py)，`:8000`）。
2. **起前端：** 仓库根 `pnpm install`（本计划**无任何新 npm 依赖**）→ `pnpm dev`（默认 http，经 Vite 代理打 `:8000`）。
3. **冒烟（按 PR 累积）：**
   - PR1：`typecheck`/`build` 过；mock 控制台手调 `api.settings.get`（完整信封、语言来自 project、`shot_hints_enabled:false`）、`api.settings.update({...data, shot_hints_enabled:true})`（返回信封、值更新、锁定字段被规整、`allow_model_training` 恒 false）；http 模式确认默认响应被规整为完整信封。
   - PR2：进 `/settings` → 隐私卡（不用于训练禁用且为关、数据存储/本地处理说明可读）、镜头默认可切换、语言只读展示；切换镜头并「保存设置」→ 成功 toast、刷新后保持；`allow_model_training` 无可开启入口。
   - PR3：设置页镜头默认设「开」并保存 → 进尚未生成剧本的项目 `/script` → 镜头开关默认「开」；已生成剧本的项目开关仍反映剧本工件值。
   - 离线：任一 PR 后 `VITE_API_MODE=mock pnpm dev` 仍可走完「进 settings → 改镜头默认 → 保存 → 进 script 看默认」流程（mock 复刻默认值/锁定/持久化）。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。人工点检 Switch 的禁用态可读性与键盘可达、Label/控件关联。
5. **窗口与规范：** 提交时间落在 2026-06-07（北京时间）；分支名/commit 经 hooks 校验（subject 纯 ASCII）；每 PR 用 [pull_request_template.md](../../.github/pull_request_template.md) 五段式并勾选合规项。

---

## AGENTS.md 合规要点

- **单一边界：** PR1 客户端、PR2 设置页、PR3 剧本页采用设置默认——每个 PR 一个清晰边界，互不混入无关重构/样式。
- **README 更新：** **本计划无新增第三方依赖、无新增外部来源、无运行/测试流程变化、无 coss 新组件**，故 **README 无需更新**。每个 PR 的「来源与依赖」段写「无新增第三方依赖；复用既有 API 客户端模式、已装 coss 组件」。
- **PR 描述据实披露：** 复用既有 API 客户端模式与 coss 基座；后端缺口（PATCH /projects 未实现、settings 默认裁剪信封、语言两份不同步、notice 英文、导出未实现）如实说明，不得把后端能力写成前端原创。
- **main 每次合并后可 `pnpm build` 通过、可启动；提交在开发窗口内（2026-06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。**
