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
  ImportPreview,
  IntentConstraints,
  IntentValidateResponse,
  MvpDirection,
  Paginated,
  PatchProjectInput,
  Project,
  ProjectId,
  ProjectSummary,
  ResegmentInput,
  Source,
  UnderstandingData,
  UpdateChapterInput,
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

export type ApiClient = {
  projects: ProjectsApi;
  source: SourceApi;
  understanding: UnderstandingApi;
  characters: CharactersApi;
  intent: IntentApi;
};

const mode = import.meta.env.VITE_API_MODE ?? "http";

export const api: ApiClient = mode === "http" ? httpClient : mockClient;
