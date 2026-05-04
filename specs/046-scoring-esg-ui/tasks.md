# Tasks: Scoring ESG visualisations UI (F46)

**Input**: Design documents from `/specs/046-scoring-esg-ui/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓ (4 docs), quickstart.md ✓

**Tests**: Tests **REQUIS** par la constitution (TDD + 80 % coverage). Chaque user story inclut tests vitest (unit/components) puis Playwright (e2e), écrits **avant** l'implémentation. Côté backend, le seul ajout (endpoint history) est précédé de pytest unit + integration.

**Organization**: Tâches groupées par user story pour livraison MVP incrémentale. La feature est très majoritairement frontend ; un seul ajout backend (`GET .../history`) est livré en phase Foundational car consommé par US7/US8.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : parallélisable (fichier différent, pas de dépendance bloquante).
- **[Story]** : US1…US9 ; pas de label pour Setup / Foundational / Polish.
- Tous les chemins sont relatifs à la racine repo.

## Path Conventions (rappel plan.md)

- Frontend Nuxt 4 : `frontend/app/{pages,components,composables,stores,lib,types,locales,services}`.
- Tests frontend : `frontend/tests/{components,e2e}` + `frontend/app/{composables,stores,lib}/__tests__` (pattern existant F44/F45).
- Backend FastAPI : `backend/app/scoring/{router,service,schemas}.py` (modifications additives) ; tests `backend/tests/scoring/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose** : préparer l'arborescence, les types miroir backend, les constantes de mapping, et les clés i18n.

- [X] T001 Créer le dossier `frontend/app/components/scoring/` et `frontend/app/pages/scoring/` (avec un `.gitkeep` temporaire dans `pages/scoring/` pour committer la structure).
- [X] T002 [P] Créer `frontend/app/types/scoring.ts` qui exporte les types miroir des schémas F23 + F46 : `ScoreSummaryOut`, `ScoreDetailOut`, `CoveredIndicatorOut`, `MissingIndicatorOut`, `ScoreListOut`, `ScoreHistoryEntry`, `ScoreHistoryOut`, et les ViewModels `ScoreSummaryVM`, `ScoreDetailVM`, `CoveredIndicatorVM`, `MissingIndicatorVM`, `ScoreHistoryEntryVM`, `PillarRowVM`, `PillarBucketVM`, `CompareSeriesVM`, `CompareDatasetVM`, `ScoringSnapshotVM` exactement comme défini dans `data-model.md` §1-§2.
- [X] T003 [P] Créer `frontend/app/lib/scoringEditableIndicateurs.ts` exportant `SCORING_EDITABLE_INDICATEUR_CODES` (Set) et `SCORING_INDICATEUR_TO_ENTREPRISE_PATH` (Record) — contenu exact défini dans `data-model.md` §5.2 (miroir manuel de `backend/app/scoring/value_source.py:VALUE_SOURCE_MAP`). Ajouter un commentaire en tête `// MIRROR — keep in sync with backend/app/scoring/value_source.py`.
- [X] T004 [P] Créer `frontend/app/lib/__tests__/scoringEditableIndicateurs.test.ts` vérifiant : (a) l'ensemble contient au minimum `EFFECTIFS_TOTAL`, `CA_AMOUNT`, `PAYS_SIEGE`, `GOUVERNANCE_BOARD_INDEPENDENCE`, `PRATIQUE_POLITIQUE_RSE` ; (b) tout code dans le Set possède une entrée dans le Record ; (c) types TypeScript du Record corrects (`field`, `jsonPath?`, `type`).
- [X] T005 [P] Créer `frontend/app/lib/__tests__/mapIndicateursByPillar.test.ts` (fichier vide — rempli en T013 pour TDD).
- [X] T006 [P] Étendre `frontend/app/locales/fr.ts` avec le namespace complet `scoring.*` listé dans `contracts/frontend-components.md` §Modifications (pageTitle, pillars, status, buttons, snapshot, errors, empty).

**Checkpoint Setup** : arborescence prête, types TS alignés sur F23, mapping miroir disponible, clés i18n en place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose** : ajout backend (endpoint history) + briques frontend transverses (store Pinia, helpers, service API, composable principal). Aucune US ne peut démarrer avant le checkpoint.

**⚠️ CRITICAL** : pas de travail US tant que cette phase n'est pas verte.

### Backend — endpoint history (livré ici car bloquant pour US7/US8)

- [X] T007 Créer `backend/tests/scoring/test_history_endpoint.py` (TDD avant code) couvrant les 6 cas du plan §Testing : (1) compte sans calcul → 200 + `entries=[]`, (2) compte avec 3 calculs → ordre `computed_at DESC`, (3) compte avec 15 calculs + `limit=12` par défaut → 12 entrées + `limit=5` respecté, (4) cross-tenant (autre `account_id`) → 404, (5) `entity_type='unknown'` → 404, (6) `referentiel_code` inconnu → 404, (7) `limit=0` ou `limit=51` → 422. Utiliser les fixtures pytest existantes `backend/tests/scoring/conftest.py`.
- [X] T008 [P] Étendre `backend/app/scoring/schemas.py` avec `ScoreHistoryEntry` et `ScoreHistoryOut` (Pydantic v2 strict, `extra='forbid'`) selon `contracts/backend-history-endpoint.md`.
- [X] T009 Étendre `backend/app/scoring/service.py` avec la fonction pure `list_history(db, *, account_id, entity_type, entity_id, referentiel_code, limit) -> list[dict]` qui (a) résout `referentiel_code → referentiel_id` (404 si inconnu via `ReferentielNotFound`), (b) `SELECT id, computed_at, score_global, referentiel_version FROM score_calculation WHERE account_id=:acc AND entity_type=:etype AND entity_id=:eid AND referentiel_id=:rid ORDER BY computed_at DESC LIMIT :limit`. Aucun `audit_log`. Réutiliser le pattern de `list_latest_scores`.
- [X] T010 Étendre `backend/app/scoring/router.py` avec la route `@router.get("/{entity_type}/{entity_id}/{referentiel_code}/history", response_model=ScoreHistoryOut)` selon `contracts/backend-history-endpoint.md` (validation `entity_type`, `account_id` via `Depends(get_current_pme)`, `limit: int = Query(12, ge=1, le=50)`, mapping `EntityNotAccessible`/`ReferentielNotFound` → 404).
- [X] T011 Lancer `cd backend && source .venv/bin/activate && pytest tests/scoring/test_history_endpoint.py -v` ; les 7 cas doivent passer GREEN.

