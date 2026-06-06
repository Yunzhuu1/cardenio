# Plan: 前端项目骨架（Cardenio 入戏）

> 实现计划 · 分支 `feat/frontend-scaffold` · 对应 MVP 路线图 M0「工程地基」

## Context

仓库目前只有文档与 Git 工具（lefthook + pnpm workspace），**没有任何应用代码**。需要搭建前端项目骨架，作为 MVP 路线图 M0「工程地基」的一部分。

经与用户确认的技术决策：

- **框架**：Vite + React Router v7（framework 模式），**SPA 模式 `ssr: false`**（后端为独立服务，前端构建为静态产物）
- **库布局**：前端放 `frontend/`，作为 pnpm workspace 包；为未来独立后端/共享包预留
- **组件库**：coss.ui（配色与 shadcn/ui 兼容）—— 结构按 shadcn 约定搭好，coss.ui 的精确安装命令在落地时确认
- **样式/主题**：Tailwind（目标 v4 + `@tailwindcss/vite`），落地 [visual-style.md](../design/visual-style.md) 的 shadcn CSS 变量令牌 + 扩展语义色 `--source`/`--inferred`/`--todo` + 双主题
- **i18n**：现在就搭（react-i18next，默认 zh-CN，区分 UI/Source/Output 三种语言，对应 NFR-7）
- **Lint/格式**：ESLint + Prettier
- **状态/数据层**：本阶段**不引入**（无 TanStack Query / Zustand）

**本次 PR 边界**：骨架 + 主题与设计令牌。即「应用可启动 + 工具链跑通 + 设计系统接好 + 一个演示首页」，**不**铺设 import/analysis/outline/script/report/settings 六个业务路由（留作后续按模块拆分的 PR）。

预期成果：`pnpm dev` 能打开一个应用了「克制的戏剧」设计系统的首页，含双主题切换、语言切换、以及验证信任语义色的演示组件；`pnpm build` 产出静态 SPA。

## 前置：分支

已切到 `feat/frontend-scaffold`（用户已创建）。无需再建分支，直接在此分支实现。

## 工作项

### 1. Workspace 接线（仓库根）

- **`pnpm-workspace.yaml`**：在现有 `allowBuilds` 基础上增加 `packages: ['frontend']`。
- **根 `package.json`**：保留 `prepare: lefthook install` 与 lefthook devDep；新增委派脚本指向 frontend 包（满足 Git hooks 在**根目录**查找脚本的逻辑）：
  - `dev` → `pnpm --filter frontend dev`
  - `build` → `pnpm --filter frontend build`（pre-push `verify-project.sh` 会调用根 `build`）
  - `lint` → `pnpm --filter frontend lint`（pre-commit `verify-format-or-lint.sh` 会调用根 `lint`）
  - `format` / `format:check` / `typecheck` / `preview` 同样委派
  - 关键依据（已核实）：`scripts/hooks/verify-format-or-lint.sh` 检测根 `package.json` 的 `scripts.lint`（否则 `format:check`）；`scripts/hooks/verify-project.sh` 检测根 `scripts.test`（否则 `build`）。因此根必须暴露 `lint` 与 `build`。
- `.gitignore` 无需改动：已覆盖 `node_modules/`、`dist/`、`build/`、`.vite/`、`.env`。

### 2. 前端应用骨架（`frontend/`，Vite + RR v7 SPA）—— 用 CLI 生成

**用官方 CLI 脚手架生成，不手工拼文件**：

- 脚手架：`pnpm create react-router@latest frontend`（在仓库根执行，生成 `frontend/`）。非交互处理提示：跳过其自带 git init（仓库已是 git repo），交由根 pnpm workspace 统一安装。
- Tailwind（按 RR v7 + Vite 官方指引，CLI/包安装而非手写）：在 `frontend` 内 `pnpm add tailwindcss @tailwindcss/vite`，将 `@tailwindcss/vite` 插件加入 `vite.config.ts`，`app/app.css` 加 `@import "tailwindcss";`。

**在 CLI 产物之上做的调整/新增**（只改必要文件）：

- `frontend/react-router.config.ts` → 改为 `ssr: false`（SPA 模式）；相应移除 SSR-only 依赖（如 `@react-router/serve`）。
- `frontend/package.json` → `name: "frontend"`；补齐 scripts：`lint`/`format`/`format:check`/`typecheck`（`dev`/`build`/`preview` 由模板提供）。
- `frontend/tsconfig.json` → 确认 strict 与路径别名（模板默认 `~/*` → `app/*`，沿用）。
- `frontend/app/root.tsx` → 注入字体变量、ThemeProvider、I18nProvider、防主题闪烁 inline 脚本、`<html lang>`。
- `frontend/app/routes.ts` + `frontend/app/routes/home.tsx` → 改为单一演示首页。
- `frontend/app/app.css` → 见 §3（令牌）。

