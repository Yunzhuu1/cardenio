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
