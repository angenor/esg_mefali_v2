// F49 — Service API pour rapports & attestations (utilise $fetch + apiBase).
//
// Adapte le contrat F49 (cible) sur l'API F24/F30 réelle :
//   Contrat : POST /me/rapports/generate { type, referentiel_id, period_* }
//   Réel    : POST /me/rapports/conformite { entity_type, entity_id, referentiels[] }
// L'adaptation est faite ici pour que les stores restent alignés sur F49.

import type {
  GenerateRequest,
  PreviewUrl,
  Rapport,
} from "~/types/reports"
import type { Attestation, RevokeReason } from "~/types/attestations"

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg =
    (g.useRuntimeConfig?.() as RuntimeConfigShape | undefined) ??
    (g.useNuxtApp?.()?.$config as RuntimeConfigShape | undefined)
  return String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>

function fetcher(): FetchFn {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const f = (globalThis as any).$fetch as FetchFn | undefined
  if (!f) throw new Error("$fetch unavailable")
  return f
}

interface RapportRowF24 {
  rapport_id: string
  entity_type: "entreprise" | "projet"
  entity_id: string
  referentiels: string[]
  language: "fr" | "en"
  file_size_bytes: number | null
  generated_at: string
  download_url: string
}

function adaptRapport(r: RapportRowF24): Rapport {
  // F24 ne distingue pas encore type=carbone/candidature ; on infère
  // "conformite" par défaut. Cette inférence sera affinée quand le backend
  // exposera un champ explicite.
  return {
    id: r.rapport_id,
    type: "conformite",
    referentiel_id: r.referentiels?.[0] ?? null,
    period_from: null,
    period_to: null,
    created_at: r.generated_at,
    size_bytes: r.file_size_bytes,
    status: "ready",
    download_filename: `rapport-esg-${r.rapport_id}.pdf`,
    entity_type: r.entity_type,
    entity_id: r.entity_id,
    referentiels: r.referentiels,
    language: r.language,
  }
}

export const reportsApi = {
  async fetchAll(): Promise<Rapport[]> {
    const f = fetcher()
    const out = await f<{ items: RapportRowF24[]; total: number }>(
      `${apiBase()}/me/rapports`,
      { credentials: "include" },
    )
    return (out.items ?? []).map(adaptRapport)
  },

  async generate(req: GenerateRequest): Promise<Rapport> {
    if (!req.entity_id) {
      throw new Error("entity_id requis (adaptation F24)")
    }
    const f = fetcher()
    const body = {
      entity_type: req.entity_type ?? "entreprise",
      entity_id: req.entity_id,
      referentiels:
        req.referentiels ?? (req.referentiel_id ? [req.referentiel_id] : []),
      language: req.language ?? "fr",
    }
    const out = await f<RapportRowF24>(
      `${apiBase()}/me/rapports/conformite`,
      {
        method: "POST",
        credentials: "include",
        body,
      },
    )
    return adaptRapport(out)
  },

  async loadPreviewUrl(rapportId: string): Promise<PreviewUrl> {
    const f = fetcher()
    return await f<PreviewUrl>(
      `${apiBase()}/me/rapports/${rapportId}/preview-url`,
      { credentials: "include" },
    )
  },

  buildDownloadUrl(rapportId: string): string {
    return `${apiBase()}/me/rapports/${rapportId}/download`
  },

  buildStreamUrl(generationId: string): string {
    return `${apiBase()}/me/rapports/generate/${generationId}/stream`
  },
}

interface AttestationRowF30 {
  id: string
  public_id: string
  status: "active" | "expired" | "revoked"
  generated_at: string
  valid_until: string
  revoked_at: string | null
  scores_inclus: Record<string, unknown>
  referentiels_versions: Record<string, string>
  signature_ed25519: string
  pubkey_fingerprint: string
  hash_document: string
  download_url: string
  verify_url: string
}

function adaptAttestation(a: AttestationRowF30): Attestation {
  // F30 actuel ne stocke pas le `type` typé : on infère via les scores inclus.
  // À défaut on retombe sur `conformite_esg` (type d'attestation de base).
  return {
    id: a.id,
    public_id: a.public_id,
    type: "conformite_esg",
    status: a.status,
    issued_at: a.generated_at,
    expires_at: a.valid_until,
    revoked_at: a.revoked_at,
    revoke_reason: null,
    verify_url: a.verify_url,
    download_url: a.download_url,
  }
}

export const attestationsApi = {
  async fetchAll(): Promise<Attestation[]> {
    const f = fetcher()
    const out = await f<AttestationRowF30[]>(
      `${apiBase()}/me/attestations`,
      { credentials: "include" },
    )
    return (out ?? []).map(adaptAttestation)
  },

  async revoke(
    attestationId: string,
    reason: RevokeReason,
  ): Promise<Attestation> {
    const f = fetcher()
    // F30 attend `reason: string min 3` (texte libre côté backend) ; on
    // poste le code de motif (≥ 3 caractères pour tous les codes).
    const out = await f<AttestationRowF30>(
      `${apiBase()}/me/attestations/${attestationId}/revoke`,
      {
        method: "POST",
        credentials: "include",
        body: { reason },
      },
    )
    return { ...adaptAttestation(out), revoke_reason: reason }
  },
}
