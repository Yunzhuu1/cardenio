import type { ApiClient } from "./client";
import {
  ApiError,
  type ArtifactEnvelope,
  type ArtifactState,
  type Chapter,
  type ChapterId,
  type CharactersData,
  type ConfirmImportInput,
  type CreateChapterInput,
  type CreateProjectInput,
  type DirectionResponse,
  type ImportPreview,
  type IntentConflict,
  type IntentConstraints,
  type IntentValidateResponse,
  type MvpDirection,
  type Paginated,
  type PatchProjectInput,
  type Project,
  type ProjectId,
  type ProjectSummary,
  type Source,
  type SourceParagraph,
  type UnderstandingData,
} from "./types";

const LATENCY_MS = 300;
const MIN_CHAPTERS = 3;
const delay = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, LATENCY_MS));

const store = new Map<ProjectId, Project>();
const sourceStore = new Map<ProjectId, Chapter[]>();
const understandingStore = new Map<
  ProjectId,
  ArtifactEnvelope<UnderstandingData>
>();
const charactersStore = new Map<ProjectId, ArtifactEnvelope<CharactersData>>();
const intentStore = new Map<ProjectId, ArtifactEnvelope<IntentConstraints>>();
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

  const understanding = makeEnvelope("understanding", "confirmed", {
    logline: "一名返乡青年在旧书店里追查父亲留下的最后一封信。",
    synopsis:
      "林澈回到多年未归的山城，在旧书店和邮亭之间发现父亲生前留下的线索。随着信件逐步拼合，她必须面对家族沉默与自己的逃避。",
    themes: ["亲情修复", "记忆与真相"],
    protagonist_goal: "找出父亲失踪前隐瞒的真相",
    protagonist_fear: "发现自己一直误解了最亲近的人",
    central_conflict: "追查真相的愿望与维持家庭表面平静的压力相冲突",
    mood: "悬疑、克制、带有潮湿的怀旧感",
    style_fingerprint: "克制、冷硬、意象密集",
    narrative: {
      perspective: "third_person_limited",
      tense: "past",
      unreliable: false,
    },
    non_visualizable: [
      {
        source_ref: { chapter: 1, paragraphs: [2] },
        note: "主角对父亲的愧疚需要外化为动作或道具。",
      },
    ],
    strengths: ["场景意象鲜明", "人物关系带有悬念"],
    difficulties: ["内心独白较多，需要转化为可表演动作"],
  });
  understandingStore.set("prj_demo_outlined", understanding);

  charactersStore.set(
    "prj_demo_outlined",
    makeEnvelope("characters", "confirmed", {
      characters: [
        {
          id: "lin_che",
          name: "林澈",
          role: "protagonist",
          voice: "短句、克制，追问时会突然变得尖锐",
          desire: "还原父亲失踪前的真相",
          fear: "自己曾经亲手错过和解机会",
          arc: "从逃避家庭记忆到主动承担真相",
          relations: [
            {
              to: "mother",
              type: "母女",
              change: "从回避争执到共同面对旧事",
            },
          ],
          hard_rules: ["不主动示弱", "谈及父亲时先转移视线"],
        },
        {
          id: "mother",
          name: "母亲",
          role: "supporting",
          voice: "含蓄、回避细节，常用反问",
          desire: "保护女儿不被旧事拖垮",
          fear: "当年的选择被重新审判",
          arc: "从隐瞒到有限坦白",
          relations: [
            {
              to: "lin_che",
              type: "母女",
              change: "由控制到放手",
            },
          ],
          hard_rules: ["不直接说谎，只省略关键事实"],
        },
      ],
    }),
  );
}

let counter = 0;
let artifactCounter = 0;
function nextId(): ProjectId {
  counter += 1;
  return `prj_${Date.now().toString(36)}${counter}`;
}

