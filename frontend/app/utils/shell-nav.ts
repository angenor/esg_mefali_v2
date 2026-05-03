// F38 — Registre interne des rubriques sidebar (FR figé, préparation i18n F45)
export interface NavItem {
  id: string
  label: string
  icon: string
  to: string
  badgeKey?: 'unread'
}

export const NAV_ITEMS: ReadonlyArray<NavItem> = [
  { id: 'dashboard', label: 'Tableau de bord', icon: 'home', to: '/dashboard' },
  { id: 'profil', label: 'Profil entreprise', icon: 'building', to: '/profil/entreprise' },
  { id: 'projets', label: 'Projets', icon: 'briefcase', to: '/profil/projets' },
  { id: 'plan-action', label: "Plan d'action", icon: 'check-circle', to: '/plan-action' },
  { id: 'scoring', label: 'Scoring ESG', icon: 'chart-bar', to: '/scoring' },
  { id: 'carbone', label: 'Empreinte carbone', icon: 'cloud', to: '/carbone' },
  { id: 'credit', label: 'Score crédit', icon: 'banknotes', to: '/credit' },
  { id: 'candidatures', label: 'Candidatures', icon: 'document-text', to: '/candidatures' },
  { id: 'rapports', label: 'Rapports & attestations', icon: 'document-check', to: '/rapports' },
  { id: 'bibliotheque', label: 'Bibliothèque', icon: 'book-open', to: '/bibliotheque' },
  { id: 'parametres', label: 'Paramètres', icon: 'cog', to: '/parametres' },
]
