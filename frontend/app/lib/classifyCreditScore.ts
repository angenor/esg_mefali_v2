/**
 * F48 — Helper pur de classification du score crédit (clarif Q2).
 *
 * Seuils (bornes inférieures inclusives) :
 *   - 0..39  → Insuffisant
 *   - 40..59 → À améliorer
 *   - 60..79 → Bon
 *   - 80..100 → Excellent
 */

import type {
  ClassificationBucket,
  ClassificationColorToken,
  ClassificationView,
} from '~/types/creditScore'

const LABELS: Record<ClassificationBucket, string> = {
  insuffisant: 'Insuffisant',
  a_ameliorer: 'À améliorer',
  bon: 'Bon',
  excellent: 'Excellent',
}

const COLORS: Record<ClassificationBucket, ClassificationColorToken> = {
  insuffisant: 'danger',
  a_ameliorer: 'warning',
  bon: 'success',
  excellent: 'success-strong',
}

function toBucket(score: number): ClassificationBucket {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'bon'
  if (score >= 40) return 'a_ameliorer'
  return 'insuffisant'
}

/**
 * Classifie un score crédit `[0..100]` en bucket + libellé + colorToken.
 * Hors borne : clamp à `[0..100]` plutôt que throw (UX résiliente).
 */
export function classifyCreditScore(score: number): ClassificationView {
  const clamped = Math.max(0, Math.min(100, Math.round(score)))
  const bucket = toBucket(clamped)
  return {
    bucket,
    label: LABELS[bucket],
    colorToken: COLORS[bucket],
  }
}

export const CLASSIFICATION_LABELS = LABELS
