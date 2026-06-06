import type { ApiClient } from "./client";
import {
  ApiError,
  type Chapter,
  type ChapterId,
  type ConfirmImportInput,
  type CreateChapterInput,
  type CreateProjectInput,
  type ImportPreview,
  type Paginated,
  type PatchProjectInput,
  type Project,
  type ProjectId,
  type ProjectSummary,
  type Source,
  type SourceParagraph,
} from "./types";

const LATENCY_MS = 300;
const MIN_CHAPTERS = 3;
const delay = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, LATENCY_MS));

const store = new Map<ProjectId, Project>();
const sourceStore = new Map<ProjectId, Chapter[]>();
let seeded = false;

function ensureSeed(): void {
  if (seeded) return;
  seeded = true;

  const seeds: Project[] = [
    {
      id: "prj_demo_outlined",
      title: "旧书店的信",
      state: "outlined",
      updated_at: "2026-06-05T09:00:00Z",
      meta: {
        ui_language: "zh-CN",
        source_language: "zh-CN",
        output_language: "zh-CN",
        adaptation_direction: "short_drama",
        style_fingerprint: "克制、冷硬、意象密集",
      },
      gates: {
        understanding: "confirmed",
        characters: "confirmed",
        outline: "draft",
      },
    },
    {
      id: "prj_demo_imported",
      title: "山中来信",
      state: "imported",
      updated_at: "2026-06-04T14:30:00Z",
      meta: {
        ui_language: "zh-CN",
        source_language: "zh-CN",
        output_language: "zh-CN",
        adaptation_direction: null,
        style_fingerprint: null,
      },
      gates: {
        understanding: "empty",
        characters: "empty",
        outline: "empty",
      },
    },
  ];

  for (const project of seeds) store.set(project.id, project);

  sourceStore.set("prj_demo_imported", [
    chapterFromText({
      id: "ch_1",
      title: "第一章",
      order: 1,
      text: "山路尽头，雾气压在旧邮亭上。\n\n林澈把信封翻过来，看见没有署名的火漆。",
    }),
    chapterFromText({
      id: "ch_2",
      title: "第二章",
      order: 2,
      text: "母亲的电话在雨声里断断续续。\n\n她只问了一句：你是不是又回去了？",
    }),
    chapterFromText({
      id: "ch_3",
      title: "第三章",
      order: 3,
      text: "夜里十一点，邮亭的灯自己亮了。\n\n林澈听见门内有人轻轻敲了三下。",
    }),
  ]);
}

let counter = 0;
function nextId(): ProjectId {
  counter += 1;
  return `prj_${Date.now().toString(36)}${counter}`;
}

function getProjectOrThrow(projectId: ProjectId): Project {
  ensureSeed();
  const project = store.get(projectId);
  if (!project) {
    throw new ApiError(404, {
      code: "not_found",
      message: "项目不存在",
      retryable: false,
    });
  }
  return project;
}

function splitParagraphs(text: string): SourceParagraph[] {
  return text
    .replace(/\n{3,}/g, "\n\n")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph, index) => ({ index: index + 1, text: paragraph }));
}

function countChars(paragraphs: SourceParagraph[]): number {
  return paragraphs.reduce(
    (total, paragraph) => total + paragraph.text.length,
    0,
  );
}

function chapterFromText(input: {
  id: ChapterId;
  title: string;
  order: number;
  text: string;
}): Chapter {
  const paragraphs = splitParagraphs(input.text);
  return {
    id: input.id,
    title: input.title,
    order: input.order,
    paragraphs,
    char_count: countChars(paragraphs),
  };
}

function nextChapterId(chapters: Chapter[]): ChapterId {
  return `ch_${chapters.length + 1}`;
}

function renumberParagraphs(paragraphs: SourceParagraph[]): SourceParagraph[] {
  return paragraphs.map((paragraph, index) => ({
    index: index + 1,
    text: paragraph.text,
  }));
}

function normalizeChapters(chapters: Chapter[]): Chapter[] {
  return [...chapters]
    .sort((a, b) => a.order - b.order)
    .map((chapter, index) => {
      const paragraphs = renumberParagraphs(chapter.paragraphs);
      return {
        ...chapter,
        order: index + 1,
        paragraphs,
        char_count: countChars(paragraphs),
      };
    });
}