### 3. 设计令牌与双主题（本 PR 的重点）

- **`app/app.css`**：`@import "tailwindcss";` + `:root`（亮色）与 `.dark`（暗色）两套 CSS 变量，**直接取自 [visual-style.md](../design/visual-style.md) §3.1/§3.2 与 §3.4 的 shadcn 映射**：
  - shadcn 基础变量：`--background`/`--foreground`/`--card(-foreground)`/`--popover(-foreground)`/`--primary(-foreground)`/`--secondary(-foreground)`/`--muted(-foreground)`/`--accent(-foreground)`/`--border`/`--input`/`--ring`/`--destructive`
  - **扩展语义变量**（产品独有，不可省略）：`--source(-foreground)`/`--inferred(-foreground)`/`--todo(-foreground)`，亮暗各一套
  - `--primary` = 靛蓝聚光（亮 `#2D6CDF` / 暗 `#5B8DEF`）；`--inferred` 暗色为聚光琥珀 `#E0A458`
  - 通过 `@theme inline` 暴露给 Tailwind 工具类（v4 写法）
  - 字体族变量：`--font-sans`（思源黑体 + IBM Plex Sans）/`--font-serif`（Noto Serif SC + Courier Prime）/`--font-mono`（等距更纱黑体 + IBM Plex Mono）
- **字体加载策略（骨架务实做法）**：用 `@fontsource` 加载较轻的西文 `IBM Plex Sans`、`Courier Prime`；CJK（思源黑体 / Noto Serif SC）体积大，骨架阶段先声明 family stack + 系统回退，**完整 CJK 子集化留作后续**（对应 visual-style.md 开放项 O2）。在 README 如实说明这一点。
- **`app/theme/`**：轻量 ThemeProvider（React context + localStorage + `prefers-color-scheme`，切换 `<html>` 的 `.dark` 类）。不依赖 next-themes（其仅 Next 适用）。root.tsx `<head>` 注入 inline 脚本，在首帧前按存储/系统设置好主题类，避免闪烁。
- **`app/components/theme-toggle.tsx`**：主题切换按钮。

### 4. coss.ui / shadcn 基座 —— 用 CLI 安装与初始化

**用组件库 CLI 完成 init 与组件添加，不手工创建 components.json / utils / 组件文件**：

- 初始化：运行 coss.ui 的 init CLI（命令在落地时按其官方文档确认；若与 shadcn 兼容则等价于 `pnpm dlx shadcn@latest init`）。CLI 会生成 `components.json`、`app/lib/utils.ts`（`cn()`）、并写入基础主题变量到 `app/app.css`。
- 添加组件：用 CLI 添加 `Button` 等基础组件（如 `pnpm dlx shadcn@latest add button`），落到 `app/components/ui/`。
- **令牌覆盖**：CLI 写入的是默认主题；随后由 §3 用 visual-style.md 的取值**覆盖** `app.css` 中的 `:root`/`.dark` 变量，并补扩展语义色。即「CLI 出基座 → 我们替换配色」。
- **信任语义色演示组件** `app/components/trust-chips.tsx`（手写，业务演示）：渲染 `source_ref` chip（靛蓝）、`ai_inferred` 标签（暖琥珀 + AI 图标）、`TODO` chip（紫色虚线）—— 验证 §3.3 语义映射在双主题下成立。
- 回退：若 coss.ui CLI 与目标 Tailwind 版本不兼容，回退用 shadcn/ui CLI 初始化（用户已确认二者配色兼容，令牌取值不变）。

### 5. i18n 脚手架

- 依赖：`i18next`、`react-i18next`、`i18next-browser-languagedetector`。
- `frontend/app/i18n/config.ts`：默认 `zh-CN`，资源结构 `locales/zh-CN/common.json`（+ `en` 占位结构，体现「从一开始不硬编码语言」）。
- `app/i18n/provider.tsx`：I18nProvider；首页文案走翻译键以证明链路通。
- **语言三分（NFR-7）**：i18next 仅驱动 **UI Language**；**Source/Output Language 是数据字段而非 UI 文案**，骨架阶段在 `app/i18n/languages.ts` 定义三者的类型与常量并加注释预留，不接数据层（本阶段无数据层）。
- `app/components/language-switcher.tsx`：UI 语言切换（zh-CN / en）。

### 6. ESLint + Prettier

