/**
 * Typed client for the Aakalan API.
 *
 * Types come from FastAPI's OpenAPI schema (`schema.d.ts`, regenerated with `make openapi`).
 * Money fields (`*_paise`) are integer paise; format them with `@/lib/format`.
 */

import type { components } from "./schema";

export type Schemas = components["schemas"];

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const TOKEN_STORAGE_KEY = "aakalan.token";

export type Role = Schemas["Role"];
export type LoginRequest = Schemas["LoginRequest"];
export type CurrentUser = Schemas["UserOut"];
export type TokenResponse = Schemas["TokenResponse"];
export type Health = Schemas["Health"];

export type Project = Schemas["ProjectOut"];
export type ProjectCreate = Schemas["ProjectCreate"];
export type ProjectUpdate = Schemas["ProjectUpdate"];
export type Requirement = Schemas["RequirementOut"];
export type RequirementCreate = Schemas["RequirementCreate"];
export type RequirementUpdate = Schemas["RequirementUpdate"];
export type Questionnaire = Schemas["QuestionnaireOut"];
export type QuestionnaireField = Schemas["QuestionnaireField"];
export type AnswerIn = Schemas["AnswerIn"];
export type Catalog = Schemas["CatalogOut"];
export type CatalogComponent = Schemas["CatalogComponentOut"];
export type Component = Schemas["ComponentOut"];
export type ComponentIn = Schemas["ComponentIn"];
export type EstimateCreate = Schemas["EstimateCreate"];
export type Estimate = Schemas["EstimateOut"];
export type EstimateSummary = Schemas["EstimateSummary"];
export type CostLine = Schemas["CostLineOut"];
export type Trace = Schemas["TraceOut"];
export type Scenario = Schemas["Scenario"];
export type ScenarioResult = Schemas["ScenarioResult"];
export type ScenariosOut = Schemas["ScenariosOut"];
export type GroupTotal = Schemas["GroupTotal"];
export type QuickOptions = Schemas["QuickOptions"];
export type QuickQuestion = Schemas["QuestionOut"];
export type QuickRequest = Schemas["QuickRequest"];
export type QuickSummary = Schemas["QuickSummary"];
export type PlainPart = Schemas["PlainPart"];

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

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item: unknown) => {
      if (typeof item === "object" && item !== null && "msg" in item) {
        const loc =
          "loc" in item && Array.isArray(item.loc)
            ? item.loc.filter((p: unknown) => p !== "body").join(".")
            : "";
        return loc ? `${loc}: ${String(item.msg)}` : String(item.msg);
      }
      return String(item);
    });
    return parts.join("; ");
  }
  return null;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const message = describeDetail(body.detail);
      if (message) return message;
    }
  } catch {
    // Body was not JSON; fall through to the status text.
  }
  if (response.status === 403) return "You do not have permission to do this.";
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
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
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

  listProjects: () => request<Project[]>("/projects"),
  createProject: (body: ProjectCreate) =>
    send<Project>("POST", "/projects", body),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  updateProject: (id: string, body: ProjectUpdate) =>
    send<Project>("PATCH", `/projects/${id}`, body),

  listRequirements: (projectId: string) =>
    request<Requirement[]>(`/projects/${projectId}/requirements`),
  createRequirement: (projectId: string, body: RequirementCreate) =>
    send<Requirement>("POST", `/projects/${projectId}/requirements`, body),
  updateRequirement: (id: string, body: RequirementUpdate) =>
    send<Requirement>("PATCH", `/requirements/${id}`, body),
  deleteRequirement: (id: string) =>
    send<void>("DELETE", `/requirements/${id}`),
  confirmRequirements: (projectId: string, requirementIds?: string[]) =>
    send<Requirement[]>("POST", `/projects/${projectId}/requirements/confirm`, {
      requirement_ids: requirementIds ?? null,
    }),

  getQuestionnaire: (projectId: string) =>
    request<Questionnaire>(`/projects/${projectId}/questionnaire`),
  putQuestionnaire: (projectId: string, answers: AnswerIn[]) =>
    send<Questionnaire>("PUT", `/projects/${projectId}/questionnaire`, {
      answers,
    }),

  getCatalog: () => request<Catalog>("/catalog"),
  listComponents: (projectId: string) =>
    request<Component[]>(`/projects/${projectId}/components`),
  putComponents: (projectId: string, components: ComponentIn[]) =>
    send<Component[]>("PUT", `/projects/${projectId}/components`, {
      components,
    }),

  createEstimate: (projectId: string, body: EstimateCreate = {}) =>
    send<Estimate>("POST", `/projects/${projectId}/estimates`, body),
  listEstimates: (projectId: string) =>
    request<EstimateSummary[]>(`/projects/${projectId}/estimates`),
  getEstimate: (id: string) => request<Estimate>(`/estimates/${id}`),
  getTrace: (estimateId: string, lineId: string) =>
    request<Trace>(`/estimates/${estimateId}/lines/${lineId}/trace`),
  runScenarios: (estimateId: string, scenarios: Scenario[]) =>
    send<ScenariosOut>("POST", `/estimates/${estimateId}/scenarios`, {
      scenarios,
    }),
  repriceEstimate: (estimateId: string) =>
    send<Estimate>("POST", `/estimates/${estimateId}/reprice`),

  quickOptions: () => request<QuickOptions>("/quick-estimate/options"),
  createQuickEstimate: (body: QuickRequest) =>
    send<QuickSummary>("POST", "/quick-estimates", body),
  listQuickEstimates: () => request<QuickSummary[]>("/quick-estimates"),
  getEstimateSummary: (estimateId: string) =>
    request<QuickSummary>(`/estimates/${estimateId}/summary`),
};

export function errorText(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}
