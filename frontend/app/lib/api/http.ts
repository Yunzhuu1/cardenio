import type { ApiClient } from "./client";
import {
  ApiError,
  type AdaptationDirection,
  type ApiErrorBody,
  type DirectionResponse,
  type MvpDirection,
  type Project,
  type ProjectGates,
  type ProjectId,
  type ProjectState,
  type SourceLanguage,
  type UiLanguage,
  type OutputLanguage,
} from "./types";

const BASE_URL = "/api/v1";

type FlatProjectPayload = {
  id: ProjectId;
  title: string;
  ui_language: UiLanguage;
  source_language: SourceLanguage;
  output_language: OutputLanguage;
  state: ProjectState;
  adaptation_direction: AdaptationDirection | null;
  style_fingerprint?: string | null;
  updated_at?: string;
};

type DirectionPayload = {
  direction: MvpDirection;
  project: FlatProjectPayload;
};

const defaultGates: ProjectGates = {
  understanding: "empty",
  characters: "empty",
  outline: "empty",
};

function normalizeProject(payload: FlatProjectPayload): Project {
  return {
    id: payload.id,
    title: payload.title,
    state: payload.state,
    updated_at: payload.updated_at ?? new Date().toISOString(),
    meta: {
      ui_language: payload.ui_language,
      source_language: payload.source_language,
      output_language: payload.output_language,
      adaptation_direction: payload.adaptation_direction,
      style_fingerprint: payload.style_fingerprint ?? null,
    },
    gates: defaultGates,
  };
}

function getDetailMessage(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (detail == null) return null;
  try {
    return JSON.stringify(detail);
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData =
    typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers = new Headers(init?.headers);
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Accept-Language")) {
    headers.set(
      "Accept-Language",
      typeof document !== "undefined"
        ? document.documentElement.lang || "zh-CN"
        : "zh-CN",
    );
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detailMessage = getDetailMessage(payload?.detail);
    const body = (payload?.error ?? {
      code: "unknown",
      message: detailMessage ?? response.statusText,
      retryable: false,
    }) as ApiErrorBody;
    throw new ApiError(response.status, body);
  }

  return payload as T;
}

