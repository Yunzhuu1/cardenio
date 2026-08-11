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
- `docs/development.md` — the personal development guidelines for this solo repo.

## Repository Workflow (solo fork, no PRs)

This is the owner's personal fork. Changes are integrated locally and pushed
directly to `main`; there is no PR process.

- Small changes (fixes, docs, config) may be committed on `main` directly.
- New features / larger changes must be developed on a topic branch
  (`feat/xxx`, `fix/xxx`, `docs/xxx`, `refactor/xxx`, `chore/xxx`, `test/xxx`),
  verified, merged into `main` with `git merge --no-ff`, then pushed.
- Commit subjects follow Conventional Commits: `<type>(<scope>): <summary>`.
- `main` must remain runnable after every push.
- **Approval gate**: before every `git commit` and `git push`, show the owner
  the changes to be committed / pushed and wait for explicit approval.

See `docs/development.md` for the full personal development guidelines.

## Lightweight Conventions

- When adding a third-party dependency or external source, note it in the
  commit / PR description and update `README.md` if runtime/build instructions
  change.
- Run the relevant tests/build after changing code:
  - backend: `cd backend && uv run pytest -q`
  - frontend: `pnpm typecheck && pnpm lint && pnpm build`
- Local git hooks are defined in `lefthook.yml`; install with
  `pnpm install && pnpm exec lefthook install`.

## History Note

Earlier versions of this file imposed hard constraints tied to a fixed development
window (Beijing time 2026-06-05 ~ 2026-06-07). The repository owner has removed
those constraints; they no longer apply and must not be re-introduced.
