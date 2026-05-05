/**
 * F44 — Dashboard PME UI : table de correspondance events chat ↔ blocs summary.
 *
 * Cf. specs/044-dashboard-pme-ui/research.md R5 et contracts/chat-eventbus-sync.md C-EVT-1.
 */

export type BlockKey =
  | 'scores'
  | 'carbon'
  | 'credit_score'
  | 'candidatures'
  | 'rapports'
  | 'attestations'
  | 'next_actions'

export type DashboardEventName =
  | 'scoring:computed'
  | 'carbon:computed'
  | 'credit:computed'
  | 'candidature:created'
  | 'candidature:status_changed'
  | 'rapport:generated'
  | 'attestation:emitted'
  | 'action_step:created'
  | 'action_step:completed'

/**
 * Pour chaque event chat, la liste des blocs summary à invalider.
 * `attestation:emitted` invalide à la fois `attestations` et `rapports` car
 * `RapportsCardVM` consomme aussi le bloc attestations (cf. data-model.md).
 */
export const EVENT_TO_BLOCK_MAP: Readonly<Record<DashboardEventName, ReadonlyArray<BlockKey>>> = {
  'scoring:computed': ['scores'],
  'carbon:computed': ['carbon'],
  'credit:computed': ['credit_score'],
  'candidature:created': ['candidatures'],
  'candidature:status_changed': ['candidatures'],
  'rapport:generated': ['rapports'],
  'attestation:emitted': ['rapports', 'attestations'],
  'action_step:created': ['next_actions'],
  'action_step:completed': ['next_actions'],
} as const
