// F40 T004 — Types Source partagés pour la viz library.
// Réf. data-model.md §1.1 + contracts/sources-resolve.openapi.yaml.

export type SourcePillar =
  | 'E'
  | 'S'
  | 'G'
  | 'financial'
  | 'regulatory'
  | 'methodology'

export const SOURCE_PILLARS: ReadonlyArray<SourcePillar> = [
  'E',
  'S',
  'G',
  'financial',
  'regulatory',
  'methodology',
]

export type SourceStatus = 'verified' | 'revoked'

export interface SourceRef {
  source_id: string
  title: string
  url: string
  pillar: SourcePillar
  valid_from: string
  valid_to?: string | null
  status: SourceStatus
  revoked_reason?: string | null
}

export class SourceNotFoundError extends Error {
  readonly source_id: string
  constructor(source_id: string) {
    super(`Source ${source_id} not found`)
    this.name = 'SourceNotFoundError'
    this.source_id = source_id
  }
}

export function isSourcePillar(value: unknown): value is SourcePillar {
  return typeof value === 'string' && (SOURCE_PILLARS as ReadonlyArray<string>).includes(value)
}
