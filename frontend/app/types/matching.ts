// F51 T003 — Types partagés pour le matching et le catalogue d'offres.
//
// Money est aligné sur la constitution P5 ({amount: string Decimal, currency}).
// Aucune valeur monétaire n'est manipulée en `number` côté frontend.

export type Currency = "XOF" | "EUR"

export interface Money {
  amount: string // Decimal sérialisé en string (P5)
  currency: Currency
}

export type OffreType = "credit" | "subvention" | "garantie" | "autre"

export interface Geolocation {
  lat: number
  lng: number
}

export interface OffreIntermediaire {
  id: string
  nom: string
  geolocation: Geolocation | null
  url?: string | null
}

export interface OffreMatchItem {
  offre_id: string
  score?: number
  rang?: number
  nom: string
  intermediaire: OffreIntermediaire
  type: OffreType
  montant_min: Money
  montant_max: Money
  duree_min_mois: number
  duree_max_mois: number
  secteurs: string[]
}

export interface OffreListItem extends OffreMatchItem {
  accepted_languages: ("fr" | "en")[]
}

export interface DocumentRequis {
  key: string
  label: string
  format: string
}

export interface OffreDetail extends OffreListItem {
  description: string
  documents_requis: DocumentRequis[]
  conditions: string[]
  lien_externe: string | null
  source_id: string | null
}

export interface MatchingFilters {
  type?: OffreType
  montant_min_eur?: number
  montant_max_eur?: number
  duree_min_mois?: number
  duree_max_mois?: number
  intermediaire_id?: string
  secteur?: string
  q?: string
}

export interface ComparatorEntry {
  offre_id: string
  projet_id: string | null
  snapshot_label: string
  snapshot_montant: Money
  snapshot_intermediaire: string
  added_at: string
}

export interface OffreListOut {
  items: OffreListItem[]
  count: number
  next_cursor: string | null
}

export interface MatchingListOut {
  items: OffreMatchItem[]
  count: number
}
