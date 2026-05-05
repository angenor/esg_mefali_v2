// F49 T014 — Types TS pour les attestations PME + page publique /verify.
//
// Cf. contracts/ui-backend.md §C et data-model.md §1+§2.

export type AttestationType =
  | "conformite_esg"
  | "bilan_carbone"
  | "score_credit"
  | "dossier_candidature"

export type AttestationStatus = "active" | "expired" | "revoked"

export type RevokeReason =
  | "erreur_emission"
  | "donnees_invalidees"
  | "demande_pme"
  | "expiration_anticipee"
  | "autre"

export const REVOKE_REASONS: ReadonlyArray<RevokeReason> = [
  "erreur_emission",
  "donnees_invalidees",
  "demande_pme",
  "expiration_anticipee",
  "autre",
] as const

export interface Attestation {
  id: string
  public_id: string
  type: AttestationType
  status: AttestationStatus
  issued_at: string // ISO
  expires_at: string // ISO
  revoked_at: string | null
  revoke_reason: RevokeReason | null
  verify_url: string
  download_url?: string
}

export interface PublicSource {
  id: string
  title: string
  url: string | null
  verified_at?: string | null
}

export interface PublicIndicator {
  code: string
  label: string
  label_en?: string | null
  value: number | string | null
  unit?: string | null
  source_id?: string | null
}

export interface PublicVerification {
  public_id: string
  type?: AttestationType | string
  entity_legal_name: string
  status: AttestationStatus
  issued_at: string
  expires_at: string
  revoked_at: string | null
  revoke_reason: RevokeReason | null
  signature_valid: boolean
  payload: {
    indicators: PublicIndicator[]
    sources: PublicSource[]
  }
  download_url?: string
}
