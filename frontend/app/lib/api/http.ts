import type { ApiClient } from "./client";
import {
  ApiError,
  type AdaptationDirection,
  type ApiErrorBody,
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
  },
};
