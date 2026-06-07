import { httpClient } from "./http";
import { mockClient } from "./mock";
import type {
  ArtifactEnvelope,
  Character,
  Chapter,
  ChapterId,
  CharactersData,
  ConfirmImportInput,
  CreateChapterInput,
  CreateProjectInput,
  DirectionResponse,
  Flag,
  ImportPreview,
  IntentConstraints,
  IntentValidateResponse,
  MergeSuggestionsResponse,
  MvpDirection,
  OutlineData,
  OutlineScene,
  Paginated,
  PatchProjectInput,
  Project,
  ProjectId,
  ProjectSummary,
  ResolveResponse,
  ResegmentInput,
  ScreenplayData,
  ScreenplayScene,
  SceneTrace,
  Source,
  TodosResponse,
  UnderstandingData,
  UpdateChapterInput,
  BeatsFilterResponse,
} from "./types";

export type ProjectsApi = {
  list(params?: {
    limit?: number;
    cursor?: string;
  }): Promise<Paginated<ProjectSummary>>;
  get(id: ProjectId): Promise<Project>;
  create(input: CreateProjectInput): Promise<Project>;
  patch(id: ProjectId, input: PatchProjectInput): Promise<Project>;
  remove(id: ProjectId): Promise<void>;
};

export type SourceApi = {
  get(projectId: ProjectId): Promise<Source>;
  addChapter(projectId: ProjectId, input: CreateChapterInput): Promise<Chapter>;
  updateChapter(
    projectId: ProjectId,
    chapterId: ChapterId,
    chapter: UpdateChapterInput,
  ): Promise<Chapter>;
  deleteChapter(projectId: ProjectId, chapterId: ChapterId): Promise<void>;
  resegment(projectId: ProjectId, input: ResegmentInput): Promise<Source>;
  importFile(projectId: ProjectId, file: File): Promise<ImportPreview>;
  confirmImport(
    projectId: ProjectId,
    input: ConfirmImportInput,
  ): Promise<Source>;
  resolve(
    projectId: ProjectId,
    chapter: number,
    paragraphs: string,
  ): Promise<ResolveResponse>;
};

export type UnderstandingApi = {
  get(projectId: ProjectId): Promise<ArtifactEnvelope<UnderstandingData>>;
  generate(projectId: ProjectId): Promise<ArtifactEnvelope<UnderstandingData>>;
  update(
    projectId: ProjectId,
    data: UnderstandingData,
  ): Promise<ArtifactEnvelope<UnderstandingData>>;
  confirm(projectId: ProjectId): Promise<ArtifactEnvelope<UnderstandingData>>;
};

export type CharactersApi = {
  get(projectId: ProjectId): Promise<ArtifactEnvelope<CharactersData>>;
  generate(projectId: ProjectId): Promise<ArtifactEnvelope<CharactersData>>;
  add(
    projectId: ProjectId,
    character: Character,
  ): Promise<ArtifactEnvelope<CharactersData>>;
  update(
    projectId: ProjectId,
    characterId: string,
    character: Character,
  ): Promise<ArtifactEnvelope<CharactersData>>;
  remove(projectId: ProjectId, characterId: string): Promise<void>;
  confirm(projectId: ProjectId): Promise<ArtifactEnvelope<CharactersData>>;
};

export type IntentApi = {
  get(projectId: ProjectId): Promise<ArtifactEnvelope<IntentConstraints>>;
  save(
    projectId: ProjectId,
    data: IntentConstraints,
  ): Promise<ArtifactEnvelope<IntentConstraints>>;
  setDirection(
    projectId: ProjectId,
    direction: MvpDirection,
  ): Promise<DirectionResponse>;
  validate(projectId: ProjectId): Promise<IntentValidateResponse>;
};

export type OutlineApi = {
  get(projectId: ProjectId): Promise<ArtifactEnvelope<OutlineData>>;
  generate(projectId: ProjectId): Promise<ArtifactEnvelope<OutlineData>>;
  addScene(
    projectId: ProjectId,
    scene: OutlineScene,
  ): Promise<ArtifactEnvelope<OutlineData>>;
  updateScene(
    projectId: ProjectId,
    sceneId: string,
    scene: OutlineScene,
  ): Promise<ArtifactEnvelope<OutlineData>>;
  deleteScene(projectId: ProjectId, sceneId: string): Promise<void>;
  reorder(
    projectId: ProjectId,
    order: string[],
  ): Promise<ArtifactEnvelope<OutlineData>>;
  confirm(projectId: ProjectId): Promise<ArtifactEnvelope<OutlineData>>;
  getMergeSuggestions(projectId: ProjectId): Promise<MergeSuggestionsResponse>;
  applyMergeSuggestion(
    projectId: ProjectId,
    suggestionId: string,
  ): Promise<ArtifactEnvelope<OutlineData>>;
  dismissMergeSuggestion(
    projectId: ProjectId,
    suggestionId: string,
  ): Promise<ArtifactEnvelope<OutlineData>>;
};

export type ScreenplayApi = {
  get(projectId: ProjectId): Promise<ArtifactEnvelope<ScreenplayData>>;
  generate(
    projectId: ProjectId,
    options?: { shot_hints?: boolean },
  ): Promise<ArtifactEnvelope<ScreenplayData>>;
  getScene(projectId: ProjectId, sceneId: string): Promise<ScreenplayScene>;
  updateScreenplay(
    projectId: ProjectId,
    data: ScreenplayData,
  ): Promise<ArtifactEnvelope<ScreenplayData>>;
  updateScene(
    projectId: ProjectId,
    sceneId: string,
    scene: ScreenplayScene,
  ): Promise<ArtifactEnvelope<ScreenplayData>>;
  rewriteScene(
    projectId: ProjectId,
    sceneId: string,
    instruction: string,
  ): Promise<ArtifactEnvelope<ScreenplayData>>;
  getTodos(projectId: ProjectId): Promise<TodosResponse>;
  getTrace(projectId: ProjectId, sceneId: string): Promise<SceneTrace>;
  getBeats(
    projectId: ProjectId,
    flag?: Flag,
    source?: { chapter: number; paragraph: number },
  ): Promise<BeatsFilterResponse>;
};

export type ApiClient = {
  projects: ProjectsApi;
  source: SourceApi;
  understanding: UnderstandingApi;
  characters: CharactersApi;
  intent: IntentApi;
  outline: OutlineApi;
  screenplay: ScreenplayApi;
};

const mode = import.meta.env.VITE_API_MODE ?? "http";

export const api: ApiClient = mode === "http" ? httpClient : mockClient;
