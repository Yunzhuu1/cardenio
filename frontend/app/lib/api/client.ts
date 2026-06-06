import { httpClient } from "./http";
import { mockClient } from "./mock";
import type {
  CreateProjectInput,
  Paginated,
  PatchProjectInput,
  Project,
  ProjectId,
  ProjectSummary,
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

export type ApiClient = {
  projects: ProjectsApi;
};

const mode = import.meta.env.VITE_API_MODE ?? "mock";

export const api: ApiClient = mode === "http" ? httpClient : mockClient;
