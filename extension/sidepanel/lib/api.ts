// F52 US4 — Client REST minimal du sidepanel.
// Authentifié via cookie partagé avec l'app web (credentials: 'include').

export interface SidepanelCandidatureItem {
  id: string
  offer_label: string
  deadline_at: string
  completion_pct: number
  resume_url: string
}

export interface SidepanelOfferItem {
  id: string
  label: string
  match_score: number
  matching_url: string
}

export interface SidepanelContext {
  matched_offer_ids: string[]
  active_candidatures: SidepanelCandidatureItem[]
  recommended_offers: SidepanelOfferItem[]
}

export interface ExtensionStatus {
  detected: boolean
  extension_version?: string | null
  last_ping_at?: string | null
}

const DEFAULT_API_BASE = "http://localhost:8010"

function getApiBase(): string {
  // Configurable via storage.local key "apiBase" pour les builds de prod.
  const cached = (globalThis as unknown as { __ESG_MEFALI_API_BASE__?: string })
    .__ESG_MEFALI_API_BASE__
  return cached || DEFAULT_API_BASE
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(
  path: string,
  params?: Record<string, string>
): Promise<T> {
  const base = getApiBase()
  const url = new URL(`${base}${path}`)
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  }
  const res = await fetch(url.toString(), {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
  })
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.status}`)
  }
  return (await res.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T | null> {
  const base = getApiBase()
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new ApiError(res.status, `POST ${path} failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return (await res.json()) as T
}

export async function fetchSidepanelContext(
  host: string,
  path: string
): Promise<SidepanelContext> {
  return getJson<SidepanelContext>("/me/extension/sidepanel-context", {
    host,
    path,
  })
}

export async function fetchExtensionStatus(): Promise<ExtensionStatus> {
  return getJson<ExtensionStatus>("/me/extension/status")
}

export async function postPing(payload: {
  extension_version: string
  user_agent_summary: string
}): Promise<void> {
  await postJson("/me/extension/ping", payload)
}
