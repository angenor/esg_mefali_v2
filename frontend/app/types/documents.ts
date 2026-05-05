// F50 — Types F50 documents (miroir backend + ViewModels UI).
// Cf. specs/050-documents-ocr-ui/contracts/documents_api_extensions.md.

export type OcrStatus = "pending" | "processing" | "done" | "deferred" | "failed" | "error"

export type OcrStatusUI =
  | "queued"
  | "processing"
  | "verify"
  | "validated"
  | "error"
  | "timeout"

export type DocumentType =
  | "statuts"
  | "rapport_activite"
  | "facture"
  | "contrat"
  | "politique"
  | "autre"

export interface Money {
  amount: string
  currency: string
}

export type ExtractedFieldValue = string | number | boolean | Money | null

export interface ExtractedField {
  key: string
  label?: string | null
  value: ExtractedFieldValue
  confidence: number
}

export interface ExtractionPayload {
  fields: ExtractedField[]
}

export interface DocumentDetail {
  id: string
  entreprise_id: string
  name: string
  original_filename: string
  mime_type: string
  size_bytes: number
  type: DocumentType
  ocr_status: OcrStatus
  ocr_error: string | null
  uploaded_by?: string | null
  created_at: string
  content_sha256?: string | null
  extraction_payload: ExtractionPayload
  extraction_validated_at: string | null
  extraction_validated_by: string | null
  linked_projets: string[]
  tags: string[]
  deleted_at: string | null
  purge_scheduled_at: string | null
}

export interface DocumentListItem {
  id: string
  name: string
  mime_type: string
  size_bytes: number
  type: DocumentType
  created_at: string
  ocr_status: OcrStatus
  extraction_validated_at: string | null
  tags: string[]
  source?: "document_entreprise" | "document_projet"
}

export interface FingerprintLookupOut {
  document: DocumentDetail
}

export interface ValidateExtractionFieldIn {
  key: string
  value: ExtractedFieldValue
}

export interface PropagationTarget {
  entity: "entreprise" | "projet"
  id: string
}

export interface ValidateExtractionIn {
  fields: ValidateExtractionFieldIn[]
  propagate_to: PropagationTarget[]
}

export interface ValidateExtractionOut {
  id: string
  extraction_validated_at: string
  extraction_validated_by: string
  propagated: { entity: "entreprise" | "projet"; id: string; fields_updated: string[] }[]
}

export type UploadJobStatus =
  | "pending"
  | "fingerprinting"
  | "duplicate"
  | "uploading"
  | "success"
  | "error"
  | "cancelled"

export interface UploadJob {
  id: string
  file: File
  filename: string
  size: number
  mime: string
  sha256: string | null
  percent: number
  status: UploadJobStatus
  error?: string | null
  documentId?: string | null
  linkProjetId?: string | null
}

export interface AppError {
  code: string
  message: string
}
