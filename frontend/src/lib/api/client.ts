/**
 * Minimal typed client for the Aakalan API.
 *
 * Types come from FastAPI's OpenAPI schema (`schema.d.ts`, regenerated with `make openapi`).
 */

import type { components } from "./schema";

type Schemas = components["schemas"];

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_STORAGE_KEY = "aakalan.token";

export type Role = Schemas["Role"];
export type LoginRequest = Schemas["LoginRequest"];
export type CurrentUser = Schemas["UserOut"];
export type TokenResponse = Schemas["TokenResponse"];
export type Health = Schemas["Health"];

// Projects arrive in M1; this type is replaced by the generated one then.
export interface ProjectSummary {
  id: string;
  name: string;
  buyer_type: string;
  domain: string;
  mode: string;
  status: string;
  created_at: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
    ) {
      return body.detail;
    }
  } catch {
    // Body was not JSON; fall through to the status text.
  }
  return response.statusText || `Request failed (${response.status})`;
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = init;
  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");
  if (rest.body !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  return (await response.json()) as T;
}

export const api = {
  login: (body: LoginRequest) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
      auth: false,
    }),
  me: () => request<CurrentUser>("/auth/me"),
  health: () => request<Health>("/health", { auth: false }),
  listProjects: () => request<ProjectSummary[]>("/projects"),
};
