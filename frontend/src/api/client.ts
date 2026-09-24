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
    interventions_total: number;
    interventions_in_progress: number;
    interventions_completed: number;
  };
  next_intervention: {
    id: number;
    title: string;
    priority: string;
    site_name: string;
    site_address: string;
    scheduled_start_time: string | null;
  } | null;
  in_progress_intervention: {
    id: number;
    title: string;
    started_at: string;
    elapsed_minutes: number;
  } | null;
  overdue_interventions: {
    id: number;
    title: string;
    priority: string;
    scheduled_date: string;
    days_overdue: number;
    site_name: string;
    site_address: string;
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
  interventions_count: number;
  last_intervention_date: string | null;
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

export interface InterventionHistoryItem {
  id: number;
  title: string;
  status: string;
  completed_at: string | null;
  technician_name: string | null;
}

export interface InterventionHistoryResponse {
  items: InterventionHistoryItem[];
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
};

// ── Site types ──────────────────────────────────────────────

export interface SiteListItem {
  id: number;
  client_id: number;
  name: string;
  address: string;
  postal_code: string | null;
  city: string | null;
}

export interface SiteListResponse {
  items: SiteListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const sitesApi = {
  getByClient: (token: string, clientId: number) =>
    api.get<SiteListResponse>(`/clients/${clientId}/sites`, token),
  create: (token: string, data: { client_id: number; name: string; address: string; postal_code?: string; city?: string }) =>
    api.post<SiteListItem>("/sites", data, token),
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
  upload: (token: string, interventionId: number, file: File, category: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", category);
    return api.upload<PhotoResponse>(`/interventions/${interventionId}/photos`, fd, token);
  },
  delete: (token: string, interventionId: number, photoId: number) =>
    api.delete<void>(`/interventions/${interventionId}/photos/${photoId}`, token),
};

// ── Materials API (INT-28) — préparé pour l'onglet Matériaux ──

export interface MaterialItem {
  id: number;
  intervention_id: number;
  name: string;
  quantity: string | null;
  position: number;
}

export const materialsApi = {
  list: (token: string, interventionId: number) => api.get<MaterialItem[]>(`/interventions/${interventionId}/materials`, token),
  add: (token: string, interventionId: number, data: { name: string; quantity?: string }) =>
    api.post<MaterialItem>(`/interventions/${interventionId}/materials`, data, token),
  update: (token: string, interventionId: number, materialId: number, data: { name?: string; quantity?: string }) =>
    api.put<MaterialItem>(`/interventions/${interventionId}/materials/${materialId}`, data, token),
  remove: (token: string, interventionId: number, materialId: number) =>
    api.delete<void>(`/interventions/${interventionId}/materials/${materialId}`, token),
};

// ── Checklist API (INT-20) ───────────────────────────────────

export const checklistApi = {
  getItems: (token: string, interventionId: number) => api.get<ChecklistItemRef[]>(`/interventions/${interventionId}/checklist`, token),
  batchUpdate: (token: string, interventionId: number, items: { id: number; checked?: boolean; note?: string | null }[]) =>
    api.put<{ updated: number }>(`/interventions/${interventionId}/checklist/batch`, { items }, token),
};

// ── Intervention types ───────────────────────────────────────────────

export interface InterventionListItem {
  id: number;
  title: string;
  status: string;
  priority: string;
  scheduled_date: string;
  site: { id: number; name: string; address: string } | null;
  technician: { id: number; full_name: string | null } | null;
}

export interface InterventionListResponse {
  items: InterventionListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const interventionsApi = {
  list: (token: string, params?: { status?: string; date?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.date) query.set("date", params.date);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<InterventionListResponse>(`/interventions${qs ? "?" + qs : ""}`, token);
  },
  getById: (token: string, id: number) => api.get<InterventionDetailResponse>(`/interventions/${id}`, token),
  create: (token: string, data: Partial<InterventionCreateRequest>) => api.post<InterventionDetailResponse>("/interventions", data, token),
};

export interface ChecklistItemRef {
  id: number;
  category: string;
  label: string;
  checked: boolean;
  note: string | null;
  position: number;
}

export interface InterventionDetailResponse {
  site_id: number;
  equipment_id: number | null;
  under_warranty: boolean;
  photos: PhotoResponse[];
  materials: MaterialItem[];
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
  site: { id: number; name: string; address: string } | null;
  technician: { id: number; full_name: string | null } | null;
  checklist_items: ChecklistItemRef[];
}

export interface InterventionCreateRequest {
  equipment_id?: number | null;
  under_warranty?: boolean;
  site_id: number;
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
    case "COMPLETED":
      return "success";
    case "IN_PROGRESS":
      return "info";
    case "PLANNED":
      return "warn";
    case "CANCELLED":
      return "danger";
    default:
      return "contrast";
  }
}

export function statusLabel(s: string): string {
  switch (s) {
    case "COMPLETED":
      return "Terminée";
    case "IN_PROGRESS":
      return "En cours";
    case "PLANNED":
      return "Planifiée";
    case "CANCELLED":
      return "Annulée";
    default:
      return s;
  }
}
