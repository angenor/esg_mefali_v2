# Research — Plan d'action ESG UI (F45)

Phase 0 — décisions techniques et levée des inconnues. Aucune `[NEEDS CLARIFICATION]` n'a été laissée dans le spec, donc cette phase consolide les choix d'implémentation et leurs justifications.

## R1 — Rendu de la timeline horizontale

**Decision** : Timeline réalisée en **HTML/Tailwind + SVG ponctuel** (lignes axiales et boutons jalons), animée par **gsap** (déjà installé) avec stagger 80 ms à l'arrivée.

**Rationale** :
- Pas besoin d'une librairie de visualisation lourde (chart.js, d3) : le rendu est essentiellement un axe + N boutons absolument positionnés selon `(horizon_at - generated_at) / span`.
- gsap est déjà utilisé par F39 (bottom sheet), F44 (skeleton dashboard) et le brief F45 le mentionne explicitement (NFR-001).
- SVG seulement pour la ligne axiale et les graduations (4 horizons : 3M, 6M, 12M, 24M) ; les jalons sont des `<button>` HTML (a11y native, focus, tooltip).
- Sur mobile (< 768 px), bascule en disposition **verticale** (axe vertical à gauche, jalons à droite) via classes responsive Tailwind ; la même structure DOM est conservée, seul le layout change. Pas de second composant, pas de SSR mismatch.

**Alternatives considered** :
- d3-timeline / vis-timeline : trop lourd pour un usage MVP simple.
- Canvas custom : sacrifie l'a11y (tooltips, focus, navigation clavier).
- Pure CSS grid : viable mais le calcul de position en pourcentage est plus simple en JS reactif côté composant.

## R2 — Buckets d'horizon

**Decision** : Définir **5 buckets** côté frontend : `< 3 mois`, `3-6 mois`, `6-12 mois`, `12-24 mois`, `Sans échéance` (étapes sans `horizon_at` explicite — cas marginal).

**Rationale** :
- Le brief mentionne 4 horizons (3/6/12/24 mois). Le bucket « Sans échéance » couvre l'edge case (étape avec date null hypothétique) et permet d'éviter de masquer silencieusement une étape.
- Le bucketing est fait dans `lib/mapPlanToTimelineBuckets.ts` à partir de `horizon_at - generated_at` (pas de fuseau horaire, dates sans heure côté backend `date`).
- Le toggle horizon (US6) `6 / 12 / 24` mois filtre les buckets : choisir `12` montre `< 3M`, `3-6M`, `6-12M` ; choisir `6` montre `< 3M`, `3-6M`. Le bucket `Sans échéance` reste toujours visible (information pas filtrable temporellement).

**Alternatives considered** :
- Faire le bucketing côté backend : ajoute un endpoint, redondant avec la donnée brute déjà retournée par `GET /me/action-plan`.
- 4 buckets seulement (sans « Sans échéance ») : risque d'étapes invisibles.

## R3 — File d'attente d'optimistic updates

**Decision** : Étendre le composable existant `useActionStepToggle.ts` (livré par F44 pour la mini-card du dashboard) avec une **file d'attente FIFO par `step_id`** : si une mutation est déjà en vol pour un `step_id` donné, la suivante est mise en attente et appliquée à la résolution de la précédente.

**Rationale** :
- Couvre l'edge case « cocher pendant un fetch en cours ».
- La file est par `step_id` (pas globale) : permet à la PME de cocher rapidement plusieurs étapes différentes en parallèle.
- Le rollback en cas d'erreur restaure l'état avant la mutation **active** uniquement, pas toute la file ; les mutations en attente sur la même `step_id` sont annulées et un toast d'erreur explique « la mise à jour précédente a échoué, veuillez réessayer ».
- L'état `loading` / `error` par étape est exposé par `useActionPlanStore` pour permettre à `StepCard.vue` d'afficher un spinner localisé.

