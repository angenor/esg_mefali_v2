# Implementation Plan: Scoring ESG visualisations UI (F46)

**Branch**: `046-scoring-esg-ui` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/046-scoring-esg-ui/spec.md`

## Summary

Livrer la page **`/scoring`** (et son sous-chemin `/scoring/[referentiel_code]`) : UI dédiée à la consultation, à la comparaison et au pilotage des scores ESG d'une PME, branchée sur le backend **F23** déjà déployé (`GET /me/scoring/{entity_type}/{entity_id}`, `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}`, `POST /me/scoring/{entity_type}/{entity_id}/recompute`).

La feature est très majoritairement **frontend** mais nécessite **un seul ajout backend ciblé** : un endpoint d'historique `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}/history?limit=12` qui lit la table append-only `score_calculation` (déjà existante, F23) et retourne les N derniers calculs pour un (entity, référentiel) donné. Aucune nouvelle table, aucune migration, aucun nouveau pivot.

La feature ajoute :

- 2 pages Nuxt : `pages/scoring/index.vue` (vue d'ensemble + redirection vers le référentiel par défaut) et `pages/scoring/[referentiel_code].vue` (détail par référentiel) — l'URL refléte le référentiel courant (FR-003, US2).
- 1 famille de composants `components/scoring/*` : `ReferentielTabs.vue`, `ScoreOverview.vue` (radar ou barres si > 6 axes), `PillarAccordion.vue`, `IndicateurRow.vue`, `IndicateurDrawer.vue`, `MissingIndicatorsList.vue`, `RecalcButton.vue`, `CompareButton.vue` + `CompareDrawer.vue`, `HistoryChart.vue`, `SnapshotToggle.vue`, `ExportPdfButton.vue` (P2), `EmptyNoCalculation.vue`, `RevokedSourceBadge.vue`.
- 1 store Pinia `useScoringStore` (par `(entity_id, referentiel_code)` : summary, detail, history, dernière `computed_at`, version référentiel, statuts loading/error, mode snapshot avec `frozen_calculation_id`).
- 4 composables : `useScoring` (orchestration fetch list/detail + abonnement EventBus), `useScoringHistory` (fetch des 12 derniers calculs), `useScoringCompare` (sélection multi-référentiels + agrégation client pour la vue côte à côte), `useIndicateurEdit` (orchestre l'ouverture du bottom sheet `ask_number` et la propagation post-PATCH).
- 1 helper de mapping pur `lib/mapIndicateursByPillar.ts` (groupe `indicateurs_couverts ∪ indicateurs_manquants` par pilier `E/S/G`, ordonne par `contribution` décroissante, marque `covered`/`missing`, signale les sources révoquées).
- 1 helper `lib/scoringEditableIndicateurs.ts` (table de correspondance miroir de `VALUE_SOURCE_MAP` côté backend pour savoir quel indicateur est éditable depuis le drawer en MVP, et via quel champ du profil entreprise — code partagé via constante TS générée à la main, voir research.md).
- Réutilisation **maximale** des primitives F37/F39/F40 : `<UiCard>`, `<UiBadge>`, `<UiButton>`, `<UiSkeleton>`, `<UiEmptyState>`, `<UiPopover>` (pour la pastille source), `<UiModal>` (pour `CompareDrawer` plein-écran si besoin, mais préférence pour un slide-in droit), `<ChatBottomSheet>` + `<ShowForm>` (pour `ask_number`), `<VizRadarChart>`, `<VizBarChart>`, `<VizLineChart>`, `<VizSourcePin>`, `<VizEmptyState>`. Aucune nouvelle bibliothèque graphique — la `viz/` est complète depuis F40.
- Branchement EventBus chat ↔ scoring (`entity_updated{indicateur, score_calculation}`) : à la réception, invalidation **ciblée** du détail du référentiel courant et de l'historique. Inversement, toute modification locale (édition d'un indicateur via le drawer, recalcul) émet l'event correspondant pour mettre à jour les autres surfaces (chat, dashboard F44).

La page **réutilise** la `CardScoringSummary` mini-version livrée par F44 sur `/dashboard` (lien « Voir le scoring complet » → `/scoring`). La cohérence UX est garantie par le partage du store : la mini-card du dashboard et la page `/scoring` lisent le même `useScoringStore`.

Côté backend, l'unique ajout `GET .../history?limit=12` est append-only en lecture, RLS-aware (filtre `account_id`), sans audit (lecture seule) et accompagné de tests `pytest` (unit + integration).

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3 / Nuxt 4 (frontend) ; Python 3.12 (backend, **un seul nouvel endpoint en lecture**).

**Primary Dependencies** :

- Frontend (déjà installés en F36–F45) : Nuxt 4, Pinia, Tailwind v4, gsap (animations radar/drawer), `chart.js` (déjà utilisé par `viz/`), `decimal.js` (P5 — pour seuils financiers éventuels affichés). Composables existants `useChatEventBus`, `useChatBottomSheet`, `useToast`, `useReducedMotion`, `useT`, `useEntrepriseProfile`, `useAuth`, `useSourceFetch`, `useDecimal`, `useMoneyFormat`, `useChartTheme`.
- Backend : aucune nouvelle dépendance Python ; on s'appuie sur SQLAlchemy + Pydantic v2 déjà présents.

**Storage** : PostgreSQL 16 + pgvector (déjà). Tables consommées en lecture : `score_calculation` (append-only, F23), `referentiel`, `indicateur`, `source` (catalogue, F09), `entreprise` (F11) pour le mapping value-source. Tables mutées : `entreprise` (PATCH champ ciblé via la route F11 existante `/me/entreprise`) et `score_calculation` (INSERT via le `recompute` F23 existant). **Aucune nouvelle table, aucune migration.**

**Testing** :

- Frontend (vitest + `@vue/test-utils`) — unit : `useScoringStore.test.ts`, `useScoring.test.ts`, `useScoringHistory.test.ts`, `useScoringCompare.test.ts`, `useIndicateurEdit.test.ts`, `mapIndicateursByPillar.test.ts`, `scoringEditableIndicateurs.test.ts`. Composants : `ReferentielTabs.test.ts`, `ScoreOverview.test.ts` (radar/bars switch ≥ 7 axes), `PillarAccordion.test.ts`, `IndicateurRow.test.ts`, `IndicateurDrawer.test.ts`, `MissingIndicatorsList.test.ts`, `RecalcButton.test.ts`, `CompareDrawer.test.ts`, `HistoryChart.test.ts`, `SnapshotToggle.test.ts`, `EmptyNoCalculation.test.ts`, `RevokedSourceBadge.test.ts`.
- E2E (Playwright, `frontend/tests/e2e/`) : (a) ouverture `/scoring` avec calcul existant → score + radar + couverture < 2 s, (b) bascule onglet `BOAD → CDP` met à jour l'URL en `/scoring/cdp` et la donnée < 200 ms si cache, (c) drilldown pilier `Environnement` puis ouverture drawer `Émissions GES` → graphique linéaire 12 mois, (d) édition d'un indicateur mappé via bottom sheet `ask_number` → score recalculé visible sans rechargement, (e) édition d'un indicateur **non mappé** → message explicite empêchant la soumission, (f) comparaison `BOAD ↔ CDP` → barres horizontales côte à côte, (g) clic sur indicateur manquant `Compléter` → ouverture du chat contextuel, (h) clic `Recalculer` → spinner puis nouveau résultat + nouvelle date, (i) source révoquée → badge avertissement + valeur grisée, (j) toggle snapshot → mode lecture seule, `Modifier` et `Recalculer` désactivés, (k) sortie du snapshot → état courant, (l) sync chat → drawer indicateur ouvert se met à jour, (m) état vide pas de calcul → CTA `Lancez votre premier diagnostic`, (n) `prefers-reduced-motion` → animations désactivées, (o) navigation directe vers un référentiel inconnu → message d'erreur + retour à la liste.
- Backend (`backend/tests/scoring/`) — un seul nouveau fichier `test_history_endpoint.py` : (1) compte sans calcul → 200 + liste vide, (2) compte avec 3 calculs → ordre desc par `computed_at`, (3) compte avec 15 calculs → limit=12 par défaut, limit=5 respecté, (4) cross-tenant (autre `account_id`) → 404, (5) `entity_type` invalide → 404, (6) référentiel inconnu → 404. Aucune autre route F23 modifiée.

**Target Platform** : Web responsive — desktop ≥ 1366×768 (radar + 2 colonnes pour la liste indicateurs et le drawer slide-in droit largeur 480 px), tablette 768–1365 px (radar + colonne unique + drawer 80 % largeur), mobile < 768 px (radar **réduit** + accordéon vertical + drawer plein écran avec bouton fermer en haut).

**Project Type** : Web application (Nuxt 4 frontend + FastAPI backend). Mono-repo existant.

**Performance Goals** :

- LCP `/scoring` < 2 s p95 sur 4G typique pour un référentiel à 50+ indicateurs (NFR-001 brief, SC-001 spec).
- Switch onglet référentiel (cache hit) < 200 ms (NFR-002, SC-002).
- Drilldown accordéon : ouverture < 100 ms même pour 30+ indicateurs (NFR-003, SC-008). Si > 30 indicateurs : pas de virtualisation au MVP, mais une optimisation `v-show` sur les rows non-visibles + chargement progressif des graphiques de drawer en lazy (`<VizLineChart>` créé seulement à l'ouverture du drawer).
- Mutation indicateur → vue d'ensemble rafraîchie sans rechargement complet en < 1,5 s p95 (recompute backend + invalidation store).
- Recalcul à la demande : début spinner < 100 ms ; fin selon backend F23 (typiquement < 3 s, hors scope UI).
- Animations : radar gsap fade-in 200 ms, drawer slide-in 250 ms, désactivés si `prefers-reduced-motion: reduce`.

**Constraints** :

- **P1 Sourcing** : chaque score affiché (global, pilier, indicateur) DOIT exposer une pastille `<VizSourcePin>` cliquable pointant vers la `Source` `verified` correspondante via `source_id` (déjà fourni par `CoveredIndicatorOut`). Indicateur sans `source_id` ou source révoquée → badge avertissement + valeur grisée (`<RevokedSourceBadge>`, FR-002, FR-017).
- **P4 Versioning** : la version du référentiel utilisée à chaque calcul est lue depuis `referentiel_version` de `ScoreSummaryOut` ; affichée dans l'en-tête, dans l'historique au survol, et dans l'export PDF. Snapshot mode = freeze sur un `score_calculation_id` historique → la vue rend l'état tel qu'il était au moment du calcul, sans ré-interrogation autre que la lecture du calcul figé.
- **P6 Pivot Indicateur unique** : la page lit les valeurs depuis le détail F23 (qui les a résolues à partir d'`entreprise` via `VALUE_SOURCE_MAP`). Aucune duplication par axe E/S/G ni par référentiel. La grille E/S/G est dérivée côté UI du champ `pillar` de chaque `CoveredIndicatorOut`.
- **P8 Édition manuelle + sync LLM** : l'édition d'un indicateur depuis le drawer écrit le champ entreprise correspondant (route F11 `/me/entreprise` PATCH ; mapping de `indicateur_code → entreprise.field` matérialisé côté front en miroir manuel de `VALUE_SOURCE_MAP`). Après PATCH, l'UI déclenche un recalcul du référentiel courant et émet l'event chat `entity_updated{indicateur}` pour propager. Les indicateurs **non mappés** affichent un message explicite : « Cet indicateur ne peut pas être édité directement ici, ouvrez la conversation pour le compléter » + CTA chat (la liste des indicateurs éditables est figée dans `lib/scoringEditableIndicateurs.ts`).
- **P10 UX bottom sheet** : la saisie chiffrée passe par `<ChatBottomSheet>` + `<ShowForm ask_number>` (F39). La pastille source ouvre un `<UiPopover>` (composant simple, pas un input). Le drawer indicateur reste un slide-in non-modal, mais le bouton « Modifier » qu'il contient ouvre le bottom sheet. Aucun `<input>` libre inline.
- **P3 Audit** : la modification d'un champ entreprise est déjà tracée par F11 (existant). Le recalcul est déjà tracé par F23 via `entity_type='score_calculation'`. La page n'introduit aucune mutation directe de table → aucun nouvel `audit_log_event_type` à créer.
- **P2 RLS** : déjà imposé côté F23. Le front ne fabrique aucune requête SQL. Toute requête passe par les routes `/me/scoring/...` qui appliquent `account_id` via le JWT.
- **a11y WCAG 2.1 AA** : titres en `<h1>/<h2>`, `aria-busy` sur les blocs en chargement, `role="alert"` pour erreurs, navigation clavier complète (Tab → onglet → accordéon → row → bouton modifier → bottom sheet), focus trap dans drawer et bottom sheet (déjà fournis par `<UiPopover>` / `<ChatBottomSheet>`).
- **URL référentiel** : `/scoring/{code}` est SSR-friendly mais le code est validé client-side après hydratation contre la liste des référentiels disponibles ; un code inconnu déclenche une redirection vers `/scoring` avec toast explicatif.
- Hébergement Europe / Afrique de l'Ouest (constitution) — inchangé.
- Langue : français par défaut (clés ajoutées dans `frontend/app/locales/fr.ts` sous le namespace `scoring.*`).

**Scale/Scope** : 2 pages nouvelles + ~14 composants nouveaux + 1 store + 4 composables + 2 helpers + 1 endpoint backend. ~1300–1600 LOC frontend nouvelles + ~80 LOC backend nouvelles + ~120 LOC tests backend. Volume utilisateur : MVP — quelques centaines de PME pendant la phase pilote, ~1 référentiel actif par session, 50 à 100 indicateurs par référentiel typiquement (cap 200).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Aucune donnée fabriquée par l'UI ; chaque indicateur couvert porte un `source_id` (schéma `CoveredIndicatorOut`). La pastille `<VizSourcePin>` est obligatoire sur toute valeur affichée. Sources révoquées → badge avertissement + valeur grisée (FR-002, FR-017). | ✅ |
| P2 | Multi-tenant RLS | Routes consommées (`GET /me/scoring/...`, `POST /me/scoring/.../recompute`, `PATCH /me/entreprise`) appliquent déjà RLS via `account_id` dérivé du JWT. Le nouvel endpoint `.../history` réutilise la même `Depends(get_current_pme)` et un filtre SQL `WHERE account_id = :acc`. Cross-tenant → 404 testé. | ✅ |
| P3 | Audit log append-only | La page n'introduit aucune nouvelle mutation directe : édition indicateur = PATCH entreprise (déjà tracé F11), recalcul = INSERT score_calculation (déjà tracé F23). L'endpoint history est en lecture pure → pas d'audit. | ✅ |
| P4 | Versioning + snapshot candidatures | Pas de candidature ici. Les **scores** portent déjà `referentiel_version` (F23) ; le mode snapshot freeze l'UI sur un `score_calculation_id` historique sans le modifier. Pas de nouvelle ligne de version à introduire. | ✅ |
| P5 | Money typé | Pas de manipulation monétaire dans cette feature. Les seuils financiers éventuels affichés (ex: indicateur `CA_AMOUNT`) lus depuis `entreprise.taille_ca_amount` sont déjà typés `Money` côté F11 ; le drawer affiche `useMoneyFormat()`. Aucune valeur monétaire fabriquée côté UI. | ✅ |
| P6 | Pivot Indicateur unique | La grille E/S/G est strictement dérivée du champ `pillar` de chaque `CoveredIndicatorOut`. Aucune duplication par axe ni par référentiel. La comparaison multi-référentiels lit `score_global` et `scores_by_pillar` (déjà calculés backend) — pas de nouveau stockage. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle Banque/Fonds/Intermédiaire. La page est réservée à la PME (rôle PME du tenant). L'export PDF (P2) est un fichier téléchargeable par le dirigeant — pas de transmission automatique vers un tiers. Le partage signé Ed25519 reste hors-scope (F30 — attestation). | ✅ |
| P8 | Édition manuelle + sync LLM | L'édition manuelle d'un indicateur (US4) écrit le champ entreprise via F11, déclenche le recalcul F23, et émet `entity_updated{indicateur, score_calculation}` sur le bus. Inversement, toute mutation chat sur un indicateur invalide le détail courant et l'historique du référentiel ouvert via `useChatEventBus`. La DB reste source de vérité — la page lit toujours après mutation. | ✅ |
| P9 | Tool-use LLM fiable | Aucun nouveau tool LLM. Les tools existants côté F23/F41 (`recompute_score`, `update_indicateur_value`) émettent déjà les events consommés ici. Pas d'eval gating à introduire pour cette feature. | ✅ N/A |
| P10 | UX bottom sheet | La seule saisie utilisateur libre (édition de la valeur d'un indicateur) vit dans `<ChatBottomSheet>` + `<ShowForm ask_number>` (F39). La pastille source utilise `<UiPopover>` (composant simple, pas un input texte — autorisé). Le drawer indicateur n'expose aucun `<input>` libre. Bouton « Répondre librement » non applicable (pas de bulle LLM ici). | ✅ |

Aucun gate ❌. Pas de Complexity Tracking nécessaire.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ✓ (existant inchangé).
- Dev local : backend `.venv`, Postgres seul service Docker, frontend `pnpm dev` ✓.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement ✓.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450 — pas d'impact direct ici (pas de nouvelle donnée personnelle collectée).
- Langue : français par défaut ✓.

## Project Structure

### Documentation (this feature)

```text
specs/046-scoring-esg-ui/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques (route history, edit-via-entreprise, radar→bars switch, snapshot freeze, intégration F44)
├── data-model.md        # Phase 1 — ViewModels UI dérivés de ScoreDetailOut + entités piliers/comparaison/snapshot
├── quickstart.md        # Phase 1 — comment tester localement de bout en bout
├── contracts/
│   ├── backend-history-endpoint.md     # Contrat OpenAPI du nouvel endpoint /history
│   ├── frontend-api-consumption.md     # Contrats des endpoints F23 + F11 consommés (entrées/sorties UI)
│   ├── frontend-components.md          # Contrats des composants/composables nouveaux
│   └── chat-eventbus-sync.md           # Contrat d'évènements chat ↔ scoring (invalidations ciblées)
├── checklists/
│   └── requirements.md                 # Spec quality checklist (déjà créée)
└── tasks.md             # Phase 2 — généré par /speckit-tasks (PAS par /speckit-plan)
```

### Source Code (repository root)

```text
backend/
└── app/
    └── scoring/
        ├── router.py                   # MODIFIE — ajout route GET .../history (≤ 30 LOC)
        ├── service.py                  # MODIFIE — ajout fonction list_history(...) (lecture seule, RLS-aware)
        └── schemas.py                  # MODIFIE — ajout ScoreHistoryEntry + ScoreHistoryOut (Pydantic v2 strict)
└── tests/
    └── scoring/
        └── test_history_endpoint.py    # NEW — pytest unit + integration (6 cas)

frontend/
├── app/
│   ├── pages/
│   │   └── scoring/
│   │       ├── index.vue                       # NEW — entry point ; redirige vers /scoring/{default_referentiel} ou affiche state vide
│   │       └── [referentiel_code].vue          # NEW — détail par référentiel (vue d'ensemble + accordéon + historique)
│   ├── components/
│   │   ├── scoring/                            # NEW — famille scoring
│   │   │   ├── ReferentielTabs.vue             # pills/tabs BOAD/CDP/GRI/ODD/custom + sélection courante
│   │   │   ├── ScoreOverview.vue               # score global + <VizRadarChart> E/S/G (ou <VizBarChart> si > 6 axes) + couverture % + date + version
│   │   │   ├── PillarAccordion.vue             # accordéon E/S/G ; à l'intérieur, liste de <IndicateurRow>
│   │   │   ├── IndicateurRow.vue               # ligne indicateur (nom, score, statut, pastille source, badge révoqué)
│   │   │   ├── IndicateurDrawer.vue            # drawer slide-in droit (nom, def, valeur, unité, formule, sources, <VizLineChart> 12 mois, bouton Modifier)
│   │   │   ├── MissingIndicatorsList.vue       # section "À renseigner" + CTA Compléter (ouvre chat contextuel)
│   │   │   ├── RecalcButton.vue                # bouton "Recalculer" + état loading + erreur
│   │   │   ├── CompareButton.vue               # ouvre <CompareDrawer>
│   │   │   ├── CompareDrawer.vue               # sélection multi-réf + <VizBarChart> horizontal côte à côte
│   │   │   ├── HistoryChart.vue                # <VizLineChart> 12 derniers calculs avec hover (date / valeur / version)
│   │   │   ├── SnapshotToggle.vue              # toggle "Voir snapshot" + sélection d'un calcul historique → freeze UI
│   │   │   ├── ExportPdfButton.vue             # P2 — bouton export PDF (flag F51, dégradé si flag off)
│   │   │   ├── EmptyNoCalculation.vue          # état vide US12 avec CTA "Lancez votre premier diagnostic"
│   │   │   └── RevokedSourceBadge.vue          # badge avertissement + tooltip explicatif
│   │   ├── viz/                                # primitives existantes (VizRadarChart, VizBarChart, VizLineChart, VizSourcePin, VizEmptyState) — F40 (inchangé)
│   │   ├── ui/                                 # primitives existantes (UiCard, UiSkeleton, UiButton, UiBadge, UiPopover, UiModal, UiEmptyState, UiSwitch) — F37 (inchangé)
│   │   ├── chat/                               # ChatBottomSheet — F39 (réutilisé)
│   │   └── dashboard/
│   │       └── CardScoringSummary.vue          # MODIFIE (F44) — lit useScoringStore au lieu de fetcher en propre + lien "Voir le scoring complet" → /scoring
│   ├── composables/
│   │   ├── useScoring.ts                       # NEW — fetch list/detail + abonnement EventBus + invalidations ciblées
│   │   ├── useScoringHistory.ts                # NEW — fetch GET .../history avec cache 60 s
│   │   ├── useScoringCompare.ts                # NEW — sélection multi-réf, agrégation client (lit ScoreSummaryOut[])
│   │   ├── useIndicateurEdit.ts                # NEW — orchestre bottom sheet ask_number → PATCH entreprise → recompute → emit
│   │   ├── useChatEventBus.ts                  # EXISTANT — abonnement entity_updated{indicateur, score_calculation}
│   │   ├── useChatBottomSheet.ts               # EXISTANT — pour piloter le sheet d'édition
│   │   ├── useT.ts                             # EXISTANT — i18n
│   │   ├── useReducedMotion.ts                 # EXISTANT — désactivation animations
│   │   ├── useChartTheme.ts                    # EXISTANT — couleurs E/S/G
│   │   └── useToast.ts                         # EXISTANT — feedback erreur
│   ├── stores/
│   │   └── scoring.ts                          # NEW — by(entity, ref): summary, detail, history, version, mode snapshot, frozen_id, loading/error
│   ├── lib/
│   │   ├── mapIndicateursByPillar.ts           # NEW — regroupement E/S/G + tri par contribution + flag covered/missing
│   │   └── scoringEditableIndicateurs.ts       # NEW — miroir manuel de VALUE_SOURCE_MAP (indicateur_code → champ entreprise) ; source de vérité = backend
│   ├── locales/
│   │   └── fr.ts                               # MODIFIE — namespace scoring.* (titres, libellés piliers, statuts, messages, empty states, snapshot)
│   └── assets/css/main.css                     # éventuelles classes utilitaires (sinon inchangé)
└── tests/
    ├── unit/
    │   ├── composables/
    │   │   ├── useScoring.test.ts
    │   │   ├── useScoringHistory.test.ts
    │   │   ├── useScoringCompare.test.ts
    │   │   └── useIndicateurEdit.test.ts
    │   ├── stores/
    │   │   └── scoring.test.ts
    │   └── lib/
    │       ├── mapIndicateursByPillar.test.ts
    │       └── scoringEditableIndicateurs.test.ts
    ├── components/
    │   └── scoring/
    │       ├── ReferentielTabs.test.ts
    │       ├── ScoreOverview.test.ts
    │       ├── PillarAccordion.test.ts
    │       ├── IndicateurRow.test.ts
    │       ├── IndicateurDrawer.test.ts
    │       ├── MissingIndicatorsList.test.ts
    │       ├── RecalcButton.test.ts
    │       ├── CompareDrawer.test.ts
    │       ├── HistoryChart.test.ts
    │       ├── SnapshotToggle.test.ts
    │       ├── EmptyNoCalculation.test.ts
    │       └── RevokedSourceBadge.test.ts
    └── e2e/
        ├── scoring-overview-render.spec.ts
        ├── scoring-tab-switch.spec.ts
        ├── scoring-drilldown-drawer.spec.ts
        ├── scoring-edit-indicateur-mapped.spec.ts
        ├── scoring-edit-indicateur-unmapped.spec.ts
        ├── scoring-compare-referentiels.spec.ts
        ├── scoring-missing-complete-cta.spec.ts
        ├── scoring-recalc.spec.ts
        ├── scoring-revoked-source.spec.ts
        ├── scoring-snapshot-freeze.spec.ts
        ├── scoring-snapshot-exit.spec.ts
        ├── scoring-chat-sync.spec.ts
        ├── scoring-empty-no-calculation.spec.ts
        ├── scoring-reduced-motion.spec.ts
        └── scoring-unknown-referentiel.spec.ts
```

**Structure Decision** : Application web mono-repo Nuxt 4 + FastAPI déjà en place. Cette feature touche principalement `frontend/app/` ; côté backend, seuls 3 fichiers existants F23 sont modifiés de façon additive (router, service, schemas) plus 1 fichier de tests nouveau. Le découpage `components/scoring/*` reflète la frontière de domaine UI (page consultation/comparaison de scores ESG) sans empiéter sur `components/dashboard/*` (F44) ni sur `components/plan-action/*` (F45) ni sur `components/chat/*` (F41). Le store `scoring.ts` est partagé : la `CardScoringSummary` du dashboard (F44, déjà livrée comme widget statique fetcher-en-propre) sera **modifiée** pour lire ce store, garantissant cohérence et invalidation unique. Les tests sont structurés en `unit/` (composables, store, lib), `components/` (composants Vue), `e2e/` (Playwright) — héritage F38/F42/F43/F44/F45.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Aucune violation. Tableau vide.
