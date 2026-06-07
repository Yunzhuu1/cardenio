# Cardenio 入戏

> AI 小说剧本改编助手，让小说自然入戏。

Cardenio / 入戏 是一款面向中文小说作者的 AI 辅助剧本改编工具。它的目标是帮助作者将 3 个章节以上的小说文本转化为结构清晰、人物一致、可继续打磨的剧本初稿。

产品以中文创作为主，同时从第一版开始预留国际化能力。中文名「入戏」强调小说进入戏剧表达的过程，英文名「Cardenio」来自早期小说改编舞台剧的文学典故，代表从小说文本到戏剧表达的长期传统。

## 产品文档

本 README 是面向读者的概览。详细、具有约束力的规格以下列文档为准：

- [产品需求文档（PRD）](docs/product/requirements.md) — 编号化需求（`FR-x` / `NFR-x`）、设计原则与权威 YAML Schema。
- [MVP 任务路线图](docs/product/mvp-roadmap.md) — 里程碑（M0–M8）、任务拆分、依赖与逐项验收。
- [项目上下文](docs/project-context.md) — 面向协作 agent 的精简产品上下文。

当 README 与 PRD 不一致时，以 PRD 为准。

## 项目状态

当前项目处于早期规划与原型开发阶段。

本仓库将逐步实现：

- 小说文本导入
- 作品理解分析
- 人物档案提取
- 作者意图锁定
- 分场大纲生成
- 剧本初稿生成
- 改编取舍报告
- 局部重写与打磨

第一阶段目标是完成一个可演示的 MVP：用户导入至少 3 个章节的小说文本后，系统能够生成作品理解、人物档案、分场大纲、剧本初稿和改编报告。

## 为什么做这个项目

很多小说作者希望将自己的作品改编成剧本，但从小说到剧本并不是简单的文本改写。

小说擅长：

- 心理描写
- 叙述声音
- 大段背景交代
- 内心独白
- 文学性表达

剧本需要：

- 场景
- 动作
- 对白
- 冲突
- 人物关系变化
- 可表演、可拍摄、可排演的内容

Cardenio / 入戏 希望降低小说作者进入剧本创作的门槛，让作者先获得一份可编辑、可复查、可继续打磨的剧本初稿。

## 产品定位

Cardenio / 入戏 不是普通 AI 改写工具，也不是一键出稿的黑盒。

它更接近一个小说改编的「副驾驶」，作者始终握有最终决定权：

1. 先读懂小说，再开始改编。
2. 先生成分场大纲，再生成剧本正文。
3. 把改编当作媒介翻译：将心理与叙述转化为动作、对白、潜台词、环境与声音，而不是删掉或硬塞台词。
4. 保留人物性格、关系变化、原作情绪和关键伏笔，并保持作者文风而非通用「编剧腔」。
5. 说明 AI 在改编中做了哪些删减、合并、重写和新增。
6. 支持作者按场景局部修改，而不是每次重新生成全文。

### 信任能力（不延后）

这些能力让产品区别于黑盒，与生成能力同步交付，而非后期再补：

- **溯源 `source_ref`**：每一场戏、每一句台词都能定位回原文章节与段落。
- **来源标记 `ai_inferred`**：凡 AI 新增、原文没有的内容均显式标注并可筛选；原文已有内容标记为 `from_source`。
- **确认关卡**：作品理解与人物档案需作者确认后，才进入剧本生成（先理解，再改编）。
- **敢于留白**：AI 不确定处以 `TODO` 标记呈现，而非用平庸内容填满。

## 目标用户

主要面向：

- 小说作者
- 网文作者
- 剧本创作爱好者
- 希望将小说改编为短剧、电影、电视剧或舞台剧的创作者
- 需要快速获得剧本初稿的内容团队

第一版会优先服务中文小说作者。

## MVP 功能范围

### 1. 小说导入

支持用户导入至少 3 个章节的小说文本。

