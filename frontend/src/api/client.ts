/**
 * Tervo — API client.
 *
 * Axios-free HTTP client using fetch with JWT token injection.
 */

const API_BASE = window.location.hostname === "tervoapp.com"
  ? "https://api.tervoapp.com/api/v1"
  : "/api/v1";

interface ApiError {
  status: number;
  detail: string;
}

async function request<T>(method: string, path: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    // Token expired → force logout + redirect
    if (res.status === 401 && token) {
      localStorage.removeItem("tervo_access_token");
      localStorage.removeItem("tervo_refresh_token");
      window.location.href = "/login";
      throw new Error("Session expirée");
    }

    const err: ApiError = {
      status: res.status,
      detail: (await res.json().catch(() => ({ detail: res.statusText }))).detail,
    };
    throw err;
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

export const api = {
  get: <T>(path: string, token?: string | null) => request<T>("GET", path, undefined, token),
  post: <T>(path: string, body: unknown, token?: string | null) => request<T>("POST", path, body, token),
  put: <T>(path: string, body: unknown, token?: string | null) => request<T>("PUT", path, body, token),
  delete: <T>(path: string, token?: string | null) => request<T>("DELETE", path, undefined, token),
  upload: <T>(path: string, formData: FormData, token?: string | null) => uploadFile<T>(path, formData, token),
};

async function uploadFile<T>(path: string, formData: FormData, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // NOTE: Ne PAS définir Content-Type — le navigateur le définit automatiquement avec le boundary

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    if (res.status === 401 && token) {
      localStorage.removeItem("tervo_access_token");
      localStorage.removeItem("tervo_refresh_token");
      window.location.href = "/login";
      throw new Error("Session expirée");
    }
    const err: ApiError = {
      status: res.status,
      detail: (await res.json().catch(() => ({ detail: res.statusText }))).detail,
    };
    throw err;
  }

  return res.json();
}

// ── Auth types ────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

// ── Auth API ──────────────────────────────────────────────

export const authApi = {
  login: (data: LoginRequest) => api.post<TokenResponse>("/auth/login", data),

  refresh: (refreshToken: string) => api.post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken }),

  me: (token: string) => api.get<UserResponse>("/auth/me", token),
};

// ── Dashboard types ────────────────────────────────────────

export interface DashboardSummary {
  today: {
    date: string;
    jobs_total: number;
    jobs_in_progress: number;
    jobs_completed: number;
  };
  next_job: {
    id: number;
    title: string;
    priority: string;
    client_full_name: string;
    client_address: string;
    scheduled_start_time: string | null;
  } | null;
  in_progress_job: {
    id: number;
    title: string;
    started_at: string;
    elapsed_minutes: number;
  } | null;
  overdue_jobs: {
    id: number;
    title: string;
    priority: string;
    scheduled_date: string;
    days_overdue: number;
    client_full_name: string;
    client_address: string;
  }[];
}


export const dashboardApi = {
  summary: (token: string) => api.get<DashboardSummary>("/dashboard/summary", token),
};

// ── Priority helpers ───────────────────────────────────────

export function prioritySeverity(p: string): "danger" | "warn" | "info" | "success" {
  switch (p) {
    case "urgente":
      return "danger";
    case "haute":
      return "warn";
    case "normale":
      return "info";
    case "basse":
      return "success";
    default:
      return "info";
  }
}

export function priorityLabel(p: string): string {
  switch (p) {
    case "urgente":
      return "🔴 Urgente";
    case "haute":
      return "🟠 Haute";
    case "normale":
      return "🟡 Normale";
    case "basse":
      return "🟢 Basse";
    default:
      return p;
  }
}

// ── Client types ────────────────────────────────────────────

export interface ClientListItem {
  id: number;
  full_name: string;
  phone: string;
  email: string | null;
  address: string;
  city: string | null;
}

