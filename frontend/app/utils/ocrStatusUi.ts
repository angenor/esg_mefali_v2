// F50 T012 — Mapping ocr_status backend → libellés UI (cf. contracts §1).

import type { DocumentDetail, OcrStatusUI } from "~/types/documents"

export interface OcrStatusUiInfo {
  status: OcrStatusUI
  label: string
  tone: "neutral" | "info" | "warning" | "success" | "danger"
}

const LABELS: Record<OcrStatusUI, OcrStatusUiInfo> = {
  queued: { status: "queued", label: "En file d'attente", tone: "neutral" },
  processing: { status: "processing", label: "Extraction en cours…", tone: "info" },
  verify: { status: "verify", label: "Vérifier", tone: "warning" },
  validated: { status: "validated", label: "Validé", tone: "success" },
  error: { status: "error", label: "Échec", tone: "danger" },
  timeout: { status: "timeout", label: "Délai dépassé", tone: "warning" },
}

export function mapOcrStatusToUi(
  doc: Pick<DocumentDetail, "ocr_status" | "extraction_validated_at">,
  opts: { timedOut?: boolean } = {},
): OcrStatusUiInfo {
  if (opts.timedOut) return LABELS.timeout
  switch (doc.ocr_status) {
    case "pending":
      return LABELS.queued
    case "processing":
    case "deferred":
      return LABELS.processing
    case "done":
      return doc.extraction_validated_at ? LABELS.validated : LABELS.verify
    case "error":
    case "failed":
      return LABELS.error
    default:
      return LABELS.queued
  }
}

export function isLowConfidence(confidence: number): boolean {
  return confidence < 0.6
}