计划支持：

- 直接粘贴文本
- 按章节录入
- TXT 文件导入
- DOCX 文件导入

### 2. 作品理解

系统会在改编前生成作品理解报告，包括：

- 故事一句话概括
- 故事简介
- 核心主题
- 主角目标
- 主角恐惧
- 主要矛盾
- 情绪基调
- 叙事风格
- 改编优势
- 改编难点

用户可以修改 AI 的理解，修改后的内容会作为后续改编依据。

### 3. 人物档案

系统会自动提取主要人物，并生成基础人物档案：

- 姓名
- 身份
- 性格
- 说话方式
- 核心欲望
- 核心恐惧
- 人物关系
- 人物弧光
- 不可违背的人设规则

人物档案用于后续检查剧本中的人物行为和对白是否一致。

### 4. 作者意图锁定

在正式生成剧本前，系统会收集作者意图：

- 最想保留的内容
- 不能删除的情节
- 不能合并的人物
- 必须保留的台词
- 作品情绪底色
- 是否允许新增桥段
- 是否允许改变故事顺序
- 是否允许调整结局
- 目标剧本类型

作者意图优先级高于 AI 自由发挥。

### 5. 改编方向选择

计划支持以下改编方向：

- 忠实改编
- 影视化增强
- 短剧模式
- 电视剧模式
- 电影模式
- 舞台剧模式

第一版会优先支持忠实改编、影视化增强和短剧模式。

### 6. 分场大纲

系统会先将小说拆分为剧本场景，再生成剧本正文。

每个场景包含：

- 场景标题
- 来源章节
- 地点
- 时间
- 出场人物
- 场景目标
- 场景冲突
- 情绪基调
- 主要事件
- 人物关系变化
- 伏笔信息
- 场景结尾状态

### 7. 剧本初稿

