# F06 — Squelette Back-Office Admin & Workflow draft → published

**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 9.1 (Gestion du Catalogue — squelette)
**Dépendances** : F02, F03
**Estimation** : 1.5 jours

## Contexte et objectif

Le back-office est le **poumon** de la plateforme : sans lui, personne ne peut peupler le catalogue (Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Templates, Facteurs d'émission, Skills) et la plateforme reste une coquille vide.

Cette feature livre **le cadre commun** réutilisé par toutes les features de catalogue qui suivent (F07 à F10, F20) :
- Layout admin séparé du frontend PME (`/admin/*`).
- Workflow standardisé `draft → published` (un objet n'est `published` que si toutes ses sources sont `verified`).
- Composants CRUD réutilisables (formulaire, liste paginée, badge de statut, indicateur de version).
- Garde d'accès basée sur le rôle Admin (F02).

Pas de logique métier propre à un type d'objet ici — c'est un squelette. Mais il doit être assez robuste pour porter 8+ types de catalogue.

## User Stories

### US1 — Layout admin distinct accessible aux admins (P1)
**En tant qu'**admin ESG Mefali,
**je veux** qu'après login, le menu de navigation me propose un accès "Back-office" (ou je suis directement redirigé), avec un layout dédié (sidebar des sections : Sources, Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Critères, Documents requis, Facteurs d'émission, Templates, Skills, PME, Métriques),
**afin de** travailler dans un contexte dédié.

**Test indépendant** : un admin se connecte et accède à `/admin` ; un user PME tentant la même URL reçoit 403 et est redirigé.

### US2 — Workflow draft → published standardisé (P1)
**En tant qu'**admin,
**je veux** que chaque objet du catalogue ait un cycle de vie commun :
- création en `draft`,
- édition libre tant qu'en `draft`,
- bouton "Publier" qui vérifie que **toutes** les sources liées sont `verified` (sinon erreur explicite listant les sources manquantes),
- une fois `published`, modifier l'objet crée une nouvelle version (F04) — l'ancienne reste accessible.

**Scénarios** :
1. Admin crée un Indicateur draft sans source vérifiée → bouton "Publier" désactivé avec tooltip "1 source en attente de vérif".
2. Admin publie un Indicateur valide → statut `published`, devient utilisable par le LLM (F03 + F23).
3. Admin tente d'éditer un Indicateur `published` → confirmation "Ceci créera la version v2 — continuer ?".

### US3 — Composants CRUD réutilisables (P1)
**En tant que** dev frontend,
**je veux** des composants Vue génériques :
- `<AdminListPage :columns :rows :filters :pagination :actions>`
- `<AdminFormPage :schema :model :on-save :on-publish>`
- `<StatusBadge :status>` (draft / published / outdated / pending)
- `<VersionTimeline :entity-type :entity-id>` (lecture seule, montre l'historique)

**afin de** ne pas réécrire le même CRUD 10 fois.

### US4 — Toutes les actions admin sont auditées (P1)
**En tant que** compliance,
**je veux** que **toute** mutation faite via le back-office soit journalisée dans `audit_log` (F04) avec `source_of_change='admin'` et `user_id` = l'admin,
**afin de** tracer qui a publié quoi.

### US5 — Recherche transversale dans le catalogue (P2)
**En tant qu'**admin,
**je veux** une barre de recherche globale qui cherche dans tous les types d'objets du catalogue (par nom, publisher, ID),
**afin de** retrouver rapidement un objet sans cliquer dans 10 menus.

### US6 — Indicateur de complétude par section (P2)
**En tant qu'**admin,
**je veux** voir sur la sidebar le nombre d'objets `draft`, `published` et `pending verification` par section,
**afin de** savoir où il reste du travail.

## Exigences fonctionnelles

- **FR-001** : Route Nuxt `/admin` avec middleware vérifiant `role === 'admin'`. 403 sinon.
- **FR-002** : Layout dédié `layouts/admin.vue` avec sidebar permanente, header simple, breadcrumbs.
- **FR-003** : Mixin/composable `useEntityCrud<T>(entityName)` exposant `list`, `get`, `create`, `update`, `publish`, `getVersions`, lié aux endpoints REST conventionnels :
  - `GET /admin/{entity}/`
  - `GET /admin/{entity}/{id}`
  - `POST /admin/{entity}/`
  - `PUT /admin/{entity}/{id}`
  - `POST /admin/{entity}/{id}/publish`
  - `GET /admin/{entity}/{id}/versions`
- **FR-004** : Endpoint `POST /admin/{entity}/{id}/publish` côté FastAPI :
  - vérifie que `all sources verified`,
  - passe le statut à `published`,
  - écrit dans `audit_log` (F04).
- **FR-005** : Composant `<StatusBadge>` avec 4 variantes visuelles (draft = jaune, published = vert, outdated = gris, pending = orange).
- **FR-006** : Composant `<VersionTimeline>` qui appelle `/admin/{entity}/{id}/versions` et rend une liste verticale avec `version, valid_from, valid_to, published_by`.
- **FR-007** : Endpoint `GET /admin/search?q=` qui retourne des résultats groupés par type d'entité (limit 10 par type).
- **FR-008** : Endpoint `GET /admin/stats/catalog` qui renvoie `{sources: {draft:N, verified:N, outdated:N}, fonds: {draft:N, published:N}, ...}` pour la sidebar.
- **FR-009** : Pas de CRUD complet par type d'entité ici — chaque type est livré par sa feature dédiée (F07, F08, F09, F10, F20). F06 livre **les rails**.
- **FR-010** : Toutes les routes `/admin/*` passent par un middleware FastAPI qui pose `app.is_admin = true` dans la session Postgres (cohérence F02 RLS).

## Exigences non-fonctionnelles

- **NFR-001** : Le back-office doit tenir 100+ admins simultanés sans dégradation. Pagination obligatoire à partir de 50 lignes.
- **NFR-002** : Le formulaire admin doit fonctionner offline-friendly (localStorage de brouillon en cours d'édition pour ne pas perdre 30 min de saisie en cas de bug navigateur). Confirmation avant écrasement à la reprise.
- **NFR-003** : Aucun composant admin n'utilise une couleur du design system PME — palette dédiée (sobre, dense d'information, pas d'animations gsap).
- **NFR-004** : Accessibilité clavier complète sur les listes et formulaires (Tab, Enter, Esc).

## Entités clés

- Aucune nouvelle table — F06 utilise les colonnes `status ENUM('draft','published','outdated','pending')` posées en F01 et le mécanisme de versions de F04.

## Success Criteria

- **SC-001** : Un admin avec son login peut accéder à `/admin`, voit la sidebar, peut cliquer sur "Sources" et arrive sur une liste vide (la feature F07 livrera le contenu).
- **SC-002** : Un user PME tentant `/admin` reçoit 403 et est redirigé.
- **SC-003** : Le composant `<AdminListPage>` est utilisé par au moins 2 features de catalogue ultérieures sans réécriture.
- **SC-004** : `POST /admin/{entity}/{id}/publish` rejette avec 422 si une source liée est `pending`.

## Hors-scope

- CRUD spécifique aux Sources, Fonds, Intermédiaires, Offres, etc. → F07, F08, F09, F10, F20.
- Métriques admin avancées (volumes, coûts LLM) → F10.
- Bulk actions (publish multiple, import CSV) → post-MVP.
- Workflow d'approbation à 4 yeux → on a déjà la double-validation des Sources en F03 ; pas d'approbation supplémentaire en MVP.

## Risques et points de vigilance

- **Couplage fort avec F04 (versioning)** : si F04 n'est pas solide, F06 va l'amplifier. Vérifier le pattern de versioning sur 1 entité (par ex. `Indicateur`) avant de le généraliser.
- **Nuxt 4 layouts** : bien séparer `layouts/admin.vue` et `layouts/default.vue` pour éviter les fuites CSS.
- **`status='draft'` sur les sources** : un objet du catalogue qui dépend d'une source `pending` ne peut pas être `published`. Cette règle est centrale et doit être testée explicitement.
