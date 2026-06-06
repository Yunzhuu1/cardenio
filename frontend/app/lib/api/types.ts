// Aligned with docs/design/api.md §3 (projects) and §14 (common objects).
export type ProjectId = string; // "prj_*"

export type UiLanguage = "zh-CN" | "en";
export type SourceLanguage = "zh-CN" | "en" | "mixed" | "unknown";
export type OutputLanguage = "zh-CN" | "en";

export type AdaptationDirection =
  | "faithful"
  | "cinematic"
  | "short_drama"
  | "tv"
  | "film"
  | "stage";

export type ProjectState =
  | "empty"
  | "imported"
  | "understood"
  | "profiled"
  | "intent_set"
  | "outlined"
  | "generated"
  | "editing"
  | "report"
  | "exported";

export type GateState = "empty" | "draft" | "confirmed";

export type ProjectGates = {
  understanding: GateState;
  characters: GateState;
  outline: GateState;
};

export type ProjectMeta = {
  ui_language: UiLanguage;
  source_language: SourceLanguage;
  output_language: OutputLanguage;
  adaptation_direction: AdaptationDirection | null;
  style_fingerprint: string | null;
};

export type ProjectSummary = {
  id: ProjectId;
  title: string;
  state: ProjectState;
  updated_at: string;
};

export type Project = ProjectSummary & {
  meta: ProjectMeta;
  gates: ProjectGates;
};

export type CreateProjectInput = {
  title: string;
  ui_language: UiLanguage;
  source_language: SourceLanguage;
  output_language: OutputLanguage;
  adaptation_direction: AdaptationDirection | null;
};

export type PatchProjectInput = Partial<
  Pick<
    CreateProjectInput,
    "title" | "source_language" | "output_language" | "adaptation_direction"
  >
>;

export type ChapterId = string; // "ch_*"

export type SourceParagraph = {
  index: number;
  text: string;
};

export type Chapter = {
  id: ChapterId;
  title: string;
  order: number;
  char_count: number;
  paragraphs: SourceParagraph[];
};

export type SourceStats = {
  chapter_count: number;
  char_count: number;
  min_chapters?: number;
};

export type SourceThreshold = {
  min_chapters: number;
  passed: boolean;
  blocked?: string;
};

export type Source = {
  chapters: Chapter[];
  stats: SourceStats;
  threshold: SourceThreshold;
};

export type CreateChapterInput = {
  title: string;
  text: string;
  order?: number;
};

export type UpdateChapterInput = Chapter;

export type ImportChapterPreview = {
  title: string;
  text: string;
  char_count?: number;
  paragraphs?: [number, number];
};

export type ImportPreview = {
  chapters: ImportChapterPreview[];
  warnings: string[];
};

export type ConfirmImportInput = {
  chapters: Array<{
    title: string;
    text: string;
    order?: number;
  }>;
};

export type ResegmentInput =
  | {
      op: "split";
      chapter_id: ChapterId;
      at_paragraph: number;
    }
  | {
      op: "merge";
      chapter_ids: ChapterId[];
      new_title?: string;
    };

export type Paginated<T> = { items: T[]; next_cursor: string | null };

export type ApiErrorBody = {
  code: string;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly details?: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.retryable = body.retryable;
    this.details = body.details;
  }
}
