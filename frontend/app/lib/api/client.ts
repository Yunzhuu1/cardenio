import { httpClient } from "./http";
import { mockClient } from "./mock";
import type {
  Chapter,
  ChapterId,
  ConfirmImportInput,
  CreateChapterInput,
  CreateProjectInput,
  ImportPreview,
  Paginated,
  PatchProjectInput,
  Project,
  ProjectId,
  ProjectSummary,
  ResegmentInput,
  Source,
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

export type ApiClient = {
  projects: ProjectsApi;
  source: SourceApi;
};

const mode = import.meta.env.VITE_API_MODE ?? "http";

export const api: ApiClient = mode === "http" ? httpClient : mockClient;
