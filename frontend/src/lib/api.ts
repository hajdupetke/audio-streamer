import type {
  User,
  TokenResponse,
  SearchResponse,
  BookDetail,
  LibraryItem,
  SaveBookPayload,
  PlaybackProgress,
  UpsertProgressPayload,
  Addon,
  AddonSettings,
} from "@/types"

const API = ""  // same-origin: Vite proxy in dev, nginx proxy in production

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (res.status === 401) {
    window.location.href = "/login"
    throw new Error("Unauthorized")
  }

  if (res.status === 204) {
    return undefined as T
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

export const api = {
  auth: {
    me: () => request<User>("/api/auth/me"),
    login: (email: string, password: string) =>
      request<User>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string) =>
      request<User>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    logout: () =>
      request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
    refresh: () =>
      request<{ ok: boolean }>("/api/auth/refresh", { method: "POST" }),
    token: () => request<TokenResponse>("/api/auth/token"),
  },

  search: {
    search: (q: string, addon_id?: string) => {
      const params = new URLSearchParams({ q })
      if (addon_id) params.set("addon_id", addon_id)
      return request<SearchResponse>(`/api/search?${params.toString()}`)
    },
    getDetail: (addonId: string, itemId: string) =>
      request<BookDetail>(`/api/addons/${addonId}/items/${itemId}`),
  },

  library: {
    list: () => request<LibraryItem[]>("/api/library"),
    save: (book: SaveBookPayload) =>
      request<LibraryItem>("/api/library", {
        method: "POST",
        body: JSON.stringify(book),
      }),
    remove: (id: string) =>
      request<void>(`/api/library/${id}`, { method: "DELETE" }),
  },

  progress: {
    get: (libraryItemId: string) =>
      request<PlaybackProgress[]>(`/api/progress/${libraryItemId}`),
    upsert: (data: UpsertProgressPayload) =>
      request<PlaybackProgress>("/api/progress", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  addons: {
    list: () => request<Addon[]>("/api/addons"),
    patch: (id: string, enabled: boolean) =>
      request<{ ok: boolean }>(`/api/addons/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    getSettings: (id: string) =>
      request<AddonSettings>(`/api/addons/${id}/settings`),
    putSettings: (id: string, settings: Record<string, unknown>) =>
      request<{ ok: boolean }>(`/api/addons/${id}/settings`, {
        method: "PUT",
        body: JSON.stringify({ settings }),
      }),
  },

  stream: {
    url: (addonId: string, itemId: string, fileId: string, token: string) =>
      `${API}/api/stream/${addonId}/${itemId}/${fileId}?token=${encodeURIComponent(token)}`,
  },
}
