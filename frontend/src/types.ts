// Auth
export interface User {
  id: string
  email: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
}

// Search
export interface AudiobookResult {
  id: string
  title: string
  addon_id: string
  author: string
  description: string
  cover_url: string | null
  extra: Record<string, unknown>
}

export interface SearchResponse {
  query: string
  results: AudiobookResult[]
}

// Chapter / File
export interface ChapterFile {
  id: string
  title: string
  track_number: number
  duration: number
  url: string
}

// Book detail
export interface BookDetail {
  id: string
  title: string
  addon_id: string
  author: string
  description: string
  cover_url: string | null
  files: ChapterFile[]
  extra: Record<string, unknown>
}

// Library
export interface LibraryItem {
  id: string
  addon_id: string
  external_id: string
  title: string
  author: string
  cover_url: string | null
  metadata: Record<string, unknown>
  added_at: string
}

export interface SaveBookPayload {
  addon_id: string
  external_id: string
  title: string
  author: string
  cover_url: string | null
  metadata: Record<string, unknown>
}

// Progress
export interface PlaybackProgress {
  library_item_id: string
  file_id: string
  position: number
  duration: number
  last_played: string
}

export interface UpsertProgressPayload {
  library_item_id: string
  file_id: string
  position: number
  duration: number
}

// Addons
export interface SettingsField {
  key: string
  type: "string" | "password" | "number" | "boolean" | "path"
  label: string
  required: boolean
  default?: unknown
  description?: string
  max_length?: number
}

export interface Addon {
  id: string
  name: string
  description: string
  version: string
  capabilities: string[]
  settings_schema: SettingsField[]
  enabled: boolean
  configured: boolean
  is_remote: boolean
  author: string | null
  icon_url: string | null
}

export interface AddonSettings {
  addon_id: string
  settings: Record<string, unknown>
}