function makeSource(chapters: Chapter[]): Source {
  const normalized = normalizeChapters(chapters);
  const chapterCount = normalized.length;
  const charCount = normalized.reduce(
    (total, chapter) => total + chapter.char_count,
    0,
  );
  return {
    chapters: normalized,
    stats: {
      chapter_count: chapterCount,
      char_count: charCount,
      min_chapters: MIN_CHAPTERS,
    },
    threshold: {
      min_chapters: MIN_CHAPTERS,
      passed: chapterCount >= MIN_CHAPTERS,
      blocked:
        chapterCount >= MIN_CHAPTERS
          ? undefined
          : `至少需要 ${MIN_CHAPTERS} 章原文`,
    },
  };
}

function saveSource(projectId: ProjectId, chapters: Chapter[]): Source {
  const source = makeSource(chapters);
  sourceStore.set(projectId, source.chapters);
  return source;
}

function detectPreviewChapters(text: string): ImportPreview {
  const normalized = text.replace(/\r\n?/g, "\n").trim();
  if (!normalized) return { chapters: [], warnings: ["文件内容为空"] };

  const headingPattern =
    /^(第\s*[一二三四五六七八九十百千万零〇\d]+\s*章[^\n]*|Chapter\s+\d+[^\n]*)$/gim;
  const matches = [...normalized.matchAll(headingPattern)];
  if (matches.length === 0) {
    return {
      chapters: [
        {
          title: "第 1 章",
          text: normalized,
          char_count: normalized.length,
          paragraphs: [1, splitParagraphs(normalized).length],
        },
      ],
      warnings: [],
    };
  }

  const chapters = matches
    .map((match, index) => {
      const start = (match.index ?? 0) + match[0].length;
      const end =
        index + 1 < matches.length
          ? (matches[index + 1].index ?? normalized.length)
          : normalized.length;
      const chapterText = normalized.slice(start, end).trim();
      const paragraphs = splitParagraphs(chapterText);
      return {
        title: match[0].trim(),
        text: chapterText,
        char_count: chapterText.length,
        paragraphs: [1, paragraphs.length] as [number, number],
      };
    })
    .filter((chapter) => chapter.text.length > 0);

  return { chapters, warnings: [] };
}

function setProjectImported(projectId: ProjectId): void {
  const project = store.get(projectId);
  if (!project) return;
  store.set(projectId, {
    ...project,
    state: "imported",
    updated_at: new Date().toISOString(),
  });
}

