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

export type MvpDirection = "faithful" | "cinematic" | "short_drama";

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

export type ResolvedParagraph = {
  index: number;
  text: string;
};

export type ResolveResponse = {
  chapter: number;
  paragraphs: ResolvedParagraph[];
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

export type SourceRef = {
  chapter: number;
  paragraphs: number[];
};

export type ArtifactState = "draft" | "confirmed" | "needs_recompute";
export type Flag = "from_source" | "ai_inferred";

export type ArtifactEnvelope<T> = {
  type: string;
  state: ArtifactState;
  version: string;
  parent_version: string | null;
  etag: string | null;
  updated_at: string;
  needs_recompute: boolean;
  data: T;
};

export type Narrative = {
  perspective: string;
  tense: string;
  unreliable: boolean;
};

export type NonVisualizableMark = {
  source_ref: SourceRef;
  note: string;
};

export type UnderstandingData = {
  logline: string;
  synopsis: string;
  themes: string[];
  protagonist_goal: string;
  protagonist_fear: string;
  central_conflict: string;
  mood: string;
  style_fingerprint: string;
  narrative: Narrative;
  non_visualizable: NonVisualizableMark[];
  strengths: string[];
  difficulties: string[];
};

export type CharacterRole = "protagonist" | "supporting" | "mentioned";

export type CharacterRelation = {
  to: string;
  type: string;
  change: string | null;
};

export type Character = {
  id: string;
  name: string;
  role: CharacterRole;
  voice: string;
  desire: string;
  fear: string;
  arc: string | null;
  relations: CharacterRelation[];
  hard_rules: string[];
};

export type CharactersData = {
  characters: Character[];
};

export type IntExt = "INT" | "EXT";
export type TimeOfDay = "DAY" | "NIGHT" | "DAWN" | "DUSK";

export type SceneHeading = {
  int_ext: IntExt;
  location: string;
  time: TimeOfDay;
};

export type RelationChange = {
  characters: string[];
  change: string;
};

export type OutlineScene = {
  id: string;
  heading: SceneHeading;
  source_ref: SourceRef;
  synopsis: string;
  goal: string | null;
  conflict: string | null;
  mood: string | null;
  characters: string[];
  foreshadowing: string[];
  relation_changes: RelationChange[];
  ending_state: string | null;
};

export type MergeSuggestionStatus = "pending" | "applied" | "dismissed";

export type MergeSuggestion = {
  id: string;
  scene_ids: string[];
  reason: string;
  status: MergeSuggestionStatus;
};

export type OutlineData = {
  scenes: OutlineScene[];
  merge_suggestions: MergeSuggestion[];
};

export type MergeSuggestionsResponse = {
  suggestions: MergeSuggestion[];
};

export type BeatType =
  | "action"
  | "dialogue"
  | "voice_over"
  | "off_screen"
  | "note"
  | "todo";

export type BeatOption = {
  kind: string;
  text: string;
};

export type Beat = {
  type: BeatType;
  text: string | null;
  character: string | null;
  parenthetical: string | null;
  dialogue: string | null;
  subtext: string | null;
  source_ref: SourceRef | null;
  flag: Flag | null;
  options: BeatOption[] | null;
};

export type ShotHints = {
  enabled: boolean;
};

export type ScreenplayScene = {
  id: string;
  heading: SceneHeading;
  source_ref: SourceRef;
  synopsis: string | null;
  goal: string | null;
  conflict: string | null;
  mood: string | null;
  characters: string[];
  foreshadowing: string[];
  relation_changes: RelationChange[];
  ending_state: string | null;
  beats: Beat[];
};

export type ScreenplayData = {
  scenes: ScreenplayScene[];
  shot_hints: ShotHints;
};

export type ReportEntry = {
  item: string;
  source_ref: SourceRef | null;
  scene_id: string | null;
  flag: Flag | null;
  desc: string | null;
};

export type ReportMergedEntry = {
  scene_ids: string[];
  into: string;
};

export type ExternalizationEntry = {
  scene_id: string;
  from_type: string;
  to_type: string;
};

export type ReviewRecommendation = {
  scene_id: string;
  reason: string;
};

export type ReportData = {
  kept: ReportEntry[];
  deleted: ReportEntry[];
  merged: ReportMergedEntry[];
  added: ReportEntry[];
  externalized: ExternalizationEntry[];
  from_source_lines: number;
  ai_inferred_lines: number;
  kept_foreshadowing: string[];
  review_recommended: ReviewRecommendation[];
};

export type BeatsFilterItem = {
  scene_id: string;
  beat_index: number;
  beat: Beat;
};

export type BeatsFilterResponse = {
  items: BeatsFilterItem[];
  count: number;
};

export type TraceBeat = {
  beat_index: number;
  source_ref: SourceRef | null;
  flag: Flag | null;
  type: string;
};

export type SceneTrace = {
  scene_id: string;
  source_ref: SourceRef;
  paragraphs: ResolvedParagraph[];
  beats: TraceBeat[];
};

export type TodoItem = {
  scene_id: string;
  beat_index: number;
  source_ref: SourceRef | null;
  beat: Beat;
};

export type TodosResponse = {
  items: TodoItem[];
  count: number;
};

export type IntentConstraints = {
  keep: string[];
  no_delete: string[];
  no_merge: string[];
  must_keep_lines: string[];
  mood_floor: string | null;
  allow_new_plot: boolean;
  allow_reorder: boolean;
  allow_new_ending: boolean;
  target_type: AdaptationDirection | null;
};

export type IntentConflict = {
  code: string;
  message: string;
  fields: string[];
};

export type DirectionResponse = {
  direction: MvpDirection;
  project: Project;
};

export type IntentValidateResponse = {
  conflicts: IntentConflict[];
};

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