系统基于分场大纲生成剧本初稿，底层以结构化 YAML 存储（Schema 见 [PRD §7](docs/product/requirements.md#7-数据模型--yaml-schema-规范)），便于编辑、版本控制与后续导出。

剧本内容包括：

- 场景标题
- 动作描写
- 人物对白
- 必要旁白
- 停顿
- 转场
- 关键道具
- 场景结尾

每个场景与台词都带 `source_ref`（溯源）与 `flag`（`from_source` / `ai_inferred` 来源标记）。作者默认看到符合中文创作习惯的剧本排版，需要时可切换到底层 YAML 手改。

第一版重点生成可继续打磨的初稿，而不是一次性生成最终成稿。

### 8. 改编取舍报告

每次生成完整剧本后，系统会给出改编报告：

- 保留了哪些关键情节
- 删除了哪些内容
- 合并了哪些场景
- 新增了哪些桥段
- 哪些心理描写被改成动作或对白
- 哪些台词来自原文
- 哪些台词是 AI 新写的
- 哪些伏笔被保留
- 哪些内容建议作者重点复查

### 9. 局部重写

用户可以对单个场景或单段对白进行修改，例如：

- 把这一场写得更压抑
- 删除旁白，改成动作
- 让女主更克制
- 增加场景冲突
- 保留原文这句台词
- 把两场合并
- 把结尾改得更有悬念

局部重写会参考前后场景、人物档案、作者意图和整体剧情。

## 后续计划

MVP 完成后，计划继续加入：

- 人物一致性检查
- 对白优化
- 节奏诊断
- 伏笔追踪
- 多版本改编
- 分集结构生成
- 长篇小说连续改编
- 剧本导出模板
- 多语言界面
- 多语言剧本格式支持

## 文件格式规划

### 小说导入

优先支持：

- 粘贴文本
- TXT
- DOCX

后续支持：

- RTF
- PDF
- EPUB

### 剧本导出

优先支持：

- DOCX
- PDF
- Fountain

后续支持：

- FDX
- RTF
- Markdown

## 国际化规划

Cardenio / 入戏 采用中文优先策略。

第一版重点支持：

- 简体中文界面
- 中文小说导入
- 中文剧本生成
- 中文改编报告
- 中文剧本导出模板

同时从一开始区分：

- UI Language：界面语言
- Source Language：原文语言
- Output Language：剧本输出语言

后续会支持英文界面和英文小说改编。

## 剧本格式方向

中文剧本默认采用符合中文创作习惯的格式：

```text
第 1 场  女主宿舍  夜  内

林一坐在床边，手机屏幕亮着。

室友
你又不接？

林一
接了也一样。
```

英文剧本后续会支持更接近传统 screenplay 的格式：

```text
INT. DORM ROOM - NIGHT

LINYI sits on the edge of the bed. Her phone glows.

ROOMMATE
You're not answering?

LINYI
It won't change anything.
```

## 设计原则

### 1. 中文优先

产品文案、剧本模板和创作流程优先服务中文小说作者。

### 2. 作者可控

AI 生成结果必须让作者能够检查、修改、回退和继续打磨。

### 3. 先理解，再改编

系统需要先生成作品理解和人物档案，再进入剧本生成。

### 4. 保留原作气质

改编时需要尽量保留原作的情绪基调、人物关系、关键意象和重要台词。

### 5. 每场戏都要有变化

剧本场景需要推动剧情、人物关系、信息揭示、冲突或情绪变化。

### 6. 心理描写需要外化

小说中的心理描写应优先转化为动作、对白、环境、声音或道具表现。

### 7. 重大改动必须说明

删除、合并、新增、改写关键内容时，需要在改编报告中说明原因。

### 8. 一切可溯源

每个场景与台词都能通过 `source_ref` 定位回原文章节与段落。

### 9. AI 产物可区分

原文已有（`from_source`）与 AI 推断/新增（`ai_inferred`）必须显式区分，便于作者重点复查。

### 10. 敢于留白

AI 不确定的地方宁可留 `TODO` 让作者填，不用平庸内容填满。

### 11. 中间产物可编辑

作品理解、人物档案、分场大纲、剧本、报告均为可保存、可回到、可编辑的工件，不隐藏在单一生成步骤背后。

> 以上原则与 [PRD 设计原则 P1–P8](docs/product/requirements.md#4-核心设计原则研发决策的判断基准) 对应，作为研发取舍的判断基准。

## 当前开发目标

短期目标：

- 搭建项目基础结构
- 完成小说导入流程
- 完成作品理解流程
- 完成人物档案生成
- 完成分场大纲生成
- 完成剧本初稿生成
- 完成改编报告生成

中期目标：

- 支持局部重写
- 支持剧本编辑
- 支持导出
- 支持人物一致性检查
- 支持节奏诊断

长期目标：

- 成为面向小说作者的完整 AI 剧本改编工作台。

## 项目结构

当前仓库已接入前端应用骨架，前端作为 pnpm workspace 包放在 `frontend/`。

```text
frontend/
  app/
    components/    UI 组件与演示组件
    i18n/          UI 语言资源与语言类型
    routes/        React Router 路由
    theme/         亮/暗主题状态
    app.css        Tailwind v4 入口与设计令牌
  components.json  coss.ui / shadcn registry 配置

docs/
  product/         产品文档
  design/          设计文档
  plans/           已确认的实现计划

scripts/
  hooks/           Git hooks 辅助脚本
```

## 开发说明

项目尚未进入稳定开发阶段，README 会随着功能实现持续更新。当前可运行的是 `frontend/` 中的 Vite + React Router v7 SPA 骨架。

### 运行方式

首次克隆仓库后：

```bash
pnpm install
pnpm exec lefthook install
```

常用命令在仓库根目录执行，根脚本会委派到 `frontend` workspace 包：

```bash
pnpm dev
pnpm build
pnpm lint
pnpm format:check
pnpm typecheck
pnpm preview
```

当前前端构建产物为静态 SPA，输出到 `frontend/build/client`。React Router v7 的 SPA 模式配置为 `ssr: false`；`@react-router/node` 仍作为 React Router 构建期运行时依赖保留。

### 前后端联调

前端默认通过真实 HTTP API 运行。联调时先在 `backend/` 目录按后端自身工具启动 dev 服务，默认监听 `http://localhost:8000`；再在仓库根目录执行：

```bash
pnpm dev
```

Vite dev server 会把前端相对路径 `/api` 代理到后端服务，不改写路径；后端接口自身保留 `/api/v1` 前缀。可用以下环境变量调整：

- `VITE_API_MODE`：默认 `http`。设为 `mock` 时使用前端内存 mock，适合离线开发。
- `VITE_BACKEND_URL`：默认 `http://localhost:8000`。后端运行在其他地址时可覆盖代理目标。

当前生产构建仍是静态 SPA；上述 `/api` 代理只作用于 Vite dev server。

计划优先完成产品主流程，再补充部署说明和贡献指南。

### 依赖与来源

本项目当前引入的第三方依赖和工具包括：

- Vite、React、React DOM、React Router v7：前端应用框架、路由和静态 SPA 构建。
- Tailwind CSS v4 与 `@tailwindcss/vite`：样式系统和 Vite 集成。
- coss.ui / shadcn CLI registry：生成 `components.json`、`cn()` 工具函数和基础 Button 组件；导入页新增 `input`、`textarea`、`field`、`card`、`collapsible`、`badge`、`alert`、`empty`、`separator`、`alert-dialog`、`toast`、`tabs`、`menu`、`dialog`、`number-field`、`checkbox` 组件源码，理解页新增 `input-group` 组件源码，人物档案页新增 `select` 组件源码，作者意图页新增 `switch`、`radio-group` 组件源码，剧本页新增 `toggle`、`toggle-group` 组件源码，以及这些组件依赖的 `scroll-area`、`label` 组件源码。本项目覆盖其默认主题为 `docs/design/visual-style.md` 中的 Cardenio 设计令牌。
- `@base-ui/react`、`class-variance-authority`、`clsx`、`tailwind-merge`、`lucide-react`：coss Button 及本地 UI 组件所需的组合、样式和图标依赖。
- `i18next`、`react-i18next`、`i18next-browser-languagedetector`：UI Language 的国际化骨架。Source Language 与 Output Language 当前仅作为数据类型预留。
- `yaml`：编辑器源码视图的 YAML 序列化与反序列化运行时依赖，来源为 npm 第三方库。
- GSAP：用于前端局部交互动效，目前仅计划驱动应用侧边栏展开/收缩过渡，不承载业务状态或改编逻辑。
- ESLint、typescript-eslint、eslint-plugin-react-hooks、eslint-plugin-react-refresh、eslint-config-prettier、Prettier：前端 lint、类型风格约束和格式化。
- `@fontsource/ibm-plex-sans`、`@fontsource/courier-prime`、`@fontsource/cormorant-garamond`：轻量西文字体包。侧边栏品牌西文和应用标题西文使用 Cormorant Garamond 300 italic。
- `@ibm/plex-sans-sc`：IBM Plex Sans SC 中文字体包，许可证为 OFL-1.1，用作中文 UI 字体栈；本项目在应用 CSS 中导入包内 `ibm-plex-sans-sc-all.css`，并使用随 npm 包分发的本地 woff/woff2 字体文件。该 npm 包包含 IBM Telemetry postinstall 逻辑；本项目安装时可使用 `--ignore-scripts` 跳过安装期遥测脚本，不影响运行时字体加载。
- ZeoSeven Fonts 的 `LXGW WenKai`（霞鹜文楷）CSS：侧边栏品牌中文和应用标题中文使用 400 normal，运行时从 `https://fontsapi.zeoseven.com/292/main/result.css` 加载。CJK 正文字体当前使用 `IBM Plex Sans SC`，并保留 `Noto Sans SC` / `Noto Serif SC` 作为系统或后续子集化 fallback。
- lefthook：本地 Git hooks 管理。

当前 `frontend/` 中的产品文案、设计令牌、主题实现、i18n 资源和演示首页为本项目原创实现。第三方 CLI 生成的 coss/shadcn 基座仅作为通用 UI 基础设施，不代表产品原创业务功能；导入页的手动录入、文件导入预览/确认、章节列表、删除、拆分、合并、编辑和门槛逻辑，analysis 阶段的录入、编辑、门控与信任信号展示逻辑，以及剧本阶段的生成、只读查看、加戏筛选、信任标记展示、双栏对照、局部重生成、行内节拍编辑、YAML 源码视图和留白清单交互与数据流为本项目业务实现。`yaml` 仅作为剧本源码视图的文本序列化基座；本地侧边栏 primitive 按 coss Sidebar 文档的组件结构与命名约定实现，用于应用外壳导航组合，不包含 Cardenio 的业务逻辑。

### Backend privacy settings

The backend exposes API-29 at `/api/v1/projects/{project_id}/settings`.
Project source text, generated artifacts, and settings are stored in the
configured Cardenio SQLite database for the active backend environment.
Cardenio does not use project data for model training, and the MVP keeps
`allow_model_training` locked to `false`. Provider access remains behind the
backend gateway, with a local/private processing path reserved for deployments
that require it.

### Backend artifact recovery

The backend keeps saved artifacts as versioned records. Recovery endpoints at
`/api/v1/projects/{project_id}/artifacts/{artifact_type}/versions` and
`/api/v1/projects/{project_id}/artifacts/{artifact_type}/versions/{version}`
list and read prior versions without mutating the latest artifact, so local
edits and rewrites can be inspected or recovered after interruption.
Screenplay scene history is also exposed at
`/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}/versions`, which
lists the target scene snapshot from each saved screenplay version that still
contains that scene. A scene can be restored from a saved screenplay version
with `/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}:checkout`,
which saves a new screenplay artifact version and does not mutate prior
history. Scene snapshots from two saved screenplay versions can be compared
with `/api/v1/projects/{project_id}/screenplay/scenes/{scene_id}/versions:diff`.

### Backend consistency rename

The backend exposes deterministic character rename at
`/api/v1/projects/{project_id}/consistency:rename`. The request requires
`confirm=true`, keeps the stable `character_id` unchanged, saves new artifact
versions for the character profile and affected text artifacts, and updates the
project back to `editing`. This implementation covers the FR-9.4 global rename
path only; conflict suggestions for changed character rules remain future work.
No third-party dependency or external model service is introduced by this
capability.

### Git hooks

本仓库使用 [lefthook](https://github.com/evilmartians/lefthook) 管理本地 Git hooks。lefthook 是第三方开发工具，当前仅用于提交前和推送前的工程规范检查，不属于产品原创功能。

当前 hooks 会执行以下检查：

- `pre-commit`：禁止在 `main` / `master` 分支提交，检查 `.env`、密钥、token，按项目脚本尝试执行 lint 或格式检查，并在依赖文件变化时提醒同步 README。
- `commit-msg`：要求 commit message 符合 `type: message` 或 `type(scope): message` 格式，type 只能是 `feat`、`fix`、`docs`、`chore`、`test`、`refactor`、`style`；提交信息必须使用 ASCII English，不能包含全角逗号、句号、冒号等全角字符。
- `pre-push`：禁止直接 push `main` / `master`，按 [Conventional Branch](https://conventionalbranch.org/) 检查分支名是否符合 `<type>/<description>`，允许的 type 包括 `feature`、`feat`、`bugfix`、`fix`、`hotfix`、`release`、`docs`、`chore`，按项目脚本尝试执行测试或构建，并提醒确认 commit 时间在开发窗口内。

## License

待定。
