# Implementation Plan: Plan d'action ESG UI (F45)

**Branch**: `045-plan-action-ui` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/045-plan-action-ui/spec.md`

## Summary

Livrer la page **`/plan-action`** : UI dédiée à la feuille de route ESG d'une PME, branchée sur le backend **F31** déjà déployé (`POST /me/action-plan/generate`, `GET /me/action-plan`, `PATCH /me/action-plan/steps/{id}`). Strictement **frontend** : aucun nouvel endpoint, aucune migration, aucune nouvelle table.

La feature ajoute :

- 1 page Nuxt `pages/plan-action/index.vue` avec deux vues synchronisées : timeline horizontale (par horizon 3/6/12/24 mois, gsap stagger 80 ms, bascule verticale < 768 px) + liste de cards filtrables / triables.
- 1 famille de composants `components/plan-action/*` : `TimelineHorizontal.vue`, `StepCard.vue`, `StepFilters.vue`, `EditStatusSheet.vue`, `RegenerateModal.vue`, `HorizonToggle.vue`, `ProgressHeader.vue`, `EmptyNoScoring.vue`, `EmptyNoGaps.vue`, `HistoryDrawer.vue` (P2), `ExportPlanButton.vue` (P2).
- 1 store Pinia `useActionPlanStore` (currentPlan, version, steps, filters, horizon vue, loading/error par étape, anti double-clic régénération).
- 3 composables : `useActionPlan` (fetch + EventBus chat), `useActionPlanFilters` (parse/serialize URL query), `useActionPlanCompletion` (KPI `done / total` réactif au filtre horizon).
- 1 helper de mapping pur `lib/mapPlanToTimelineBuckets.ts` (regroupe les étapes par bucket d'horizon : `<3M`, `3-6M`, `6-12M`, `12-24M`, `Sans échéance`).
- Réutilisation **maximale** des primitives F37/F39/F40 : `<UiCard>`, `<UiBadge>`, `<UiButton>`, `<UiSkeleton>`, `<UiEmptyState>`, `<UiCheckbox>`, `<ChatBottomSheet>`, `<ShowForm>`, `<VizSourcePin>`. Aucune nouvelle bibliothèque graphique : la timeline est en SVG + divs Tailwind animés via `gsap` (déjà installé).
- Branchement EventBus chat ↔ plan-action (`entity_updated{action_step}`) : à la réception, invalidation **ciblée** d'une seule card (pas de re-fetch global). Inversement, toute mutation locale (cocher étape, édition bottom sheet, régénération) émet un event sur le bus pour notifier les autres surfaces (chat ouvert, dashboard F44).

La page **réutilise** la `CardActionPlan` mini-version livrée par F44 sur `/dashboard` (lien « Voir le plan complet » → `/plan-action`). La cohérence UX est garantie par le partage du store : la `CardActionPlan` du dashboard et la page `/plan-action` lisent le même `useActionPlanStore`.

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **lecture + 1 PATCH existant**).
**Primary Dependencies** :

- Frontend (déjà installés en F36–F44) : Nuxt 4, Pinia, Tailwind v4, gsap (timeline + bottom sheet), `decimal.js` (P5 — non utilisé ici), composables existants `useChatEventBus`, `useChatBottomSheet`, `useToast`, `useReducedMotion`, `useT`, `useEntrepriseProfile`, `useActionStepToggle` (déjà créé en F44 pour la mini-card du dashboard, **étendu** ici pour gérer la file d'attente d'optimistic updates).
- Backend : aucune nouvelle dépendance.

**Storage** : PostgreSQL 16 + pgvector (déjà). Tables consommées en lecture : `action_plans`, `action_plan_steps`, `accounts`, `account_users`, `indicateurs` (pour le lien source de gap), `score_calculations` (pour US7 « pas encore de scoring »). Tables mutées : `action_plan_steps` (PATCH d'une seule ligne, route F31 existante) et `action_plans` (POST regenerate, route F31 existante). Aucune nouvelle table, aucune migration.

**Testing** :

- Frontend (vitest + `@vue/test-utils`) — unit : `useActionPlanStore.test.ts`, `useActionPlan.test.ts`, `useActionPlanFilters.test.ts`, `useActionPlanCompletion.test.ts`, `mapPlanToTimelineBuckets.test.ts`. Composants : `TimelineHorizontal.test.ts`, `StepCard.test.ts`, `StepFilters.test.ts`, `EditStatusSheet.test.ts`, `RegenerateModal.test.ts`, `HorizonToggle.test.ts`, `ProgressHeader.test.ts`, `EmptyNoScoring.test.ts`, `EmptyNoGaps.test.ts`.
- E2E (Playwright, `frontend/tests/e2e/`) : (a) plan plein → timeline + liste affichées en < 2 s, (b) filtre `?priority=haute` → URL persistée + résultat, (c) cocher étape optimiste + rollback sur erreur 500 simulée, (d) régénération → version v+1 visible, (e) double-clic régénération bloqué, (f) sync chat → carte mise à jour, (g) empty state pas de scoring → CTA `/scoring`, (h) empty state pas de gaps → message célébration, (i) bascule horizon `6 mois` → sous-ensemble visible, (j) `prefers-reduced-motion` → pas d'animation.
- Backend : aucun nouveau test (les tests F31 `backend/tests/action_plan/` restent valides ; on s'appuie sur le contrat OpenAPI déjà figé).

**Target Platform** : Web responsive — desktop ≥ 1366×768 (timeline horizontale + grille 2 colonnes pour la liste), tablette 768–1365 px (timeline horizontale compacte + liste 1 colonne), mobile < 768 px (timeline **verticale** empilée + liste 1 colonne).

**Project Type** : Web application (Nuxt 4 frontend + FastAPI backend).

**Performance Goals** :

- LCP `/plan-action` < 1,5 s p95 sur 4G typique avec 50 étapes (NFR-001 du brief, SC-001 du spec).
- Filtrage client < 50 ms pour 100 étapes (NFR-002, SC-003).
- Mutation cocher → UI reflète le changement < 100 ms (optimistic), confirmation serveur < 1 s p95 (SC-002).
- Régénération : début spinner < 100 ms, fin (nouveau plan affiché) selon backend F31 (typiquement 2-5 s, hors scope UI).
- Animations : stagger gsap 80 ms (= ~16 jalons en < 1,3 s), désactivation totale si `prefers-reduced-motion: reduce`.

**Constraints** :

- **P8 Sync bidirectionnelle** : la mise à jour optimiste DOIT être réversible (rollback complet UI + barre de progression + KPI) sur échec backend. La file d'attente d'optimistic updates (édge case « cocher pendant fetch en cours ») applique les mutations séquentiellement par `step_id`.
- **P10 UX bottom sheet** : tout input (sélecteur statut, sélecteur responsable, sélecteur horizon de régénération) vit dans un bottom sheet ou modal. Aucun `<input>`/`<select>` inline dans une card. La checkbox reste autorisée (composant simple, pas un input texte).
- **P1 Sourcing** : chaque card affiche un `<VizSourcePin>` lié à l'`indicateur_id` source ; clic ouvre la fiche indicateur (route `/scoring/indicateurs/{id}` existante depuis F23).
- **P2 RLS multi-tenant** : déjà imposé côté backend. Aucun ID utilisateur ne fuit vers le client en dehors du tenant courant.
- **a11y WCAG 2.1 AA** : titres de section en `<h2>`, `aria-busy` sur cards en chargement, `role="alert"` pour erreurs, navigation clavier complète sur la liste (Tab → card → checkbox → bouton modifier), focus trap dans bottom sheet (déjà fourni par `<ChatBottomSheet>`).
- **URL filters** : query string parsée côté **client** uniquement ; le SSR sert la page sans filtre appliqué pour ne pas casser sur query invalide (FR-007). Hydratation applique les filtres validés.
- Hébergement Europe / Afrique de l'Ouest (constitution) — inchangé.
- Langue : français par défaut (clés ajoutées dans `frontend/app/locales/fr.ts` sous le namespace `planAction.*`).

**Scale/Scope** : 1 page nouvelle + ~12 composants nouveaux + 1 store + 3 composables + 1 helper de mapping. ~900–1200 LOC frontend nouvelles. Volume utilisateur : MVP — quelques centaines de PME pendant la phase pilote, ~1 plan ouvert par session, plans contenant 5 à 30 étapes typiquement (cap théorique 100).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée fabriquée par l'UI ; les étapes proviennent du générateur F31 où chaque step est liée à un `indicateur_id` (gap source) et chaque indicateur porte un `source_id`. La card affiche `<VizSourcePin>` cliquable (FR-008, FR-025). | ✅ |
| P2 | Multi-tenant RLS | Routes consommées (`GET /me/action-plan`, `PATCH /me/action-plan/steps/{id}`, `POST /me/action-plan/generate`) appliquent déjà RLS via `account_id` dérivé du JWT. Cross-tenant → 404 (testé F31). Le front ne fabrique aucune requête SQL. | ✅ |
| P3 | Audit log append-only | La mutation `PATCH /me/action-plan/steps/{id}` écrit déjà dans `audit_log` côté backend (F31) avec `source_of_change='manual'`. La régénération écrit aussi un audit. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de candidature ici. Les **plans** sont versionnés (`version` int croissant, ancien plan conservé) — c'est précisément US5 + US11. | ✅ |
| P5 | Money typé | Pas de montant monétaire dans cette feature. | ✅ N/A |
| P6 | Pivot Indicateur unique | Aucune donnée ESG saisie. La feature affiche les étapes avec un lien (lecture seule) vers l'indicateur source. Pas de duplication par axe E/S/G. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle Banque/Fonds/Intermédiaire. La page est réservée à la PME (rôle PME du tenant). Aucun partage automatique vers un tiers. | ✅ |
| P8 | Édition manuelle + sync LLM | C'est l'objet central de US3, US9, FR-009, FR-010, FR-019. La mutation manuelle invalide le contexte LLM côté backend (cascade existante F31) ; les mutations chat sont propagées via `useChatEventBus` → re-fetch ciblé d'une seule card. La DB reste source de vérité. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM dans cette feature. Les tools existants (`complete_action_step`, `regenerate_action_plan` côté F31/F41) émettent déjà les events chat consommés ici. | ✅ N/A |
| P10 | UX bottom sheet | Tout input riche (édition statut + responsable, choix horizon de régénération) vit dans un bottom sheet ou une modale (FR-011, FR-014). Aucun `<input>` inline dans une card. La checkbox de bascule rapide est un composant simple non-textuel — autorisée par la constitution. Bouton "Répondre librement" non applicable (pas de bulle LLM ici). | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓ (existant inchangé).
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450 — pas d'impact direct ici.
- Langue : français par défaut ✓.

## Project Structure

### Documentation (this feature)

```text
specs/045-plan-action-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (timeline SVG vs flexbox, optimistic queue, URL filter parsing, integration F44 dashboard)
├── data-model.md        # Phase 1 — ViewModels UI dérivés de ActionPlanRead + entités cards/buckets
├── quickstart.md        # Phase 1 — comment tester localement de bout en bout
├── contracts/
│   ├── frontend-api-consumption.md   # Contrats des endpoints F31 consommés (entrées/sorties UI)
│   ├── frontend-components.md        # Contrats des composants/composables nouveaux
│   └── chat-eventbus-sync.md         # Contrat d'évènements chat ↔ plan-action (invalidations ciblées)
├── checklists/
│   └── requirements.md               # Spec quality checklist (déjà créée)
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/                                    # AUCUNE MODIFICATION dans cette feature.
└── app/
    └── action_plan/                       # F31 — déjà déployé
        ├── routes.py                      # POST /generate, GET "", PATCH /steps/{id} (utilisés)
        ├── service.py                     # ActionPlanService (utilisé)
        ├── schemas.py                     # ActionPlanRead, ActionStepRead, ActionStepPatch (référence pour le mapping)
        └── enums.py                       # Category, Priority, StepStatus, Horizon (réutilisés côté UI via types miroir)

frontend/
├── app/
│   ├── pages/
│   │   └── plan-action/
│   │       └── index.vue                  # NEW — page complète (timeline + liste + header progression + actions)
│   ├── components/
│   │   ├── plan-action/                   # NEW — famille plan-action
│   │   │   ├── TimelineHorizontal.vue     # timeline horizontale SVG + jalons stagger gsap (vertical < 768 px)
│   │   │   ├── StepCard.vue               # card étape (titre, desc, prio, horizon, statut, responsable, source pin, checkbox + bouton modifier)
│   │   │   ├── StepFilters.vue            # filtres priorité / statut / horizon / responsable, sync URL
│   │   │   ├── EditStatusSheet.vue        # bottom sheet d'édition (status + responsible_user_id) — encapsule <ChatBottomSheet> + <ShowForm>
│   │   │   ├── RegenerateModal.vue        # modale confirmation régénération avec sélecteur horizon
│   │   │   ├── HorizonToggle.vue          # toggle 6 / 12 / 24 mois (filtre vue, n'altère pas le plan)
│   │   │   ├── ProgressHeader.vue         # barre + KPI X/Y et %
│   │   │   ├── EmptyNoScoring.vue         # empty state US7 avec CTA /scoring
│   │   │   ├── EmptyNoGaps.vue            # empty state US8 célébration
│   │   │   ├── HistoryDrawer.vue          # P2 — drawer versions antérieures lecture seule
│   │   │   └── ExportPlanButton.vue       # P2 — bouton export PDF (flag F51)
│   │   ├── viz/                           # primitives existantes (VizSourcePin) — F40
│   │   ├── ui/                            # primitives existantes (UiCard, UiSkeleton, UiButton, UiBadge, UiCheckbox, UiEmptyState) — F37
│   │   ├── chat/                          # ChatBottomSheet — F39 (réutilisé)
│   │   └── dashboard/
│   │       └── CardActionPlan.vue         # MODIFIE (F44) — lit `useActionPlanStore` au lieu de fetcher en propre + lien "Voir le plan complet" → /plan-action
│   ├── composables/
│   │   ├── useActionPlan.ts               # NEW — fetch GET /me/action-plan + abonnement EventBus + invalidations ciblées
│   │   ├── useActionPlanFilters.ts        # NEW — parse/serialize URL query (priority, status, horizon, responsible)
│   │   ├── useActionPlanCompletion.ts     # NEW — KPI done/total réactif au sous-ensemble filtré par horizon
│   │   ├── useActionStepToggle.ts         # EXISTANT (F44) — étendu avec file d'attente d'optimistic updates
│   │   ├── useChatEventBus.ts             # EXISTANT — abonnement entity_updated{action_step}
│   │   ├── useChatBottomSheet.ts          # EXISTANT — pour piloter le sheet d'édition
│   │   ├── useT.ts                        # EXISTANT — i18n
│   │   ├── useReducedMotion.ts            # EXISTANT — désactivation animations
│   │   └── useToast.ts                    # EXISTANT — feedback erreur rollback
│   ├── stores/
│   │   └── actionPlan.ts                  # NEW — currentPlan + version + steps + filters + horizonView + loading/error par step
│   ├── lib/
│   │   └── mapPlanToTimelineBuckets.ts    # NEW — regroupement par buckets d'horizon (< 3M, 3-6M, 6-12M, 12-24M, Sans échéance)
│   ├── locales/
│   │   └── fr.ts                          # MODIFIE — namespace planAction.* (titres, filtres, statuts, messages, empty states)
│   └── assets/css/main.css                # éventuelles classes utilitaires (sinon inchangé)
└── tests/
    ├── unit/
    │   ├── composables/
    │   │   ├── useActionPlan.test.ts
    │   │   ├── useActionPlanFilters.test.ts
    │   │   └── useActionPlanCompletion.test.ts
    │   ├── stores/
    │   │   └── actionPlan.test.ts
    │   └── lib/
    │       └── mapPlanToTimelineBuckets.test.ts
    ├── components/
    │   └── plan-action/
    │       ├── TimelineHorizontal.test.ts
    │       ├── StepCard.test.ts
    │       ├── StepFilters.test.ts
    │       ├── EditStatusSheet.test.ts
    │       ├── RegenerateModal.test.ts
    │       ├── HorizonToggle.test.ts
    │       ├── ProgressHeader.test.ts
    │       ├── EmptyNoScoring.test.ts
    │       └── EmptyNoGaps.test.ts
    └── e2e/
        ├── plan-action-timeline-render.spec.ts
        ├── plan-action-filter-url.spec.ts
        ├── plan-action-toggle-optimistic.spec.ts
        ├── plan-action-toggle-rollback.spec.ts
        ├── plan-action-edit-sheet.spec.ts
        ├── plan-action-regenerate.spec.ts
        ├── plan-action-regenerate-double-click.spec.ts
        ├── plan-action-horizon-toggle.spec.ts
        ├── plan-action-empty-no-scoring.spec.ts
        ├── plan-action-empty-no-gaps.spec.ts
        ├── plan-action-chat-sync.spec.ts
        └── plan-action-reduced-motion.spec.ts
```

**Structure Decision** : Application web mono-repo Nuxt 4 + FastAPI déjà en place ; cette feature ne touche que `frontend/app/`. Le découpage `components/plan-action/*` reflète la frontière de domaine UI (page feuille de route ESG) sans empiéter sur `components/dashboard/*` (F44, page d'accueil) ni sur `components/chat/*` (timeline LLM, F41). Le store `actionPlan.ts` est partagé : la `CardActionPlan` du dashboard (F44, déjà livrée comme widget statique fetcher-en-propre) sera **modifiée** pour lire ce store, garantissant cohérence et invalidation unique. Les tests sont structurés en `unit/` (composables, store, lib), `components/` (composants Vue), `e2e/` (Playwright) — héritage F38/F42/F43/F44.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Tableau vide.
