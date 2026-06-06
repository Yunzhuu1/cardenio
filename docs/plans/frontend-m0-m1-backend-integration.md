# 前端接入后端 M0/M1 接口 — 实现计划

> 面向执行 Agent 的实施文档。后端同学已完成 M0（项目管理）与 M1（导入预处理）接口，本计划把这两层接到前端，并把 M1 导入页从占位升级为可用界面。**全程只改 `frontend/`，不改 `backend/`。**

---

## Context（为什么做、目标）

- 产品流程的第一步是「导入小说 → 满足 ≥3 章门槛 → 进入理解层」。后端已经把这一步的接口（M0 项目 + M1 源文件）实现完毕（见下「后端现状核对」），但前端当前：
  - API 客户端层（`frontend/app/lib/api/`）**只有 `projects` 资源**，且默认走内存 mock（`VITE_API_MODE` 默认 `mock`），从未真正打过后端。
  - 导入页 [project-import.tsx](frontend/app/routes/project-import.tsx) 只是 `StagePlaceholder` 占位，没有任何导入交互。
- 目标产出：作者能在前端**新建项目 → 粘贴/按章录入或上传 TXT/DOCX → 自动切分预览并确认 → 查看章节列表与字数/章节计数 → 通过 ≥3 章门槛 → 进入下一阶段**，全部数据来自真实后端。
- 已与用户确认的三项决策：
  1. **范围 = API 客户端 + 可用导入 UI**（不是只接客户端、也不是只接项目）。
  2. **联调方式 = Vite 代理；默认模式翻转为 `http`**（mock 改为 opt-in）。
  3. **章节标题后端不持久化的问题：接受并在计划/PR 中标注为后端缺口**，前端用派生标签显示，不阻塞。

---

## 后端现状核对（执行前必读，避免按 api.md 想当然）

`docs/design/api.md` 是「全量契约」，但**后端 M0/M1 只实现了其中一部分，且有若干与 api.md 不一致的真实行为**。以下以**代码实际行为为准**（已逐文件核对）：

### M0 · 项目（[backend/.../routes/projects.py](backend/src/cardenio/api/routes/projects.py)）

| 方法 路径 | 实际行为 | 注意点 |
| --- | --- | --- |
| `POST /api/v1/projects` | 201，请求体即 `ProjectMeta`：`{title, ui_language, source_language, output_language, adaptation_direction, style_fingerprint?}`。返回**扁平**项目对象 | `ProjectMeta` 设了 `extra="forbid"`：**多传任何字段会 422**。前端 `CreateProjectInput` 恰好只含允许字段，勿增字段 |
| `GET /api/v1/projects` | 200，`{items:[{id,title,state,updated_at}], next_cursor:null}` | 与前端 `ProjectSummary` 一致 |
| `GET /api/v1/projects/{id}` | 200，返回**扁平**项目；不存在时 `404 {"detail":"Project not found"}` | 见下「形状不一致」 |
| `PATCH /api/v1/projects/{id}` | **未实现**，抛 `NotImplementedError` → 500 | 本期不接入，前端不要触发 |
| `DELETE /api/v1/projects/{id}` | **未实现** → 500 | 同上 |

**关键：项目对象「形状不一致」。** 后端 `GET/POST` 返回的是扁平结构：
`{ id, title, ui_language, source_language, output_language, state, adaptation_direction, style_fingerprint }`
——**没有** `meta`、**没有** `gates`、**没有** `updated_at`（仅列表项有 `updated_at`）。
而前端 [types.ts](frontend/app/lib/api/types.ts) 的 `Project = ProjectSummary & { meta, gates }`（嵌套）。当前 M0/M1 页面只读 `id/title/state`（这三者扁平结构里都有），所以即便不适配也「能跑」，但类型与运行时不符是隐患。**本计划在 http 适配层做一次扁平→嵌套归一化**。

**项目状态不前进的缺口：** M1 的 source 路由**从不调用** `update_project_state`，所以导入原文后 `project.state` 仍是 `"empty"`。因此 [project-layout.tsx](frontend/app/routes/project-layout.tsx) 顶部「幕步骤条」里 `import` 永远不会显示为完成（`isStageDone('import', state)` 需要 `state>=imported`）。→ **导入是否完成必须由 `GET /source` 的 `threshold.passed` 派生，不能依赖 `project.state`。** 这是后端缺口，标注但不修。

### M1 · 源文件（[backend/.../routes/source.py](backend/src/cardenio/api/routes/source.py)）

路由前缀：`/api/v1/projects/{project_id}/source`

| 用途 | 方法 路径 | 请求体 | 返回 |
| --- | --- | --- | --- |
| 录入单章（粘贴/按章） | `POST /chapters` | `{title, text, order?}` | `{id:"ch_N", title, order, char_count, paragraphs:[{index,text}]}` |
| 读取全部源 + 门槛 | `GET ` (前缀根) | — | `{chapters:[{id,title,order,char_count,paragraphs:[{index,text}]}], stats:{chapter_count,char_count,min_chapters}, threshold:{min_chapters,passed,blocked}}` |
| 门槛单查 | `GET /threshold` | — | 通过 200 `{min_chapters,current_chapters,current_chars,passed}`；不足 409 错误信封 |
| 文件导入（预览，不落库） | `POST /import` | `multipart/form-data`，字段名 **`file`** | `{chapters:[{title, char_count, paragraphs:[start,end], text}], warnings:[]}` |
| 确认导入（落库） | `POST /import:confirm` | `{chapters:[{title,text,order?}]}` | 同 `GET ` 的源结构 |
| 编辑章节 | `PUT /chapters/{cid}` | `Chapter` 全量：`{id,title,order,char_count,paragraphs:[{index,text}]}` | 章节回显 |
| 删除章节 | `DELETE /chapters/{cid}` | — | 204；不存在 404 |
| 合并/拆分 | `POST /chapters:resegment` | `{op:"split",chapter_id,at_paragraph}` 或 `{op:"merge",chapter_ids:[...],new_title?}` | 同 `GET ` 的源结构 |