### Frontend — service API + store + helpers + composable principal

- [X] T012 [P] Créer `frontend/app/services/api/scoring.ts` exportant `scoringApi` avec : `listSummaries(entityType, entityId)`, `getDetail(entityType, entityId, refCode)`, `recompute(entityType, entityId, refCode)`, `getHistory(entityType, entityId, refCode, limit?)`. Encapsule `$fetch` Nuxt + JWT, miroir de `services/api/action-plan.ts` (F45). Aucun appel direct `$fetch` ailleurs dans la feature.
- [X] T013 Remplir `frontend/app/lib/__tests__/mapIndicateursByPillar.test.ts` (créé vide en T005) : (a) détail avec 3 couverts E/S/G + 2 manquants → 3 buckets ordonnés E,S,G, couverts triés par `contribution` desc, missing en queue ; (b) source révoquée → `isSourceRevoked=true` ; (c) indicateur dans `SCORING_EDITABLE_INDICATEUR_CODES` → `isEditable=true` ; (d) pilier custom (code différent de E/S/G) → label = code en majuscules ; (e) détail vide → tableau vide.
- [X] T014 [P] Créer `frontend/app/lib/mapIndicateursByPillar.ts` qui passe T013. Pure ; aucune dépendance Vue.
- [X] T015 [P] Créer `frontend/app/stores/__tests__/scoring.test.ts` couvrant le store Pinia selon `data-model.md` §3 : (a) `setEntity` initialise état ; (b) `loadSummaries` appelle l'API et remplit `summariesByRef` ; (c) `loadDetail(ref)` cache 60 s — second appel ne refait pas l'API sauf cache miss ; (d) `loadHistory(ref, limit)` met à jour `historyByRef` ; (e) `setCurrentReferentiel('CDP')` lazy-charge detail+history si manquants ; (f) `recompute(ref)` rejette si déjà `recomputingByRef[ref]===true` (anti double-clic) ; (g) `editIndicateur` rejette en mode snapshot ; (h) `enterSnapshot(calcId)` charge le summary historique correspondant et active le mode ; (i) `exitSnapshot` repasse en live ; (j) `onChatEntityUpdated({entity_type:'indicateur', meta:{indicateur_code}})` invalide detail+history du `currentRef` ; (k) `onChatEntityUpdated({entity_type:'score_calculation'})` invalide detail+history seulement. Mock `scoringApi`.
- [X] T016 Créer `frontend/app/stores/scoring.ts` qui passe T015 (Pinia setup store, exposition selon §3.2 et §3.3).
- [X] T017 [P] Créer `frontend/app/composables/__tests__/useScoring.test.ts` : (a) au mount, `setEntity` puis `loadSummaries` appelés une fois ; (b) abonnement `useChatEventBus` reçoit `entity_updated{indicateur, meta:{indicateur_code:'EFFECTIFS_TOTAL'}}` → `onChatEntityUpdated` invoqué ; (c) reçoit `entity_updated{score_calculation}` → invalidations détail + history ; (d) garde anti-boucle : event reçu < 500 ms après une émission locale (`source==='manual'` + flag `_localEmission`) est ignoré ; (e) cleanup `onBeforeUnmount` désouscrit ; (f) debounce 200 ms : 3 events rapides → 1 seul re-fetch.
- [X] T018 Créer `frontend/app/composables/useScoring.ts` qui passe T017. Expose `currentSummary`, `currentDetail`, `pillarsBuckets`, `coveragePercent`, `loading`, `error`, `isSnapshot`, `setCurrentReferentiel`, `recompute`.

### Modification F44 (CardScoringSummary)