export const httpClient: ApiClient = {
  projects: {
    list: (params) => {
      const search = new URLSearchParams();
      if (params?.limit) search.set("limit", String(params.limit));
      if (params?.cursor) search.set("cursor", params.cursor);
      const qs = search.toString();
      return request(`/projects${qs ? `?${qs}` : ""}`);
    },
    get: async (id) => normalizeProject(await request(`/projects/${id}`)),
    create: (input) =>
      request<FlatProjectPayload>("/projects", {
        method: "POST",
        body: JSON.stringify(input),
      }).then(normalizeProject),
    patch: (id, input) =>
      request(`/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    remove: (id) =>
      request<void>(`/projects/${id}`, { method: "DELETE" }).then(
        () => undefined,
      ),
  },
  source: {
    get: (projectId) => request(`/projects/${projectId}/source`),
    addChapter: (projectId, input) =>
      request(`/projects/${projectId}/source/chapters`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    updateChapter: (projectId, chapterId, chapter) =>
      request(`/projects/${projectId}/source/chapters/${chapterId}`, {
        method: "PUT",
        body: JSON.stringify(chapter),
      }),
    deleteChapter: (projectId, chapterId) =>
      request<void>(`/projects/${projectId}/source/chapters/${chapterId}`, {
        method: "DELETE",
      }).then(() => undefined),
    resegment: (projectId, input) =>
      request(`/projects/${projectId}/source/chapters:resegment`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    importFile: (projectId, file) => {
      const body = new FormData();
      body.append("file", file);
      return request(`/projects/${projectId}/source/import`, {
        method: "POST",
        body,
      });
    },
    confirmImport: (projectId, input) =>
      request(`/projects/${projectId}/source/import:confirm`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    resolve: (projectId, chapter, paragraphs) => {
      const search = new URLSearchParams();
      search.set("chapter", String(chapter));
      search.set("paragraphs", paragraphs);
      return request(
        `/projects/${projectId}/source:resolve?${search.toString()}`,
      );
    },
  },
  understanding: {
    get: (projectId) => request(`/projects/${projectId}/understanding`),
    generate: (projectId) =>
      request(`/projects/${projectId}/understanding:generate`, {
        method: "POST",
      }),
    update: (projectId, data) =>
      request(`/projects/${projectId}/understanding`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    confirm: (projectId) =>
      request(`/projects/${projectId}/understanding:confirm`, {
        method: "POST",
      }),
  },
  characters: {
    get: (projectId) => request(`/projects/${projectId}/characters`),
    generate: (projectId) =>
      request(`/projects/${projectId}/characters:generate`, {
        method: "POST",
      }),
    add: (projectId, character) =>
      request(`/projects/${projectId}/characters`, {
        method: "POST",
        body: JSON.stringify(character),
      }),
    update: (projectId, characterId, character) =>
      request(`/projects/${projectId}/characters/${characterId}`, {
        method: "PUT",
        body: JSON.stringify(character),
      }),
    remove: (projectId, characterId) =>
      request<void>(`/projects/${projectId}/characters/${characterId}`, {
        method: "DELETE",
      }).then(() => undefined),
    confirm: (projectId) =>
      request(`/projects/${projectId}/characters:confirm`, {
        method: "POST",
      }),
  },
  intent: {
    get: (projectId) => request(`/projects/${projectId}/intent`),
    save: (projectId, data) =>
      request(`/projects/${projectId}/intent`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    setDirection: async (projectId, direction): Promise<DirectionResponse> => {
      const payload = await request<DirectionPayload>(
        `/projects/${projectId}/intent/direction`,
        {
          method: "PUT",
          body: JSON.stringify({ direction }),
        },
      );
      return {
        direction: payload.direction,
        project: normalizeProject(payload.project),
      };
    },
    validate: (projectId) =>
      request(`/projects/${projectId}/intent:validate`, {
        method: "POST",
      }),
  },
  outline: {
    get: (projectId) => request(`/projects/${projectId}/outline`),
    generate: (projectId) =>
      request(`/projects/${projectId}/outline:generate`, {
        method: "POST",
      }),
    addScene: (projectId, scene) =>
      request(`/projects/${projectId}/outline/scenes`, {
        method: "POST",
        body: JSON.stringify(scene),
      }),
    updateScene: (projectId, sceneId, scene) =>
      request(`/projects/${projectId}/outline/scenes/${sceneId}`, {
        method: "PUT",
        body: JSON.stringify(scene),
      }),
    deleteScene: (projectId, sceneId) =>
      request<void>(`/projects/${projectId}/outline/scenes/${sceneId}`, {
        method: "DELETE",
      }).then(() => undefined),
    reorder: (projectId, order) =>
      request(`/projects/${projectId}/outline/scenes:reorder`, {
        method: "POST",
        body: JSON.stringify({ order }),
      }),
    confirm: (projectId) =>
      request(`/projects/${projectId}/outline:confirm`, {
        method: "POST",
      }),
    getMergeSuggestions: (projectId) =>
      request(`/projects/${projectId}/outline/merge-suggestions`),
    applyMergeSuggestion: (projectId, suggestionId) =>
      request(
        `/projects/${projectId}/outline/merge-suggestions/${suggestionId}:apply`,
        {
          method: "POST",
        },
      ),
    dismissMergeSuggestion: (projectId, suggestionId) =>
      request(
        `/projects/${projectId}/outline/merge-suggestions/${suggestionId}:dismiss`,
        {
          method: "POST",
        },
      ),
  },
  screenplay: {
    get: (projectId) => request(`/projects/${projectId}/screenplay`),
    generate: (projectId, options) => {
      const hasShotHints = options?.shot_hints !== undefined;
      return request(`/projects/${projectId}/screenplay:generate`, {
        method: "POST",
        body: hasShotHints
          ? JSON.stringify({ shot_hints: options.shot_hints })
          : undefined,
      });
    },
    getScene: (projectId, sceneId) =>
      request(`/projects/${projectId}/screenplay/scenes/${sceneId}`),
    updateScreenplay: (projectId, data) =>
      request(`/projects/${projectId}/screenplay`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    updateScene: (projectId, sceneId, scene) =>
      request(`/projects/${projectId}/screenplay/scenes/${sceneId}`, {
        method: "PUT",
        body: JSON.stringify(scene),
      }),
    rewriteScene: (projectId, sceneId, instruction) =>
      request(`/projects/${projectId}/screenplay/scenes/${sceneId}:rewrite`, {
        method: "POST",
        body: JSON.stringify({ instruction }),
      }),
    getTodos: (projectId) => request(`/projects/${projectId}/screenplay/todos`),
    getTrace: (projectId, sceneId) =>
      request(`/projects/${projectId}/screenplay/scenes/${sceneId}/trace`),
    getBeats: (projectId, flag, source) => {
      const search = new URLSearchParams();
      if (flag) search.set("flag", flag);
      if (source) {
        search.set("source_chapter", String(source.chapter));
        search.set("source_paragraph", String(source.paragraph));
      }
      const qs = search.toString();
      return request(
        `/projects/${projectId}/screenplay/beats${qs ? `?${qs}` : ""}`,
      );
    },
  },
};