function nextVersion(): string {
  artifactCounter += 1;
  return `v_mock${artifactCounter}`;
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

function makeEnvelope<T>(
  type: string,
  state: ArtifactState,
  data: T,
  parentVersion: string | null = null,
): ArtifactEnvelope<T> {
  return {
    type,
    state,
    version: nextVersion(),
    parent_version: parentVersion,
    etag: null,
    updated_at: new Date().toISOString(),
    needs_recompute: false,
    data,
  };
}

function notFound(message: string): ApiError {
  return new ApiError(404, {
    code: "not_found",
    message,
    retryable: false,
  });
}

function updateProject(
  projectId: ProjectId,
  updater: (project: Project) => Project,
): void {
  const project = store.get(projectId);
  if (!project) return;
  store.set(projectId, updater(project));
}

function setUnderstandingGate(
  projectId: ProjectId,
  state: "draft" | "confirmed",
  styleFingerprint: string,
): void {
  updateProject(projectId, (project) => ({
    ...project,
    state:
      state === "confirmed" && project.state === "imported"
        ? "understood"
        : project.state,
    meta: {
      ...project.meta,
      style_fingerprint: styleFingerprint,
    },
    gates: {
      ...project.gates,
      understanding: state,
    },
    updated_at: new Date().toISOString(),
  }));
}

function setCharactersGate(
  projectId: ProjectId,
  state: "draft" | "confirmed",
): void {
  updateProject(projectId, (project) => ({
    ...project,
    state:
      state === "confirmed" && project.state === "understood"
        ? "profiled"
        : project.state,
    gates: {
      ...project.gates,
      characters: state,
    },
    updated_at: new Date().toISOString(),
  }));
}

function makeUnderstandingData(projectId: ProjectId): UnderstandingData {
  const source = makeSource(sourceStore.get(projectId) ?? []);
  const firstTitle = source.chapters[0]?.title ?? "第一章";
  return {
    logline: "一名返乡青年在旧地追查一封无名信背后的家族真相。",
    synopsis: `${firstTitle}开始，主角被一封没有署名的信带回旧日关系。随着章节推进，她逐步发现沉默的家人和旧地记忆都藏着未说出口的选择。`,
    themes: ["记忆与真相", "亲情修复"],
    protagonist_goal: "查清无名信的来源",
    protagonist_fear: "真相会证明自己当年的逃离不可原谅",
    central_conflict: "追问真相会撕开家人努力维持的沉默",
    mood: "悬疑、克制、带一点潮湿的怀旧感",
    style_fingerprint: "短句推进，意象密集，情绪压在动作之后",
    narrative: {
      perspective: "third_person_limited",
      tense: "past",
      unreliable: false,
    },
    non_visualizable: [
      {
        source_ref: { chapter: 1, paragraphs: [2] },
        note: "主角的愧疚和迟疑需要改写成可观察的动作。",
      },
    ],
    strengths: ["章节钩子清晰", "场景意象适合影视化"],
    difficulties: ["心理活动较多", "家庭旧事需要通过对白和道具揭示"],
  };
}

function makeCharactersData(): CharactersData {
  return {
    characters: [
      {
        id: "lin_che",
        name: "林澈",
        role: "protagonist",
        voice: "短句、克制，紧张时会反问",
        desire: "找到无名信的来源",
        fear: "真相证明自己误解了家人",
        arc: "从逃避旧事到主动追问",
        relations: [
          {
            to: "mother",
            type: "母女",
            change: "从对抗到有限合作",
          },
        ],
        hard_rules: ["不主动示弱", "谈及父亲时会回避眼神"],
      },
      {
        id: "mother",
        name: "母亲",
        role: "supporting",
        voice: "话少、常用反问回避核心问题",
        desire: "阻止旧事伤害女儿",
        fear: "自己的隐瞒被彻底揭开",
        arc: "从压制真相到交出关键线索",
        relations: [
          {
            to: "lin_che",
            type: "母女",
            change: "从控制到放手",
          },
        ],
        hard_rules: ["不直接承认自己害怕", "不主动提父亲名字"],
      },
      {
        id: "bookstore_owner",
        name: "旧书店老板",
        role: "mentioned",
        voice: "慢条斯理，喜欢用旧物打比方",
        desire: "守住故人的承诺",
        fear: "信件被交给错误的人",
        arc: null,
        relations: [
          {
            to: "lin_che",
            type: "线索提供者",
            change: "从试探到交付信件",
          },
        ],
        hard_rules: ["不一次说完全部线索"],
      },
    ],
  };
}

function getUnderstandingEnvelope(
  projectId: ProjectId,
): ArtifactEnvelope<UnderstandingData> {
  const envelope = understandingStore.get(projectId);
  if (!envelope) throw notFound("Understanding not found");
  return envelope;
}

function getCharactersEnvelope(
  projectId: ProjectId,
): ArtifactEnvelope<CharactersData> {
  const envelope = charactersStore.get(projectId);
  if (!envelope) throw notFound("Characters not found");
  return envelope;
}

function getIntentEnvelope(
  projectId: ProjectId,
): ArtifactEnvelope<IntentConstraints> {
  const envelope = intentStore.get(projectId);
  if (!envelope) throw notFound("Intent not found");
  return envelope;
}

function validateIntentConflicts(
  direction: MvpDirection | null,
  intent: IntentConstraints,
): IntentConflict[] {
  const conflicts: IntentConflict[] = [];
  if (direction === "faithful" && intent.allow_new_ending) {
    conflicts.push({
      code: "faithful_vs_new_ending",
      message: "忠实改编方向与允许调整结局存在冲突。",
      fields: ["direction", "allow_new_ending"],
    });
  }
  if (direction === "faithful" && intent.allow_new_plot) {
    conflicts.push({
      code: "faithful_vs_new_plot",
      message: "忠实改编方向与允许新增桥段存在冲突。",
      fields: ["direction", "allow_new_plot"],
    });
  }
  if (direction === "faithful" && intent.allow_reorder) {
    conflicts.push({
      code: "faithful_vs_reorder",
      message: "忠实改编方向与允许调整顺序存在冲突。",
      fields: ["direction", "allow_reorder"],
    });
  }
  if (direction === "short_drama" && !intent.allow_reorder) {
    conflicts.push({
      code: "short_drama_vs_no_reorder",
      message: "短剧模式通常需要调整顺序以强化前置钩子。",
      fields: ["direction", "allow_reorder"],
    });
  }
  return conflicts;
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
  understanding: {
    async get(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      return getUnderstandingEnvelope(projectId);
    },
    async generate(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      const source = makeSource(sourceStore.get(projectId) ?? []);
      if (!source.threshold.passed) {
        throw new ApiError(409, {
          code: "chapter_threshold_unmet",
          message: `至少需要 ${MIN_CHAPTERS} 章原文才能生成作品理解`,
          retryable: false,
          details: {
            min_chapters: MIN_CHAPTERS,
            current_chapters: source.stats.chapter_count,
            passed: false,
          },
        });
      }
      const previous = understandingStore.get(projectId);
      const data = makeUnderstandingData(projectId);
      const envelope = makeEnvelope(
        "understanding",
        "draft",
        data,
        previous?.version ?? null,
      );
      understandingStore.set(projectId, envelope);
      setUnderstandingGate(projectId, "draft", data.style_fingerprint);
      return envelope;
    },
    async update(projectId, data) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getUnderstandingEnvelope(projectId);
      const envelope = makeEnvelope(
        "understanding",
        "draft",
        data,
        previous.version,
      );
      understandingStore.set(projectId, envelope);
      setUnderstandingGate(projectId, "draft", data.style_fingerprint);
      return envelope;
    },
    async confirm(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getUnderstandingEnvelope(projectId);
      const envelope = makeEnvelope(
        "understanding",
        "confirmed",
        previous.data,
        previous.version,
      );
      understandingStore.set(projectId, envelope);
      setUnderstandingGate(
        projectId,
        "confirmed",
        previous.data.style_fingerprint,
      );
      return envelope;
    },
  },
  characters: {
    async get(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      return getCharactersEnvelope(projectId);
    },
    async generate(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      const understanding = understandingStore.get(projectId);
      if (understanding?.state !== "confirmed") {
        throw new ApiError(409, {
          code: "state_gate_blocked",
          message: "请先确认作品理解",
          retryable: false,
          details: {
            artifact: "understanding",
            required_state: "confirmed",
            current_state: understanding?.state ?? "empty",
          },
        });
      }
      const previous = charactersStore.get(projectId);
      const envelope = makeEnvelope(
        "characters",
        "draft",
        makeCharactersData(),
        previous?.version ?? null,
      );
      charactersStore.set(projectId, envelope);
      setCharactersGate(projectId, "draft");
      return envelope;
    },
    async add(projectId, character) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getCharactersEnvelope(projectId);
      if (previous.data.characters.some((item) => item.id === character.id)) {
        throw new ApiError(409, {
          code: "conflict",
          message: "Character already exists",
          retryable: false,
        });
      }
      const envelope = makeEnvelope(
        "characters",
        "draft",
        { characters: [...previous.data.characters, character] },
        previous.version,
      );
      charactersStore.set(projectId, envelope);
      setCharactersGate(projectId, "draft");
      return envelope;
    },
    async update(projectId, characterId, character) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getCharactersEnvelope(projectId);
      const index = previous.data.characters.findIndex(
        (item) => item.id === characterId,
      );
      if (index < 0) throw notFound("Character not found");
      const characters = [...previous.data.characters];
      characters[index] = character;
      const envelope = makeEnvelope(
        "characters",
        "draft",
        { characters },
        previous.version,
      );
      charactersStore.set(projectId, envelope);
      setCharactersGate(projectId, "draft");
      return envelope;
    },
    async remove(projectId, characterId) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getCharactersEnvelope(projectId);
      if (!previous.data.characters.some((item) => item.id === characterId)) {
        throw notFound("Character not found");
      }
      const envelope = makeEnvelope(
        "characters",
        "draft",
        {
          characters: previous.data.characters.filter(
            (item) => item.id !== characterId,
          ),
        },
        previous.version,
      );
      charactersStore.set(projectId, envelope);
      setCharactersGate(projectId, "draft");
    },
    async confirm(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = getCharactersEnvelope(projectId);
      const envelope = makeEnvelope(
        "characters",
        "confirmed",
        previous.data,
        previous.version,
      );
      charactersStore.set(projectId, envelope);
      setCharactersGate(projectId, "confirmed");
      return envelope;
    },
  },
  intent: {
    async get(projectId) {
      getProjectOrThrow(projectId);
      await delay();
      return getIntentEnvelope(projectId);
    },
    async save(projectId, data) {
      getProjectOrThrow(projectId);
      await delay();
      const previous = intentStore.get(projectId);
      const envelope = makeEnvelope(
        "intent",
        "confirmed",
        data,
        previous?.version ?? null,
      );
      intentStore.set(projectId, envelope);
      updateProject(projectId, (project) => ({
        ...project,
        state:
          project.state === "profiled" ||
          charactersStore.get(projectId)?.state === "confirmed"
            ? "intent_set"
            : project.state,
        updated_at: new Date().toISOString(),
      }));
      return envelope;
    },
    async setDirection(projectId, direction) {
      getProjectOrThrow(projectId);
      await delay();
      let updatedProject: Project | null = null;
      updateProject(projectId, (project) => {
        updatedProject = {
          ...project,
          meta: {
            ...project.meta,
            adaptation_direction: direction,
          },
          updated_at: new Date().toISOString(),
        };
        return updatedProject;
      });
      return {
        direction,
        project: updatedProject ?? getProjectOrThrow(projectId),
      } satisfies DirectionResponse;
    },
    async validate(projectId): Promise<IntentValidateResponse> {
      const project = getProjectOrThrow(projectId);
      await delay();
      const intent = getIntentEnvelope(projectId);
      const direction = project.meta.adaptation_direction;
      return {
        conflicts: validateIntentConflicts(
          direction === "faithful" ||
            direction === "cinematic" ||
            direction === "short_drama"
            ? direction
            : null,
          intent.data,
        ),
      };
    },
  },
};
