import type { ApiClient } from "./client";
import {
  ApiError,
  type CreateProjectInput,
  type Paginated,
  type PatchProjectInput,
  type Project,
  type ProjectId,
  type ProjectSummary,
} from "./types";

const LATENCY_MS = 300;
const delay = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, LATENCY_MS));

const store = new Map<ProjectId, Project>();
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
}

let counter = 0;
function nextId(): ProjectId {
  counter += 1;
  return `prj_${Date.now().toString(36)}${counter}`;
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
    },
  },
};
