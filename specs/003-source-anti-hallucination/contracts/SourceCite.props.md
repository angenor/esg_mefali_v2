# Composant Vue `<SourceCite>` — Contrat Props/Events

Fichier cible : `frontend/app/components/source/SourceCite.vue`

## Props

| Prop | Type | Required | Default | Notes |
|---|---|---|---|---|
| `sourceIds` | `string[]` (UUID) | yes | — | Liste des sources à afficher |
| `inline` | `boolean` | no | `true` | `true` = picto à côté du texte ; `false` = badge bloc |
| `size` | `'sm' \| 'md' \| 'lg'` | no | `'sm'` | |
| `accent` | `'auto' \| 'verified' \| 'pending' \| 'outdated'` | no | `'auto'` | `auto` = pire statut parmi sourceIds |

## Events

| Event | Payload | Notes |
|---|---|---|
| `open` | `{ sourceIds: string[] }` | Émis à l'ouverture du bottom sheet |
| `external-link` | `{ sourceId: string, url: string }` | Émis au clic sur lien externe (analytics) |

## Comportement

- Picto `<i class="iconify" data-icon="material-symbols:link"/>` (icône configurable plus tard).
- Au clic : ouvre `<SourceListBottomSheet>` (gsap, slide-up).
- La bottom sheet liste chaque Source : titre, publisher, version, `date_publi`, `captured_at`, badge statut (Vérifiée vert / Non vérifiée orange / Obsolète rouge), bouton "Ouvrir la source" (target=_blank, rel=noopener).
- Bouton "Fermer" en haut + tap-out backdrop.
- Récupération via `useSourceFetch(id)` → `GET /sources/{id}` (lecture publique unitaire FR-004).
- États : loading (skeleton), error (toast + bouton réessayer), empty (badge gris "Aucune source").
- Accessibilité : focus trap dans la bottom sheet, `aria-label="Voir les sources de cette donnée"` sur le picto.