- [X] T019 [P] Créer `frontend/tests/components/dashboard/CardScoringSummary.test.ts` (ou étendre l'existant) vérifiant que la card lit `useScoringStore` au lieu de `$fetch` et expose un lien `Voir le scoring complet` vers `/scoring`. Inclure assertion : aucun `$fetch` direct dans le composant.
- [X] T020 Modifier `frontend/app/components/dashboard/CardScoringSummary.vue` (livré F44) pour lire `useScoringStore` au mount (`store.setEntity(...)` + `loadSummaries()`) et afficher `currentSummary` ; remplacer le bouton existant par un `<NuxtLink to="/scoring">`. Faire passer T019 sans régression du test F44 existant.

**Checkpoint Foundational** : endpoint backend `GET .../history` opérationnel, store + service + composable principal + helpers + dashboard intégré.

---

## Phase 3: User Story 1 — Vue d'ensemble du score ESG (Priority: P1) 🎯 MVP

**Goal** : afficher score global + radar E/S/G + couverture + date + version, avec sources cliquables et état vide explicite (US12 inclus).

**Independent Test** : un compte PME avec un calcul `BOAD` ouvre `/scoring`, voit score, radar, couverture, date, version, et clique une source vérifiée qui s'ouvre.

### Tests d'abord (TDD)

- [X] T021 [P] [US1] Créer `frontend/tests/components/scoring/ScoreOverview.test.ts` couvrant : (a) avec 3 axes E/S/G → `<VizRadarChart>` rendu ; (b) avec 7 axes → `<VizBarChart>` vertical rendu (bascule R3) ; (c) `summary=null` → `<UiSkeleton>` ; (d) `coverage_ratio=0.85` → texte `85 %` ; (e) `referentiel_version=3` → pastille `v.3` ; (f) `computed_at` ISO → date FR (`useT`/Intl) ; (g) tableau `sr-only` listant chaque pilier et son score (a11y R13) ; (h) `isSnapshot=true` → bandeau snapshot affiché ; (i) score `null` → placeholder `—`.
- [X] T022 [P] [US1] Créer `frontend/tests/components/scoring/EmptyNoCalculation.test.ts` couvrant : (a) rendu `<UiEmptyState>` avec titre et CTA ; (b) clic CTA émet `start` ; (c) bouton désactivé pendant `loading=true`.
- [X] T023 [P] [US1] Créer `frontend/tests/components/scoring/RevokedSourceBadge.test.ts` couvrant : (a) rendu `<UiBadge variant="warning">` ; (b) tooltip i18n `scoring.errors.revokedSource` ; (c) `aria-label` correct.
- [X] T024 [P] [US1] Créer `frontend/tests/components/scoring/IndicateurRow.test.ts` couvrant le rendu d'une `PillarRowVM` couverte avec `<VizSourcePin>` + score + label (test minimal pour la vue d'ensemble ; le drilldown complet est testé en US3).
- [X] T025 [P] [US1] Créer `frontend/tests/e2e/scoring-overview-render.spec.ts` (Playwright) : authentification PME → seed 1 calcul BOAD via `POST recompute` → ouvrir `/scoring` → assertions : score global visible < 2 s, radar SVG/canvas rendu, % couverture + date FR + pastille v.X visibles, clic sur pastille source ouvre popover avec titre/organisme/lien.
- [X] T026 [P] [US1] Créer `frontend/tests/e2e/scoring-empty-no-calculation.spec.ts` : compte sans calcul → ouvrir `/scoring/BOAD` → empty state visible → clic CTA → spinner → score affiché.

### Implémentation US1

- [X] T027 [P] [US1] Créer `frontend/app/components/scoring/RevokedSourceBadge.vue` qui passe T023.
- [X] T028 [P] [US1] Créer `frontend/app/components/scoring/EmptyNoCalculation.vue` qui passe T022 (props `referentielCode`, event `start`).
- [X] T029 [P] [US1] Créer `frontend/app/components/scoring/IndicateurRow.vue` (version minimale US1 — sera complété en US3) qui passe T024 : props `row: PillarRowVM`, `disableEdit`, event `open(row)`, rendu `<VizSourcePin>` ou `<RevokedSourceBadge>`.
- [X] T030 [US1] Créer `frontend/app/components/scoring/ScoreOverview.vue` qui passe T021 : props `summary`, `loading`, `isSnapshot` ; rend `<VizRadarChart>` (≤6 axes) ou `<VizBarChart>` (≥7) selon nombre de clés non-nulles dans `scores_by_pillar` ; affiche score global tabular-nums, couverture %, date FR, pastille version ; tableau `sr-only` ; bandeau snapshot conditionnel ; slot `extra` pour boutons.
- [X] T031 [US1] Créer `frontend/app/pages/scoring/index.vue` : `<ScriptSetup>` qui lit `useScoring()` + `useEntrepriseProfile()` ; au mount, charge summaries ; si pas de référentiel courant → redirige vers `/scoring/BOAD` (default constitution) ; si pas du tout de calcul → `<EmptyNoCalculation>`. Sinon, redirection `<NuxtLink replace to="/scoring/BOAD">`. Page minimale, pas de logique métier dupliquée.
- [X] T032 [US1] Créer `frontend/app/pages/scoring/[referentiel_code].vue` (squelette US1) : route param `referentiel_code` validé contre `availableReferentiels` (sinon redirect `/scoring` + toast `scoring.errors.unknownReferentiel`) ; rend `<ScoreOverview>` + `<EmptyNoCalculation>` selon état du store. Le drilldown, l'historique, la comparaison et le snapshot seront ajoutés dans les phases suivantes.
- [X] T033 [US1] Lancer `pnpm vitest run` (unit + components US1) et `pnpm test:e2e --grep scoring-overview-render` ; tous GREEN.

**Checkpoint US1** : MVP livrable — `/scoring` fonctionnelle avec score global, radar, couverture, version, sources, et état vide. La PME voit sa note ESG.

---

## Phase 4: User Story 2 — Choix du référentiel et comparaison (Priority: P1)

**Goal** : tabs référentiels + URL synchronisée + drawer de comparaison côte à côte.

**Independent Test** : sur `/scoring`, basculer BOAD → CDP met à jour l'URL en `/scoring/CDP` et affiche les données ; cliquer « Comparer » et sélectionner BOAD+CDP affiche un bar chart côte à côte.

### Tests d'abord

