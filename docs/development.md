# Cardenio 个人开发规范（Personal Development Guidelines）

> 适用对象：仓库所有者（Yunzhuu1）的个人 fork 仓库二次开发。
> 自 2026-08 起，仓库不再走 PR 协作流程，改为「main 直推 + 功能分支」模式。

## 1. 协作模式

- 仓库：个人 fork（origin = `https://github.com/Yunzhuu1/cardenio.git`），无 PR 流程，合并在本机完成。
- `main` 是唯一长期主干，必须始终保持可运行。
- 小型改动（修复、文档、配置、依赖说明）可直接在 `main` 提交并推送。
- 新功能 / 较大改动必须在分支上开发，验证通过后合并回 `main`。

## 2. 分支策略

| 类型 | 前缀 | 示例 |
| --- | --- | --- |
| 新功能 | `feat/` | `feat/screenplay-export` |
| 修复 | `fix/` | `fix/import-encoding` |
| 文档 | `docs/` | `docs/api-cleanup` |
| 重构 | `refactor/` | `refactor/service-layer` |
| 工程 | `chore/` | `chore/remove-guard-hooks` |
| 测试 | `test/` | `test/export-service` |

- 命名：`<type>/<kebab-case>`，小写字母 + 数字 + 连字符。
- 生命周期：创建 → 开发 → 本地测试 → 合并回 `main` → 删除（本地 + 远程）。

## 3. 标准工作流

### 3.1 小改动（直接 main）

```bash
git checkout main && git pull
# 修改代码...
git add <files>
git commit -m "fix(scope): 简短描述"
git push origin main
```

### 3.2 新功能（分支开发 + 本地合并，无 PR）

```bash
git checkout main && git pull
git checkout -b feat/xxx
# 开发 + 测试...
git add <files>
git commit -m "feat(scope): 简短描述"
# 合并回 main
git checkout main && git pull
git merge --no-ff feat/xxx
git push origin main
# 清理
git branch -d feat/xxx
git push origin --delete feat/xxx
```

## 4. 提交规范（Conventional Commits）

- 格式：`<type>(<scope>): <summary>`
- `type`：`feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore`
- `scope` 可选，写模块名，如 `backend`、`frontend`、`import`、`export`。
- subject 用中文撰写（便于仓库所有者审阅），类型/scope 保留英文；commit-msg 钩子已放开 ASCII 限制，仅校验格式。
- 一个 commit 只做一个逻辑单元；避免 `update`、`wip`、`misc` 这类模糊消息。

示例：

```
feat(export): implement docx export service
fix(import): handle gbk-encoded txt files
docs: add personal development guidelines
```

## 5. 测试与质量门禁

- 后端：`cd backend && uv run pytest -q`
- 前端：`pnpm typecheck && pnpm lint && pnpm build`
- 合并到 `main` 前必须通过相关测试 / 构建；`main` 每次推送后保持可运行。

## 6. 依赖与来源披露

- 引入第三方库 / 框架 / 外部 API / 模板 / 示例代码 → 更新 `README.md`（说明依赖与原创功能边界），并在 commit 或 PR 描述中注明来源。
- 复用旧代码 → 在 commit 或代码注释中说明来源与改动范围。

## 7. Git hooks（lefthook）

配置在 `lefthook.yml`，需要本地安装一次：

```bash
pnpm install
pnpm exec lefthook install
```

启用后自动校验：

| Hook | 时机 | 校验内容 |
| --- | --- | --- |
| `scan-staged-secrets` | pre-commit | 拒绝提交 `.env` / 疑似密钥 |
| `remind-readme-dependencies` | pre-commit | 依赖文件变更时提醒更新 README |
| `check-commit-msg` | commit-msg | commit 格式（Conventional Commits + ASCII） |
| `check-branch-name` | pre-push | 分支命名规范 |
| `verify-project` | pre-push | 前端 build / test |

已按单开发者流程移除：`guard-main-commit`、`guard-main-push`（`main` 允许直推）。
注意：`verify-project` 会在 push 时执行 `pnpm run build`，需要前端依赖已安装；如觉得过重，可改为仅当 frontend 文件变更时触发。

## 8. 网络与代理备忘

公司内网直连 GitHub 不可靠，本仓库已配置本地代理（写入 `.git/config`，不随仓库提交）：

```bash
git config --local --get http.proxy   # http://127.0.0.1:7892
# 如需移除：git config --unset http.proxy && git config --unset https.proxy
```

## 9. 红线（不做）

- 不把 `.env`、密钥、token 提交进仓库。
- 不在 `main` 上直接做破坏性重构；先开分支验证。
- 不引入无法说明来源的第三方代码。