export const mockClient: ApiClient = {
  projects: {
    async list() {
      ensureSeed();
      await delay();
      const items: ProjectSummary[] = [...store.values()]
        .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
        .map(({ id, title, state, updated_at }) => ({
          id,
          title,
          state,
          updated_at,
        }));
      return { items, next_cursor: null } satisfies Paginated<ProjectSummary>;
    },
    async get(id) {
      ensureSeed();
      await delay();
      const project = store.get(id);
      if (!project) {
        throw new ApiError(404, {
          code: "not_found",
          message: "项目不存在",
          retryable: false,
        });
      }
      return project;
    },
    async create(input: CreateProjectInput) {
      ensureSeed();
      await delay();
      const id = nextId();
      const project: Project = {
        id,
        title: input.title,
        state: "empty",
        updated_at: new Date().toISOString(),
        meta: {
          ui_language: input.ui_language,
          source_language: input.source_language,
          output_language: input.output_language,
          adaptation_direction: input.adaptation_direction,
          style_fingerprint: null,
        },
        gates: {
          understanding: "empty",
          characters: "empty",
          outline: "empty",
        },
      };
      store.set(id, project);
      return project;
    },
    async patch(id, input: PatchProjectInput) {
      ensureSeed();
      await delay();
      const project = store.get(id);
      if (!project) {
        throw new ApiError(404, {
          code: "not_found",
          message: "项目不存在",
          retryable: false,
        });
      }
      const updated: Project = {
        ...project,
        title: input.title ?? project.title,
        meta: {
          ...project.meta,
          source_language:
            input.source_language ?? project.meta.source_language,
          output_language:
            input.output_language ?? project.meta.output_language,
          adaptation_direction:
            input.adaptation_direction ?? project.meta.adaptation_direction,
        },
        updated_at: new Date().toISOString(),
      };
      store.set(id, updated);
      return updated;
    },
    async remove(id) {
      ensureSeed();
      await delay();
      store.delete(id);
      sourceStore.delete(id);
    },
  },
  source: {
    async get(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      return makeSource(sourceStore.get(projectId) ?? []);
    },
    async addChapter(projectId, input: CreateChapterInput) {
      getProjectOrThrow(projectId);
      await delay();
      const chapters = sourceStore.get(projectId) ?? [];
      const chapter = chapterFromText({
        id: nextChapterId(chapters),
        title: input.title,
        order: input.order ?? chapters.length + 1,
        text: input.text,
      });
      saveSource(projectId, [...chapters, chapter]);
      setProjectImported(projectId);
      return chapter;
    },
    async updateChapter(projectId, chapterId, chapter) {
      getProjectOrThrow(projectId);
      await delay();
      const chapters = sourceStore.get(projectId) ?? [];
      const index = chapters.findIndex((item) => item.id === chapterId);
      if (index < 0) {
        throw new ApiError(404, {
          code: "not_found",
          message: "章节不存在",
          retryable: false,
        });
      }
      const next = [...chapters];
      next[index] = {
        id: chapter.id,
        title: chapter.title,
        order: chapter.order,
        char_count: chapter.char_count,
        paragraphs: chapter.paragraphs,
      };
      return saveSource(projectId, next).chapters.find(
        (item) => item.id === chapter.id,
      ) as Chapter;
    },
    async deleteChapter(projectId, chapterId) {
      getProjectOrThrow(projectId);
      await delay();
      const chapters = sourceStore.get(projectId) ?? [];
      sourceStore.set(
        projectId,
        normalizeChapters(
          chapters.filter((chapter) => chapter.id !== chapterId),
        ),
      );
    },
    async resegment(projectId, input) {
      getProjectOrThrow(projectId);
      await delay();
      const chapters = normalizeChapters(sourceStore.get(projectId) ?? []);

      if (input.op === "split") {
        const index = chapters.findIndex(
          (chapter) => chapter.id === input.chapter_id,
        );
        if (index < 0) {
          throw new ApiError(404, {
            code: "not_found",
            message: "章节不存在",
            retryable: false,
          });
        }

        const chapter = chapters[index];
        const splitIndex = input.at_paragraph - 1;
        const before = chapter.paragraphs.slice(0, splitIndex);
        const after = chapter.paragraphs.slice(splitIndex);
        if (before.length === 0 || after.length === 0) {
          throw new ApiError(400, {
            code: "invalid_split",
            message: "拆分点必须位于章节中间段落",
            retryable: false,
          });
        }

        const first: Chapter = {
          ...chapter,
          paragraphs: renumberParagraphs(before),
          char_count: countChars(before),
        };
        const second: Chapter = {
          id: `ch_${chapters.length + 2}`,
          title: `${chapter.title}（下）`,
          order: chapter.order + 1,
          paragraphs: renumberParagraphs(after),
          char_count: countChars(after),
        };
        return saveSource(projectId, [
          ...chapters.slice(0, index),
          first,
          second,
          ...chapters.slice(index + 1),
        ]);
      }

      const selected = chapters.filter((chapter) =>
        input.chapter_ids.includes(chapter.id),
      );
      if (selected.length < 2) {
        throw new ApiError(400, {
          code: "invalid_merge",
          message: "至少选择两章才能合并",
          retryable: false,
        });
      }

      const selectedIds = new Set(input.chapter_ids);
      const firstSelected = selected[0];
      const mergedParagraphs = renumberParagraphs(
        selected.flatMap((chapter) => chapter.paragraphs),
      );
      const merged: Chapter = {
        id: firstSelected.id,
        title: input.new_title ?? firstSelected.title,
        order: firstSelected.order,
        paragraphs: mergedParagraphs,
        char_count: countChars(mergedParagraphs),
      };
      const next = chapters.flatMap((chapter) => {
        if (chapter.id === firstSelected.id) return [merged];
        if (selectedIds.has(chapter.id)) return [];
        return [chapter];
      });
      return saveSource(projectId, next);
    },
    async importFile(projectId, file) {
      getProjectOrThrow(projectId);
      await delay();
      return detectPreviewChapters(await file.text());
    },
    async confirmImport(projectId, input: ConfirmImportInput) {
      getProjectOrThrow(projectId);
      await delay();
      const chapters = input.chapters.map((chapter, index) =>
        chapterFromText({
          id: `ch_${index + 1}`,
          title: chapter.title,
          order: chapter.order ?? index + 1,
          text: chapter.text,
        }),
      );
      setProjectImported(projectId);
      return saveSource(projectId, chapters);
    },
  },
};
