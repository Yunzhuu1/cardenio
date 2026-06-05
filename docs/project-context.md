# Project Context

This document gives agents lightweight product context without expanding `AGENTS.md`.

## Current Status

- The project is in early planning and prototype development.
- The repository currently contains project documentation, agent rules, and PR process setup.
- The first milestone is a demonstrable MVP for Chinese novel-to-script adaptation.

## Product Direction

Cardenio / 入戏 is an AI-assisted adaptation tool for Chinese novel authors. It helps transform at least 3 chapters of novel text into a structured, character-consistent script draft that authors can keep editing.

The product should behave like an adaptation assistant, not a generic rewriting tool:

- Understand the source novel before adapting it.
- Generate scene outlines before script text.
- Preserve character traits, relationship changes, emotional tone, and key foreshadowing.
- Explain adaptation tradeoffs such as deletions, merges, rewrites, and additions.
- Support local scene or dialogue rewrites without regenerating the entire script.

## Target Users

- Novel authors
- Web novel authors
- Scriptwriting learners
- Creators adapting novels into short dramas, films, TV series, or stage plays
- Content teams that need a first script draft quickly

The first version prioritizes Chinese novel authors while keeping future internationalization in mind.

## MVP Scope

The MVP should let a user import at least 3 chapters of novel text and generate:

- Work understanding report
- Character profiles
- Author intent constraints
- Adaptation direction selection
- Scene outline
- Script draft
- Adaptation tradeoff report
- Local rewrite support

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

- Prefer features that move the MVP toward a runnable demonstration.
- Keep Chinese author workflows as the default product assumption.
- Preserve user-editable intermediate artifacts instead of hiding everything behind one final generation step.
- When adding functionality, make the current project status and future roadmap visible through documentation or UI only when it helps the MVP.
- Do not implement future-roadmap features unless the current task explicitly requests them.
