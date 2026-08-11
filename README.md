# Cardenio 入戏

Cardenio / 入戏 是一个面向中文小说作者的 AI 剧本改编工作台。系统把 3 个章节以上的小说文本转化为可确认、可编辑、可溯源的剧本初稿，并在生成过程中保留作者控制权。

本项目当前已完成可演示的前后端 MVP：用户可以注册/登录、创建项目、导入小说、确认作品理解和人物档案、设置作者意图、生成分场大纲、生成剧本、查看/编辑局部内容、生成改编报告，并在项目级别保存设置和历史版本。

项目演示视频链接：https://www.bilibili.com/video/BV1GQE86RE36/

## 核心能力

- **登录与项目隔离**：第一方注册/登录，Bearer Token 访问后端，项目数据按当前用户隔离。
- **小说导入与预处理**：支持粘贴文本、按章录入、TXT/DOCX 导入，自动识别章节并建立段落索引。
- **理解先行**：先生成作品理解，再生成人物档案，确认后才能继续下游改编。
- **作者意图约束**：保留内容、不可删除情节、改编方向等被编译为后续生成硬约束。
- **分场大纲**：把小说拆解为剧本场景，每场保留 `source_ref` 溯源信息。
- **剧本生成与编辑**：生成结构化剧本，支持信任标记筛选、源码视图、局部重写、行内编辑和 TODO 留白。
- **改编报告**：根据剧本标记和版本差异汇总保留、删除、合并、新增和外化内容。
- **可观测 Agent 运行边界**：后端使用受控 Agent Runtime、ToolRegistry 和 ContextAssembler 组织 LLM 调用与内部工具执行。

## 当前边界

Cardenio 不是一个开放式自主规划 Agent。当前后端采用确定性阶段流：

```text
HTTP route -> domain service -> ToolRegistry -> AgentRuntime -> ControlledAgent -> LLM gateway
```

阶段推进由 API、状态机和确认关卡控制；LLM 不自由决定下一步。内部 tool 是本地 Python tool，不是 MCP server。`ToolRegistry` 负责注册和解析内部工具，`AgentRuntime` 负责统一执行边界和内部 trace，`ContextAssembler` 负责把项目工件、场景上下文和作者意图组装给局部重写等任务。

## 项目结构

```text
backend/
  src/cardenio/
    api/              FastAPI app、依赖、错误模型和 HTTP routes
    domain/           领域模型、services、agents、tools、runtime、validation
    gateway/          LLM gateway 协议、stub provider、DeepSeek provider
    storage/          SQLAlchemy models、repository、SQLite store
  tests/              后端 API 和领域单元测试

frontend/
  app/
    components/       应用组件和 coss/shadcn UI 基础组件
    i18n/             zh-CN / en 文案资源
    lib/api/          http/mock API client、类型定义
    routes/           React Router 页面和阶段路由
    theme/            主题状态
    app.css           Tailwind v4 与设计令牌

docs/
  design/             API、架构、Agent workflow、视觉规范
  product/            PRD 与 MVP roadmap
  plans/              已确认的前后端集成计划

scripts/hooks/        lefthook 使用的本地 Git hooks
```

## 快速启动

本项目使用 `pnpm` 管理前端依赖，使用 `uv` 管理后端 Python 依赖。禁止使用 `pip`。

### 1. 安装依赖

在仓库根目录执行：

```bash
pnpm install
pnpm exec lefthook install
```

后端依赖在 `backend/` 下通过 uv 同步：

```bash
cd backend
uv sync
```

### 2. 启动后端

在 `backend/` 目录执行：

```bash
uv run uvicorn cardenio.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

默认配置：

- 数据库：`sqlite+aiosqlite:///./cardenio.db`
- LLM：默认 DeepSeek（LLM 模式）；未配置 `DEEPSEEK_API_KEY` 时自动回退本地 `StubLlmGateway`
- API 前缀：`/api/v1`

### 3. 启动前端

在仓库根目录执行：

```bash
pnpm dev
```

前端默认使用真实 HTTP API，Vite dev server 会把 `/api` 代理到 `http://localhost:8000`。打开前端页面后先注册或登录，再创建项目并执行改编流程。

## LLM 模式（默认 DeepSeek）