**M1 必须知道的真实行为与坑：**

1. **章节标题不持久化（已确认为后端缺口）。** 没有 chapters 表，只有 `source_paragraphs`（无 title 列）。`GET /source` 的章节标题是从 id 派生的——`list_chapters` 用 `cid.replace("_"," ").title()`，于是 `ch_1` → **"Ch 1"**。无论 `POST /chapters` 还是 `import:confirm` 传什么 `title`，**落库后都丢失**。→ 前端列表渲染时**忽略后端返回的 title，改用按 `order` 派生的本地化标签**（`第 N 章` / `Chapter N`），并在页面挂一条「标题暂不保存（后端待补）」的轻提示。
2. **段落切分依据空行（`\n\n`）。** `POST /chapters` 与 `import:confirm` 都用 `_split_paragraphs`（按 `\n\n` 分块）建段落索引；`_clean_basic` 会把 3+ 连续换行压成 2。→ 录入文本框必须**保留段落间空行**，否则整章会被当成 1 段（影响后续 `source_ref` 溯源粒度）。UI 文案需提示「段落之间空一行」。
3. **`/import` 预览 vs `/import:confirm` 形状不同：** 预览返回的章节是 `{title, char_count, paragraphs:[start,end], text}`（`paragraphs` 是 `[起,止]` 两元区间、且带 `text`、**无 id**）；确认时只需回传 `{title, text, order?}` 列表。两者不要混用类型。
4. **`PUT /chapters/{cid}` 的 `Chapter` 模型 `extra="forbid"`：** 必须**恰好**发送 `{id,title,order,char_count,paragraphs:[{index,text}]}`，多字段会 422。
5. **`:resegment` split 的新章 id 计算为 `ch_{现有数+2}`**，可能产生非连续 id；`merge` 保留首个 id。前端**不要假设 id 连续**，统一用 `GET /source` 回来的 `id` 与派生 `order` 渲染。
6. **错误信封不统一：** `/threshold` 与少量分支返回标准 `{error:{code,message,...}}`，但「项目不存在」等走 FastAPI 默认 `{"detail":...}`，而 `cardenio_error_handler` 在 [app.py](backend/src/cardenio/api/app.py) **并未注册**。前端 [http.ts](frontend/app/lib/api/http.ts) 已对缺 `error` 字段优雅兜底（落到 `code:"unknown"`）；本计划再补一手：兜底时**也读取 `detail` 作为 message**。

### 联调阻塞：无 CORS、无代理

[app.py](backend/src/cardenio/api/app.py) **没挂 CORS 中间件**；后端跑在 `:8000`（[dev_server.py](backend/scripts/dev_server.py)），前端 dev 跑在 `:5173`，[http.ts](frontend/app/lib/api/http.ts) 打相对 `/api/v1`。→ 必须在 [vite.config.ts](frontend/vite.config.ts) 加 `server.proxy` 把 `/api` 转发到后端（**纯前端改动**，符合「不改后端」）。

---

## 总体方案与不变量

- **资源契约层不动既有约定：** 沿用 api.md 字段命名与现有 `ApiClient` 接口模式（[client.ts](frontend/app/lib/api/client.ts) 已留「后续里程碑在此扩展 source/...」注释），新增 `source` 资源，http 与 mock 双实现，经 `VITE_API_MODE` 切换。
- **不引入任何第三方依赖：** 用浏览器原生 `fetch` / `FormData`、React Router v7 内置 `clientLoader`/`clientAction`（仓库 `ssr:false`，必须用 client 版，不能用 `loader`/`action`）。复用现有 `Button`/`Spinner`/`cn`/i18n。
- **main 始终可运行：** 每个 PR 自身可 `pnpm build`/`typecheck`/`lint` 通过；功能需后端在跑才能手测（README 写清）。
- **信任能力对齐：** 本期是导入层，溯源根是 `source_paragraphs` 的 `{index,text}`；保留段落索引语义即可，`source_ref` 的下游消费在 M2+。

---

## PR 拆分（4 个 PR，依次从 `main` 切分支；分支名/commit 已按仓库 hooks 校验）

> 分支名正则（[check-branch-name.sh](scripts/hooks/check-branch-name.sh)）：`<type>/<小写-数字-连字符>`，type ∈ feature/feat/bugfix/fix/hotfix/release/docs/chore。
> commit 正则（[check-commit-msg.sh](scripts/hooks/check-commit-msg.sh)）：`type(scope)?: 描述`，type ∈ feat/fix/docs/chore/test/refactor/style，**subject 必须纯 ASCII**。
> pre-push 会跑 `build`（[verify-project.sh](scripts/hooks/verify-project.sh)）+ 分支名校验；pre-commit 跑 `lint`。每个 PR 合并后 main 可运行。

### PR 1 — 项目层接真实后端（M0 联调）

