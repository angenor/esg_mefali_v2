// F38 T077 — Libellés FR centralisés du shell.
// Préparation i18n future (R-018) : tout libellé visible utilisateur du shell
// doit être listé ici. Quand i18n sera ajouté (post-MVP), ce fichier devient la
// table FR et un équivalent par langue sera produit.
//
// Convention : clé en SCREAMING_SNAKE_CASE, valeur en français (par défaut UEMOA).

export const SHELL_LABELS_FR = {
  // Navigation principale (sidebar + bottom nav)
  NAV_PRIMARY: 'Navigation principale',
  NAV_QUICK: 'Navigation rapide',
  NAV_MORE: 'Plus de rubriques',
  NAV_BREADCRUMB: "Fil d'Ariane",

  // Sidebar
  SIDEBAR_COLLAPSE: 'Replier la barre latérale',
  SIDEBAR_EXPAND: 'Déplier la barre latérale',
  SIDEBAR_TOGGLE_OPEN: 'Ouvrir le menu de navigation',
  SIDEBAR_TOGGLE_CLOSE: 'Fermer le menu de navigation',

  // Notifications
  NOTIFICATIONS: 'Notifications',
  NOTIFICATIONS_COUNT: (n: number) => `Notifications, ${n} non lues`,

  // Palette de commandes
  PALETTE_LABEL: 'Palette de commandes',
  PALETTE_SEARCH: 'Recherche dans la palette de commandes',
  PALETTE_PLACEHOLDER: 'Rechercher une action, une page, un projet…',
  PALETTE_EMPTY: 'Aucun résultat',

  // Menu utilisateur
  USER_MENU: (name: string) => `Menu de l'utilisateur ${name}`,
  LOGOUT: 'Se déconnecter',
  PROFILE: 'Mon profil',
  SETTINGS: 'Paramètres',

  // États globaux
  OFFLINE_BANNER: 'Connexion internet perdue. Vos modifications seront synchronisées au retour.',
  ROUTE_LOADING: 'Chargement de la page…',
  ERROR_GENERIC: "Une erreur est survenue. Réessayez ou contactez l'assistance.",
  ERROR_RETRY: 'Réessayer',
} as const

export type ShellLabelKey = keyof typeof SHELL_LABELS_FR