后端**默认使用 DeepSeek**（LLM 模式）。启动时后端会从 `backend/.env` 读取配置（未找到则用环境变量），只要配置了 `DEEPSEEK_API_KEY` 即走真实模型；**未配置 key 时自动回退到本地 `StubLlmGateway`**，保证应用始终可启动。

推荐把 key 写入 `backend/.env`（已被 gitignore 忽略，不会进仓库）：

```bash
DEEPSEEK_API_KEY=<your-api-key>
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_TIMEOUT_SECONDS=120
DEEPSEEK_MAX_TOKENS=8192
```

然后直接用 uv 启动：

```bash
cd backend
uv run uvicorn cardenio.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

如需显式回到 stub 模式（离线/无费用调试）：

```bash
CARDENIO_LLM_PROVIDER=stub uv run uvicorn cardenio.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

## 环境变量

### 后端

| 变量                       | 默认值                              | 说明                  |
| -------------------------- | ----------------------------------- | --------------------- |
| `CARDENIO_DATABASE_URL`    | `sqlite+aiosqlite:///./cardenio.db` | 后端数据库连接 URL    |
| `CARDENIO_LLM_PROVIDER`    | `deepseek`                          | `deepseek`（默认）或 `stub`；缺 key 时自动回退 stub |
| `DEEPSEEK_API_KEY`         | 无                                  | 配置后走 LLM 模式；未配置回退 stub |
| `DEEPSEEK_MODEL`           | `deepseek-v4-flash`                 | DeepSeek 模型名       |
| `DEEPSEEK_BASE_URL`        | `https://api.deepseek.com`          | DeepSeek API Base URL |
| `DEEPSEEK_TIMEOUT_SECONDS` | `60`                                | LLM 请求超时          |
| `DEEPSEEK_MAX_TOKENS`      | `8192`                              | 结构化输出最大 token  |

### 前端

| 变量               | 默认值                  | 说明                                          |
| ------------------ | ----------------------- | --------------------------------------------- |
| `VITE_API_MODE`    | `http`                  | `http` 使用真实后端，`mock` 使用前端内存 mock |
| `VITE_BACKEND_URL` | `http://localhost:8000` | Vite dev proxy 目标                           |

## 登录与数据隔离

后端提供第一方认证接口：

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

注册和登录返回 opaque bearer token。前端将 token 存在 `localStorage` 的 `cardenio.auth.token`，并在 HTTP 请求中附加：

```text
Authorization: Bearer <access_token>
```

项目 API 均要求登录。新项目会绑定当前用户，项目列表只返回当前用户项目，访问其他用户项目返回 `403 forbidden`。

## 后端 Agent 编排

后端 Agent 系统由以下组件组成：

- `ControlledAgent`：调用 LLM gateway，校验结构化响应，记录 issue，有限重试，失败时返回 `needs_attention`。
- `AgentRuntime`：统一 agent/tool 执行边界，记录内部运行 trace，不暴露为用户 API。
- `ToolRegistry`：注册和解析内部工具，例如 `rewrite.scene`、`report.generate`、`scene.generate`。
- `ContextAssembler`：为局部重写等任务组装目标场景、前后文、人物档案、作者意图和源文段落。
- `LlmGateway`：抽象 LLM provider，当前支持 stub 和 DeepSeek provider。

当前没有实现 MCP server。services 层调用的是本地 tools 和 controlled agents；编排是确定性 gateway 模式，而不是模型自主 planner。

## 主要流程

```text
注册/登录
  -> 创建项目
  -> 导入 TXT/DOCX 或手动添加章节
  -> 满足至少 3 章门槛
  -> 生成并确认作品理解
  -> 生成并确认人物档案
  -> 设置作者意图与改编方向
  -> 生成并确认分场大纲
  -> 生成剧本
  -> 查看信任标记、TODO、溯源和局部重写
  -> 生成改编报告
  -> 项目设置与版本恢复
```

导出 API 已在契约和路由中预留，但 Fountain/DOCX/PDF 文件生成尚未实现。

## 小说预处理规则

章节识别支持：

- `第一章`、`第一节`、`第一卷`
- `第一回`、`第一百二十回`
- 大写中文数字，例如 `第壹章`、`第贰拾回`
- 英文 `chapter 1`

段落切分规则：

- 如果章节内存在空白行 `\n\n`，按空白行切成段落块。
- 如果章节内不存在空白行，按单换行切分，每个非空行作为一个段落。
- 清洗阶段会把 3 个以上连续换行压缩为 2 个换行。