**Alternatives considered** :
- Verrou global (ignorer les clics tant qu'un fetch est en cours) : trop restrictif sur 100 étapes.
- Re-fetch complet à chaque erreur : casse l'expérience optimiste et coûte du réseau.

## R4 — URL filters parsing

**Decision** : Parser les filtres URL **côté client uniquement** dans `useActionPlanFilters.ts`. Le SSR rend la liste sans filtre appliqué ; l'hydratation applique les filtres validés.

**Rationale** :
- FR-007 exige qu'une query string invalide ne casse pas le SSR.
- Les filtres sont appliqués sur des données déjà chargées en mémoire (filtrage client), donc leur application au SSR n'apporte aucun bénéfice.
- Le parser :
  - `priority` ∈ {`haute`, `moyenne`, `basse`} (sinon ignoré),
  - `status` ∈ {`todo`, `doing`, `done`, `postponed`} (sinon ignoré),
  - `horizon` ∈ {`6`, `12`, `24`} (sinon ignoré),
  - `responsible` = UUID validé syntaxiquement (sinon ignoré).
- Sérialisation : un objet vide produit une URL sans query string (clean URL) ; l'ordre des clés est stable pour faciliter les liens partagés.
- Multi-valeurs : `priority=haute,moyenne` est supporté (split par virgule), permet le filtre OR sur une dimension.

**Alternatives considered** :
- `vue-router` query reactivity directe : couplée à des plugins lourds, alors qu'une simple lecture/écriture suffit ici.
- Filtres en `localStorage` : casse le partage de lien, indésirable.

## R5 — Cohabitation avec F44 (CardActionPlan dans le dashboard)

**Decision** : Modifier la `components/dashboard/CardActionPlan.vue` (livrée par F44) pour qu'elle **lise le store `useActionPlanStore`** au lieu de fetcher en propre. Le store devient la source unique de vérité pour le plan courant côté UI.

**Rationale** :
- Cohérence garantie entre la mini-card du dashboard et la page complète : cocher une étape sur `/plan-action` met instantanément à jour la mini-card du dashboard, et inversement.
- Évite double fetch quand l'utilisateur navigue dashboard → plan-action.
- Le store applique sa stratégie de cache (60 s, comme `useDashboardStore`) ; en cas de cache hit, l'ouverture de `/plan-action` est instantanée.
- F44 reste fonctionnellement intacte côté backend : la mini-card consomme toujours `GET /me/action-plan` indirectement via le store.

**Alternatives considered** :
- Garder deux fetchers séparés : risque de désynchronisation visuelle (cocher sur une page, pas reflété sur l'autre tant que le polling de F44 ne tourne pas).
- Centraliser dans `useDashboardStore` : viole la séparation de domaines (action plan ≠ dashboard summary).

## R6 — Régénération anti double-clic

**Decision** : Le bouton « Régénérer » émet un flag `regenerating: true` dans le store dès le clic confirmé dans la modale ; ce flag désactive (`disabled`) le bouton et bloque toute nouvelle ouverture de modale tant qu'il n'est pas levé (à la résolution succès **ou** échec).

**Rationale** :
- Couvre l'edge case « régénération concurrente » du spec.
- Pattern identique à `ExportButton.vue` livré par F44 (anti double-clic export JSON).
- Pas besoin de debounce serveur : F31 est idempotent côté DB (versionnement) mais consommer 2 requêtes coûte LLM.

**Alternatives considered** :
- Désactiver le bouton sans flag store : casse si la modale est rouverte par navigation arrière.

## R7 — Synchronisation EventBus chat ↔ plan-action

**Decision** : Réutiliser le composable existant `useChatEventBus.ts` (F41). Souscrire à `entity_updated` filtré sur `entity_type === 'action_step'`. Sur réception, le store **invalide** la step ciblée (`steps.set(id, refetched)`) et émet sur le bus un event `action_step:invalidated` consommé par les autres surfaces (mini-card dashboard, listes ouvertes ailleurs).

**Rationale** :
- Pattern identique à F44 (`dashboard:action_step_completed`).
- Granularité fine : pas de re-fetch global du plan, on appelle `GET /me/action-plan` filtré ? Non, F31 ne supporte pas le filtre par step_id : on re-fetch le plan complet et on remplace **uniquement** la step changée dans le store. Coût acceptable (1 plan ≤ 100 steps, < 10 KB JSON).
- Inversement, toute mutation locale (cocher, éditer, régénérer) émet un event sur le bus pour que le chat ouvert puisse invalider son contexte LLM (P8).

**Alternatives considered** :
- SSE dédié : surdimensionné pour un MVP avec un seul utilisateur par session.
- WebSocket : pas justifié.

## R8 — Réutilisation des primitives F37/F39/F40

**Decision** : Inventaire strict des primitives existantes :

| Besoin UI | Primitive existante |
|---|---|
| Card étape | `<UiCard>` (F37) |
| Chip statut / priorité | `<UiBadge>` (F37) |
| Bouton checkbox | `<UiCheckbox>` (F37) |
| Bouton primaire / secondaire | `<UiButton>` (F37) |
| Skeleton chargement | `<UiSkeleton>` (F37) |
| Empty state | `<UiEmptyState>` (F37) |
| Bottom sheet édition statut | `<ChatBottomSheet>` + `<ShowForm>` (F39) |
| Modale régénération | `<ChatBottomSheet>` en mode modal centré (F39) ou nouveau `<UiModal>` si pas livré → vérifier en Phase 2 |
| Pin source indicateur | `<VizSourcePin>` (F40) |

**Rationale** : zéro nouvelle dépendance UI. Si `<UiModal>` n'existe pas dans F37 (à vérifier au moment des tasks), réutiliser `<ChatBottomSheet>` avec un mode `display="modal"` (déjà supporté).

## R9 — Rôles et autorisations

**Decision** : La page est accessible uniquement à un utilisateur `role=PME` connecté sur son tenant. La middleware d'auth Nuxt déjà en place (F42) couvre ce cas. Aucun rôle Admin n'a accès à cette page (les Admins consultent les plans via les routes admin séparées, hors scope F45).

**Rationale** : aligné avec la constitution P7 (pas d'intermédiaires) et avec le routage existant.

## R10 — Internationalisation

**Decision** : Toutes les chaînes vivent dans `frontend/app/locales/fr.ts` sous le namespace `planAction.*`. Sous-namespaces : `planAction.title`, `planAction.filters.*`, `planAction.statuses.*`, `planAction.priorities.*`, `planAction.empty.*`, `planAction.regenerate.*`, `planAction.history.*`, `planAction.errors.*`.

**Rationale** : aligné sur le pattern F38/F42/F43/F44 ; la traduction anglaise est hors scope MVP (constitution).

## R11 — Tests E2E : seed data

**Decision** : Réutiliser le helper Playwright `seedPmeWithActionPlan(page, { stepsCount, withScoring, withGaps })` à créer dans `frontend/tests/e2e/helpers/seed-action-plan.ts` (calque sur les helpers F44 `seedPmeWithSummary`). Le seed appelle directement les routes backend (login → POST scoring → POST action-plan/generate).

**Rationale** : pas de mock côté frontend ; les E2E s'exécutent contre un backend réel sur Postgres dockerisé (constitution dev-loop).

## R12 — Performance LCP

**Decision** : Le SSR Nuxt sert immédiatement la coquille (header, skeleton timeline, skeleton liste). Le fetch `GET /me/action-plan` se déclenche dans `onMounted` (client-side) pour ne pas allonger le TTFB. Sur cache hit (60 s, store partagé avec F44), le rendu est instantané.

**Rationale** :
- LCP < 1,5 s p95 (NFR-001) atteint en pratique : la coquille squelettée est < 200 ms, les données ≤ 800 ms (réseau 4G + payload < 10 KB).
- Filtrage 100 % client garantit < 50 ms (NFR-002).

**Alternatives considered** :
- SSR + fetch en pré-rendu : casse RLS (le SSR Nuxt n'a pas le JWT du user en mode prod sans relayage explicite, déjà résolu pour `/dashboard` mais conservé inchangé pour rester cohérent F44).

## Synthèse

Toutes les inconnues techniques sont levées. La feature ne nécessite aucun nouveau service, aucune nouvelle bibliothèque, aucune migration DB. L'effort est essentiellement UI Vue + tests vitest/Playwright.
