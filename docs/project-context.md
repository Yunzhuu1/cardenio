# Project Context

This document gives agents lightweight product context without expanding `AGENTS.md`.

## Authoritative Documents

This file is a summary. For detailed, binding specifications, defer to:

- [`docs/product/requirements.md`](./product/requirements.md) — full PRD with numbered requirements (`FR-x` / `NFR-x`), design principles, and the canonical YAML schema.
- [`docs/product/mvp-roadmap.md`](./product/mvp-roadmap.md) — milestone breakdown (M0–M8), task list, dependencies, and per-task acceptance.

When this summary and the PRD disagree, the PRD wins.

## Current Status

- The project is in early planning and prototype development.
- The repository currently contains product documentation (PRD, MVP roadmap), agent rules, and PR process setup.
- The first milestone is a demonstrable MVP for Chinese novel-to-script adaptation.

## Product Direction

Cardenio / 入戏 is an AI-assisted adaptation tool for Chinese novel authors. It helps transform at least 3 chapters of novel text into a structured, character-consistent script draft that authors can keep editing.

The product should behave like an adaptation assistant (a co-pilot), not a generic rewriting tool or a one-click black box. The author always keeps the final decision.

- Understand the source novel before adapting it.
- Generate scene outlines before script text.
- Treat adaptation as media translation: turn psychology and narration into action, dialogue, subtext, environment, and sound — never silently delete or stuff in filler lines.
- Preserve character traits, relationship changes, emotional tone, and key foreshadowing; keep the author's style, not a generic screenwriter voice.
- Explain adaptation tradeoffs such as deletions, merges, rewrites, and additions.
- Support local scene or dialogue rewrites without regenerating the entire script.

### Trust features (do not defer)

These make the difference between a usable tool and a black box. They ship with the generation features, not as later polish:

- `source_ref` — every scene and line traces back to its source chapter and paragraph.
- `ai_inferred` flag — anything the AI added that is not in the source is explicitly marked and filterable; `from_source` marks original content.
- Author confirmation gates — understanding and character profiles must be confirmed before script generation (understand first, then adapt).
- Leave blanks (`TODO`) where the AI is unsure rather than filling with mediocre content.

## Target Users

- Novel authors
- Web novel authors
- Scriptwriting learners
- Creators adapting novels into short dramas, films, TV series, or stage plays
- Content teams that need a first script draft quickly

The first version prioritizes Chinese novel authors while keeping future internationalization in mind.

## MVP Scope

The MVP should let a user import at least 3 chapters of novel text and generate the following, each as an editable, re-visitable artifact:

- Work understanding report (with narrative-perspective markers and a style fingerprint)
- Character profiles (with voice fingerprint and hard rules)
- Author intent constraints
- Adaptation direction selection (faithful / cinematic / short drama for MVP)
- Scene outline
- Script draft as structured YAML, carrying `source_ref` and `ai_inferred` markers
- Adaptation tradeoff report
- Local rewrite support (natural-language, single scene, does not touch the rest)

The script artifact follows the canonical YAML schema in the PRD (`requirements.md` §7). Implementation is sequenced as milestones M0–M8 in `mvp-roadmap.md`; M0 freezes the data contract before upstream generation work.

## Planned Input Formats

Initial priority:

- Pasted text
- Chapter-by-chapter input
- TXT import
- DOCX import

Future formats:

- RTF
- PDF
- EPUB

## Planned Export Formats

Initial priority:

- DOCX
- PDF
- Fountain

Future formats:

- FDX
- RTF
- Markdown

## Future Roadmap

- Character consistency checks
- Dialogue optimization
- Pacing diagnosis
- Foreshadowing tracking
- Multiple adaptation versions
- Episode structure generation
- Long-form continuous novel adaptation
- Script export templates
- Multilingual UI
- Multilingual script format support

## Implementation Guidance For Agents

- Prefer features that move the MVP toward a runnable demonstration; follow the milestone order in `mvp-roadmap.md` (data contract first).
- Keep Chinese author workflows as the default product assumption.
- Preserve user-editable intermediate artifacts instead of hiding everything behind one final generation step.
- Ship trust features (`source_ref`, `ai_inferred`, confirmation gates, `TODO` blanks) alongside generation, not as later polish.
- Treat the PRD's numbered requirements and YAML schema as the binding contract; raise an issue before changing the schema.
- When adding functionality, make the current project status and future roadmap visible through documentation or UI only when it helps the MVP.
- Do not implement future-roadmap features unless the current task explicitly requests them.