## 常用命令

### 前端

```bash
pnpm dev
pnpm build
pnpm lint
pnpm format:check
pnpm typecheck
pnpm preview
```

### 后端

```bash
cd backend
uv sync
uv run pytest
uv run pytest tests/api
uv run pytest -m eval  # 生成质量基线（需 DEEPSEEK_API_KEY）
uv run ruff check src tests
uv run uvicorn cardenio.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

## 生成质量评估（Eval）

后端提供可重复运行的生成质量基线（OpenSpec 变更 `llm-quality-baseline` 引入）：

- **运行前提**：配置 `DEEPSEEK_API_KEY`（见上文 DeepSeek 模式）；未配置时 eval 用例自动跳过。
- **运行方式**：

```bash
cd backend
uv run pytest -m eval
```

- **覆盖流程**：导入固定 3 章中文小说 fixture（`backend/tests/fixtures/novel_sample_3chapters.txt`）→ 理解 → 人物 → 意图 → 大纲 → 剧本 → 报告。
- **输出**：`docs/eval/baseline-<YYYY-MM-DD>.md`，包含分阶段结果、指标（schema 通过率、`source_ref` 覆盖率、TODO 降级率、报告统计一致性、`must_keep_lines` 命中率）与 LLM 调用统计（token、延迟、重试代理指标），不覆盖历史基线。
- **指标口径**：`must_keep_lines` 在基线中默认关闭（避免整链失败），该能力由单测覆盖；阈值与口径见 `backend/tests/eval/metrics.py`。

## 测试状态


后端测试覆盖：

- auth 注册/登录/登出
- 项目所有权与越权隔离
- 小说导入、清洗、分章、分段、章节阈值
- 作品理解、人物档案、作者意图、分场大纲、剧本生成
- 局部重写、版本恢复、改编报告、设置和导出 stub
- DeepSeek provider 配置与 stub gateway

前端测试命令通过 pnpm 脚本执行 lint、typecheck、build。

## API 文档

完整 HTTP 契约见 [docs/design/api.md](docs/design/api.md)。核心资源包括：

- Auth
- Projects
- Source
- Understanding
- Characters
- Intent
- Outline
- Screenplay
- Report
- Settings
- Artifacts / versions
- Consistency rename

## 依赖与来源边界

本项目业务代码、产品文案、阶段流程、Agent 编排、后端 services、API routes、导入预处理、剧本与报告逻辑为项目实现。

第三方依赖包括：

- 前端：Vite、React、React Router、Tailwind CSS、coss.ui / shadcn registry、Base UI、lucide-react、i18next、yaml、cytoscape、GSAP、字体包和 ESLint/Prettier 工具链。
- 后端：FastAPI、Uvicorn、Pydantic、SQLAlchemy、aiosqlite、Alembic、sse-starlette、python-multipart、PyYAML、python-docx、pytest、ruff、httpx。
- 外部服务：DeepSeek API 为默认 LLM provider；配置 `DEEPSEEK_API_KEY` 后调用外部模型，未配置时回退本地 stub，不调用外部服务。
- 开发工具：lefthook 用于本地 Git hooks。

coss/shadcn 组件源码作为通用 UI 基础设施，不代表 Cardenio 的业务原创功能。ZeoSeven Fonts 的 Zhuque Fangsong CSS 和各字体包仅作为显示资源。

## Git 与协作规范

分支名遵循：

```text
<type>/<description>
```

允许 type：`feature`、`feat`、`bugfix`、`fix`、`hotfix`、`release`、`docs`、`chore`、`refactor`。

提交信息遵循 Conventional Commits：

```text
<type>(<scope>): <summary>
```

commit subject 必须使用 ASCII English。仓库使用 lefthook 在 pre-commit、commit-msg、pre-push 阶段检查 main 保护、密钥、lint/build、分支名和提交窗口。

## 重要文档

- [产品需求文档](docs/product/requirements.md)
- [MVP 路线图](docs/product/mvp-roadmap.md)
- [API 规范](docs/design/api.md)
- [技术设计](docs/design/design.md)
- [Agent Workflow](docs/design/agent-workflow.md)
- [视觉规范](docs/design/visual-style.md)

## License

待定。
