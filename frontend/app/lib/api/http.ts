import type { ApiClient } from "./client";
import { ApiError, type ApiErrorBody } from "./types";

const BASE_URL = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "Accept-Language":
        typeof document !== "undefined"
          ? document.documentElement.lang || "zh-CN"
          : "zh-CN",
      ...init?.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const body = (payload?.error ?? {
      code: "unknown",
      message: response.statusText,
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
    get: (id) => request(`/projects/${id}`),
    create: (input) =>
      request("/projects", { method: "POST", body: JSON.stringify(input) }),
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
};
