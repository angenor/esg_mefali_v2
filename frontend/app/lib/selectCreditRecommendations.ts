/**
 * F48 — Filet de sécurité front pour le tri/filtre des recommandations crédit.
 *
 * Le backend (`/me/credit-score/recommendations`) trie déjà par impact desc et
 * limite à `limit`. Cette fonction sécurise le rendu si le backend renvoie
 * une liste plus large ou non triée (ex: clients legacy / cache désynchronisé).
 */

import type {
  CreditRecommendationDTO,
  SubscoreBucket,
  SubscoresView,
} from '~/types/creditScore'

export function selectCreditRecommendations(
  raw: CreditRecommendationDTO[],
  subscores: SubscoresView,
  limit: number,
): CreditRecommendationDTO[] {
  if (limit <= 0 || !raw.length) return []

  // Filtre minimal : impact > 0
  const valid = raw.filter((r) => r.estimated_credit_points_impact > 0)

  // Buckets ordonnés par valeur croissante (None traité comme 0 = priorité max).
  const ranked: SubscoreBucket[] = (Object.keys(subscores) as SubscoreBucket[])
    .slice()
    .sort((a, b) => {
      const va = subscores[a] ?? -1
      const vb = subscores[b] ?? -1
      return va - vb
    })

  const out: CreditRecommendationDTO[] = []
  const seen = new Set<string>()
  for (const bucket of ranked) {
    const inBucket = valid
      .filter((r) => r.target_subscore === bucket && !seen.has(r.step_id))
      .sort(
        (a, b) =>
          b.estimated_credit_points_impact - a.estimated_credit_points_impact,
      )
    for (const r of inBucket) {
      if (out.length >= limit) break
      out.push(r)
      seen.add(r.step_id)
    }
    if (out.length >= limit) break
  }
  return out.slice(0, limit)
}