- [X] T034 [P] [US2] Créer `frontend/tests/components/scoring/ReferentielTabs.test.ts` : (a) rend N pills selon `availableCodes` ; (b) pill `currentCode` a `aria-selected="true"` ; (c) clic émet `select(code)` ; (d) `disabled=true` empêche le clic.
- [X] T035 [P] [US2] Créer `frontend/app/composables/__tests__/useScoringCompare.test.ts` : (a) `selectedRefs` initialisé à `[currentRef]` ; (b) `select('CDP')` ajoute ; (c) `unselect('BOAD')` retire ; (d) max 5 sélections (6e refusée + toast) ; (e) `dataset` calcule l'union ordonnée des piliers présents dans `scores_by_pillar`.
- [X] T036 [P] [US2] Créer `frontend/tests/components/scoring/CompareDrawer.test.ts` : (a) `open=true` rend modal ; (b) checkboxes correspondent à `availableSummaries` ; (c) `<VizBarChart>` reçoit `dataset` ; (d) légende affiche libellé + version ; (e) close émet `close`.
- [X] T037 [P] [US2] Créer `frontend/tests/e2e/scoring-tab-switch.spec.ts` : ouvrir `/scoring/BOAD` → cliquer tab `CDP` → URL devient `/scoring/CDP` < 200 ms (cache hit après 2e visite) ; assertion : pas de full-reload (test via `page.evaluate(() => window.performance.navigation.type)` ou cookie sentinel).
- [X] T038 [P] [US2] Créer `frontend/tests/e2e/scoring-compare-referentiels.spec.ts` : ouvrir `/scoring`, cliquer « Comparer », cocher BOAD + CDP, assertion bar chart horizontal avec 2 séries × N piliers visible.
- [X] T039 [P] [US2] Créer `frontend/tests/e2e/scoring-unknown-referentiel.spec.ts` : ouvrir `/scoring/UNKNOWN_CODE` → toast erreur + redirect `/scoring`.

### Implémentation US2

- [X] T040 [P] [US2] Créer `frontend/app/composables/useScoringCompare.ts` qui passe T035.
- [X] T041 [P] [US2] Créer `frontend/app/components/scoring/ReferentielTabs.vue` qui passe T034 (rôle `tablist`, `aria-selected`, navigation clavier flèches gauche/droite).
- [X] T042 [US2] Créer `frontend/app/components/scoring/CompareDrawer.vue` qui passe T036 (`<UiModal>` ou `<UiPopover side="right">` en plein écran ; checkbox liste ; `<VizBarChart orientation="horizontal">`).
- [X] T043 [P] [US2] Créer `frontend/app/components/scoring/CompareButton.vue` (simple wrapper qui ouvre/ferme `<CompareDrawer>` via state local + slot `default`).
- [X] T044 [US2] Étendre `frontend/app/pages/scoring/[referentiel_code].vue` : ajouter `<ReferentielTabs>` en haut + `<CompareButton>` dans le slot `extra` de `<ScoreOverview>`. Brancher la sélection sur `store.setCurrentReferentiel(code)` qui maj URL via `navigateTo`.
- [X] T045 [US2] Lancer `pnpm vitest run` + `pnpm test:e2e --grep "scoring-tab-switch|scoring-compare|scoring-unknown"` ; GREEN.

**Checkpoint US2** : navigation entre référentiels + comparaison opérationnelles.

---

## Phase 5: User Story 3 — Drilldown par pilier puis par indicateur (Priority: P1)

**Goal** : accordéon E/S/G + drawer indicateur (définition, valeur, sources, graphique 12 mois).

**Independent Test** : sur `/scoring/BOAD`, dérouler `Environnement`, cliquer un indicateur, drawer s'ouvre avec graphique linéaire 12 mois.

### Tests d'abord

