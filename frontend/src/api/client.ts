import type { CreateProjectInput, Project } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api").replace(
  /\/$/,
  "",
);

interface ApiErrorBody {
  detail?: string | Array<{ msg: string }>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new Error("Could not reach the API. Make sure the backend is running.");
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg).join(", ")
      : body.detail;
    throw new Error(detail || `Request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

export const projectApi = {
  create: (payload: CreateProjectInput) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  get: (projectId: string) => request<Project>(`/projects/${projectId}`),
  list: () => request<Project[]>("/projects"),
};
