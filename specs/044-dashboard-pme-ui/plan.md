# Implementation Plan: Dashboard PME UI (F44)

**Branch**: `044-dashboard-pme-ui` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/044-dashboard-pme-ui/spec.md`

## Summary

Brancher la **page d'accueil PME** (`/dashboard`) — aujourd'hui un stub livré par F38 — sur le backend F32 déjà déployé (`GET /me/dashboard/summary`, `GET /me/data/export`). La feature est **strictement frontend** : aucun nouvel endpoint backend, aucune migration, aucune nouvelle table.

Elle ajoute :

- 1 page Nuxt enrichie (`pages/dashboard.vue`) + une famille de composants `components/dashboard/*` : bandeau d'accueil, six cartes principales (Scoring ESG, Empreinte carbone, Score crédit, Candidatures, Rapports & attestations, Plan d'action), une carte secondaire (Intermédiaires recommandés) et un bouton d'export en haut à droite.
- 1 store Pinia `useDashboardStore` (cache 60 s, état d'erreur par bloc, refresh manuel + automatique).
- 1 composable `useDashboardSummary` (fetch initial, polling 60 s, écoute EventBus chat pour invalidation ciblée par bloc).
- 1 composable `useDataExport` (déclenche le téléchargement, gère le double-clic, nomme le fichier).
- 1 mutation isolée : `PATCH /me/action-plan/steps/{id}` (existant côté F31, livré par cette UI au point de friction "cocher une étape depuis la carte plan d'action").
- Réutilisation **maximale** des primitives `components/viz/*` (VizKPICard, VizRadarChart, VizLineChart, VizGaugeChart, VizLeafletMap) déjà livrées par F40, et `components/ui/*` (UiCard, UiSkeleton, UiButton, UiBadge, UiEmptyState) livrés par F37.
- Branchement EventBus chat ↔ dashboard : à la réception d'un tool result mutation côté chat (ex. nouveau scoring calculé, étape de plan d'action complétée par le LLM), invalidation ciblée du bloc concerné dans `useDashboardStore`.

La page redirige toujours vers `EmptyStateLanding` (F42) si le profil entreprise est < 50 % complété — ce comportement est **conservé tel quel** ; au-delà de 50 %, le nouveau dashboard 6 cartes prend le relais.

## Technical Context

**Language/Version**: TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **lecture seule**).
**Primary Dependencies**:
- Frontend (déjà installés en F36–F43) : Nuxt 4, Pinia, Tailwind v4, gsap (animation des skeleton et de la carte plan d'action), `decimal.js` (P5 Money — déjà introduit en F43), Leaflet (déjà installé via F40 pour `VizLeafletMap`), composables existants `useChatEventBus`, `useMoneyFormat`, `useToast`, `useReducedMotion`, `useT`, `useEntrepriseProfile` (lecture du nom commercial pour le bandeau).
- Backend : aucune nouvelle dépendance.
**Storage**: PostgreSQL 16 + pgvector (déjà). Tables consommées en lecture via les routes F32 : `entreprises`, `scores`, `carbon_footprints`, `credit_scores`, `candidatures`, `rapports`, `attestations`, `action_plan_steps`. Table mutée : `action_plan_steps` (PATCH d'une seule ligne via route F31 existante). Aucune nouvelle table.
**Testing**:
- Frontend : vitest pour `useDashboardStore`, `useDashboardSummary`, `useDataExport`, `mapSummaryToCardViewModels.ts` ; `@vue/test-utils` pour `WelcomeStrip.vue`, `CardScoring.vue`, `CardCarbon.vue`, `CardCredit.vue`, `CardCandidatures.vue`, `CardRapports.vue`, `CardActionPlan.vue`, `CardIntermediaires.vue`, `EmptyCardCTA.vue`.
- E2E : Playwright (`frontend/tests/e2e/`) — parcours complets : (a) PME pleine de données → 6 cartes affichées + clics navigation, (b) compte vierge → CTA d'invitation sur chaque carte, (c) cocher une étape → carte rafraîchie, (d) export JSON téléchargé, (e) double-clic export bloqué, (f) sync chat → carte ESG mise à jour, (g) erreur réseau sur 1 carte → 5 autres restent fonctionnelles. Réutilise la base configurée en F38.
- Backend : aucun nouveau test — les tests F32 (`backend/tests/dashboard/`) restent valides.
**Target Platform**: Web responsive — desktop ≥ 1366×768 (six cartes above-the-fold en grille 3×2), tablette 768–1365 px (grille 2×3), mobile < 768 px (cartes empilées 1 colonne).
**Project Type**: Web application (Nuxt 4 frontend + FastAPI backend).
**Performance Goals**:
- LCP `/dashboard` < 1,5 s p95 sur connexion 4G typique avec `summary` réel (SC-001).
- Première peinture des squelettes < 200 ms (SSR + hydratation).
- Mutation cocher étape → carte rafraîchie < 1 s p95 (SC-006).
- Export JSON début download < 5 s p95 (SC-005).
- Polling : 1 requête `summary` toutes les 60 s tant que l'onglet est focus (visibility API), 0 quand l'onglet est en arrière-plan.
- Mobile : scroll 60 fps sur cartes empilées (SC-008).
**Constraints**:
- **P5 Money typé** : tous les montants venant de `summary.credit_score` et `summary.candidatures` sont reçus en string `Decimal` côté JSON et formatés via `useMoneyFormat` (XOF par défaut). Aucune arithmétique `Number` côté UI.
- **P8 Sync bidirectionnelle** : la carte plan d'action est l'**unique** mutation de cette feature. Elle déclenche immédiatement (a) un PATCH backend, (b) un re-fetch du bloc `next_actions` de `summary`, (c) une émission `dashboard:action_step_completed` sur `useChatEventBus` pour que tout chat ouvert invalide son contexte. Inversement, à réception d'un event chat (`scoring:computed`, `carbon:computed`, `credit:computed`, `attestation:emitted`, `rapport:generated`, `candidature:status_changed`, `action_step:completed`), `useDashboardStore` invalide le bloc concerné et déclenche un re-fetch ciblé (pas de re-fetch global).
- **Cloisonnement multi-tenant** : déjà imposé côté backend par RLS (P2). Le front se contente d'appeler `/me/dashboard/summary` et `/me/data/export` qui dérivent l'`account_id` du JWT.
- **a11y WCAG 2.1 AA** : titres de carte en `<h2>`, statut de chargement annoncé via `aria-busy`, erreurs annoncées via `role="alert"`, lien "voir tout" focusable au clavier, contraste AA respecté.
- **Source clickable (P1)** : pour chaque chiffre ESG (score, sous-scores, émissions), un badge `<VizSourcePin>` (existant) ouvre la liste des `source_id` ayant servi au calcul. La donnée `sources_by_indicator` est déjà retournée par F32 via le bloc `scores[*]` et `carbon[*]` (cf. data-model).
- Hébergement Europe / Afrique de l'Ouest (constitution) — inchangé.
- Langue : français par défaut (clés ajoutées dans `frontend/app/locales/fr.ts`).
**Scale/Scope**: 1 page enrichie + ~13 composants nouveaux + 1 store + 2 composables + 1 helper de mapping. ~700–1000 LOC frontend nouvelles. Volume utilisateur : MVP — quelques centaines de PME pendant la phase pilote, ~1 dashboard ouvert par session.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Pas de donnée factuelle ESG fabriquée par l'UI ; les chiffres viennent de F23 (scoring) / F28 (carbone) / F29 (crédit) où `source_id` est déjà imposé. La carte ESG affiche un `<VizSourcePin>` cliquable (FR-015). | ✅ |
| P2 | Multi-tenant RLS | Routes consommées (`/me/dashboard/summary`, `/me/data/export`, `/me/action-plan/steps/{id}`) appliquent déjà RLS via `account_id` dérivé du JWT. Le front ne fabrique aucune requête SQL. | ✅ |
| P3 | Audit log append-only | La seule mutation (`PATCH /me/action-plan/steps/{id}`) écrit déjà dans `audit_log` côté backend (F31) avec `source_of_change='manual'`. La consultation du dashboard logue aussi un audit `dashboard_view` côté F32. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de candidature soumise ni de référentiel modifié ici. La carte candidatures affiche les statuts agrégés ; aucun snapshot n'est touché. | ✅ N/A |
| P5 | Money typé | Les montants (score crédit méthodologie, valeurs candidatures éventuelles) sont reçus en `Decimal` (string JSON) et formatés via `useMoneyFormat`. Aucune arithmétique `Number`. | ✅ |
| P6 | Pivot Indicateur unique | Aucune donnée ESG n'est saisie. La carte ESG affiche le score global + une projection radar 3 axes — la projection est déjà calculée backend (vue), pas dupliquée. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucune route, aucun rôle nouveau. La carte "Intermédiaires recommandés" affiche une lecture seule de la table catalogue, sans webhook ni partage automatique. | ✅ |
| P8 | Édition manuelle + sync LLM | C'est précisément l'objet de FR-010 / FR-017 (cocher étape + sync temps réel). La mutation manuelle invalide le contexte LLM côté backend (cascade existante F31) ; les mutations chat sont propagées via `useChatEventBus` → re-fetch ciblé. La DB reste source de vérité. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM dans cette feature. Les tools existants (`compute_score_*`, `complete_action_step`…) émettent déjà les events chat consommés ici. | ✅ N/A |
| P10 | UX bottom sheet | La feature est **hors flux chat** : pas de bulle LLM, pas d'input dans une bulle. La seule interaction sur les cartes est un clic checkbox (cocher étape) — composant simple, pas un input texte ; le pattern bottom sheet ne s'applique pas. Le bouton "Discuter avec l'IA" du bandeau renvoie vers `/chat` (F41) où le pattern bottom sheet est déjà respecté. | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓ (existant inchangé).
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450 — l'export `/me/data/export` est précisément la matérialisation du droit à la portabilité (RGPD art. 20).
- Langue : français par défaut ✓.

## Project Structure

### Documentation (this feature)

```text
specs/044-dashboard-pme-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (polling vs SSE, mapping summary, EmptyStateLanding cohabitation, mini-charts perf)
├── data-model.md        # Phase 1 — ViewModels UI dérivés de DashboardSummaryOut + entités cartes
├── quickstart.md        # Phase 1 — comment tester localement de bout en bout
├── contracts/
│   ├── frontend-api-consumption.md   # Contrats des endpoints consommés (entrées/sorties UI)
│   ├── frontend-components.md        # Contrats des composants/composables nouveaux
│   └── chat-eventbus-sync.md         # Contrat d'évènements chat ↔ dashboard (invalidations ciblées)
├── checklists/
│   └── requirements.md               # Spec quality checklist (déjà créée)
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/                                    # AUCUNE MODIFICATION dans cette feature.
└── app/
    ├── dashboard/                         # F32 — déjà déployé
    │   ├── router.py                      # GET /me/dashboard/summary, GET /me/data/export (utilisés)
    │   ├── service.py                     # build_summary, build_export (utilisés)
    │   └── schemas.py                     # DashboardSummaryOut, DataExportOut (référence pour le mapping)
    └── action_plan/                       # F31 — déjà déployé
        └── router.py                      # PATCH /me/action-plan/steps/{id} (utilisé pour US2)

frontend/
├── app/
│   ├── pages/
│   │   └── dashboard.vue                  # MODIFIE — passe de stub à dashboard 6 cartes (conserve EmptyStateLanding < 50 %)
│   ├── components/
│   │   ├── dashboard/                     # NEW — famille dashboard
│   │   │   ├── WelcomeStrip.vue           # bandeau salutation + raison sociale + dernière maj + bouton "Discuter avec l'IA"
│   │   │   ├── DashboardGrid.vue          # grille responsive 3×2 / 2×3 / 1×6
│   │   │   ├── CardScoring.vue            # carte scores ESG (score global + mini-radar)
│   │   │   ├── CardCarbon.vue             # carte empreinte carbone (KPI tCO2e + mini line-chart 4 trim)
│   │   │   ├── CardCredit.vue             # carte score crédit (gauge 0-100 + badge éligibilité)
│   │   │   ├── CardCandidatures.vue       # compteurs par statut + 3 dernières
│   │   │   ├── CardRapports.vue           # 3 derniers rapports + 2 attestations actives QR mini
│   │   │   ├── CardActionPlan.vue         # 3 prochaines étapes + checkbox cocher
│   │   │   ├── CardIntermediaires.vue     # mini Leaflet 3 pins (P2)
│   │   │   ├── CardSkeleton.vue           # skeleton générique réutilisable par toutes les cartes
│   │   │   ├── CardErrorState.vue         # état erreur avec bouton "Réessayer" (FR-020)
│   │   │   ├── EmptyCardCTA.vue           # appel à l'action pour carte vide (FR-012)
│   │   │   └── ExportButton.vue           # bouton "Exporter mes données" + anti double-clic
│   │   ├── viz/                           # primitives existantes (VizKPICard, VizRadarChart, VizLineChart, VizGaugeChart, VizLeafletMap, VizSourcePin) — F40
│   │   └── ui/                            # primitives existantes (UiCard, UiSkeleton, UiButton, UiBadge, UiEmptyState) — F37
│   ├── composables/
│   │   ├── useDashboardSummary.ts         # NEW — fetch + polling 60 s + visibility API + EventBus invalidation
│   │   ├── useDataExport.ts               # NEW — déclenche download, génère nom de fichier, anti double-clic
│   │   ├── useChatEventBus.ts             # EXISTANT — utilisé pour invalidations ciblées
│   │   ├── useMoneyFormat.ts              # EXISTANT — formatage Decimal → XOF/EUR/USD
│   │   ├── useEntrepriseProfile.ts        # EXISTANT — pour récupérer la raison sociale du bandeau
│   │   └── useT.ts                        # EXISTANT — i18n
│   ├── stores/
│   │   └── dashboard.ts                   # NEW — état summary + cache 60 s + invalidations ciblées par bloc
│   ├── lib/
│   │   └── mapSummaryToCardViewModels.ts  # NEW — adapter pur DashboardSummaryOut → ViewModels par carte
│   ├── locales/
│   │   └── fr.ts                          # MODIFIE — ajout des clés dashboard
│   └── assets/css/main.css                # éventuelles classes utilitaires (sinon inchangé)
└── tests/
    ├── unit/
    │   ├── composables/
    │   │   ├── useDashboardSummary.test.ts
    │   │   └── useDataExport.test.ts
    │   ├── stores/
    │   │   └── dashboard.test.ts
    │   └── lib/
    │       └── mapSummaryToCardViewModels.test.ts
    ├── components/
    │   └── dashboard/
    │       ├── WelcomeStrip.test.ts
    │       ├── CardScoring.test.ts
    │       ├── CardCarbon.test.ts
    │       ├── CardCredit.test.ts
    │       ├── CardCandidatures.test.ts
    │       ├── CardRapports.test.ts
    │       ├── CardActionPlan.test.ts
    │       ├── CardIntermediaires.test.ts
    │       ├── EmptyCardCTA.test.ts
    │       ├── CardErrorState.test.ts
    │       └── ExportButton.test.ts
    └── e2e/
        ├── dashboard-full-data.spec.ts
        ├── dashboard-empty-account.spec.ts
        ├── dashboard-action-plan-toggle.spec.ts
        ├── dashboard-export.spec.ts
        ├── dashboard-export-double-click.spec.ts
        ├── dashboard-chat-sync.spec.ts
        └── dashboard-card-failure-isolation.spec.ts
```

**Structure Decision**: Application web mono-repo Nuxt 4 + FastAPI déjà en place ; cette feature ne touche que `frontend/app/`. Le découpage `components/dashboard/*` reflète la frontière de domaine UI (page d'accueil PME) sans empiéter sur `components/chat/*` (timeline LLM) ni sur `components/profil/*` (édition profil F43). Les primitives de visualisation (`components/viz/*`) sont **réutilisées telles quelles** depuis F40 ; aucune nouvelle bibliothèque graphique n'est introduite. Les tests sont structurés en `unit/` (composables, store, lib), `components/` (composants Vue), `e2e/` (Playwright) — héritage F38/F42/F43.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Tableau vide.