export interface ClientListResponse {
  items: ClientListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ClientDetailResponse {
  id: number;
  full_name: string;
  phone: string;
  email: string | null;
  address: string;
  postal_code: string | null;
  city: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  jobs_count: number;
  last_job_date: string | null;
}

export interface ClientCreateRequest {
  full_name: string;
  phone: string;
  email?: string;
  address: string;
  postal_code?: string;
  city?: string;
  notes?: string;
}

export interface ClientUpdateRequest {
  full_name?: string;
  phone?: string;
  email?: string;
  address?: string;
  postal_code?: string;
  city?: string;
  notes?: string;
}

export interface JobHistoryItem {
  id: number;
  title: string;
  status: string;
  completed_at: string | null;
  technician_name: string | null;
}

export interface JobHistoryResponse {
  items: JobHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const clientsApi = {
  list: (token: string, params?: { search?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<ClientListResponse>(`/clients${qs ? "?" + qs : ""}`, token);
  },
  getById: (token: string, id: number) => api.get<ClientDetailResponse>(`/clients/${id}`, token),
  create: (token: string, data: Partial<ClientCreateRequest>) =>
    api.post<ClientDetailResponse>("/clients", data, token),
  update: (token: string, id: number, data: Partial<ClientUpdateRequest>) =>
    api.put<ClientListItem>(`/clients/${id}`, data, token),
  delete: (token: string, id: number) => api.delete<void>(`/clients/${id}`, token),
  getJobs: (token: string, id: number) => api.get<JobHistoryResponse>(`/clients/${id}/jobs`, token),
};

// ── Photos API (INT-27) ────────────────────────────────────

export interface PhotoResponse {
  id: number;
  category: string;
  file_url: string;
  thumbnail_url: string | null;
  taken_at: string;
}

export const photosApi = {
  upload: (token: string, jobId: number, file: File, category: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", category);
    return api.upload<PhotoResponse>(`/jobs/${jobId}/photos`, fd, token);
  },
  delete: (token: string, jobId: number, photoId: number) =>
    api.delete<void>(`/jobs/${jobId}/photos/${photoId}`, token),
};

// ── Materials API (INT-28) — préparé pour l'onglet Matériaux ──

export interface MaterialItem {
  id: number;
  job_id: number;
  name: string;
  quantity: string | null;
  position: number;
}

export const materialsApi = {
  list: (token: string, jobId: number) => api.get<MaterialItem[]>(`/jobs/${jobId}/materials`, token),
  add: (token: string, jobId: number, data: { name: string; quantity?: string }) =>
    api.post<MaterialItem>(`/jobs/${jobId}/materials`, data, token),
  update: (token: string, jobId: number, materialId: number, data: { name?: string; quantity?: string }) =>
    api.put<MaterialItem>(`/jobs/${jobId}/materials/${materialId}`, data, token),
  remove: (token: string, jobId: number, materialId: number) =>
    api.delete<void>(`/jobs/${jobId}/materials/${materialId}`, token),
};

// ── Checklist API (INT-20) ───────────────────────────────────

export const checklistApi = {
  getItems: (token: string, jobId: number) => api.get<ChecklistItemRef[]>(`/jobs/${jobId}/checklist`, token),
  batchUpdate: (token: string, jobId: number, items: { id: number; checked?: boolean; note?: string | null }[]) =>
    api.put<{ updated: number }>(`/jobs/${jobId}/checklist/batch`, { items }, token),
};

// ── Job types ───────────────────────────────────────────────

export interface JobListItem {
  id: number;
  title: string;
  status: string;
  priority: string;
  scheduled_date: string;
  client: { id: number; full_name: string } | null;
  technician: { id: number; full_name: string | null } | null;
}

export interface JobListResponse {
  items: JobListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const jobsApi = {
  list: (token: string, params?: { status?: string; date?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.date) query.set("date", params.date);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<JobListResponse>(`/jobs${qs ? "?" + qs : ""}`, token);
  },
  getById: (token: string, id: number) => api.get<JobDetailResponse>(`/jobs/${id}`, token),
  create: (token: string, data: Partial<JobCreateRequest>) => api.post<JobDetailResponse>("/jobs", data, token),
};

export interface ChecklistItemRef {
  id: number;
  category: string;
  label: string;
  checked: boolean;
  note: string | null;
  position: number;
}

export interface JobDetailResponse {
  id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  scheduled_date: string;
  scheduled_start_time: string | null;
  scheduled_end_time: string | null;
  started_at: string | null;
  completed_at: string | null;
  observations: string | null;
  created_at: string;
  updated_at: string;
  client: { id: number; full_name: string } | null;
  technician: { id: number; full_name: string | null } | null;
  checklist_items: ChecklistItemRef[];
}

export interface JobCreateRequest {
  client_id: number;
  title: string;
  description?: string;
  scheduled_date: string;
  priority?: string;
  scheduled_start_time?: string;
  scheduled_end_time?: string;
}

// ── Status helpers ──────────────────────────────────────────

export function statusSeverity(s: string): "success" | "info" | "warn" | "danger" | "contrast" {
  switch (s) {
    case "terminé":
      return "success";
    case "en_cours":
      return "info";
    case "planifié":
      return "warn";
    case "annulé":
      return "danger";
    default:
      return "contrast";
  }
}