- **分支：** `feat/connect-projects-backend`
- **一句话目标：** 让现有项目列表/新建/详情页跑通真实 M0 后端：加 Vite 代理、默认切 http、归一化项目形状、强化错误解析、更新 README 运行说明。
- **改动文件：**
  - [frontend/vite.config.ts](frontend/vite.config.ts)：加 `server.proxy`，把 `/api` 转发到后端。target 取环境变量 `VITE_BACKEND_URL`，缺省 `http://localhost:8000`；`changeOrigin: true`；后端已自带 `/api/v1` 前缀，**不做 path rewrite**。
  - [frontend/app/lib/api/client.ts](frontend/app/lib/api/client.ts)：把默认模式从 `?? "mock"` 改为 `?? "http"`（mock 变 opt-in：`VITE_API_MODE=mock`）。
  - [frontend/app/lib/api/http.ts](frontend/app/lib/api/http.ts)：
    1. 新增「扁平项目 → 前端 `Project`」归一化：把后端 `GET/POST /projects` 的扁平体映射为 `{ id, title, state, updated_at, meta:{ui_language,source_language,output_language,adaptation_direction,style_fingerprint}, gates }`。`updated_at` 缺失时回退空串或当前时间；`gates` 后端未提供，统一填默认 `{understanding:"empty",characters:"empty",outline:"empty"}`（M2 前不消费，仅满足类型与未来页面）。`list` 的项保持 `ProjectSummary` 原样（已匹配）。
    2. 错误兜底增强：非 2xx 且无 `payload.error` 时，若有 `payload.detail` 则用作 `message`（code 仍 `unknown`），覆盖后端 FastAPI 默认错误体。
  - [frontend/app/lib/api/vite-env.d.ts](frontend/app/vite-env.d.ts)：在 `ImportMetaEnv` 增 `VITE_BACKEND_URL?: string`（`VITE_API_MODE` 已声明）。
  - [README.md](README.md) §运行方式：新增「前后端联调」小节——说明先起后端（`backend/` 目录按其自身工具运行 dev 服务，监听 `:8000`），再 `pnpm dev` 起前端；说明 `VITE_API_MODE`（默认 http，可设 `mock` 离线开发）与 `VITE_BACKEND_URL`、Vite 代理 `/api → :8000`。这是「运行/demo 流程变化」，按 AGENTS.md README 规则必须更新。
- **mock 保留：** [mock.ts](frontend/app/lib/api/mock.ts) 不动（其 `Project` 已是嵌套形状，离线模式继续可用）。
- **不在本 PR：** 任何 source/导入逻辑；PATCH/DELETE 项目（后端未实现，保持现状，页面不触发）。
- **建议 commits：**
  1. `chore(frontend): proxy /api to backend in vite dev server`（vite.config + vite-env.d.ts）
  2. `feat(frontend): default api client to http mode`（client.ts）
  3. `fix(frontend): normalize flat project payload and detail errors`（http.ts）
  4. `docs: document frontend backend dev integration`（README）
- **验收：** 后端在跑时，`pnpm dev` 概览页列出真实项目；新建项目 `POST /projects` 成功并跳 `/projects/:id/import`；刷新详情页 `GET /projects/:id` 正常；停掉后端时 `VITE_API_MODE=mock pnpm dev` 仍以 mock 运行。`pnpm build`/`typecheck`/`lint` 全过。

### PR 2 — 新增 `source` API 客户端（M1 数据层，无 UI）

- **分支：** `feat/source-api-client`
- **一句话目标：** 按后端真实行为给 `ApiClient` 增加 `source` 资源（types + client 接口 + http 实现 + mock 实现），不接 UI。
- **改动文件：**
  - [frontend/app/lib/api/types.ts](frontend/app/lib/api/types.ts)：新增类型（字段对齐「后端现状核对·M1」表）：
    - `ChapterId`（`"ch_*"`）、`SourceParagraph {index:number; text:string}`、`Chapter {id; title; order; char_count; paragraphs: SourceParagraph[]}`。
    - `SourceStats {chapter_count; char_count; min_chapters?}`、`SourceThreshold {min_chapters; passed; blocked?}`、`Source {chapters: Chapter[]; stats; threshold}`。
    - `CreateChapterInput {title; text; order?}`、`UpdateChapterInput`（= `Chapter` 全量，给 PUT 用）。
    - 导入预览：`ImportChapterPreview {title; text; char_count?; paragraphs?: [number,number]}`、`ImportPreview {chapters: ImportChapterPreview[]; warnings: string[]}`、`ConfirmImportInput {chapters: {title; text; order?}[]}`。
    - `ResegmentInput`：判别联合 `{op:"split"; chapter_id; at_paragraph}` | `{op:"merge"; chapter_ids: string[]; new_title?}`。
  - [frontend/app/lib/api/client.ts](frontend/app/lib/api/client.ts)：`ApiClient` 增 `source: SourceApi`，并在 mock/http 两实现里都补齐。`SourceApi` 方法：
    - `get(projectId): Promise<Source>` → `GET /projects/{id}/source`
    - `addChapter(projectId, input): Promise<Chapter>` → `POST .../source/chapters`
    - `updateChapter(projectId, chapterId, chapter): Promise<Chapter>` → `PUT .../source/chapters/{cid}`（发送 `Chapter` 全量，禁止多字段）
    - `deleteChapter(projectId, chapterId): Promise<void>` → `DELETE`
    - `resegment(projectId, input): Promise<Source>` → `POST .../source/chapters:resegment`
    - `importFile(projectId, file): Promise<ImportPreview>` → `POST .../source/import`（multipart）
    - `confirmImport(projectId, input): Promise<Source>` → `POST .../source/import:confirm`
  - [frontend/app/lib/api/http.ts](frontend/app/lib/api/http.ts)：
    - 实现上述 7 个方法，路径按表拼接，注意 `:resegment` / `import:confirm` 里的冒号是字面量路径段（直接拼，不要 encode 成 `%3A`）。
    - **multipart 处理：** 现有 `request()` 写死 `Content-Type: application/json`，对 `FormData` 会破坏 boundary。新增逻辑：当 body 是 `FormData` 时**不要设 `Content-Type`**（交给浏览器自动带 boundary），其余头（Accept-Language）保留。可在 `request()` 内判 `init.body instanceof FormData` 后删掉 json 头，或加一个 `requestForm()` 辅助。`importFile` 用字段名 **`file`** append 文件。
  - [frontend/app/lib/api/mock.ts](frontend/app/lib/api/mock.ts)：加一份内存 source 存储（`Map<projectId, Chapter[]>`），复刻关键语义供离线 UI 开发：按 `\n\n` 切段建 `{index,text}`、累加 `char_count`、`threshold = chapter_count>=3`、split/merge 重建索引、import 预览（简单整文 → 单章或按「第 N 章」探测）、confirm 落库。标题可在 mock 里**真实保存**（mock 不必复刻后端的标题丢失缺口；以 http 为准即可，注释说明差异）。
