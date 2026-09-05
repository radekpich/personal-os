import type { Category, Context, ListResponse, Tag, Task, TaskCreate, TaskFilters, TaskList, TaskUpdate, User } from "./types";

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
  params?: Record<string, unknown>;
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
  const csrf = getCookie(CSRF_COOKIE_NAME);
  if (mutates && csrf) headers.set(CSRF_HEADER_NAME, csrf);

  const response = await fetch(buildUrl(path, options.params), {
    ...options,
    method,
    headers,
    credentials: "include",
    body: options.json !== undefined ? JSON.stringify(options.json) : options.text,
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
  categories: () => request<ListResponse<Category>>("/categories"),
  createCategory: (payload: Pick<Category, "name" | "color" | "icon"> & Partial<Pick<Category, "parent_id" | "position" | "is_archived">>) => request<Category>("/categories", { method: "POST", json: payload }),
  contexts: () => request<ListResponse<Context>>("/contexts"),
  createContext: (payload: Pick<Context, "name"> & Partial<Pick<Context, "position" | "is_archived">>) => request<Context>("/contexts", { method: "POST", json: payload }),
  tags: () => request<ListResponse<Tag>>("/tags"),
  createTag: (payload: { name: string }) => request<Tag>("/tags", { method: "POST", json: payload }),
  tasks: (filters: TaskFilters = {}) => request<TaskList>("/tasks", { params: { ...filters, tag_ids: filters.tag_ids } }),
  task: (id: string) => request<Task>(`/tasks/${id}`),
  quickTask: (title: string) => request<Task>("/tasks/quick", { method: "POST", text: title }),
  createTask: (payload: TaskCreate) => request<Task>("/tasks", { method: "POST", json: payload }),
  updateTask: (id: string, payload: TaskUpdate) => request<Task>(`/tasks/${id}`, { method: "PATCH", json: payload }),
  deleteTask: (id: string) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
  regenerateCalendarToken: () => request<User>("/calendar/regenerate-token", { method: "POST" }),
};

export function calendarUrl(token: string) {
  return buildUrl(`/calendar/${token}.ics`);
}
