/// <reference types="vite/client" />
import { resolveApiBase, resolvePublicUrl } from "./urlConfig";

export const API_BASE = resolveApiBase(import.meta.env.VITE_API_BASE_URL, import.meta.env.PROD);
export const publicPhotoUrl = (path: string): string => resolvePublicUrl(path, API_BASE);