- **不在本 PR：** 任何路由/页面改动（没有消费者，纯扩客户端，app 行为不变）。
- **建议 commits：**
  1. `feat(frontend): add source api types`（types.ts）
  2. `feat(frontend): add source resource to api client and http`（client.ts + http.ts，含 multipart）
  3. `feat(frontend): add source mock adapter`（mock.ts）
- **验收：** `pnpm typecheck`/`build`/`lint` 通过；app 运行行为与 PR1 后一致（无新 UI）。可在浏览器控制台手调 `api.source.get(...)`（mock 模式）自测形状。

### PR 3 — 导入页核心：录入 / 列表 / 计数 / 门槛（M1 主体 UI）

- **分支：** `feat/import-stage-core`
- **一句话目标：** 把 [project-import.tsx](frontend/app/routes/project-import.tsx) 从占位升级为可用页：按章/粘贴录入、章节列表（派生标题 + 字数/段落数）、源文件总计数、≥3 章门槛与「进入下一步」CTA、删除章节。**文件导入与拆分/合并放 PR 4。** UI 一律用 coss 组件（见「coss UI 组件映射」表）。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/input @coss/textarea @coss/field @coss/card @coss/collapsible @coss/badge @coss/alert @coss/empty @coss/separator @coss/alert-dialog @coss/toast`（生成到 `app/components/ui/`）。装完 `git diff package.json` 确认无新增 npm 依赖（如有则披露）。
- **Toast 接线（app 级，一次性）：** 在 [root.tsx](frontend/app/root.tsx) 用 `ToastProvider`+`AnchoredToastProvider` 包裹应用内容（包在现有 i18n/theme provider 内层即可），否则 `toastManager.add` 无渲染出口。
- **改动文件：**
  - [frontend/app/routes/project-import.tsx](frontend/app/routes/project-import.tsx)：重写为真实页面。
    - `clientLoader({params})`：调 `api.source.get(projectId)` 取 `Source`；失败（如尚无任何章节，后端 `GET /source` 对空项目应返回空 chapters 而非报错——按实际：`list_chapters` 空时返回 `[]`，`threshold.passed=false`）正常渲染空态。
    - `clientAction`：用 `intent`（隐藏字段 `intent`）区分操作，全部走 `api.source.*` 后 `return null` 让 RR 重新跑 loader 刷新（或返回最新 `Source`）：
      - `add-chapter`：读 `title`、`text`，调 `addChapter`。空 `text` 前端校验拦截。
      - `delete-chapter`：读 `chapterId`，调 `deleteChapter`。
    - 视图结构（组件见映射表）：
      1. 顶部：阶段标题/说明（复用 i18n `pages.import.*`）+ 一条 `Alert variant="info"` 轻提示「章节标题暂不会被保存（后端待补）；段落之间请空一行」。
      2. **录入区**：`Field`+`Input`（标题）、`Field`+`Textarea size="lg"`+`FieldDescription`（正文，提示空行分段）、`Button type="submit" loading`。整块用 react-router `<Form method="post">`，隐藏字段 `intent=add-chapter`。用 `Separator` 与列表分隔。
      3. **章节列表**：遍历 `source.chapters`，每章一个 `Card`：`CardHeader` 放**派生标题**（按 `order` → i18n `import.chapterLabel`，如「第 1 章 / Chapter 1」，忽略后端 `title`）+ `Badge`（`char_count` 字 / `paragraphs.length` 段）+ 删除按钮；卡内 `Collapsible`「查看原文」展开 `paragraphs[].text`（即「原文视图」，FR-1「与源文件一致」靠展示后端回存段落实现）。无章节时渲染 `Empty`。删除走 `AlertDialog` 二次确认。成功/失败用 `toastManager.add`。
      4. **底部门槛条**：读 `source.stats.chapter_count` 与 `source.threshold`，用 `Alert`：
         - 未达标：`variant="warning"`「已 N 章，还需 M 章（≥3）」，**禁用** CTA。
         - 达标：`variant="success"`「已满足 3 章门槛」，`AlertAction` 内放**启用**的「进入下一步」`Button`（render 成 `Link`）→ `/projects/:id/analysis`（理解阶段，目前仍是占位页，可跳转）。
      - **门槛与完成态一律来自 `GET /source`，不读 `project.state`**（见后端缺口）。
  - [frontend/app/i18n/locales/zh-CN/common.json](frontend/app/i18n/locales/zh-CN/common.json) 与 [.../en/common.json](frontend/app/i18n/locales/en/common.json)：新增 `import` 命名空间，键在两个 locale **完全一致**。至少包含：`titleLabel`、`titlePlaceholder`、`textPlaceholder`、`addChapter`、`chapterLabel`（含 `{{n}}` 插值）、`charCount`（`{{count}}`）、`paragraphCount`（`{{count}}`）、`delete`、`deleteConfirm`、`empty`、`thresholdMet`、`thresholdUnmet`（`{{current}}`/`{{need}}`）、`nextStep`、`titleNotPersistedHint`、`paragraphSpacingHint`、`previewToggle`、以及 PR4 需要的 `upload*`/`merge*`/`split*`/`edit*` 键（可在本 PR 先占好或 PR4 再加，保持两 locale 同步）。
- **复用：** [Button](frontend/app/components/ui/button.tsx)（`type="submit"` + `loading`）、[Spinner](frontend/app/components/ui/spinner.tsx)、`cn`、`useNavigation` 的提交态、`Form`/`redirect`/`Link`。设计令牌沿用现有 card/border/muted 等。
- **建议 commits：**
  1. `chore(frontend): add coss components for import stage`（`shadcn add` 生成的 ui 组件 + README「依赖与来源」追加组件清单）
  2. `feat(frontend): wire toast providers in root`（root.tsx 接 ToastProvider）
  3. `feat(frontend): add import stage i18n keys`
  4. `feat(frontend): build chapter entry and source list in import stage`（含 Card/Collapsible/Badge/Empty/AlertDialog/toast）
  5. `feat(frontend): add chapter-threshold gate and next-step cta`（Alert warning/success + CTA）
- **验收：** 后端在跑：新建空项目进入导入页 → 录入 3 章（每章正文含空行）→ 列表显示 3 条、各章字数/段落数正确、底部显示「已满足」并可点「进入下一步」到 analysis；删除一章后回到「还需 1 章」、CTA 禁用；刷新后数据持久（来自后端）。`build`/`typecheck`/`lint` 过。

### PR 4 — 导入页增强：文件导入预览/确认 + 拆分/合并 + 章节编辑

- **分支：** `feat/import-file-and-resegment`
- **一句话目标：** 在导入页补齐 TXT/DOCX 上传（预览→确认）、章节拆分/合并、单章编辑。UI 用 coss 组件（见映射表）。
- **先安装 coss 组件：** `pnpm dlx shadcn@latest add @coss/tabs @coss/menu @coss/dialog @coss/number-field @coss/checkbox`（`alert-dialog`/`field`/`textarea` 等 PR3 已装，复用）。装完 `git diff package.json` 确认依赖，必要时披露。
- **改动文件：**
  - [frontend/app/routes/project-import.tsx](frontend/app/routes/project-import.tsx)：在 PR3 基础上扩展。
    - **录入模式切换：** 用 `Tabs`（`TabsTab`「按章录入」/「文件上传」+ 对应 `TabsPanel`）把 PR3 的录入区与新增的上传区分到两个面板。
    - **文件导入：** 上传面板内 `Field`+`Input type="file"`（accept `.txt,.docx`）。选择文件后调 `api.source.importFile(projectId, file)` 拿 `ImportPreview`，打开一个 `Dialog` 进入**预览编辑态**（本地 React state，非提交）：`DialogPanel` 内逐章 `Field`+`Input`(标题)/`Textarea`(正文)、可删除某预览章；`DialogFooter` 放「确认导入」。确认时把预览章映射为 `ConfirmImportInput`（只取 `{title, text}`，`order` 用下标+1）调 `confirmImport`，成功后刷新 loader 并 toast。要点：
      - **预览与确认形状不同**（预览 `paragraphs:[start,end]+text+无 id`，确认只回传 title/text）——按 PR2 类型区分。
      - `confirmImport` 会**清空并替换**整个项目的已存章节（后端 `delete_all_paragraphs` 后重建）；点「确认导入」前用 `AlertDialog` 二次确认「将替换当前所有章节」。
      - 展示后端返回的 `warnings`（若有），可用 `Alert variant="warning"`。
      - 文件上传是 multipart，**不要**经 `clientAction`/react-router `Form` 默认 json 流程，直接在 `Input[type=file]` 的 onChange 里调客户端方法（`importFile` 内部用 FormData，见 PR2）。
    - **拆分/合并：** 章节卡片操作改用 `Menu`（`MenuTrigger` 为 ghost icon 按钮）聚合「编辑/在第 K 段拆分/在此合并/删除」——
      - 拆分：菜单项打开一个 `Dialog`，内含 `Field`+`NumberField`（`min=2`、`max=该章段落数`）选拆分点 K，确认调 `resegment({op:"split", chapter_id, at_paragraph:K})`。
      - 合并：每张卡加 `Checkbox`（带 `aria-label`）多选 ≥2 章 → 列表上方工具条 `Button`「合并所选」→ `AlertDialog` 确认 → 调 `resegment({op:"merge", chapter_ids:[...], new_title?})`。
      - 两者返回最新 `Source`，刷新列表并 toast。提示用户**章节 id/order 可能重排**（不要在 UI 缓存旧 id）。
    - **单章编辑：** 菜单「编辑」打开 `Dialog`，内 `Field`+`Textarea` 编辑正文（标题可编但会被后端丢弃，UI 标注「标题不保存」或本期只允许编辑正文）。保存时构造 `Chapter` **全量**对象（`id` 用该章现有 id；`paragraphs` 由编辑后的正文按空行重切为 `{index,text}`，`index` 从 1 连续；`char_count` 取段落字数和；`order` 用现值）调 `updateChapter`。**严禁多传字段**（`extra="forbid"`）。
  - 两个 `common.json`：补 `import.upload*`（`uploadButton`/`replaceWarning`/`previewConfirm`/`previewCancel`/`warnings`）、`import.split*`/`import.merge*`/`import.edit*` 键（两 locale 同步）。若 PR3 已占位则在此填值。
- **建议 commits：**
  1. `chore(frontend): add coss components for import enhancements`（`shadcn add` tabs/menu/dialog/number-field/checkbox + README 追加清单）
  2. `feat(frontend): add txt docx import preview and confirm`（Tabs + file Input + Dialog + AlertDialog）
  3. `feat(frontend): add chapter split and merge actions`（Menu + NumberField + Checkbox + AlertDialog）
  4. `feat(frontend): add single-chapter edit`（Dialog + Textarea）
- **验收：** 上传含「第一章/第二章/第三章」标记的 TXT → 预览出 3 章可编辑 → 确认导入后列表 3 章、计数正确、门槛满足；对某章在第 K 段拆分得到两章；勾选两章合并为一章；编辑某章正文后字数/段落数随之更新且刷新持久。`build`/`typecheck`/`lint` 过。

---

## coss UI 组件映射（导入页每个界面元素用哪个组件 — 执行 Agent 照表实现）

> 本项目 UI 用 **coss.ui**（基于 Base UI），经 shadcn CLI 的 `@coss` registry 安装到 `app/components/ui/`（见 [components.json](frontend/components.json) 的 `registries["@coss"]`）。**当前只装了 `button`/`sidebar`/`spinner`**，下表其余组件都需先安装。
> 安装命令统一：`pnpm dlx shadcn@latest add @coss/<name>`（或 `npx`）。安装后从 `~/components/ui/<name>` 导入**已样式化导出**（如 `Card`/`Field`），仅在需要自定义组合时才用 `*Primitive` 导出。
> coss 组件文件由 registry 生成，属第三方基座（非原创业务），**每个引入它们的 PR 必须在 README「依赖与来源」追加所装组件清单，并在 PR 描述据实披露**（沿用现有 coss/shadcn 披露段，见 [README.md](README.md) §依赖与来源）。安装后务必 `git diff package.json` 检查是否带入新 npm 依赖（预期不会，`@base-ui/react` 已在依赖中；若有则一并披露）。

| 界面元素 | coss 组件（安装名） | 关键 composition / 注意点 | 参考 particle | 所属 PR |
| --- | --- | --- | --- | --- |
| 录入区「标题」输入 | `field` + `input` | `Field`>`FieldLabel`+`Input type="text"`。**始终显式写 `type`** | p-field-1 / p-input-6 | PR3 |
| 录入区「正文」输入 | `textarea`（+`field`） | `Field`>`FieldLabel`+`Textarea size="lg"`+`FieldDescription`（写「段落之间空一行」提示）。`Textarea` 已内置 Base UI Field 控件语义，**不要**再套 `FieldControl render` | p-textarea-5 / p-textarea-6 | PR3 |
| 「添加为新章节」按钮 | `button`（已装） | `type="submit"` + `loading`。**提交走 react-router 的 `<Form method="post">`**（导航/动作），coss 的 `Field`/`Input`/`Textarea` 只负责标签与样式；**不要**再叠加 coss `Form`（除非要做 zod 客户端校验） | — | PR3 |
| 顶部「标题不保存 / 段落空行」轻提示 | `alert` | `Alert variant="info"`>图标+`AlertTitle`/`AlertDescription`。语义图标**不要**加 `aria-hidden` | p-alert-4 | PR3 |
| 章节列表 — 每章卡片 | `card` | 每章一个 `Card`：`CardHeader`（派生标题 + 计数 Badge + 操作）/ body（原文折叠）。比 Table 更适合「可展开看原文」 | p-card-1 | PR3 |
| 派生章节标题 | （纯文本，置于 `CardTitle`） | 用 i18n `import.chapterLabel`（按 `order` 派生），**忽略后端 title** | — | PR3 |
| 字数 / 段落数 | `badge` | `Badge variant="secondary"` 或 `outline`，如「1234 字」「8 段」 | p-badge-3 | PR3 |
| 「查看原文」展开段落 | `collapsible` | 每张卡内 `Collapsible`：trigger「查看原文」、panel 列出 `paragraphs[].text`。**用 Collapsible 而非把按钮塞进 Accordion trigger**，避免按钮嵌套按钮的 a11y 问题 | p-collapsible-1 | PR3 |
| 区块分隔 | `separator` | 录入区与列表之间、卡内 meta 与正文之间 | p-separator-1 | PR3 |
| ≥3 章门槛提示 | `alert` | 未达标 `Alert variant="warning"`（「已 N 章，还需 M 章」）；达标 `variant="success"`。可用 `AlertAction` 容纳「进入下一步」按钮 | p-alert-6 / p-alert-5 | PR3 |
| 空状态（无章节） | `empty` | `Empty`>`EmptyHeader`（`EmptyMedia variant="icon"` 放 `FileInputIcon`）+`EmptyTitle`/`EmptyDescription` | p-empty-1 | PR3 |
| 删除章节确认 | `alert-dialog` | **破坏性操作用 AlertDialog（非 Dialog）**：`AlertDialogTrigger render={<Button variant="destructive-outline"/>}`，footer 两个 `AlertDialogClose`（取消 ghost / 确认 destructive） | p-alert-dialog-1 | PR3 |
| 操作成功/失败反馈 | `toast` | `toastManager.add({title,description,type})`（成功）/`type:"error"`（失败）。**这是 Base UI toast，不是 Sonner**；需在 [root.tsx](frontend/app/root.tsx) 包 `ToastProvider`+`AnchoredToastProvider`（一次性 app 级接线，放在 PR3 首次用 toast 时） | p-toast-2 | PR3 |
| 录入模式切换（按章录入 / 文件上传） | `tabs` | `Tabs`（可 `variant="underline"`）>`TabsList`/`TabsTab`/`TabsPanel`，两 panel 的 `value` 与 tab 对齐 | p-tabs-2 | PR4 |
| 文件选择 | `input`（+`field`） | `Field`>`FieldLabel`+`Input type="file"`（`accept=".txt,.docx"`），onChange 调 `api.source.importFile` | p-input-5 | PR4 |
| 导入预览编辑弹窗 | `dialog` | `Dialog`>`DialogPopup`>`DialogHeader`(标题在 form 外)+`DialogPanel`(可编辑预览列表，长内容在此滚动)+`DialogFooter`(确认/取消)。若内嵌表单：`<Form className="contents">` 只包 panel+footer | p-dialog-1 / p-dialog-5 | PR4 |
| 「确认导入将替换全部章节」二次确认 | `alert-dialog`（复用 PR3 已装） | 破坏性确认（confirmImport 会清空重建） | p-alert-dialog-1 | PR4 |
| 行操作菜单（编辑/拆分/在此合并/删除） | `menu` | `Menu`>`MenuTrigger render={<Button size="icon" variant="ghost"/>}`+`MenuItem`。删除项仍跳 AlertDialog 确认 | p-menu-1 | PR4 |
| 拆分点选择（第 K 段） | `number-field`（+`field`） | `Field`>`NumberField min=2 max=段落数`>`NumberFieldGroup`(`Decrement`/`Input`/`Increment`)，置于一个 Dialog 内 | p-number-field-7 | PR4 |
| 合并多选 | `checkbox` | 每张卡 `Checkbox`（带 `aria-label`）多选 → 工具条 Button「合并所选」→ AlertDialog 确认 | p-checkbox-1 | PR4 |
| 单章编辑弹窗 | `dialog`（+`field`/`textarea`，已装） | `Dialog` 内 `Field`+`Textarea` 编辑正文；保存时构造 `Chapter` 全量回传 `updateChapter` | p-dialog-1 | PR4 |

**安装清单汇总：**
- **PR3 安装：** `input`、`textarea`、`field`、`card`、`collapsible`、`badge`、`alert`、`empty`、`separator`、`alert-dialog`、`toast`。（`button`/`spinner` 已装；本期录入用 react-router `Form`，**不装 coss `form`**。）
- **PR4 安装：** `tabs`、`menu`、`dialog`、`number-field`、`checkbox`。（`alert-dialog` 等沿用 PR3。）

---

## 跨 PR 的关键实现细则（执行 Agent 必须照此处理，勿自行揣测）

1. **Vite 代理而非改后端：** 只在 [vite.config.ts](frontend/vite.config.ts) 配 `server.proxy['/api'] = { target: VITE_BACKEND_URL || 'http://localhost:8000', changeOrigin: true }`。后端自带 `/api/v1`，不要 rewrite。生产构建是静态 SPA，代理只作用于 dev，与现状一致。
2. **默认 http、mock opt-in：** 仅改 [client.ts](frontend/app/lib/api/client.ts) 的默认值。两实现必须实现**同一** `ApiClient` 接口（含新 `source`），组件零分支。
3. **项目形状归一化只在 http 层做：** 组件继续消费前端 `Project`/`ProjectSummary` 类型，不感知后端扁平结构。mock 已是嵌套，无需改。
4. **multipart 唯一特例：** 仅 `importFile` 用 FormData 且**省略** json `Content-Type`；其余请求保持 json。
5. **路径里的冒号动作段**（`:resegment`、`import:confirm`、`/threshold`）按字面拼接，勿 URL-encode 冒号。
6. **章节标题：** 列表/计数一律用派生标签，**不信任**后端回传 title；页面挂明确提示。这是已确认接受的后端缺口，PR 描述「来源与依赖/合规」里据实写明。
7. **完成态来自 source 门槛**，非 `project.state`（后端不前进 state）。
8. **段落空行语义：** 所有「正文 → 段落」转换（录入、编辑、确认）都按 `\n\n` 切；UI 提示作者段落间空行。
9. **错误呈现：** 复用 `ApiError`（已含 `code`/`message`/`status`）。门槛不足等后端 409 不会在「录入」时触发（录入不校验门槛），仅在下游 `:generate`（本期不调用）才有；前端门槛判断完全基于 `GET /source` 的 `threshold`。
10. **依赖与披露**：PR1/PR2 不加任何包。PR3/PR4 通过 `shadcn add @coss/*` 引入 **coss registry 生成的 UI 组件文件**（第三方基座，非原创）——预期不带新 npm 依赖（`@base-ui/react` 已在），但**每个安装后都要 `git diff package.json` 核对**；README「依赖与来源」的 coss/shadcn 段追加本次新增组件清单，PR 描述「来源与依赖」据实写明这些是 coss 组件、非原创业务。其余自写逻辑（适配器、导入交互、mock）用原生 `fetch`/`FormData`/React Router，无新依赖；涉及后端缺口处据实说明（不得把后端能力写成前端原创）。
11. **coss 用法红线**（照 coss skill）：① 安装名 `@coss/<name>`，导入 `~/components/ui/<name>` 的已样式化导出，优先于 `*Primitive`。② **trigger/popup 组合不可跨组件混用**（Dialog/AlertDialog/Menu/Tabs 各按其文档层级），动作按钮用 `*Trigger`/`*Close` 的 `render={<Button .../>}` 组合。③ 弹窗内表单：`DialogHeader` 在 form 外，`<Form className="contents">` 只包 `DialogPanel`+`DialogFooter`。④ `Input` 必显式 `type`；`Textarea`/`NumberField` 直接放进 `Field`，勿叠 `FieldControl render`。⑤ `Alert` 语义图标不要 `aria-hidden`；选择型/图标按钮补 `aria-label`。⑥ Toast 是 Base UI（非 Sonner）：先在 root 接 `ToastProvider`+`AnchoredToastProvider`，再用 `toastManager.add`。⑦ **破坏性确认（删除/替换/合并）用 `AlertDialog`，普通编辑/预览用 `Dialog`。**

---

## 已知后端缺口（在相关 PR 描述里据实标注，便于后端排期，不在本期修）

- 章节标题不持久化（`GET /source` 返回派生 "Ch N"）。
- 导入原文不前进 `project.state`（停留 `empty`），导致幕步骤条 import 不亮。
- `PATCH/DELETE /projects` 未实现（500）。
- `cardenio_error_handler` 未在 app 注册；部分错误走 FastAPI 默认 `{"detail":...}`。
- 无 CORS（已由前端 Vite 代理规避）。

> 这些只标注、不修改后端。若后端后续补齐标题持久化与 state 前进，前端可去掉派生标签/提示并改用 `project.state`，属后续小改。

---

## 验证方式（端到端）

1. **起后端：** 在 `backend/` 按其工具启动 dev 服务（[scripts/dev_server.py](backend/scripts/dev_server.py)，监听 `:8000`）。确认 `GET http://localhost:8000/api/v1/projects` 可访问（空库返回 `{items:[],next_cursor:null}`）。
2. **起前端：** 仓库根 `pnpm install`（无新依赖）→ `pnpm dev`（默认 http，经代理打 `:8000`）。
3. **冒烟（按 PR 累积）：**
   - PR1：概览列出真实项目；新建项目成功并跳导入占位页；详情刷新正常；`VITE_API_MODE=mock pnpm dev` 离线可用。
   - PR2：`typecheck`/`build` 过；控制台 `api.source.*`（mock）形状正确。
   - PR3：录入 3 章（含空行）→ 列表/计数正确 → 门槛满足 → 「进入下一步」可跳 analysis；删除回退门槛；刷新持久。
   - PR4：上传 TXT/DOCX → 预览编辑 → 确认替换导入；拆分/合并/编正文均刷新且持久。
4. **质量门：** 每 PR `pnpm lint`、`pnpm format:check`、`pnpm typecheck`、`pnpm build` 全过（pre-commit 跑 lint、pre-push 跑 build）。PR3/PR4 装完 coss 组件后 `git diff package.json` 核对依赖，并人工点检 Dialog/AlertDialog/Menu/Tabs 的键盘与焦点返回（coss/Base UI overlay 交互）。
5. **窗口与规范：** 提交时间落在 2026-06-05 ~ 2026-06-07（北京时间，今天 2026-06-06 在窗口内）；分支名/commit 经 hooks 校验；每 PR 用 [pull_request_template.md](.github/pull_request_template.md) 五段式填写，勾选合规项。

---

## AGENTS.md 合规要点

- 每个 PR **单一边界**：PR1 项目联调、PR2 source 客户端、PR3 导入核心、PR4 导入增强——互不混入无关重构/样式。
- README 更新：PR1 改「运行方式/联调」；**PR3/PR4 在「依赖与来源」coss 段追加本次 `shadcn add` 的组件清单**（third-party 生成资产须披露，AGENTS.md §Originality/§README）。
- PR 描述据实披露：复用既有 API 客户端模式与组件；新增的 coss 组件标明为 registry 生成的第三方基座（非原创业务）；后端缺口/标题不持久化如实说明，不冒充原创。
- main 每次合并后可 `pnpm build` 通过、可启动。
- 提交在开发窗口内（2026-06-05~06-07 北京时间）；分支名/commit 过 hooks；每 PR 用仓库 PR 模板五段式。
</content>
</invoke>
