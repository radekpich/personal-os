import type {
  AgentActionFilters,
  AgentActionList,
  AgentChannel,
  AgentConfigChange,
  AgentIntegration,
  AgentJob,
  AgentKey,
  AgentList,
  AgentOverview,
  AgentRun,
  AgentWatch,
  Attachment,
  AttachmentUpdate,
  Category,
  Challenge,
  ChallengeCreate,
  ChallengeHeatmap,
  ChallengeStats,
  ChallengeUpdate,
  CheckInCreate,
  CheckInResult,
  Context,
  ListResponse,
  Note,
  NoteAttachment,
  NoteCreate,
  NoteFilters,
  NoteList,
  NoteUpdate,
  RevertResult,
  StagnatingVision,
  StorageUsage,
  Tag,
  Task,
  TaskAttachment,
  TaskCreate,
  TaskFilters,
  TaskList,
  TaskUpdate,
  User,
  Vision,
  VisionCreate,
  VisionProgress,
  VisionTreeNode,
  VisionUpdate,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const CSRF_COOKIE_NAME = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "csrf_token";
const CSRF_HEADER_NAME = process.env.NEXT_PUBLIC_CSRF_HEADER_NAME ?? "X-CSRF-Token";

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

function getCookie(name: string) {
  if (typeof document === "undefined") return null;
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function buildUrl(path: string, params?: Record<string, unknown>) {
  const url = new URL(path, API_BASE_URL);
  for (const [key, raw] of Object.entries(params ?? {})) {
    if (raw === undefined || raw === null || raw === "" || raw === "all") continue;
    if (Array.isArray(raw)) {
      for (const value of raw) url.searchParams.append(key, String(value));
    } else {
      url.searchParams.set(key, String(raw));
    }
  }
  return url.toString();
}

type RequestOptions = Omit<RequestInit, "body"> & {
  json?: unknown;
  text?: string;
  formData?: FormData;
  params?: Record<string, unknown>;
  ifMatch?: number;
  retryOnUnauthorized?: boolean;
};

async function ensureCsrf() {
  if (getCookie(CSRF_COOKIE_NAME)) return;
  await fetch(buildUrl("/health"), { credentials: "include" });
}

async function readBody(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return response.json();
  return response.text();
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const mutates = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (mutates) await ensureCsrf();

  const headers = new Headers(options.headers);
  if (options.json !== undefined) headers.set("Content-Type", "application/json");
  if (options.text !== undefined) headers.set("Content-Type", "text/plain; charset=utf-8");
  if (options.ifMatch !== undefined) headers.set("If-Match", String(options.ifMatch));
  const csrf = getCookie(CSRF_COOKIE_NAME);
  if (mutates && csrf) headers.set(CSRF_HEADER_NAME, csrf);

  const response = await fetch(buildUrl(path, options.params), {
    ...options,
    method,
    headers,
    credentials: "include",
    body: options.json !== undefined ? JSON.stringify(options.json) : options.text ?? options.formData,
  });

  if (response.status === 401 && options.retryOnUnauthorized !== false && path !== "/auth/login" && path !== "/auth/refresh") {
    const refreshed = await refreshSession();
    if (refreshed) return request<T>(path, { ...options, retryOnUnauthorized: false });
  }

  if (!response.ok) {
    const body = await readBody(response).catch(() => undefined);
    const message = typeof body === "object" && body && "detail" in body ? String((body as { detail: unknown }).detail) : response.statusText;
    throw new ApiError(response.status, message, body);
  }

  if (response.status === 204) return undefined as T;
  return readBody(response) as Promise<T>;
}

async function refreshSession() {
  try {
    await request<{ status: string }>("/auth/refresh", { method: "POST", retryOnUnauthorized: false });
    return true;
  } catch {
    return false;
  }
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  login: (payload: { email: string; password: string }) => request<User>("/auth/login", { method: "POST", json: payload, retryOnUnauthorized: false }),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  refresh: refreshSession,
  agentActions: (filters: AgentActionFilters = {}) => request<AgentActionList>("/agent/actions", { params: filters }),
  agentOverview: () => request<AgentOverview>("/agent/overview"),
  agentJobs: () => request<AgentList<AgentJob>>("/agent/jobs"),
  agentIntegrations: () => request<AgentList<AgentIntegration>>("/agent/integrations"),
  agentWatches: () => request<AgentList<AgentWatch>>("/agent/watches"),
  agentChannels: () => request<AgentList<AgentChannel>>("/agent/channels"),
  agentRuns: (filters: { job_id?: string; trigger?: string; status?: string; q?: string; page?: number; page_size?: number } = {}) =>
    request<AgentList<AgentRun>>("/agent/runs", { params: filters }),
  agentConfigChanges: (filters: { acknowledged?: boolean } = {}) => request<AgentList<AgentConfigChange>>("/agent/config-changes", { params: filters }),
  agentKeys: () => request<AgentList<AgentKey>>("/agent/keys"),
  acknowledgeAgentConfigChange: (id: string) => request<{ status: string }>(`/agent/config-changes/${id}/acknowledge`, { method: "POST" }),
  revokeAllAgentKeys: () => request<{ revoked_count: number }>("/agent/keys/revoke-all", { method: "POST" }),
  revertAgentAction: (id: string) => request<RevertResult>(`/agent/actions/${id}/revert`, { method: "POST" }),
  revertAgentActionBatch: (payload: { batch_id?: string | null; created_from?: string | null; created_to?: string | null }) =>
    request<RevertResult>("/agent/actions/revert-batch", { method: "POST", json: payload }),
  categories: () => request<ListResponse<Category>>("/categories"),
  createCategory: (payload: Pick<Category, "name" | "color" | "icon"> & Partial<Pick<Category, "parent_id" | "position" | "is_archived">>) => request<Category>("/categories", { method: "POST", json: payload }),
  contexts: () => request<ListResponse<Context>>("/contexts"),
  createContext: (payload: Pick<Context, "name"> & Partial<Pick<Context, "position" | "is_archived">>) => request<Context>("/contexts", { method: "POST", json: payload }),
  challenges: () => request<ListResponse<Challenge>>("/challenges"),
  challenge: (id: string) => request<Challenge>(`/challenges/${id}`),
  challengeStats: (id: string) => request<ChallengeStats>(`/challenges/${id}/stats`),
  challengeHeatmap: (id: string, year: number) => request<ChallengeHeatmap>(`/challenges/${id}/heatmap`, { params: { year } }),
  createChallenge: (payload: ChallengeCreate) => request<Challenge>("/challenges", { method: "POST", json: payload }),
  updateChallenge: (id: string, payload: ChallengeUpdate) => request<Challenge>(`/challenges/${id}`, { method: "PATCH", json: payload }),
  deleteChallenge: (id: string) => request<void>(`/challenges/${id}`, { method: "DELETE" }),
  checkInChallenge: (id: string, payload: CheckInCreate) => request<CheckInResult>(`/challenges/${id}/check-in`, { method: "POST", json: payload }),
  createChallengePause: (id: string, payload: { start_date: string; end_date?: string | null; note?: string | null }) => request(`/challenges/${id}/pauses`, { method: "POST", json: payload }),
  tags: () => request<ListResponse<Tag>>("/tags"),
  createTag: (payload: { name: string }) => request<Tag>("/tags", { method: "POST", json: payload }),
  tasks: (filters: TaskFilters = {}) => request<TaskList>("/tasks", { params: { ...filters, tag_ids: filters.tag_ids } }),
  task: (id: string) => request<Task>(`/tasks/${id}`),
  quickTask: (title: string) => request<Task>("/tasks/quick", { method: "POST", text: title }),
  createTask: (payload: TaskCreate) => request<Task>("/tasks", { method: "POST", json: payload }),
  updateTask: (id: string, payload: TaskUpdate, version: number) => request<Task>(`/tasks/${id}`, { method: "PATCH", json: payload, ifMatch: version }),
  deleteTask: (id: string, version: number) => request<void>(`/tasks/${id}`, { method: "DELETE", ifMatch: version }),
  taskAttachments: (taskId: string) => request<ListResponse<Attachment>>(`/tasks/${taskId}/attachments`),
  uploadAttachment: (file: File, caption?: string | null) => {
    const formData = new FormData();
    formData.set("file", file);
    if (caption) formData.set("caption", caption);
    return request<Attachment>("/attachments", { method: "POST", formData });
  },
  attachToTask: (taskId: string, attachmentId: string, position = 0) =>
    request<TaskAttachment>(`/tasks/${taskId}/attachments`, {
      method: "POST",
      json: { attachment_id: attachmentId, position },
    }),
  updateAttachment: (id: string, payload: AttachmentUpdate) =>
    request<Attachment>(`/attachments/${id}`, { method: "PATCH", json: payload }),
  deleteAttachment: (id: string) => request<void>(`/attachments/${id}`, { method: "DELETE" }),
  unlinkTaskAttachment: (taskId: string, attachmentId: string) =>
    request<void>(`/tasks/${taskId}/attachments/${attachmentId}`, { method: "DELETE" }),
  notes: (filters: NoteFilters = {}) => request<NoteList>("/notes", { params: filters }),
  note: (id: string) => request<Note>(`/notes/${id}`),
  createNote: (payload: NoteCreate) => request<Note>("/notes", { method: "POST", json: payload }),
  updateNote: (id: string, payload: NoteUpdate, version: number) => request<Note>(`/notes/${id}`, { method: "PATCH", json: payload, ifMatch: version }),
  deleteNote: (id: string, version: number) => request<void>(`/notes/${id}`, { method: "DELETE", ifMatch: version }),
  noteAttachments: (noteId: string) => request<ListResponse<Attachment>>(`/notes/${noteId}/attachments`),
  attachToNote: (noteId: string, attachmentId: string, position = 0) =>
    request<NoteAttachment>(`/notes/${noteId}/attachments`, {
      method: "POST",
      json: { attachment_id: attachmentId, position },
    }),
  unlinkNoteAttachment: (noteId: string, attachmentId: string) =>
    request<void>(`/notes/${noteId}/attachments/${attachmentId}`, { method: "DELETE" }),
  storageUsage: () => request<StorageUsage>("/storage/usage"),
  visions: () => request<ListResponse<Vision>>("/visions"),
  visionTree: () => request<ListResponse<VisionTreeNode>>("/visions/tree"),
  visionProgress: (id: string) => request<VisionProgress>(`/visions/${id}/progress`),
  stagnatingVisions: (days = 14) => request<ListResponse<StagnatingVision>>("/visions/stagnating", { params: { days } }),
  createVision: (payload: VisionCreate) => request<Vision>("/visions", { method: "POST", json: payload }),
  updateVision: (id: string, payload: VisionUpdate) => request<Vision>(`/visions/${id}`, { method: "PATCH", json: payload }),
  deleteVision: (id: string) => request<void>(`/visions/${id}`, { method: "DELETE" }),
  regenerateCalendarToken: () => request<User>("/calendar/regenerate-token", { method: "POST" }),
};

export function calendarUrl(token: string) {
  return buildUrl(`/calendar/${token}.ics`);
}

export function attachmentUrl(id: string, variant: "original" | "thumb" = "original") {
  return buildUrl(variant === "thumb" ? `/attachments/${id}/thumb` : `/attachments/${id}`);
}