- `frontend/eslint.config.js`（flat config）：`typescript-eslint` + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh` + `eslint-config-prettier`。
- `frontend/.prettierrc` + `frontend/.prettierignore`。
- 校验脚本：`lint`（eslint）、`format`（prettier --write）、`format:check`（prettier --check）、`typecheck`（`react-router typegen && tsc`）。

### 7. README 更新（AGENTS.md 要求）

引入第三方库必须在 README 记录依赖与运行方式：

- 「项目结构」：更新为 `frontend/`（Vite + RR v7 SPA），替换原 `app/...` 概念草图为实际结构。
- 新增/更新「运行方式」：`pnpm install` → `pnpm exec lefthook install` → `pnpm dev` / `pnpm build` / `pnpm lint`。
- 「依赖与来源」：列出 Vite、React、React Router v7、Tailwind、coss.ui、react-i18next、ESLint/Prettier、@fontsource 字体（含字体授权与来源、CJK 子集化为后续项），并界定原创功能边界。

## 提交策略（每完成一项即提交，不要最后一次性提交）

每完成一个工作项就做一次提交，保证**每次提交后工作树都可构建、lint 通过**。提交顺序经过排列以满足这一点（先让 frontend 的 `lint`/`build` 存在，再接根委派脚本）。全部在 `feat/frontend-scaffold` 上，遵循 Conventional Commits（ASCII English，type ∈ feat/fix/docs/chore/test/refactor/style）。

建议的提交序列：

1. `chore(frontend): scaffold Vite and React Router v7 app` —— CLI 脚手架 + 改 SPA（`ssr: false`）。
2. `chore(frontend): add eslint and prettier config` —— 使 `lint`/`format:check`/`typecheck` 脚本就位并通过。
3. `chore: wire pnpm workspace and root delegating scripts` —— `pnpm-workspace.yaml` 加 `packages: [frontend]`，根 `package.json` 委派 `lint`/`build` 等（此刻根脚本才能解析到 frontend）。
4. `feat(frontend): add tailwind and coss.ui base via CLI` —— Tailwind + 组件库 CLI init + `Button`。
5. `feat(frontend): apply design tokens and dual theme` —— 用 visual-style.md 取值覆盖 `app.css` 令牌 + 扩展语义色 + 字体变量 + ThemeProvider + 主题切换。
6. `feat(frontend): add i18n scaffold` —— react-i18next + zh-CN/en 资源 + 语言切换 + 语言三分类型。
7. `feat(frontend): add demo home page with trust chips` —— 演示首页 + trust-chips 组件。
8. `docs: document frontend stack and run instructions in README` —— 按 AGENTS.md 记录依赖、来源、运行方式与原创边界。

说明：
- 每次提交前 pre-commit 会跑根 `lint`；提交序列保证第 3 步之后根 `lint` 可解析、各步均通过。
- 第 8 步集中更新 README 依赖与运行说明；如某一步引入显著新依赖，也可在该步顺带补 README 对应条目。
- 提交时间需落在开发窗口内（AGENTS.md：2026-06-05 ~ 06-07 北京时间）。

## 关键复用与依据

- **设计令牌**直接复用 [visual-style.md](../design/visual-style.md) §3.1–3.4（色值、shadcn 变量映射、扩展语义色、字体族）—— 不重新设计。
- **结构原则**遵循 [design.md](../design/design.md)：领域层与框架解耦、框架无关令牌（本骨架只做表现层）。
- **Hook 脚本约定**已核实：根 `lint` / `build` 必须存在（`scripts/hooks/verify-format-or-lint.sh`、`verify-project.sh`）。

## 验证方式（端到端）

1. 根目录 `pnpm install` && `pnpm exec lefthook install` —— 无报错。
2. `pnpm dev` —— 打开首页：
   - 「克制的戏剧」配色生效；右上角主题切换在亮/暗间切换且无闪烁；
   - 语言切换 zh-CN ↔ en，首页文案随之变化；
   - trust-chips 演示：`source`/`inferred`/`todo` 三色在两套主题下均正确且可辨（不只靠颜色，含标签+图标）。
3. `pnpm build` —— 产出静态 SPA（`frontend/build/client`），无类型/构建错误。
4. `pnpm lint`、`pnpm format:check`、`pnpm typecheck` —— 全部通过。
5. **Hooks 联调**：在 `feat/frontend-scaffold` 上做一次测试提交 → 触发 pre-commit `lint`；`git push` → 触发 pre-push `build`，均通过（确认根委派脚本被正确发现）。

## 风险与回退

- **coss.ui 与 Tailwind 版本兼容性**：若 coss.ui 不支持目标 Tailwind 版本，回退到 shadcn/ui 基座（配色兼容，令牌不变）。
- **CJK 字体体积**：骨架不打包完整思源/Noto Serif SC，先 family stack + 回退，README 注明；完整子集化为后续 PR。
- **RR v7 SPA + Tailwind v4 集成**：若 `@tailwindcss/vite` 与 RR v7 dev server 有 gotcha，回退 Tailwind v3 + postcss（令牌写法相应调整，不影响令牌取值）。
