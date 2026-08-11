# AGENTS.md

This file gives AI agents lightweight orientation for working in this repository.

## Project Overview

Cardenio / 入戏 is an AI-assisted novel-to-script adaptation workbench for Chinese
novel authors. This is a monorepo:

- `backend/` — Python 3.12 / FastAPI / SQLAlchemy async / Pydantic v2 / SQLite.
  Deterministic agent orchestration: routes → domain services → ToolRegistry →
  AgentRuntime → ControlledAgent → LlmGateway (stub or DeepSeek).
- `frontend/` — React 19 / React Router 7 / Vite / Tailwind v4 / TypeScript.
- `docs/` — PRD, technical design, API contract, milestone plans (historical archive).
- `scripts/hooks/` + `lefthook.yml` — local git hooks (commit message, branch name,
  secret scan, README dependency reminder).

## Lightweight Conventions

- Use topic branches for changes (e.g. `feat/xxx`, `fix/xxx`, `docs/xxx`); keep
  `main` runnable and deliver larger features through pull requests.
- Commit subjects should follow Conventional Commits: `<type>(<scope>): <summary>`.
- When adding a third-party dependency or external source, note it in the PR
  description and update `README.md` if runtime/build instructions change.
- Run the relevant tests/build after changing code:
  - backend: `cd backend && uv run pytest -q`
  - frontend: `pnpm typecheck && pnpm lint && pnpm build`

## History Note

Earlier versions of this file imposed hard constraints tied to a fixed development
window (Beijing time 2026-06-05 ~ 2026-06-07). The repository owner has removed
those constraints; they no longer apply and must not be re-introduced.