- [X] T046 [P] [US3] Créer `frontend/tests/components/scoring/PillarAccordion.test.ts` : (a) rend N `<details>` natifs (un par pilier) ; (b) `defaultOpen=['E','S','G']` ouvre les 3 ; (c) bucket avec > 30 rows → bouton « Voir les N restants » + 30 rows initiales ; (d) clic row émet `openIndicateur(row)` ; (e) `disableEdit=true` est propagé aux rows.
- [X] T047 [P] [US3] Créer `frontend/tests/components/scoring/IndicateurDrawer.test.ts` : (a) `open=false` ne monte pas le contenu ; (b) `open=true` rend nom, définition, valeur, unité, formule, sources ; (c) `<VizLineChart>` créé uniquement si `open=true` (R9) ; (d) bouton `Modifier` désactivé si `disableEdit || !row.isEditable` ; (e) clic `Modifier` émet `edit(row)` ; (f) Escape ferme + émet `close`.
- [X] T048 [P] [US3] Créer `frontend/app/composables/__tests__/useScoringHistory.test.ts` : (a) `loadHistory(refCode)` appelle `scoringApi.getHistory` ; (b) cache 60 s ; (c) `entries` triées DESC ; (d) erreur 404 → toast + `entries=[]`.
- [X] T049 [P] [US3] Créer `frontend/tests/e2e/scoring-drilldown-drawer.spec.ts` : `/scoring/BOAD`, dérouler `Environnement`, cliquer indicateur `EFFECTIFS_TOTAL` → drawer ouvert, valeur courante affichée, graphique linéaire visible (au moins l'élément canvas), Escape ferme.

### Implémentation US3

- [X] T050 [P] [US3] Créer `frontend/app/composables/useScoringHistory.ts` qui passe T048.
- [X] T051 [P] [US3] Compléter `frontend/app/components/scoring/IndicateurRow.vue` (commencé en T029) avec : statut couvert/missing badge, `tabular-nums` sur scoreContribution, support `disableEdit` propagé via prop, tooltip « Édition disponible via le chat » si `!isEditable`.
- [X] T052 [P] [US3] Créer `frontend/app/components/scoring/PillarAccordion.vue` qui passe T046 (rendu `<details>` HTML, props `buckets`, `defaultOpen`, `disableEdit`, event `openIndicateur`).
- [X] T053 [US3] Créer `frontend/app/components/scoring/IndicateurDrawer.vue` qui passe T047 (slide-in droite via `<UiPopover side="right">` ; `v-if="open"` autour du `<VizLineChart>` ; focus trap ; props `row`, `referentielCode`, `open`, `disableEdit`).
- [X] T054 [US3] Étendre `frontend/app/pages/scoring/[referentiel_code].vue` pour ajouter `<PillarAccordion :buckets="store.pillarsBuckets">` + state local `openedIndicateur: PillarRowVM | null` + `<IndicateurDrawer>` lié.
- [X] T055 [US3] Lancer vitest + `pnpm test:e2e --grep scoring-drilldown-drawer` ; GREEN.

**Checkpoint US3** : drilldown complet, drawer indicateur fonctionnel.

---

## Phase 6: User Story 4 — Modifier la valeur d'un indicateur (Priority: P1)

**Goal** : édition via bottom sheet `ask_number`, recalcul automatique, propagation event.

**Independent Test** : drawer ouvert sur indicateur éditable, clic Modifier → bottom sheet, saisir nouvelle valeur, valider, score global et radar mis à jour sans rechargement.

### Tests d'abord

- [X] T056 [P] [US4] Créer `frontend/app/composables/__tests__/useIndicateurEdit.test.ts` : (a) `openFor(row)` avec `row.isEditable=true` ouvre `<ChatBottomSheet>` type `ask_number` avec valeur courante + unité ; (b) `row.isEditable=false` → toast + émet `open_chat_for_indicateur` au lieu d'ouvrir le sheet ; (c) `snapshot.active` → toast + ne fait rien ; (d) `onSubmit` valide → appelle `store.editIndicateur({...})` ; (e) erreur PATCH → toast d'erreur, sheet reste ouvert avec valeur précédente ; (f) succès → ferme le sheet et émet `entity_updated{indicateur, manual}` puis `entity_updated{score_calculation, manual}` (ordre garanti). Mock `useChatBottomSheet`, store, `useChatEventBus`.
- [X] T057 [P] [US4] Étendre `frontend/app/stores/__tests__/scoring.test.ts` (créé en T015) avec couverture `editIndicateur` : (a) résout le mapping via `SCORING_INDICATEUR_TO_ENTREPRISE_PATH` ; (b) appelle PATCH `/me/entreprise` avec payload partiel correct (cas `number`, `money`, `boolean`, `jsonPath`) ; (c) après PATCH OK, appelle `recompute(refCode)` ; (d) push/pop `editingIndicateurIds` ; (e) émission events bus dans l'ordre.
- [X] T058 [P] [US4] Créer `frontend/tests/e2e/scoring-edit-indicateur-mapped.spec.ts` : ouvrir drawer indicateur `EFFECTIFS_TOTAL`, clic Modifier, saisir `200`, valider → drawer mis à jour, score global du radar change, nouvelle entrée history (nouveau computed_at).
- [X] T059 [P] [US4] Créer `frontend/tests/e2e/scoring-edit-indicateur-unmapped.spec.ts` : indicateur non dans `SCORING_EDITABLE_INDICATEUR_CODES` → bouton Modifier désactivé OU clic affiche toast + ouvre chat (selon UX retenue : tooltip + bouton désactivé). Assertion : aucune mutation backend (vérifier via `route.fulfill` ou interception réseau).

### Implémentation US4

- [X] T060 [P] [US4] Créer le service de PATCH ciblé : étendre `frontend/app/services/api/scoring.ts` avec une fonction `editIndicateurValue(indicateurCode, newValue)` qui (a) résout via `SCORING_INDICATEUR_TO_ENTREPRISE_PATH`, (b) construit le payload partiel (gestion `jsonPath` via merge avec valeur courante lue depuis `useEntrepriseProfile`), (c) appelle PATCH `/me/entreprise`. Tests unit dans le même fichier de tests T015 ou nouveau.
- [X] T061 [P] [US4] Créer `frontend/app/composables/useIndicateurEdit.ts` qui passe T056.
- [X] T062 [US4] Étendre `frontend/app/stores/scoring.ts` avec `editIndicateur({indicateurId, indicateurCode, newValue, refCode})` qui passe T057 : appelle `editIndicateurValue` puis `recompute(refCode)` puis émet les 2 events bus dans l'ordre.
- [X] T063 [US4] Brancher `<IndicateurDrawer>` event `edit(row)` → `useIndicateurEdit.openFor(row)` dans `pages/scoring/[referentiel_code].vue`.
- [X] T064 [US4] Lancer vitest + `pnpm test:e2e --grep scoring-edit-indicateur` ; GREEN.

**Checkpoint US4** : édition opérationnelle pour les indicateurs mappés ; CTA chat clair pour les autres.

---

## Phase 7: User Story 5 — Indicateurs manquants et passage à l'action (Priority: P1)

**Goal** : section « À renseigner » + CTA `Compléter` ouvrant le chat contextualisé.

**Independent Test** : référentiel à couverture incomplète → section visible → clic Compléter sur un indicateur → chat ouvert avec contexte.

### Tests d'abord

- [X] T065 [P] [US5] Créer `frontend/tests/components/scoring/MissingIndicatorsList.test.ts` : (a) `missing=[]` → composant masqué ; (b) `missing=[3]` → 3 lignes + CTA `Compléter` chacune ; (c) clic Compléter émet `complete(indicateurCode)` ; (d) i18n libellés OK.
- [X] T066 [P] [US5] Créer `frontend/tests/e2e/scoring-missing-complete-cta.spec.ts` : ouvrir `/scoring/BOAD` (couverture incomplète), trouver section À renseigner, cliquer Compléter sur 1er manquant → assertion : event chat émis (intercepter via spy `useChatEventBus`) + chat panel ouvert (selon impl F41).

### Implémentation US5

- [X] T067 [US5] Créer `frontend/app/components/scoring/MissingIndicatorsList.vue` qui passe T065 ; émet `complete(code)` qui appelle `useChatEventBus.emit('open_chat_for_indicateur', {indicateur_code, referentiel_code, source:'scoring_page'})`.
- [X] T068 [US5] Étendre `pages/scoring/[referentiel_code].vue` pour insérer `<MissingIndicatorsList :missing="store.currentDetail?.indicateursManquants ?? []" :referentiel-code="ref">` au-dessus de `<PillarAccordion>`. Caché auto si vide.
- [X] T069 [US5] Lancer vitest + e2e ; GREEN.

**Checkpoint US5** : passerelle scoring → chat opérationnelle.

---

## Phase 8: User Story 6 — Recalcul à la demande + sync chat (Priority: P1)

**Goal** : bouton Recalculer + indicateur de progression + anti double-clic + propagation chat ↔ scoring (US11 fusionné ici).

**Independent Test** : (a) clic Recalculer → spinner → nouveau score + nouvelle date ; (b) modification depuis le chat → page se rafraîchit auto ; (c) double-clic Recalculer → second clic ignoré.

### Tests d'abord

- [X] T070 [P] [US6] Créer `frontend/tests/components/scoring/RecalcButton.test.ts` : (a) rendu bouton + label ; (b) `disabled=true` (snapshot) → click ignoré ; (c) clic appelle `store.recompute(ref)` ; (d) `isRecomputing=true` → spinner + bouton désactivé (anti double-clic) ; (e) erreur backend → toast i18n `scoring.errors.recomputeFailed` avec raison.
- [X] T071 [P] [US6] Créer `frontend/tests/e2e/scoring-recalc.spec.ts` : ouvrir `/scoring/BOAD`, clic Recalculer → spinner → nouveau `computed_at` plus récent ; double-clic rapide → un seul recompute backend (intercepter compte d'appels).
- [X] T072 [P] [US6] Créer `frontend/tests/e2e/scoring-chat-sync.spec.ts` : ouvrir `/scoring/BOAD`, déclencher via fixture API directe `PATCH /me/entreprise` puis `recompute` (simulant le chat) + émettre `entity_updated{indicateur, source:'tool'}` sur le bus → assertion : score global page se rafraîchit sans clic utilisateur, sans toast d'erreur.

### Implémentation US6

- [X] T073 [P] [US6] Créer `frontend/app/components/scoring/RecalcButton.vue` qui passe T070 ; lit `useScoringStore` pour `isRecomputing` ; appelle `store.recompute(refCode)`.
- [X] T074 [US6] Vérifier que `useScoring` (T018) et `scoring.ts` store (T016) émettent et consomment correctement le bus selon `contracts/chat-eventbus-sync.md` ; ajuster le store pour : (a) émettre dans l'ordre `entity_updated{indicateur,manual}` puis `{score_calculation,manual}` après `editIndicateur` ; (b) émettre `{score_calculation,manual}` après `recompute` manuel ; (c) consommer `entity_updated{indicateur, meta.indicateur_code}` avec invalidation ciblée ; (d) debounce 200 ms ; (e) garde anti-boucle par flag local. Faire passer T072.
- [X] T075 [US6] Brancher `<RecalcButton>` dans le slot `extra` de `<ScoreOverview>` (à côté de `<CompareButton>`).
- [X] T076 [US6] Lancer vitest + `pnpm test:e2e --grep "scoring-recalc|scoring-chat-sync"` ; GREEN.

**Checkpoint US6** : recalcul + sync bidirectionnelle opérationnels.

---

## Phase 9: User Story 7 — Historique des scores (Priority: P1)

**Goal** : graphique linéaire 12 derniers calculs + tooltip date/valeur/version.

**Independent Test** : référentiel avec ≥ 2 calculs → graphique linéaire visible → survol point révèle date FR + score + version.

### Tests d'abord

- [X] T077 [P] [US7] Créer `frontend/tests/components/scoring/HistoryChart.test.ts` : (a) `entries=[]` + `loading=false` → message « Pas encore d'historique » ; (b) `entries.length=1` → un point ; (c) `entries.length=12` → 12 points triés DESC ; (d) tooltip mock affiche `date FR + score + v.X` ; (e) clic point émet `select(entry)`.
- [X] T078 [P] [US7] Créer (ou étendre) `frontend/tests/e2e/scoring-overview-render.spec.ts` avec un cas dédié `displays history chart with multiple points` : seed 3 recompute → assertion `<canvas>` historique présent + 3 points (au moins via `aria-label` ou data-testid).

### Implémentation US7

- [X] T079 [US7] Créer `frontend/app/components/scoring/HistoryChart.vue` qui passe T077 ; utilise `<VizLineChart>` (F40) avec dataset issu de `useScoringHistory(refCode).entries`.
- [X] T080 [US7] Étendre `pages/scoring/[referentiel_code].vue` pour ajouter `<HistoryChart>` sous `<ScoreOverview>`, lazy-mount si `entries.length > 0`.
- [X] T081 [US7] Au mount de la page, déclencher `store.loadHistory(currentRef, 12)` (idempotent).
- [X] T082 [US7] Lancer vitest + e2e ; GREEN.

**Checkpoint US7** : historique visible et navigable.

---

## Phase 10: User Story 8 — Snapshot intangible (Priority: P1)

**Goal** : toggle snapshot + freeze UI + désactivation des mutations.

**Independent Test** : activer snapshot → bandeau visible → boutons Modifier et Recalculer désactivés ; désactiver → retour à l'état courant.

### Tests d'abord

- [X] T083 [P] [US8] Créer `frontend/tests/components/scoring/SnapshotToggle.test.ts` : (a) `<UiSwitch>` reflète `active` ; (b) sélecteur date liste les `entries` formatées FR ; (c) activation + sélection émet `enter(calcId)` ; (d) désactivation émet `exit()` ; (e) bandeau « SNAPSHOT du JJ/MM/AAAA — version v.X » visible quand active ; (f) bandeau non dismissible.
- [X] T084 [P] [US8] Étendre `stores/__tests__/scoring.test.ts` avec couverture snapshot (déjà partielle en T015) : (a) `enterSnapshot(calcId)` charge le summary historique correspondant via `historyByRef` (pas de fetch supplémentaire si déjà en cache) et active le mode ; (b) `editIndicateur` rejette pendant snapshot avec toast i18n ; (c) `recompute` rejette pendant snapshot ; (d) `exitSnapshot` purge `frozenCalculationId` et reprend les data live ; (e) entrée en snapshot purge `editingIndicateurIds`.
- [X] T085 [P] [US8] Créer `frontend/tests/e2e/scoring-snapshot-freeze.spec.ts` : seed ≥ 2 calculs, ouvrir `/scoring/BOAD`, activer toggle, sélectionner 1er calcul historique → bandeau snapshot affiché, boutons Modifier (sur drawer) et Recalculer **désactivés** (pas masqués) ; tentative clic → aucune mutation.
- [X] T086 [P] [US8] Créer `frontend/tests/e2e/scoring-snapshot-exit.spec.ts` : depuis état snapshot → désactiver toggle → bandeau disparaît, boutons réactivés, données live à nouveau visibles.

### Implémentation US8

- [X] T087 [US8] Créer `frontend/app/components/scoring/SnapshotToggle.vue` qui passe T083 (`<UiSwitch>` + `<UiSelect>` listant `entries` ; émet `enter`/`exit`).
- [X] T088 [US8] Étendre `frontend/app/stores/scoring.ts` `enterSnapshot` / `exitSnapshot` selon T084 ; faire passer la totalité de `scoring.test.ts`.
- [X] T089 [US8] Étendre `pages/scoring/[referentiel_code].vue` pour ajouter `<SnapshotToggle>` à côté de `<HistoryChart>` ; propager `disableEdit = store.isSnapshot` à `<PillarAccordion>` et `<IndicateurDrawer>` et `<RecalcButton>` ; afficher le bandeau snapshot en haut de page (composant inline ou via `<ScoreOverview :isSnapshot="true">`).
- [X] T090 [US8] Désactiver le drilldown indicateur en mode snapshot (R5) : dans `<IndicateurDrawer>`, message `Le détail des indicateurs n'est disponible qu'en mode courant` + boutons grisés.
- [X] T091 [US8] Lancer vitest + `pnpm test:e2e --grep snapshot` ; GREEN.

**Checkpoint US8** : snapshot fonctionnel et inviolable.

---

## Phase 11: User Story 9 — Export PDF (Priority: P2)

**Goal** : bouton Exporter PDF (dégradé si F51 absent).

**Independent Test** : si flag `F51_PDF_EXPORT=true` → clic télécharge un PDF ; sinon, bouton désactivé + tooltip.

### Tests d'abord

- [X] T092 [P] [US9] Créer `frontend/tests/components/scoring/ExportPdfButton.test.ts` : (a) flag off → bouton `disabled` + tooltip `Disponible bientôt` ; (b) flag on → clic appelle `POST /me/rapports/scoring/export` avec payload `{entity_type, entity_id, referentiel_code, score_calculation_id?}` ; (c) snapshot actif → payload inclut `score_calculation_id` ; (d) téléchargement déclenché via `<a download>`.
- [X] T093 [P] [US9] Créer `frontend/tests/e2e/scoring-export-pdf.spec.ts` (skip-able si `F51_PDF_EXPORT=false`) : clic Exporter → fichier PDF téléchargé, `Content-Type: application/pdf`.

### Implémentation US9

- [X] T094 [US9] Créer `frontend/app/components/scoring/ExportPdfButton.vue` qui passe T092 ; lecture du flag via `useRuntimeConfig().public.featureFlags.f51_pdf_export`.
- [X] T095 [US9] Brancher `<ExportPdfButton>` dans le slot `extra` de `<ScoreOverview>`.
- [X] T096 [US9] Lancer vitest + e2e (conditionnel) ; GREEN.

**Checkpoint US9** : export prêt, dégrade proprement.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose** : a11y, perf, source révoquée, reduced-motion, edge cases globaux, doc.

- [X] T097 [P] Créer `frontend/tests/e2e/scoring-revoked-source.spec.ts` : seed une source `revoked` via API admin → ouvrir `/scoring/BOAD` → assertion : `<RevokedSourceBadge>` visible sur l'indicateur + valeur grisée (CSS `line-through`).
- [X] T098 [P] Créer `frontend/tests/e2e/scoring-reduced-motion.spec.ts` : `page.emulateMedia({ reducedMotion: 'reduce' })` → assertion : pas d'animation gsap (durée 0 sur drawer/radar).
- [X] T099 [P] Audit a11y axe-core sur `/scoring/BOAD` (intégrer `@axe-core/playwright`) — 0 violation `serious`/`critical`. Vérifier : focus trap drawer + bottom sheet ; navigation clavier complète ; tableau `sr-only` sous radar.
- [ ] T100 [P] Mesurer LCP < 2 s p95 avec 50+ indicateurs : créer un test perf `frontend/tests/e2e/scoring-perf-lcp.spec.ts` (Playwright + `page.evaluate(performance)`), seed 50 indicateurs (ou réutiliser BOAD étendu), assertion LCP.
- [ ] T101 [P] Mesurer switch tab < 200 ms cache hit : extension de `scoring-tab-switch.spec.ts` avec assertion timing.
- [ ] T102 [P] Vérifier que `<VizLineChart>` du drawer indicateur n'est créé qu'à l'ouverture (R9) : ajouter assertion test unit `IndicateurDrawer.test.ts` (T047) — déjà couvert, juste valider GREEN.
- [ ] T103 [P] Documenter le miroir `SCORING_INDICATEUR_TO_ENTREPRISE_PATH` dans `frontend/app/lib/scoringEditableIndicateurs.ts` : commentaire pointant `backend/app/scoring/value_source.py` + ajouter une entrée dans `docs/devops/maintenance.md` (ou créer si absent) pour rappeler la double mise à jour.
- [ ] T104 [P] Vérifier que toutes les chaînes utilisateur passent par `useT()` : grep `frontend/app/components/scoring/` pour chaînes en dur — 0 occurrence (sauf placeholders ASCII).
- [ ] T105 [P] Lancer la suite complète `make test` (backend pytest --cov + frontend vitest) ; coverage backend ≥ 80 % ; coverage frontend ≥ 80 % sur `frontend/app/{components,composables,stores,lib}/scoring*`.
- [ ] T106 [P] Lancer `make lint` (ruff backend + eslint frontend) ; 0 erreur.
- [ ] T107 [P] Smoke quickstart : suivre `quickstart.md` étapes 1 à 14 manuellement ou via un script ; valider chaque check.
- [ ] T108 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F46 comme `done` et lier vers `specs/046-scoring-esg-ui/`.

---

## Dependencies — ordre de complétion des user stories

```text
Setup (T001-T006)
  └─► Foundational (T007-T020)            # endpoint history + store + service + composable + dashboard
        ├─► US1 (T021-T033)               # MVP livrable
        │     └─► US2 (T034-T045)         # tabs + comparaison
        │           └─► US3 (T046-T055)   # drilldown + drawer
        │                 └─► US4 (T056-T064)   # édition
        │                 └─► US5 (T065-T069)   # missing + chat CTA
        │                 └─► US6 (T070-T076)   # recalc + sync
        │                 └─► US7 (T077-T082)   # historique
        │                       └─► US8 (T083-T091)   # snapshot (dépend de l'historique)
        │                 └─► US9 (T092-T096)   # export PDF (P2)
        └─► Polish (T097-T108)            # exécutable en parallèle des dernières US
```

US4, US5, US6, US7, US9 sont **indépendantes** entre elles une fois US3 terminé (chacune peut être livrée et testée séparément). US8 dépend de US7 (besoin de l'historique). US2 dépend uniquement de US1 (besoin des tabs).

## Parallel Execution Opportunities

- **Setup** : T002, T003, T004, T005, T006 en parallèle (fichiers indépendants).
- **Foundational** : T008, T012, T013, T014, T015, T017, T019 en parallèle (T016 dépend de T015 ; T018 dépend de T017 ; T020 dépend de T019).
- **US1** : T021–T026 (tests) en parallèle, puis T027–T029 en parallèle, puis T030 → T031 → T032 séquentiels (page consolidante).
- **US2** : T034–T039 en parallèle, puis T040, T041, T043 en parallèle, puis T042 → T044.
- **US3** : T046–T049 en parallèle, puis T050, T051 en parallèle, puis T052 → T053 → T054.
- **US4** : T056–T059 en parallèle, puis T060, T061 en parallèle, puis T062 → T063.
- **US6** : T070–T072 en parallèle, puis T073 → T074 → T075.
- **US7** : T077, T078 en parallèle, puis T079 → T080 → T081.
- **US8** : T083–T086 en parallèle, puis T087, T088 en parallèle, puis T089 → T090.
- **Polish** : T097–T106 quasi tous parallèles.

## Implementation Strategy

1. **MVP = Setup + Foundational + US1** (≈ T001 → T033). Livre une page `/scoring` qui affiche le score global, le radar et les sources. Suffisant pour démo client.
2. **MVP+ navigation** : ajouter US2 (T034-T045). La PME peut comparer.
3. **MVP+ analyse** : ajouter US3 (T046-T055). Drilldown indicateurs.
4. **MVP+ édition** : ajouter US4 (T056-T064) puis US5 (T065-T069). La PME modifie ses données.
5. **Synchronisation et historique** : ajouter US6 (T070-T076), US7 (T077-T082). Le scoring vit avec l'utilisateur.
6. **Audit/archivage** : ajouter US8 (T083-T091). Snapshot pour l'export.
7. **Export PDF** (P2) : ajouter US9 (T092-T096) lorsque F51 est livré ; sinon bouton dégradé.
8. **Polish** : T097-T108 en continu pendant les dernières US.

Chaque checkpoint US est livrable et testable **indépendamment** — c'est le principe directeur.
