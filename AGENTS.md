# AGENTS.md

This file defines execution instructions for AI agents working in this repository. Agents must follow these rules when reading files, editing files, proposing commits, or helping create pull requests.

## Hard Constraints

- The development window is fixed to Beijing time, from 2026-06-05 00:00 to 2026-06-07 23:59.
- Do not create, modify, suggest, or assist with commits whose timestamps fall outside the development window.
- Do not forge, rewrite, or work around commit timestamps.
- Do not treat a large last-day code import as valid continuous development.
- Feature development must keep continuous, traceable commit and PR history.
- The main branch must remain runnable after every merged PR.

## Before Changing Files

Before modifying code or documentation, complete these checks:

- Run or inspect `git status` to understand the current working tree.
- Read `docs/project-context.md` to understand current project progress and roadmap.
- Decide whether the task should be implemented on a separate branch and delivered through a separate PR.
- Decide whether the task has exactly one clear goal; split it first if it contains multiple goals.
- Check whether the task introduces any third-party library, framework, template, example code, generated asset, external API, model, or data source.
- Check whether the task reuses code previously written by a teammate or agent.
- Check whether `README.md` must be updated.

If the task goal, source, dependency, or PR boundary is unclear, ask the user before editing files.

## Change Scope

- Each PR must implement or modify exactly one feature or clearly bounded change.
- Split large features into smaller PRs that can run and be verified independently.
- Do not mix unrelated features, style changes, refactors, or dependency upgrades in one PR.
- Do not perform unrelated refactors.
- Do not add placeholder code or bulk files unrelated to the project goal.
- Keep edits minimal and follow the existing directory structure, naming, and technical style.

## Originality And Sources

- Do not copy unauthorized code.
- Do not hide third-party sources.
- Do not present third-party work, template code, example code, or generated assets as original work.
- When introducing a third-party library, framework, template, example code, generated asset, external API, model, or data source, update `README.md` to document the dependency and the boundary of original project functionality.
- When reusing previously written code, state the source, reuse scope, and current modifications in the PR description.
- Do not submit code whose source cannot be explained.

## README Updates

Update `README.md` when any of the following changes occur:

- A third-party library, framework, template, or tool is added or removed.
- An external service, API, model, data source, or asset source is added.
- Runtime instructions, environment variables, build commands, test commands, or demo flow change.
- MVP capability, feature scope, or the boundary of original functionality changes.

When updating `README.md`, make dependencies, source boundaries, runtime instructions, test instructions, and original functionality boundaries directly identifiable.

## Commit Rules

Before committing or suggesting a commit, check:

- The current time is still between 2026-06-05 00:00 and 2026-06-07 23:59 Beijing time.
- `git status` and the relevant diff contain only changes needed for the current task.
- `README.md` is not missing dependency, runtime, or original-boundary documentation.
- The PR description does not need additional third-party source or reused-code disclosure.

Commit messages must use Conventional Commits:

```text
<type>(<scope>): <summary>
```

`scope` is optional; prefer it when a clear module is affected.

Common allowed types:

- `feat`: new functionality
- `fix`: bug fix
- `docs`: documentation change
- `style`: formatting or styling change that does not affect logic
- `refactor`: behavior-preserving refactor
- `test`: test addition or change
- `chore`: project configuration, scaffolding, or dependency maintenance

Do not use vague commit messages such as `update`, `fix bug`, `wip`, or `misc`.
Commit subjects must be written in ASCII English. Do not use full-width punctuation such as `，`, `。`, or `：`.

## PR Rules

When creating or helping write a PR, ensure:

- The PR title states in one sentence what was added or changed.
- The PR description is not blank.
- The PR description matches the actual code changes.
- The PR covers only one feature or one clearly bounded change.
- The main branch will remain runnable after the PR is merged.

The PR description must use this structure:

```markdown
## 功能描述

说明该功能的作用与使用方式。

## 实现思路

说明技术选型、核心实现逻辑、重要数据流或关键模块。

## 测试方式

说明如何验证该功能正常运行。列出执行过的命令、手动测试步骤或未能测试的原因。

## 来源与依赖

说明是否引用第三方库、框架、模板、示例代码、生成素材，或复用过去代码。没有则写“无”。
```

If a PR introduces dependencies, reuses code, or cites external sources, confirm that both `README.md` and the PR description disclose them.

## Testing And Verification

- After changing code, run the relevant tests, build, or manual verification.
- If tests cannot be run, explain why in the final response or PR description.
- Do not hide failing tests, build errors, or runtime errors.
- Do not claim that unexecuted tests passed.

## Final Response Checklist

After completing a development task, tell the user:

- Which files changed.
- Whether `README.md` was updated.
- Which tests or verification steps were run.
- Whether third-party dependencies, external sources, or reused code were involved.
- The suggested Conventional Commit message.
