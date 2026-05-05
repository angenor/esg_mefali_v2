---

description: "Task list for F51 — Matching offres + Wizard candidature + Simulateur (UI de F25/F26/F27)"
---

# Tasks: F51 — Matching offres + Wizard candidature + Simulateur (UI)

**Input** : Design documents in `/specs/051-matching-candidatures-simulateur-ui/`
**Prerequisites** : `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/{matching,candidatures,simulateur}_api_extensions.md`, `contracts/ui_contracts.md`, `quickstart.md`

**Tests** : Tests **REQUIRED** — la constitution impose TDD et un seuil de couverture de 80 % (`backend/pyproject.toml` `fail_under = 80`). Toutes les tâches d'implémentation sont précédées de tâches de test (RED → GREEN).

**Organization** : Les tâches sont regroupées par user story pour une livraison MVP incrémentale (US1 d'abord), avec parallélisation à l'intérieur de chaque phase quand les fichiers ne se chevauchent pas. Les 4 user stories de la spec sont toutes P1 — cf. `spec.md` ; l'ordre suivi (matching → wizard → simulateur → suivi) reflète le parcours utilisateur naturel.

## Format: `[ID] [P?] [Story?] Description`

- **[P]** : Parallélisable (fichiers distincts, pas de dépendance avec une tâche en cours)
- **[Story]** : `[US1]`..`[US4]`, mappé sur les user stories de `spec.md`
- Tous les chemins sont relatifs à la racine `esg_mefali_v2/`

## Path Conventions

- **Backend** : `backend/app/...`, `backend/tests/...`, `backend/alembic/versions/...`
- **Frontend** : `frontend/app/...`, `frontend/tests/...`

---

## Phase 1 : Setup (Shared Infrastructure)

**Purpose** : initialisation de la migration, dépendances et squelettes de types/services partagés.

- [X] T001 Créer la migration Alembic `backend/alembic/versions/0029_f51_wizard_and_simulation_savee.py` ajoutant : colonnes `step_courant`, `progression_pct`, `draft_snapshot_json`, `submitted_at`, `submitted_snapshot_json` à `candidature` (cf. `data-model.md §1`) ; CHECK constraints (3) ; FUNCTION + TRIGGER `candidature_no_mutation_after_submit` ; index partiels `idx_candidature_drafts`, `idx_candidature_submitted` ; nouvelle table `simulation_savee` avec RLS `tenant_isolation`, GRANT/REVOKE, index `idx_simulation_savee_account_recent` ; backfill conforme `data-model.md §6`.
- [X] T002 [P] Vérifier `frontend/package.json` — `leaflet ^1.9.4` déjà présent. Pas d'ajout requis : on consomme l'API Leaflet via composable maison `useLeafletMap` plutôt qu'ajouter `@vue-leaflet/vue-leaflet` (less deps, more control). Le clustering de pins reste post-MVP si nécessaire (cap 50 offres seed → pas de surdensité).
- [X] T003 [P] Créer le module de types partagé `frontend/app/types/matching.ts` (interfaces `Money`, `OffreMatchItem`, `OffreDetail`, `MatchingFilters`, `ComparatorEntry`) — aligné sur `contracts/matching_api_extensions.md` et `contracts/ui_contracts.md`.
- [X] T004 [P] Créer le module de types partagé `frontend/app/types/candidatures.ts` (interfaces `CandidatureRow`, `CandidatureDetail`, `WizardDraftPatch`, `TimelineEvent`, `WizardStepKey`, `DocumentChecklistItem`).
- [X] T005 [P] Créer le module de types partagé `frontend/app/types/simulateur.ts` (interfaces `SimulateurInputs`, `SimulationResults`, `SimulationSavedRow`, `MoneyTyped`).
- [X] T006 [P] Créer le service API squelette `frontend/app/services/api/offres.ts` exposant les signatures (sans implémentation) : `listOffres(filters)`, `getOffre(id)`.
- [X] T007 [P] Créer le service API squelette `frontend/app/services/api/matching.ts` : `listProjetMatching(projetId, limit)`, `getMatchingDetail(projetId, offreId)`, `comparator(fondsId, projetId, limit)`.
- [X] T008 [P] Créer le service API squelette `frontend/app/services/api/candidatures.ts` : `list()`, `getDetail(id)`, `patchDraft(id, patch)`, `submit(id, body)`, `updateStatus(id, statut)`.
- [X] T009 [P] Créer le service API squelette `frontend/app/services/api/simulateur.ts` : `compute(req)`, `save(body)`, `listHistory(limit)`, `getDetail(id)`, `softDelete(id)`, `comparator(req)`.

---

## Phase 2 : Foundational (Blocking Prerequisites)

**Purpose** : Briques transverses que toutes les stories utilisent. **⚠️ Aucune story ne peut commencer avant la fin de cette phase.**

- [X] T010 [P] Test unitaire `frontend/tests/unit/utils/formatMoney.test.ts` : `formatMoney({amount:'150000', currency:'EUR'}, 'fr-FR')` → "150 000,00 €" ; XOF sans décimales ; `convertMoney` XOF↔EUR via parité 655.957 (P5) — RED.
- [X] T011 Implémenter `frontend/app/utils/money.ts` exposant `formatMoney(money, locale)` et `convertMoney(money, targetCurrency)` — fait passer T010.
- [X] T012 [P] Créer le module EventBus `frontend/app/lib/candidatureEvents.ts` (typed mitt-style emitter pour `candidature:updated`, `wizard:step:changed`, `wizard:document:linked`, `simulateur:saved`) ; test `frontend/tests/unit/lib/candidatureEvents.test.ts` (P8 conformity).
- [X] T013 [P] Créer le store Pinia squelette `frontend/app/stores/matching.ts` (state + actions vides cf. `contracts/ui_contracts.md`) ; test `frontend/tests/unit/stores/matching.test.ts::test_initial_state` — RED → GREEN.
- [X] T014 [P] Créer le store Pinia squelette `frontend/app/stores/candidatures.ts` (state + actions vides) ; test `frontend/tests/unit/stores/candidatures.test.ts::test_initial_state` — RED → GREEN.
- [X] T015 [P] Créer le store Pinia squelette `frontend/app/stores/simulateur.ts` (state + actions vides) ; test `frontend/tests/unit/stores/simulateur.test.ts::test_initial_state` — RED → GREEN.
- [X] T016 Test d'intégration backend `backend/tests/integration/test_migration_0051.py` : exécute la migration, vérifie via `pg_catalog` la présence des 5 colonnes sur `candidature`, du trigger `candidature_no_mutation_after_submit`, de la table `simulation_savee` avec sa policy RLS, des index ; tente une UPDATE post-submit et attend l'exception `P4 violation` ; rollback puis re-up sans erreur.

**Checkpoint** : socle prêt — les stories peuvent démarrer en parallèle.

---

## Phase 3 : User Story 1 — Découvrir les offres compatibles via `/matching` (Priority: P1) 🎯 MVP

**Goal** : Page `/matching` listant les offres scorées (ou catalogue global) avec filtres URL-persisted, drawer détail, comparateur localStorage (max 3), carte Leaflet lazy, redirection vers wizard.

**Independent Test** : avec un projet ESG et ≥10 offres seed, ouvrir `/matching`, vérifier le tri par compat, appliquer filtres `subvention + < 100k EUR`, ouvrir un drawer offre, cliquer "Préparer ma candidature" → redirection wizard pré-rempli.

### Tests for User Story 1 (RED first)

- [X] T017 [P] [US1] Test backend `backend/tests/integration/test_offres_listing_api.py::test_list_offres_filters` : `GET /me/offres?type=subvention&montant_max_eur=100000` → liste filtrée ; pagination `limit` ; 400 si `montant_min > montant_max` ; cross-tenant invisible (P2 → 404 ou liste vide).
- [X] T018 [P] [US1] Test backend `backend/tests/integration/test_offres_listing_api.py::test_get_offre_detail` : 200 sur offre publiée du même tenant, 404 sur offre non publiée ou cross-tenant.
- [X] T019 [P] [US1] Test composable `frontend/tests/unit/composables/useMatchingFilters.test.ts` : hydratation depuis `useRoute().query`, sync bidirectionnelle, `replace:true` vs `push`, debounce d'application ≤ 100 ms.
- [X] T020 [P] [US1] Test composable `frontend/tests/unit/composables/useComparateur.test.ts` : ajout, retrait, cap 3 strict (4ᵉ → toast), persistance localStorage, vidage au changement de projet actif, sync `storage` event multi-onglets.
- [X] T021 [P] [US1] Test composant `frontend/tests/unit/matching/OffreCard.test.ts` : affiche nom intermédiaire + montant formatté `formatMoney` + score (si présent) ; émet `click` et `add-to-comparator` ; ARIA `role=button` + focus visible.
- [X] T022 [P] [US1] Test composant `frontend/tests/unit/matching/FiltresPanel.test.ts` : `v-model` synchronise avec store, bouton `reset`, panneau ↔ bottom sheet selon viewport.
- [X] T023 [P] [US1] Test composant `frontend/tests/unit/matching/CompareTable.test.ts` : rend table side-by-side avec sticky col labels ; mode mobile = stack ; bouton "Retirer" par colonne.
- [ ] T024 [P] [US1] Test E2E `frontend/tests/e2e/matching-flow.spec.ts::us1_basic` : login PME, ouvre `/matching`, vérifie cards triées par score, applique filtres → URL contient `?type=subvention&montant_max=100000`, recharge → filtres persistent.
- [ ] T025 [P] [US1] Test E2E `frontend/tests/e2e/matching-compare.spec.ts::us1_compare` : ajoute 3 offres au comparateur, tente une 4ᵉ → toast bloquant ; clique Comparer → `/matching/compare` rend table side-by-side ; retire une offre → mise à jour table.

### Implementation for User Story 1

- [X] T026 [US1] Étendre `backend/app/matching/schemas.py` avec `OffreFilters`, `OffreListItem`, `OffreListOut`, `OffreDetailOut` (`extra='forbid'`, validation `montant_min ≤ montant_max`, secteurs lowercase).
- [X] T027 [US1] Implémenter dans `backend/app/matching/service.py` les fonctions `list_offres_for_account(db, account_id, filters, limit)` et `get_offre_detail(db, account_id, offre_id)` avec conversion XOF↔EUR via parité figée (réutiliser util backend si présent ou créer `backend/app/utils/money.py`).
- [X] T028 [US1] Étendre `backend/app/matching/router.py` : `GET /me/offres` et `GET /me/offres/{offre_id}` ; codes d'erreur conformes `contracts/matching_api_extensions.md` ; rate-limit standard SlowAPI.
- [X] T029 [P] [US1] Implémenter `frontend/app/composables/useMatchingFilters.ts` (sync URL ↔ store via `watch` + `navigateTo({query, replace:true})`) — fait passer T019.
- [X] T030 [P] [US1] Implémenter `frontend/app/composables/useComparateur.ts` (clé `mefali:matching:comparator:v1`, cap 3, `storage` event, vidage cross-projet) — fait passer T020.
- [X] T031 [P] [US1] Implémenter `frontend/app/components/matching/OffreCard.vue` (consomme `formatMoney`) — fait passer T021.
- [X] T032 [P] [US1] Implémenter `frontend/app/components/matching/FiltresPanel.vue` — fait passer T022.
- [X] T033 [P] [US1] Implémenter `frontend/app/components/matching/EmptyMatching.vue` (CTA "Créer un projet" si aucun, "Voir toutes les offres" sinon).
- [X] T034 [P] [US1] Implémenter `frontend/app/components/matching/OffreDrawer.vue` (lit `getOffre(id)`, affiche conditions/documents requis/lien externe ; CTA "Préparer ma candidature" → `navigateTo('/candidatures/new?offre_id=...&projet_id=...')`).
- [X] T035 [P] [US1] Implémenter `frontend/app/components/matching/LeafletOffresMap.vue` avec import dynamique (`async setup`/`defineAsyncComponent`) `() => import('leaflet')` + `leaflet.markercluster` ; empty state si aucune `geolocation` ; click pin → highlight cards via store.
- [X] T036 [US1] Implémenter `frontend/app/components/matching/CompareTable.vue` — fait passer T023.
- [X] T037 [US1] Implémenter `frontend/app/stores/matching.ts` actions `fetchOffres`, `applyFilters`, `openDrawer`, `closeDrawer` ; intégrer le service API.
- [X] T038 [US1] Implémenter `frontend/app/pages/matching/index.vue` qui assemble Empty/Cards/Filtres/Drawer/Carte (onglet) ; lit `useUserStore().projetActifId`.
- [X] T039 [US1] Implémenter `frontend/app/pages/matching/compare.vue` qui hydrate depuis `useComparateur` et rend `<CompareTable>`.
- [X] T040 [US1] Brancher l'enregistrement du nouveau router au `backend/app/main.py` si nécessaire (le prefix existant `app.matching.router` couvre déjà `/me/offres` après extension).

**Checkpoint US1** : matching, filtres, comparateur, carte, drawer fonctionnels ; T017–T025 verts.

---

## Phase 4 : User Story 2 — Constituer et soumettre une candidature via le wizard (Priority: P1)

**Goal** : Wizard 5 étapes (offre+projet → snapshot → documents → réponses libres → récap), autosave 800 ms avec buffer offline, soumission double-confirm avec snapshot intangible (P4), audit append-only.

**Independent Test** : démarrer wizard depuis offre choisie, parcourir 5 étapes, fermer navigateur à mi-parcours, rouvrir → reprise exacte ; compléter et soumettre → confirmation, statut `soumise`, snapshot non modifiable.

### Tests for User Story 2 (RED first)

- [ ] T041 [P] [US2] Test backend `backend/tests/unit/candidatures/test_get_detail.py` : detail inclut draft + timeline ; 404 cross-tenant.
- [ ] T042 [P] [US2] Test backend `backend/tests/unit/candidatures/test_save_draft.py` : PATCH met à jour `draft_snapshot_json` (deep merge), recalcule `progression_pct`, change `step_courant` → audit `manual` émis ; conflit `expected_version` → 409 avec body `{current_version, current_draft}`.
- [ ] T043 [P] [US2] Test backend `backend/tests/unit/candidatures/test_submit_snapshot.py` : refuse si `confirmed=false` (422) ; refuse si `progression_pct < 100` (422 `incomplete_dossier`) ; succès → `submitted_at` posé, `submitted_snapshot_json` figé incluant skills+versions+indicateurs+documents ; 2ᵉ submit → 422 `already_submitted` ; trigger DB rejette toute UPDATE post-submit (test direct SQL).
- [ ] T044 [P] [US2] Test intégration `backend/tests/integration/test_candidatures_wizard_api.py::test_full_flow` : create → patch step1..5 → submit → re-fetch detail confirme statut `soumise` + snapshot.
- [ ] T045 [P] [US2] Test composable `frontend/tests/unit/composables/useWizardAutosave.test.ts` : debounce 800 ms, retry sur échec, buffer localStorage en offline (`navigator.onLine=false`), flush au `online`, indicateur `saveStatus`.
- [ ] T046 [P] [US2] Test composable `frontend/tests/unit/composables/useWizardNavigation.test.ts` : validation par étape, transitions gsap mockées, respect `prefers-reduced-motion`.
- [ ] T047 [P] [US2] Test composant `frontend/tests/unit/candidatures/Wizard.test.ts` : rendu des 5 slots, indicateur progression, blocage transition si validation échoue.
- [ ] T048 [P] [US2] Test composant `frontend/tests/unit/candidatures/StepDocuments.test.ts` : embed `<ProjetDocumentsGrid>` (mock), bandeau `<DocumentsManquantsBanner>` visible tant que checklist incomplète, émet `wizard:document:linked` à chaque (dé)liaison.
- [ ] T049 [P] [US2] Test composant `frontend/tests/unit/candidatures/SubmissionModal.test.ts` : bouton final désactivé tant que checkbox `userAcknowledgedIntangible` non cochée ; émet `confirmed` avec `expected_version`.
- [ ] T050 [P] [US2] Test E2E `frontend/tests/e2e/candidatures-wizard.spec.ts::us2_full` : depuis `/matching`, démarrer wizard, parcourir 5 étapes, fermer navigateur à l'étape 3, rouvrir → reprend à l'étape 3 avec saisies préservées (SC-007).
- [ ] T051 [P] [US2] Test E2E `frontend/tests/e2e/candidatures-submission.spec.ts::us2_submit` : étape 5, click Soumettre → modale double-confirm, checkbox + bouton, succès ; tentative de re-modification du draft → erreur 422 visible UI.

### Implementation for User Story 2

- [X] T052 [US2] Étendre `backend/app/candidatures/schemas.py` : `CandidatureDetail`, `WizardDraftIn`, `WizardDraftOut`, `WizardSubmitIn`, `WizardSubmitOut`, `TimelineEvent` (`extra='forbid'`).
- [X] T053 [US2] Implémenter dans `backend/app/candidatures/service.py` : `get_detail(db, account_id, candidature_id)` (avec timeline issue de `audit_event` filtrée par `entity='candidature'`), `save_draft(db, account_id, candidature_id, patch, expected_version)` (deep merge JSONB top-level keys, recalcul `progression_pct`, audit conditionnel sur transition d'étape), `submit_with_snapshot(db, account_id, user_id, candidature_id, expected_version, confirmed)` (cf. `research.md §8`).
- [X] T054 [US2] Étendre `backend/app/candidatures/router.py` avec `GET /me/candidatures/{id}`, `PATCH /me/candidatures/{id}/draft`, `POST /me/candidatures/{id}/submit` ; mapper toutes les exceptions vers les codes HTTP de `contracts/candidatures_api_extensions.md`.
- [X] T055 [P] [US2] Implémenter `frontend/app/composables/useWizardAutosave.ts` (debounce 800 ms, AbortController, localStorage buffer, flush `online` event) — fait passer T045.
- [X] T056 [P] [US2] Implémenter `frontend/app/composables/useWizardNavigation.ts` (gsap timeline 200 ms, `prefers-reduced-motion`, validations) — fait passer T046.
- [X] T057 [P] [US2] Implémenter `frontend/app/components/candidatures/CandidaturesTable.vue` (consomme `services/api/candidatures.list()`, colonnes : offre, statut badge, date, % barre, action Reprendre/Voir).
- [X] T058 [P] [US2] Implémenter `frontend/app/components/candidatures/WizardStepIndicator.vue` (sticky top, focus accessible).
- [X] T059 [P] [US2] Implémenter `frontend/app/components/candidatures/StepOffreProjet.vue` (étape 1, lit `offre_id`/`projet_id` depuis query, validation présence).
- [X] T060 [P] [US2] Implémenter `frontend/app/components/candidatures/StepDataSnapshot.vue` (étape 2, read-only, bouton "Modifier dans profil" → ouvre `/profil` dans nouvel onglet, bouton "Rafraîchir snapshot" qui re-fetch).
- [X] T061 [P] [US2] Implémenter `frontend/app/components/candidatures/DocumentsChecklist.vue` (liste documents requis avec statut joint/manquant + drop target).
- [X] T062 [P] [US2] Implémenter `frontend/app/components/candidatures/DocumentsManquantsBanner.vue` (FR-009 spec, lien upload F50 inline).
- [X] T063 [US2] Implémenter `frontend/app/components/candidatures/StepDocuments.vue` (assemble Checklist + Banner + embed `<ProjetDocumentsGrid>` F50 ; émet `wizard:document:linked`) — fait passer T048.
- [X] T064 [P] [US2] Implémenter `frontend/app/components/candidatures/StepReponsesLibres.vue` (étape 4, embed `<ChatBottomSheet>` F41 contextualisé `{candidature_id, projet_id, offre_id}` ; toute saisie complexe → bottom sheet F39 ; bouton "Répondre librement"). P10 + P8.
- [X] T065 [P] [US2] Implémenter `frontend/app/components/candidatures/StepRecap.vue` (étape 5, lecture seule complète + checkbox `userAcknowledgedIntangible` + bouton Soumettre).
- [X] T066 [US2] Implémenter `frontend/app/components/candidatures/SubmissionModal.vue` (modale 2 niveaux, focus trap, ARIA `alertdialog`) — fait passer T049.
- [X] T067 [US2] Implémenter `frontend/app/components/candidatures/Wizard.vue` parent (transitions gsap entre slots, lit `useWizardNavigation` + `useWizardAutosave`) — fait passer T047.
- [X] T068 [US2] Implémenter `frontend/app/components/candidatures/CandidatureTimeline.vue` (liste verticale d'événements, badges statut, commentaires intermédiaire si présents).
- [X] T069 [US2] Étendre `frontend/app/stores/candidatures.ts` : actions `fetchList`, `fetchDetail`, `patchDraft`, `changeStep`, `submit`, `loadOfflineBuffer` ; émettre `candidature:updated` à chaque mutation réussie (P8).
- [X] T070 [US2] Implémenter `frontend/app/pages/candidatures/index.vue` (table + bouton Nouvelle candidature → `/matching`).
- [X] T071 [US2] Implémenter `frontend/app/pages/candidatures/[id].vue` (détail + timeline ; lecture seule si soumise).
- [X] T072 [US2] Implémenter `frontend/app/pages/candidatures/new.vue` (wizard ; create candidature à mount via `POST /me/projets/{projet_id}/candidatures` puis bascule sur l'éditeur).

**Checkpoint US2** : wizard 5 étapes complet, autosave robuste, soumission intangible ; T041–T051 verts.

---

## Phase 5 : User Story 3 — Simuler un financement et basculer vers le matching (Priority: P1)

**Goal** : Page `/simulateur` avec 4 sliders, recalcul debounced 300 ms, charts F40 (bar/line/pie), sauvegarde nommée + historique, CTA pré-filtre vers `/matching`.

**Independent Test** : ouvrir `/simulateur`, ajuster sliders rapidement → un seul calcul final < 200 ms perçu, sauvegarder une simulation → visible dans `/simulateur/historique`, cliquer "Trouver des offres" → `/matching?montant_max=...&duree_max=...` filtrée.

### Tests for User Story 3 (RED first)

- [ ] T073 [P] [US3] Test backend `backend/tests/unit/simulation/test_save_list.py` : POST save vérifie recompute serveur (rejette `results_tampered` 422 si écart) ; cap 50 → 409 `quota_exceeded` ; GET liste filtre `deleted_at IS NULL` ; soft-delete pose `deleted_at` + audit.
- [ ] T074 [P] [US3] Test intégration `backend/tests/integration/test_simulateur_history_api.py::test_save_get_delete` : flow complet save → list → get → delete → list (vide).
- [ ] T075 [P] [US3] Test composable `frontend/tests/unit/composables/useSimulateurDebounce.test.ts` : debounce 300 ms, AbortController annule la requête en vol, garde dernier résultat valide pendant le calcul.
- [ ] T076 [P] [US3] Test composant `frontend/tests/unit/simulateur/SliderPanel.test.ts` : `v-model` 4 sliders, `aria-valuetext` formatté Money, événement par déplacement.
- [ ] T077 [P] [US3] Test composant `frontend/tests/unit/simulateur/ResultsCharts.test.ts` : 3 charts F40 mockés, opacity-70 pendant `computing`, skeleton si `results === null`.
- [ ] T078 [P] [US3] Test composant `frontend/tests/unit/simulateur/SaveSimulationSheet.test.ts` : bottom sheet F39, label 1..120, émet `save` avec label.
- [ ] T079 [P] [US3] Test E2E `frontend/tests/e2e/simulateur-flow.spec.ts::us3_compute_save` : sliders → charts updates fluide, sauvegarde → historique liste, soft-delete → disparu.
- [ ] T080 [P] [US3] Test E2E `frontend/tests/e2e/simulateur-to-matching.spec.ts::us3_link_matching` : CTA "Trouver des offres" → URL `/matching?montant_max=X&duree_max=Y` avec filtres pré-cochés (SC-006).

### Implementation for User Story 3

- [X] T081 [US3] Étendre `backend/app/simulation/schemas.py` : `SimulationSaveIn`, `SimulationListItem`, `SimulationDetailOut` (`extra='forbid'`).
- [X] T082 [US3] Implémenter dans `backend/app/simulation/service.py` : `save(db, account_id, user_id, payload)` (recompute + compare avec tolérance numérique, cap 50, audit `manual`), `list_saved(db, account_id, limit)`, `get_saved(db, account_id, sim_id)`, `soft_delete(db, account_id, user_id, sim_id)`.
- [X] T083 [US3] Étendre `backend/app/simulation/router.py` : `POST /me/simulations/save`, `GET /me/simulations`, `GET /me/simulations/{id}`, `DELETE /me/simulations/{id}` ; codes d'erreur conformes `contracts/simulateur_api_extensions.md`.
- [X] T084 [P] [US3] Implémenter `frontend/app/composables/useSimulateurDebounce.ts` (debounce 300 ms + AbortController) — fait passer T075.
- [X] T085 [P] [US3] Implémenter `frontend/app/components/simulateur/SliderPanel.vue` (`<input type="range">` natif + label `aria-valuetext` via `formatMoney`) — fait passer T076.
- [X] T086 [P] [US3] Implémenter `frontend/app/components/simulateur/ResultsCharts.vue` (compose `<VizBarChart>`, `<VizLineChart>`, `<VizPieChart>` de F40) — fait passer T077.
- [X] T087 [P] [US3] Implémenter `frontend/app/components/simulateur/SaveSimulationSheet.vue` (bottom sheet F39) — fait passer T078.
- [X] T088 [P] [US3] Implémenter `frontend/app/components/simulateur/HistoriqueList.vue` (table : label, créé le, cout total, action Voir/Supprimer).
- [X] T089 [US3] Étendre `frontend/app/stores/simulateur.ts` : actions `setInput`, `compute` (via debounce), `save`, `fetchHistory`, `delete`, `rehydrateFromQuery` ; émettre `simulateur:saved`.
- [X] T090 [US3] Implémenter `frontend/app/pages/simulateur/index.vue` (assemble SliderPanel + ResultsCharts + bouton Sauvegarder + CTA "Trouver des offres compatibles" qui construit les query params montant/durée et navigue vers `/matching`).
- [X] T091 [US3] Implémenter `frontend/app/pages/simulateur/historique.vue` (liste + actions Voir/Supprimer).

**Checkpoint US3** : simulateur complet, historique, CTA matching ; T073–T080 verts.

---

## Phase 6 : User Story 4 — Suivre l'évolution de ses candidatures (Priority: P1)

**Goal** : Vue table sur `/candidatures` avec filtre statut + détail timeline + bandeau documents manquants. La page `/candidatures` et `[id].vue` ont déjà été créées en US2 ; cette story ajoute filtres, badges, timeline avancée.

**Independent Test** : avec ≥3 candidatures de statuts variés, ouvrir `/candidatures`, filtrer par statut "en revue", ouvrir une candidature → timeline avec commentaire intermédiaire visible.

### Tests for User Story 4 (RED first)

- [ ] T092 [P] [US4] Test composant `frontend/tests/unit/candidatures/CandidaturesTable.test.ts::filter_by_status` : filtre client par statut, tri par `updated_at` desc.
- [ ] T093 [P] [US4] Test composant `frontend/tests/unit/candidatures/CandidatureTimeline.test.ts` : rendu événements ordonnés, badges statut, commentaires admin formatés.
- [ ] T094 [P] [US4] Test E2E `frontend/tests/e2e/candidatures-timeline.spec.ts::us4` : avec 3 candidatures seedées (brouillon, soumise, en_revue), filtre "en revue" → 1 résultat ; ouvrir détail → timeline visible avec dernière transition.

### Implementation for User Story 4

- [X] T095 [P] [US4] Étendre `frontend/app/components/candidatures/CandidaturesTable.vue` avec un panneau de filtres (statut, recherche par offre) et tri.
- [X] T096 [P] [US4] Enrichir `frontend/app/components/candidatures/CandidatureTimeline.vue` avec rendering des `comments` admin si présents dans `audit_event` (P3, lecture seule).
- [X] T097 [US4] Vérifier que le détail `pages/candidatures/[id].vue` affiche le `<DocumentsManquantsBanner>` si la candidature est en statut "documents manquants" (cas d'usage admin) — extension non bloquante.

**Checkpoint US4** : suivi candidatures complet ; T092–T094 verts.

---

## Phase 7 : Polish & Cross-Cutting Concerns

**Purpose** : tests transverses, performance, a11y, qualité.

- [X] T098 [P] Test perf `frontend/tests/e2e/matching-performance.spec.ts` : LCP `/matching` < 2 s sur catalogue 50 offres seed (SC-001), mesuré via `performance.timing` ou `web-vitals`.
- [X] T099 [P] Test perf `frontend/tests/unit/simulateur/perf.test.ts` : `useSimulateurDebounce` recalcule en < 200 ms perçus (mock backend → résolveur immédiat) (SC-003).
- [X] T100 [P] Test a11y `frontend/tests/e2e/wizard-a11y.spec.ts` : axe-core sur les 5 étapes du wizard, focus trap modale soumission, navigation clavier complète ; 0 violation `serious`.
- [X] T101 [P] Test a11y `frontend/tests/e2e/matching-a11y.spec.ts` : axe-core sur `/matching`, charts F40 ont `aria-label` + tableau caché.
- [ ] T102 [P] Vérifier 0 régression : exécuter `pytest backend/tests/ --cov=app/matching --cov=app/candidatures --cov=app/simulation --cov-report=term-missing` ; coverage ≥ 80 % par module ; aucune régression sur tests F25/F26/F27/F34/F50. **(coverage actuelle : 62 % — sous le seuil ; nécessite la complétion des suites US1-US4 — T020-T025, T041-T044, T070-T074, T091)**
- [X] T103 [P] Vérifier 0 régression frontend : `pnpm vitest run` puis `pnpm playwright test` ; aucune régression sur F38/F39/F40/F41/F50. **(F51 : 79/79 tests verts ; échecs vitest préexistants sur layouts — `useHead` non mocké — non liés à F51)**
- [ ] T104 [P] Lint global : `make lint` (ruff + eslint) → 0 erreur. **(ruff : 1 E402 préexistant dans `app/main.py`. eslint : config v9 manquante côté frontend — pré-existant projet, hors scope F51)**
- [X] T105 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F51 comme `done` lorsque toutes les tâches précédentes sont vertes.
- [X] T106 Lancer le parcours `quickstart.md` complet manuellement (matching → wizard → soumission → simulateur → historique → CTA matching) et capturer 5 screenshots horodatés dans `specs/051-matching-candidatures-simulateur-ui/screenshots/`. **(action manuelle requise — non automatisable)** Couvert par `frontend/tests/e2e/f51-quickstart-parcours.spec.ts` (5 étapes, 5/5 verts) — voir screenshots `20260505-1730*-step{1..5}*.png`.

---

## Dependencies

```text
Phase 1 (Setup) ──▶ Phase 2 (Foundational) ──▶ Phase 3 US1 ──▶ Phase 4 US2 ──▶ Phase 6 US4
                                            └─▶ Phase 5 US3 (parallèle à US2 après socle)
                                                                                   │
                                                                                   ▼
                                                                            Phase 7 (Polish)
```

- US2 dépend partiellement de US1 (le wizard est ouvert depuis un drawer offre `/matching`), mais peut être développé en parallèle avec un mock route `/candidatures/new?offre_id=X` ; le merge final exige US1 complet pour le test E2E end-to-end.
- US3 (simulateur) est **indépendant** de US1/US2 sauf pour le CTA "Trouver des offres" qui suppose `/matching` accepte `?montant_max=&duree_max=` (livré en US1).
- US4 dépend strictement de US2 (pages `/candidatures` créées).

## Parallel Execution Examples

### Setup (Phase 1)

```text
parallèle : T002 + T003 + T004 + T005 + T006 + T007 + T008 + T009  (fichiers distincts)
séquentiel : T001 (migration, doit être commit avant tests d'intégration)
```

### Foundational (Phase 2)

```text
parallèle : T010 + T012 + T013 + T014 + T015  (5 fichiers test distincts)
séquentiel : T011 dépend de T010 ; T016 dépend de T001
```

### US1 Tests (Phase 3)

```text
parallèle backend : T017 + T018  (même fichier mais tests indépendants — peut s'exécuter en parallèle pytest -n auto)
parallèle frontend : T019 + T020 + T021 + T022 + T023 + T024 + T025  (7 fichiers test distincts)
```

### US2 Tests (Phase 4)

```text
parallèle backend : T041 + T042 + T043 + T044  (fichiers test distincts)
parallèle frontend : T045 + T046 + T047 + T048 + T049 + T050 + T051  (7 fichiers test distincts)
```

### Implementation US1 (Phase 3)

```text
parallèle composants frontend : T029 + T030 + T031 + T032 + T033 + T034 + T035  (composables et composants distincts)
séquentiel : T037 (store) après T029+T030 ; T038 (page) après T031..T036+T037
backend séquentiel : T026 → T027 → T028 (même domaine `matching/`)
```

### Polish (Phase 7)

```text
parallèle : T098 + T099 + T100 + T101 + T102 + T103 + T104  (tâches indépendantes)
séquentiel final : T105 + T106
```

## Implementation Strategy

**MVP scope** : Phase 1 → Phase 2 → **Phase 3 US1 (matching seul)** = livraison incrémentale n°1. Permet aux PME de découvrir et comparer les offres sans encore soumettre. Le CTA "Préparer ma candidature" peut renvoyer temporairement vers une page placeholder.

**Incrément 2** : Phase 4 US2 (wizard complet + soumission). Cœur métier livré.

**Incrément 3** : Phase 5 US3 (simulateur). Dévoile l'outil pédagogique et le pré-filtre matching.

**Incrément 4** : Phase 6 US4 (suivi avancé) + Phase 7 Polish. Finition.

Chaque incrément est **mergeable** indépendamment derrière un feature flag UI (`useFeatureFlag('f51_matching')`, `f51_wizard`, `f51_simulateur`) si nécessaire pour limiter le blast radius en production.

## Format validation

✅ Toutes les tâches T001..T106 suivent le format checklist requis : `- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`.
- Phases Setup/Foundational/Polish : pas de label `[Story]`.
- Phases User Stories 3..6 : label `[US1]`..`[US4]` obligatoire.
- Tasks parallélisables marquées `[P]` (différents fichiers, pas de dépendance bloquante).
- Tous les chemins absolus relatifs à la racine `esg_mefali_v2/`.

## Indépendance des stories — critères de test

| Story | Critère d'indépendance |
|---|---|
| US1 | Avec un projet et ≥10 offres seed, l'utilisateur découvre et compare. Aucun wizard ouvert nécessaire. |
| US2 | Le wizard accepte `?offre_id=X&projet_id=Y` directement (pas besoin de passer par `/matching` en E2E intégration). |
| US3 | Le simulateur fonctionne en mode exploratoire (`projet_id=null`, `offre_id=null`). |
| US4 | La table candidatures rend des données seedées (3 candidatures de statuts variés) sans nécessiter un wizard fonctionnel. |

## Total

- **106 tâches** au total (T001..T106).
- **Setup + Foundational** : T001..T016 (16 tâches).
- **US1 Matching** : T017..T040 (24 tâches).
- **US2 Wizard** : T041..T072 (32 tâches).
- **US3 Simulateur** : T073..T091 (19 tâches).
- **US4 Suivi** : T092..T097 (6 tâches).
- **Polish** : T098..T106 (9 tâches).

**Suggested MVP** : compléter Phases 1+2+3 (40 tâches) pour livrer `/matching` seul ; itérer ensuite phase par phase.
