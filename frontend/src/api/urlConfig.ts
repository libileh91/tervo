/** One base for JSON requests and uploads; production requires an explicit URL. */
export function validateProductionApiBase(value: string | undefined): string {
  if (!value || value !== value.trim()) {
    throw new Error("VITE_API_BASE_URL must be an explicit HTTPS URL ending in /api/v1");
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("VITE_API_BASE_URL must be an absolute HTTPS URL");
  }
  if (url.protocol !== "https:" || !url.hostname || url.username || url.password ||
      url.search || url.hash || url.pathname.replace(/\/$/, "") !== "/api/v1") {
    throw new Error("VITE_API_BASE_URL must be HTTPS, end in /api/v1, and contain no credentials, query or fragment");
  }
  return value.replace(/\/$/, "");
}

export function resolveApiBase(value: string | undefined, production: boolean): string {
  return production ? validateProductionApiBase(value) : (value ? validateProductionApiBase(value) : "/api/v1");
}

/** PhotoRef paths are rooted at /uploads, not at the API's /api/v1 prefix. */
export function resolvePublicUrl(path: string, apiBase: string): string {
  let decoded: string;
  try {
    decoded = decodeURIComponent(path);
  } catch {
    throw new Error("Photo URL must be a relative /uploads path");
  }
  if (!/^\/uploads\//.test(path) || /[\\?#]/.test(decoded) ||
      decoded.split("/").some(segment => segment === "." || segment === "..")) {
    throw new Error("Photo URL must be a relative /uploads path");
  }
  return apiBase.startsWith("/") ? path : new URL(path, new URL(apiBase).origin).href;
}
