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
export type Suggestion = Schemas["Suggestion"];
export type ContactIn = Schemas["ContactIn"];
export type QuickSummary = Schemas["QuickSummary"];
export type PlainPart = Schemas["PlainPart"];
export type TenderDocument = Schemas["DocumentOut"];
export type TenderExtraction = Schemas["TenderExtraction"];
export type FoundFeature = Schemas["FoundFeature"];
export type FoundValue = Schemas["FoundValue"];
export type FoundOtherFeature = Schemas["FoundOtherFeature"];
export type CustomFeature = Schemas["CustomFeature"];
export type CustomFeatureType = Schemas["CustomTypeOut"];
export type Size = Schemas["Size"];
export type Evidence = Schemas["VerifiedEvidence"];
export type UnclearPoint = Schemas["UnclearPoint"];
export type QuestionImpact = Schemas["QuestionImpact"];
export type OptionPrice = Schemas["OptionPrice"];
export type PrebidQuery = Schemas["PrebidQuery"];
export type OutcomeIn = Schemas["OutcomeIn"];
export type Outcome = Schemas["OutcomeOut"];
export type BidResult = OutcomeIn["bid_result"];
export type CalibrationReport = Schemas["CalibrationReport"];
export type Country = Schemas["CountryOut"];
export type CompanySettings = Schemas["CompanySettings-Output"];
export type CompanySettingsIn = Schemas["CompanySettings-Input"];
export type RoleRate = Schemas["RoleRate"];
export type Template = Schemas["TemplateOut"];

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
  // FormData sets its own multipart Content-Type (with boundary); never override it.
  if (rest.body !== undefined && !(rest.body instanceof FormData)) {
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
  deleteProject: (id: string) => send<void>("DELETE", `/projects/${id}`),
  deleteEstimate: (id: string) => send<void>("DELETE", `/estimates/${id}`),
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

  quickOptions: (country = "india") =>
    request<QuickOptions>(
      `/quick-estimate/options?country=${encodeURIComponent(country)}`,
    ),
  createQuickEstimate: (body: QuickRequest) =>
    send<QuickSummary>("POST", "/quick-estimates", body),
  listQuickEstimates: () => request<QuickSummary[]>("/quick-estimates"),
  getEstimateSummary: (estimateId: string) =>
    request<QuickSummary>(`/estimates/${estimateId}/summary`),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<TenderDocument>("/documents", {
      method: "POST",
      body: form,
    });
  },
  getDocument: (documentId: string) =>
    request<TenderDocument>(`/documents/${encodeURIComponent(documentId)}`),
  prebidQueries: (documentId: string) =>
    request<PrebidQuery[]>(`/documents/${documentId}/prebid-queries`),

  sendContact: (body: ContactIn) =>
    send<{ id: string }>("POST", "/contact", body),
  suggestFeatures: (text: string) =>
    send<Suggestion>("POST", "/quick-estimate/suggest", { text }),
  questionImpact: (body: QuickRequest, signal?: AbortSignal) =>
    request<QuestionImpact[]>("/quick-estimate/impact", {
      method: "POST",
      body: JSON.stringify(body),
      signal,
    }),

  getOutcome: (projectId: string) =>
    request<Outcome | null>(`/projects/${projectId}/outcome`),
  recordOutcome: (projectId: string, body: OutcomeIn) =>
    send<Outcome>("POST", `/projects/${projectId}/outcome`, body),
  calibration: () => request<CalibrationReport>("/calibration"),

  getSettings: () => request<CompanySettings>("/settings"),
  getRoleRates: () => request<RoleRate[]>("/settings/roles"),
  listTemplates: () => request<Template[]>("/templates"),
  getTemplate: (id: string) => request<Template>(`/templates/${id}`),
  createTemplate: (projectId: string, name: string) =>
    send<Template>("POST", "/templates", { project_id: projectId, name }),
  deleteTemplate: (id: string) => send<void>("DELETE", `/templates/${id}`),
  putSettings: (body: CompanySettingsIn) =>
    send<CompanySettings>("PUT", "/settings", body),
};

function filenameFrom(disposition: string | null, fallback: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] ?? fallback;
}

/**
 * Downloads an authenticated file (PDF report / Excel BoQ). Plain links cannot send the bearer
 * token, so the file is fetched, turned into a Blob and saved via a temporary link.
 */
export async function downloadFile(
  path: string,
  fallbackName: string,
): Promise<void> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { headers });
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFrom(
    response.headers.get("Content-Disposition"),
    fallbackName,
  );
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function errorText(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}
