# Tasks: Empreinte carbone UI (F47)

**Input**: Design documents from `/specs/047-empreinte-carbone-ui/`
**Prerequisites** : `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (tous présents).

**Tests** : la spec liste pour chaque US un *Independent Test* et le plan détaille un plan de tests `vitest` + `pytest` + Playwright. **Tests inclus** dans cette tasks list.

**Organisation** : tâches groupées par user story (P1 d'abord = MVP, puis P2). Chaque US est livrable et testable indépendamment.

## Format : `- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`

- **[P]** : parallélisable (fichier différent, aucune dépendance sur tâches non terminées).
- **[USx]** : tâche d'une user story (US1…US9).
- Phases Setup / Foundational / Polish : pas de label US.

---

## Phase 1 — Setup (Shared Infrastructure)

**Purpose** : structure de dossiers + scaffolding partagé.

- [X] T001 Créer les dossiers `frontend/app/components/carbone/`, `frontend/app/pages/carbone/`, `frontend/app/composables/__tests__/`, `frontend/app/lib/__tests__/`, `frontend/app/stores/__tests__/` (avec `.gitkeep` temporaire dans `pages/carbone/`) et `backend/tests/carbon/` (avec un `__init__.py` vide).
- [X] T002 [P] Créer `frontend/app/types/carbon.ts` exportant les types TS miroirs définis dans `data-model.md` §3.1 : `Scope`, `CarbonPosteCode`, `CarbonBreakdownLine`, `CarbonFootprint`, `CarbonIndexEntry`, `CarbonSourceItemPayload`, `CarbonEditLineRequest`, `CarbonRecomputeResponse`, `CarbonEditLineResponse`, `WizardDraft`. Conserver tous les `Decimal` en `string` (pas de `number`).
- [X] T003 [P] Créer `frontend/app/lib/groupCarbonByScope.ts` exportant la constante figée `CARBON_EXPECTED_POSTS_BY_SCOPE` (cf. `data-model.md` §6) et la fonction pure `groupCarbonByScope(breakdown: CarbonBreakdownLine[]): GroupedBreakdown` (signature exacte définie dans `data-model.md` §3.2). Aucune dépendance Vue/Nuxt — fonction pure.
- [X] T004 [P] Créer `frontend/app/lib/computeCarbonCoverage.ts` exportant `computeCarbonCoverage(grouped: GroupedBreakdown): CoverageSnapshot` (signature exacte définie dans `data-model.md` §3.3). Pure ; couverture basse `isLow = globalPct < 60`.
- [X] T005 [P] Étendre `frontend/app/locales/fr.ts` avec le namespace complet `carbon.*` : `pageTitle`, `kpis.{total,deltaVsLastYear,coverage,noComparison}`, `scopes.{1,2,3}`, `posts.{combustion_fixe,combustion_mobile,fugitives,electricite,vapeur,chaleur,froid,achats,transport_amont,dechets,deplacements,transport_aval}`, `marketVsLocationBased`, `recalc.{button,lastComputed,running,success,error}`, `editLine.{title,quantity,unit,source,sourceRequired,submit,success,error}`, `coverageBanner.{title,description,cta}`, `wizard.{title,subtitle,steps.{energy,mobility,purchases},progress,start,answerFreely,partialSaved}`, `factorSwitch.{title,ademeLabel,ipccLabel,disabledTooltip,estimateBadge}`, `errors.{footprintNotFound,factorNotFound,sourceNotVerified,recomputeRateLimited,generic}`.
- [X] T006 [P] Créer `frontend/app/services/api/carbon.ts` exportant l'objet `carbonApi` avec les 5 méthodes définies dans `contracts/frontend-api-consumption.md` (`fetchIndex`, `fetchFootprint`, `recompute`, `editLine`, `computeInitial`). Encapsule `$fetch` + JWT (réutiliser le pattern de `services/api/scoring.ts` livré par F46). Aucun `$fetch` direct ailleurs dans la feature.

---

## Phase 2 — Foundational (Blocking Prerequisites)

**Purpose** : backend extension (3 endpoints + extension schéma) + store Pinia + composables socles. Aucune US ne peut commencer avant la fin de cette phase.

### 2.1 Backend — Extension de schéma `CarbonSourceItem`

- [X] T007 Étendre `backend/app/carbon/schemas.py` : ajouter `source_id: UUID | None = None` à `CarbonSourceItem` (cf. `data-model.md` §2.1). Ajouter les nouveaux DTO `CarbonIndexEntryOut`, `CarbonIndexOut`, `CarbonRecomputeResponse`, `CarbonEditLineRequest`, `CarbonEditLineResponse` (cf. `data-model.md` §2.2–§2.6) avec `ConfigDict(extra="forbid")`.
- [X] T008 [P] Créer `backend/tests/carbon/test_carbon_source_item_source_id.py` couvrant la rétrocompatibilité : (a) `CarbonSourceItem(code="x", quantity="1")` valide (source_id None par défaut) ; (b) `CarbonSourceItem(code="x", quantity="1", source_id="<uuid>")` valide ; (c) `CarbonSourceItem(code="x", quantity="1", source_id="not-a-uuid")` → ValidationError ; (d) `extra="forbid"` rejette champ inconnu.

### 2.2 Backend — Service & router : index multi-année

- [X] T009 Créer `backend/tests/carbon/test_index_endpoint.py` (TDD avant code) couvrant les 6 cas définis dans `contracts/backend-index-endpoint.md` §Tests. Utiliser les fixtures pytest existantes dans `backend/tests/carbon/conftest.py` (créer si absent en réutilisant le pattern de `backend/tests/scoring/conftest.py`).
- [X] T010 Étendre `backend/app/carbon/service.py` avec la fonction `list_index(db, *, account_id, limit_years=10) -> list[dict]` qui exécute `SELECT DISTINCT ON (year) id, year, total_tco2e, computed_at, version FROM carbon_footprint WHERE account_id=:acc ORDER BY year DESC, computed_at DESC LIMIT :limit_years`. Aucun audit (lecture seule).
- [X] T011 Étendre `backend/app/carbon/router.py` avec la route `@router.get("/me/carbon", response_model=CarbonIndexOut)` qui appelle `list_index` ; query param `limit_years: int = Query(10, ge=1, le=20)` ; auth `Depends(get_current_pme)`. Sérialiser via le helper existant `_serialize` adapté pour les Decimal.
- [X] T012 Lancer `cd backend && source .venv/bin/activate && pytest tests/carbon/test_index_endpoint.py -v` — les 6 cas doivent passer GREEN.

### 2.3 Backend — Service & router : recompute global

- [X] T013 Créer `backend/tests/carbon/test_recompute_endpoint.py` (TDD) couvrant les 7 cas définis dans `contracts/backend-recompute-endpoint.md` §Tests, dont la vérification de l'audit (`source_of_change=manual`, `entity="carbon_footprint"`, `field="recompute"`, old/new corrects).
- [X] T014 Étendre `backend/app/carbon/service.py` avec `recompute(db, *, account_id, year, user_id) -> dict` : (a) charge le dernier `CarbonFootprint(account_id, year)` ou lève `FootprintNotFound` ; (b) reconstruit `CarbonComputeRequest(year=year, source_data=[CarbonSourceItem(**item) for item in previous.source_data_json])` ; (c) appelle `compute_footprint(db, account_id, entreprise_id=previous.entreprise_id, user_id, request)` ; (d) `record_audit(entity="carbon_footprint", field="recompute", source_of_change=SourceOfChange.MANUAL, old={"footprint_id": str(previous.id), "total_tco2e": str(previous.total_tco2e)}, new={"footprint_id": str(new.id), "total_tco2e": str(new.total_tco2e)})` ; (e) retourne `{**new_result, "previous_footprint_id": str(previous.id)}`.
- [X] T015 Étendre `backend/app/carbon/router.py` avec la route `@router.post("/me/carbon/{year}/recompute", response_model=CarbonRecomputeResponse)` ; mappe `FootprintNotFound`/`FactorNotFound` → 404, applique le rate-limit SlowAPI `@limiter.limit("1/5seconds")` (clé = `account_id`).
- [X] T016 Lancer `pytest tests/carbon/test_recompute_endpoint.py -v` — les 7 cas doivent passer GREEN.

### 2.4 Backend — Service & router : edit-line

- [X] T017 Créer `backend/tests/carbon/test_edit_line_endpoint.py` (TDD) couvrant les 10 cas définis dans `contracts/backend-edit-line-endpoint.md` §Tests, en particulier : édition d'une ligne existante, ajout d'une ligne absente, source non `verified` → 400, cross-tenant → 404, audit complet.
- [X] T018 Étendre `backend/app/carbon/service.py` avec un helper privé `_assert_source_verified(db, *, source_id, account_id) -> None` qui lit la table `source` et lève `SourceNotVerified` si absente, autre tenant, ou `statut != "verified"`. Importer ou créer cette exception dans le module.
- [X] T019 Étendre `backend/app/carbon/service.py` avec `edit_line(db, *, account_id, year, user_id, payload: CarbonEditLineRequest) -> dict` : (a) `_assert_source_verified` ; (b) charge le dernier `CarbonFootprint(account_id, year)` ou lève `FootprintNotFound` ; (c) reconstruit la liste `source_data` avec remplacement par `code` ou ajout si absent ; (d) appelle `compute_footprint` ; (e) `record_audit(entity="carbon_footprint", field="edit-line", source_of_change=MANUAL, old={"code": payload.code, "quantity": <prev or null>, "source_id": <prev or null>}, new={"code": payload.code, "quantity": str(payload.quantity), "source_id": str(payload.source_id), "country": payload.country})` ; (f) retourne `{**new_result, "previous_footprint_id": str(previous.id), "edited_line_code": payload.code}`.
- [X] T020 Étendre `backend/app/carbon/router.py` avec la route `@router.post("/me/carbon/{year}/edit-line", response_model=CarbonEditLineResponse)` ; mappe `FootprintNotFound`/`FactorNotFound` → 404, `SourceNotVerified` → 400 `source_not_verified`.
- [X] T021 Lancer `pytest tests/carbon/test_edit_line_endpoint.py -v` — les 10 cas doivent passer GREEN.
- [X] T022 Lancer `pytest tests/carbon/ -v --cov=app/carbon --cov-report=term-missing` — coverage `app/carbon` ≥ 80 %.

### 2.5 Frontend — Store + composables socles

- [X] T023 [P] Créer `frontend/app/stores/__tests__/carbon.test.ts` couvrant `useCarbonStore` selon `data-model.md` §3.4 : (a) `loadIndex` appelle `carbonApi.fetchIndex` et remplit `index` + `indexLoadedAt` ; (b) cache TTL 60 s — `loadIndex` re-fetch si `now - indexLoadedAt > 60_000` ; (c) `loadFootprint(year)` appelle `fetchFootprint`, gère 404 → `footprints[year] = null` ; (d) `applyFootprint(year, fp)` met à jour `footprints[year]` et invalide les dérivées ; (e) `editLine(year, payload)` appelle `carbonApi.editLine`, met à jour le store et émet l'EventBus ; (f) `recompute(year)` appelle `carbonApi.recompute` et met à jour ; (g) garde anti-double-clic : `loadingRecompute[year]=true` → second appel rejette ; (h) `selectedYear` modifiable, `currentFootprint` getter dérive ; (i) `wizardDraft` lu/écrit dans `localStorage` (mock global). Mock `carbonApi`.
- [X] T024 Créer `frontend/app/stores/carbon.ts` qui passe T023 (Pinia setup store, exposition selon `data-model.md` §3.4).
- [~] T025 [P] Créer `frontend/app/composables/__tests__/useCarbon.test.ts` : (a) au mount, `loadIndex` puis `loadFootprint(selectedYear)` appelés une fois ; (b) abonnement `useChatEventBus` reçoit `entity_updated{carbon_footprint, year=selectedYear}` → `loadFootprint(year)` appelé + `loadIndex` invalidé ; (c) reçoit `entity_updated{carbon_footprint, year=autre}` → seul `index` mis à jour, footprint courant non re-fetché ; (d) reçoit `entity_updated{source, source_id=X}` référencé par une ligne → marque la ligne pour rafraîchissement (flag local) ; (e) garde anti-boucle : event reçu < 500 ms après émission locale (`source==='manual'` + flag `_localEmission`) ignoré ; (f) cleanup `onBeforeUnmount` désouscrit ; (g) debounce 200 ms : 3 events rapides → 1 seul re-fetch ; (h) expose `coverage` réactif dérivé de `currentFootprint`.
- [X] T026 Créer `frontend/app/composables/useCarbon.ts` qui passe T025. Expose : `index`, `currentFootprint`, `previousYearFootprint`, `groupedBreakdown`, `coverage`, `loading`, `error`, `selectedYear`, `setSelectedYear`, `recompute(year)`, `editLine(year, payload)`, `refresh()`.

**Checkpoint Phase 2** : backend opérationnel (tests verts) + frontend store + `useCarbon` prêts. Les US peuvent démarrer en parallèle (sauf US3 qui dépend du drawer édité, US7 qui dépend de l'EventBus déjà en place ici).

---

## Phase 3 — User Story 1 : Vue synthèse de l'empreinte (Priority: P1) 🎯 MVP

**Goal** : afficher au-dessus de la ligne de flottaison KPI total `tCO2e`, donut Scope 1/2/3, delta % vs N-1, couverture %.

**Independent Test** : `/carbone` avec données mock non vides → KPI total 2 décimales `tabular-nums`, donut, delta vs N-1 avec signe/couleur, couverture % visibles sans scroll.

### Tests US1

- [~] T027 [P] [US1] Créer `frontend/tests/components/carbone/CarbonOverview.test.ts` couvrant : (a) `footprint.total_tco2e=12.402450` → texte `12.40 tCO₂e` (2 décimales `tabular-nums`) ; (b) `previousYearFootprint=null` → delta affiché `—` + libellé `carbon.kpis.noComparison` ; (c) `previousYearFootprint.total=14, current=12` → delta `−14.3 %` couleur verte ; (d) `current=14, prev=12` → delta `+16.7 %` couleur rouge ; (e) `coverage.globalPct=85` → barre 85 % + texte `85 %` ; (f) `coverage.isLow=true` → propage l'info au parent (n'affiche pas la bannière elle-même) ; (g) `loading=true` → `<UiSkeleton>`.
- [~] T028 [P] [US1] Créer `frontend/tests/components/carbone/ScopeDonut.test.ts` couvrant : (a) `byScope={1:"3210.5", 2:"5800.1", 3:"3499.4"}` → wrap `<VizDonutChart>` avec 3 segments aux bonnes proportions ; (b) légende affiche les libellés `carbon.scopes.{1,2,3}` ; (c) clic sur segment Scope 2 émet `select(scope: "2")` ; (d) tableau `sr-only` accessible avec 3 lignes (catégorie, valeur, %) ; (e) `byScope` tout à 0 → état vide `<VizEmptyState>` ; (f) `prefers-reduced-motion` → pas d'animation gsap.
- [~] T029 [P] [US1] Créer `frontend/tests/components/carbone/LowCoverageBanner.test.ts` couvrant : (a) `coverage.isLow=false` → composant non rendu ; (b) `coverage.isLow=true` → `<UiBanner variant="warning">` avec textes i18n + CTA `carbon.coverageBanner.cta` ; (c) clic CTA émet `complete`.
- [X] T030 [P] [US1] Créer `frontend/tests/lib/__tests__/groupCarbonByScope.test.ts` (déclaré T003) : (a) breakdown vide → 3 entrées Scope avec `groups=[]` et `expectedPostesCount` corrects ; (b) breakdown avec 1 ligne `electricite` → Scope 2 `filledPostesCount=1`, autres 0 ; (c) plusieurs lignes même poste → regroupées dans `lines[]` avec `subtotalKgCo2e` correct (Decimal somme exacte via `decimal.js`) ; (d) `categorie` inconnue (hors MVP) → ignorée ou rangée dans un poste générique selon décision (vérifier la décision implémentée et figer le test) ; (e) ordre des groupes = ordre de `CARBON_EXPECTED_POSTS_BY_SCOPE`.
- [X] T031 [P] [US1] Créer `frontend/lib/__tests__/computeCarbonCoverage.test.ts` (déclaré T004) : (a) tous postes vides → `globalPct=0`, `isLow=true` ; (b) tous postes remplis → `globalPct=100`, `isLow=false` ; (c) Scope 2 complet (4/4), autres vides → `scope2Pct=100`, `globalPct=4/12*100=33`, `isLow=true` ; (d) globalPct = 65 → `isLow=false` (seuil strict `< 60`).
- [~] T032 [P] [US1] Créer `frontend/tests/e2e/carbone-overview.spec.ts` (Playwright) : auth PME → seed 1 empreinte 2026 + 1 empreinte 2025 via `POST /me/carbon/compute` → ouvrir `/carbone` → assertions : KPI total `tCO₂e` visible et lisible sans scroll, donut SVG/canvas rendu, delta % vs 2025 avec signe et couleur, couverture % visible, LCP < 1.8 s (mesure via `performance.getEntriesByType("largest-contentful-paint")`).
- [~] T033 [P] [US1] Créer `frontend/tests/e2e/carbone-no-previous-year.spec.ts` : seed 1 empreinte 2026 uniquement → ouvrir `/carbone` → delta affiché `—` + libellé `Pas de comparaison disponible`.

### Implémentation US1

- [X] T034 [P] [US1] Créer `frontend/app/components/carbone/CarbonOverview.vue` qui passe T027. Props `footprint`, `previousYearFootprint`, `coverage`, `loading`. Utilise `useDecimal().format()` pour 2 décimales. Émet `coverageLow` si applicable.
- [X] T035 [P] [US1] Créer `frontend/app/components/carbone/ScopeDonut.vue` qui passe T028. Props `byScope`. Wrap `<VizDonutChart>` (F40). Légende interactive. A11y via tableau `sr-only`.
- [X] T036 [P] [US1] Créer `frontend/app/components/carbone/LowCoverageBanner.vue` qui passe T029. Props `coverage`. Émet `complete` au clic CTA.
- [X] T037 [US1] Créer `frontend/app/pages/carbone/index.vue` (version MVP US1) : utilise `useCarbon()`, place `<CarbonOverview>`, `<ScopeDonut>`, `<LowCoverageBanner>` en grid responsive (3 col desktop, 1 col mobile). Sélecteur d'année via `<UiSelect>` synchronisé avec query `?year=`. Gère le cas `currentFootprint === null` en affichant un placeholder vide (le wizard arrive en US6).
- [~] T038 [US1] Lancer les tests US1 : `pnpm vitest run app/components/carbone/CarbonOverview.test.ts app/components/carbone/ScopeDonut.test.ts app/components/carbone/LowCoverageBanner.test.ts app/lib/__tests__/groupCarbonByScope.test.ts app/lib/__tests__/computeCarbonCoverage.test.ts` puis `pnpm playwright test tests/e2e/carbone-overview.spec.ts tests/e2e/carbone-no-previous-year.spec.ts` — tout vert.

**Checkpoint US1** : `/carbone` montre la synthèse avec KPI total + donut + delta + couverture (avec bannière si < 60 %). MVP démontrable.

---

## Phase 4 — User Story 2 : Drilldown par scope avec traçabilité (Priority: P1)

**Goal** : accordéon par scope, lignes (valeur + unité + facteur + pin source). Mention market vs location-based sur S2.

**Independent Test** : déplier S1 → chaque ligne expose `valeur+unité+facteur(version,valid_from)` + pin source cliquable.

### Tests US2

- [~] T039 [P] [US2] Créer `frontend/tests/components/carbone/EmissionLine.test.ts` couvrant : (a) ligne avec `quantity="50000", unit="kWh", factorValue="0.075", factorVersion=3, kgco2e="3750"` → rendu valeur/unité/facteur/total ; (b) `sourceId !== null` → `<FactorSourcePopover>` rendu ; (c) `sourceId === null` → badge `Source manquante` ; (d) bouton `Modifier` cliquable émet `edit(line)` (drawer ouvert en US3) ; (e) `prefers-reduced-motion` → pas d'animation.
- [~] T040 [P] [US2] Créer `frontend/tests/components/carbone/FactorSourcePopover.test.ts` : (a) clic ouvre `<UiPopover>` ; (b) lazy-fetch `Source` via `useSourceFetch(factorSourceId)` au premier ouvert seulement ; (c) loading → `<UiSkeleton>` ; (d) source `verified` → titre + organisme + lien externe (rel `noopener`) ; (e) source `revoked` → `<RevokedSourceBadge>` (réutilisé de F46) ; (f) erreur fetch → message i18n.
- [~] T041 [P] [US2] Créer `frontend/tests/components/carbone/ScopeAccordion.test.ts` : (a) header affiche `carbon.scopes.{scope}` + total + ratio postes `n/m` ; (b) clic toggle ouvert/fermé ; (c) chaque poste rend un sous-bloc avec libellé `carbon.posts.{posteCode}` et liste `<EmissionLine>` ; (d) Scope 2 → infobulle `marketVsLocationBased` au survol de l'icône info ; (e) poste attendu sans ligne → bloc vide avec CTA `Ajouter` (drawer mode ajout, US3).
- [~] T042 [P] [US2] Créer `frontend/tests/e2e/carbone-drilldown.spec.ts` : seed empreinte 2026 avec 1 ligne S1 combustion fixe + 2 lignes S2 électricité + 1 ligne S3 achats → ouvrir `/carbone` → déplier chaque scope → assertions : 3 lignes S1 (1 remplie + 2 vides), 4 lignes S2 (2 dans `electricite` regroupées + 3 postes vides), 5 lignes S3 (1 remplie + 4 vides) ; chaque ligne remplie expose valeur, unité, facteur version, popover source cliquable (le clic ouvre la fiche).

### Implémentation US2

- [X] T043 [P] [US2] Créer `frontend/app/components/carbone/FactorSourcePopover.vue` qui passe T040. Lazy fetch via `useSourceFetch`. A11y `aria-haspopup`.
- [X] T044 [P] [US2] Créer `frontend/app/components/carbone/EmissionLine.vue` qui passe T039. Props `line`, `posteLabel`, `disableEdit`. Émet `edit(line)`.
- [X] T045 [US2] Créer `frontend/app/components/carbone/ScopeAccordion.vue` qui passe T041. Props `scope`, `breakdown` (`ScopeBreakdown`). Utilise `<UiAccordion>` (F37) ou implémentation locale si absent. Mention market vs location-based sur S2.
- [X] T046 [US2] Étendre `frontend/app/pages/carbone/index.vue` pour rendre 3 `<ScopeAccordion>` (un par scope) sous la grid synthèse, alimentés par `groupedBreakdown` du `useCarbon()`.
- [~] T047 [US2] Lancer les tests US2 : `pnpm vitest run app/components/carbone/EmissionLine.test.ts app/components/carbone/FactorSourcePopover.test.ts app/components/carbone/ScopeAccordion.test.ts && pnpm playwright test tests/e2e/carbone-drilldown.spec.ts` — tout vert.

**Checkpoint US2** : drilldown par scope opérationnel ; chaque ligne expose facteur + source.

---

## Phase 5 — User Story 3 : Édition d'une donnée d'activité (Priority: P1)

**Goal** : éditer une ligne via bottom sheet (quantité + unité + source obligatoire) → recalcul immédiat + audit.

**Independent Test** : modifier S2 électricité 50 000 → 45 000 kWh + source `verified` → ligne et KPI mis à jour < 2 s, audit row inscrite.

### Tests US3

- [X] T048 [P] [US3] Créer `frontend/app/composables/__tests__/useCarbonEdit.test.ts` : (a) `openDrawer({year, line, posteCode})` ouvre `useChatBottomSheet().show({type:"ask_form"})` avec champs `quantity`, `country?`, `source_id` pré-remplis ; (b) submit avec `source_id=null` → rejet local + toast `carbon.editLine.sourceRequired` (jamais envoyé au backend) ; (c) submit valide → `carbonApi.editLine(year, payload)` appelé, store mis à jour via `applyFootprint`, EventBus `entity_updated{carbon_footprint,year,edited_line_code}` + `context_invalidated{carbon_footprint}` émis, toast `success` ; (d) backend 400 `source_not_verified` → toast spécifique + drawer reste ouvert ; (e) backend 5xx → toast générique + état précédent préservé ; (f) mode `line=null, posteCode=...` → drawer en mode "ajout" avec `code=posteCode` pré-rempli vide ; (g) garde anti-double-submit.
- [X] T049 [P] [US3] Créer `frontend/tests/components/carbone/EditLineDrawer.test.ts` : (a) composant orchestrateur sans UI propre ; (b) écoute l'event `edit(line)` émis par `<EmissionLine>` et délègue à `useCarbonEdit`.
- [~] T050 [P] [US3] Créer `frontend/tests/e2e/carbone-edit-line.spec.ts` : (a) seed empreinte avec ligne S2 électricité 50000 → ouvrir `/carbone` → déplier S2 → cliquer `Modifier` → bottom sheet ouvert avec valeur pré-remplie → modifier en 45000 → choisir une source `verified` (mock seed) → valider → ligne et KPI mis à jour < 2 s, toast succès ; (b) requête API `GET /me/audit?entity=carbon_footprint` retourne 1 nouvelle entrée `field=edit-line, source_of_change=manual`.
- [~] T051 [P] [US3] Créer `frontend/tests/e2e/carbone-edit-line-no-source.spec.ts` : tenter d'éditer sans renseigner de source → bouton `Valider` désactivé OU soumission rejetée localement avec message `Source obligatoire pour toute donnée carbone` ; aucune requête `POST /me/carbon/{year}/edit-line` envoyée (vérifié via interception réseau).
- [~] T052 [P] [US3] Créer `frontend/tests/e2e/carbone-edit-line-error.spec.ts` : mock backend 400 `source_not_verified` → toast spécifique + drawer reste ouvert ; mock 500 → toast générique + état précédent préservé.

### Implémentation US3

- [X] T053 [US3] Créer `frontend/app/composables/useCarbonEdit.ts` qui passe T048. Dépend de `useCarbon`, `useChatBottomSheet`, `useToast`, `useChatEventBus`. Le sélecteur de source utilise `useSourcesList({statut:"verified"})` (composable F09 existant).
- [X] T054 [US3] Créer `frontend/app/components/carbone/EditLineDrawer.vue` qui passe T049 (composant minimal monté à la racine de la page, écoute global event ou prop callback).
- [X] T055 [US3] Étendre `frontend/app/components/carbone/EmissionLine.vue` pour brancher le bouton `Modifier` sur `useCarbonEdit().openDrawer({year, line, posteCode})`.
- [X] T056 [US3] Étendre `frontend/app/pages/carbone/index.vue` pour monter `<EditLineDrawer>` une seule fois et propager le callback aux accordéons.
- [X] T057 [US3] Lancer les tests US3 : `pnpm vitest run app/composables/__tests__/useCarbonEdit.test.ts app/components/carbone/EditLineDrawer.test.ts && pnpm playwright test tests/e2e/carbone-edit-line.spec.ts tests/e2e/carbone-edit-line-no-source.spec.ts tests/e2e/carbone-edit-line-error.spec.ts` — tout vert.

**Checkpoint US3** : édition de ligne opérationnelle avec source obligatoire, audit, propagation EventBus.

---

## Phase 6 — User Story 4 : Évolution annuelle par scope (Priority: P1)

**Goal** : courbe N vs N-1 segmentée par scope (max 5 ans), légende interactive.

**Independent Test** : 2 années de données → courbe avec ≥ 2 séries, axe X temporel, axe Y `tCO2e`, légende toggle scope.

### Tests US4

- [X] T058 [P] [US4] Créer `frontend/app/composables/__tests__/useCarbonHistory.test.ts` : (a) au mount, lit `index` du store (pas de fetch supplémentaire si déjà chargé) ; (b) charge à la demande les `footprint` de chaque année listée (max 5) pour obtenir `byScope` détaillé, en parallèle (`Promise.all`) ; (c) dérive 4 séries (`total`, `scope1`, `scope2`, `scope3`) en `tCO2e` ; (d) cache : ne refetch pas si déjà chargé ; (e) erreur sur une année → série affichée avec point manquant + log warning ; (f) expose `series` et `loading`.
- [X] T059 [P] [US4] Créer `frontend/tests/components/carbone/EvolutionLineChart.test.ts` : (a) wrap `<VizLineChart>` avec 4 séries (`total`, `scope1`, `scope2`, `scope3`) ; (b) clic sur légende `Scope 2` masque la série, total recalcule sans rechargement ; (c) `series=[]` → état vide ; (d) `currentYear` mis en évidence (point plus large) ; (e) accessibilité tableau `sr-only` listant chaque année et chaque série.
- [~] T060 [P] [US4] Créer `frontend/tests/e2e/carbone-evolution.spec.ts` : seed 3 années (2024, 2025, 2026) → ouvrir `/carbone` → courbe affiche 3 points par série, légende toggle Scope 2 → série masquée + total mis à jour.

### Implémentation US4

- [X] T061 [P] [US4] Créer `frontend/app/composables/useCarbonHistory.ts` qui passe T058.
- [X] T062 [US4] Créer `frontend/app/components/carbone/EvolutionLineChart.vue` qui passe T059. Wrap `<VizLineChart>` (F40).
- [X] T063 [US4] Étendre `frontend/app/pages/carbone/index.vue` pour rendre `<EvolutionLineChart>` dans la grid synthèse (3e colonne desktop), alimenté par `useCarbonHistory().series`.
- [X] T064 [US4] Lancer les tests US4 : `pnpm vitest run app/composables/__tests__/useCarbonHistory.test.ts app/components/carbone/EvolutionLineChart.test.ts && pnpm playwright test tests/e2e/carbone-evolution.spec.ts` — tout vert.

**Checkpoint US4** : courbe d'évolution opérationnelle.

---

## Phase 7 — User Story 5 : Recalcul global manuel (Priority: P1)

**Goal** : bouton `Recalculer` → spinner → horodatage `Dernier calcul` mis à jour. < 2 s pour 30 lignes.

**Independent Test** : clic `Recalculer` → spinner → KPI rafraîchi + horodatage actualisé < 2 s.

### Tests US5

- [X] T065 [P] [US5] Créer `frontend/tests/components/carbone/RecalcStrip.test.ts` : (a) affiche `lastComputedAt` formaté FR (Intl) ; (b) bouton `Recalculer` cliquable ; (c) `loading=true` → bouton désactivé + spinner ; (d) clic émet `recompute` ; (e) `prefers-reduced-motion` → pas de spinner animé (icône statique).
- [~] T066 [P] [US5] Créer `frontend/tests/e2e/carbone-recompute.spec.ts` : seed 30 lignes → cliquer `Recalculer` → spinner visible → retour < 2 s → horodatage mis à jour ; vérifier audit row `field=recompute` créée.
- [~] T067 [P] [US5] Créer `frontend/tests/e2e/carbone-recompute-error.spec.ts` : mock backend 500 → toast français explicite + état précédent préservé + bouton réactivé.

### Implémentation US5

- [X] T068 [P] [US5] Créer `frontend/app/components/carbone/RecalcStrip.vue` qui passe T065. Props `year`, `lastComputedAt`, `loading`. Émet `recompute`.
- [X] T069 [US5] Étendre `frontend/app/pages/carbone/index.vue` pour rendre `<RecalcStrip>` au-dessus de la synthèse, branché sur `useCarbon().recompute(year)`.
- [X] T070 [US5] Lancer les tests US5 : `pnpm vitest run app/components/carbone/RecalcStrip.test.ts && pnpm playwright test tests/e2e/carbone-recompute.spec.ts tests/e2e/carbone-recompute-error.spec.ts` — tout vert.

**Checkpoint US5** : recalcul global opérationnel avec audit + erreur gérée.

---

## Phase 8 — User Story 6 : Wizard empty-state 3 étapes (Priority: P1)

**Goal** : compte vide → wizard 3 étapes énergie/déplacements/achats, persistance partielle, bouton `Répondre librement`.

**Independent Test** : compte vide → wizard visible, 3 étapes complétées → bilan calculé + synthèse remplace le wizard. Réponses partielles restaurées après reload.

### Tests US6

- [X] T071 [P] [US6] Créer `frontend/app/composables/__tests__/useCarbonWizard.test.ts` : (a) `start(year)` initialise `WizardDraft = {step:1, answers:{}}` et persiste dans `localStorage` clé `carbon-wizard-{accountId}-draft` ; (b) `setAnswer(stepKey, payload)` met à jour le draft + persiste ; (c) `nextStep()` valide le pas courant et passe au suivant ; (d) `previousStep()` retour ; (e) `submit()` agrège les 3 pas en `CarbonSourceItem[]` (mapping énergie→`electricite`, déplacements→`deplacements`, achats→`achats`), appelle `carbonApi.computeInitial(year, sourceData)`, purge `localStorage`, met à jour le store via `applyFootprint`, émet `entity_updated{carbon_footprint, trigger:"wizard"}` ; (f) hydratation au mount : si draft `localStorage` présent et non expiré (TTL 7 jours) → restauré ; (g) `cancel()` purge localStorage ; (h) bouton `Répondre librement` émet `freeText` qui ouvre le chat libre via `useChatBottomSheet`.
- [X] T072 [P] [US6] Créer `frontend/tests/components/carbone/EmptyStateWizard.test.ts` : (a) `currentFootprint=null` → composant rendu ; (b) header + 3 cartes (énergie/déplacements/achats) + bouton `Commencer` ; (c) clic `Commencer` appelle `useCarbonWizard.start(year)` et ouvre le bottom sheet ; (d) progression visible (1/3, 2/3, 3/3) ; (e) bouton `Répondre librement` présent et visible (P10) ; (f) après `submit` réussi → composant disparaît (le footprint apparaît).
- [~] T073 [P] [US6] Créer `frontend/tests/e2e/carbone-wizard-empty.spec.ts` : compte vide → ouvrir `/carbone` → wizard visible → cliquer `Commencer` → compléter pas 1 (électricité 12000 kWh + source) → pas 2 (déplacements 8000 km + source) → pas 3 (achats 1500 EUR + source) → submit → wizard ferme + synthèse visible avec les 3 lignes < 5 secondes utilisateur (mesure).
- [~] T074 [P] [US6] Créer `frontend/tests/e2e/carbone-wizard-resume.spec.ts` : compte vide → démarrer wizard, compléter pas 1 et 2, fermer le navigateur (ou recharger la page) → revenir sur `/carbone` → wizard reprend au pas 3 avec pas 1 et 2 pré-remplis.

### Implémentation US6

- [X] T075 [P] [US6] Créer `frontend/app/composables/useCarbonWizard.ts` qui passe T071. Utilise `useChatBottomSheet().show({type:"show_form"})` séquentiellement pour les 3 pas.
- [X] T076 [US6] Créer `frontend/app/components/carbone/EmptyStateWizard.vue` qui passe T072. Props `year`. Affiche `currentFootprint===null` uniquement.
- [X] T077 [US6] Étendre `frontend/app/pages/carbone/index.vue` : si `currentFootprint===null` → masquer la grid synthèse + drilldown + recalc et afficher `<EmptyStateWizard>` à la place. Réafficher tout dès que `currentFootprint` devient non null.
- [X] T078 [US6] Lancer les tests US6 : `pnpm vitest run app/composables/__tests__/useCarbonWizard.test.ts app/components/carbone/EmptyStateWizard.test.ts && pnpm playwright test tests/e2e/carbone-wizard-empty.spec.ts tests/e2e/carbone-wizard-resume.spec.ts` — tout vert.

**Checkpoint US6** : wizard onboarding opérationnel avec persistance partielle.

---

## Phase 9 — User Story 7 : Synchronisation avec le chat (Priority: P1)

**Goal** : `entity_updated{carbon_footprint}` reçu via EventBus → mise à jour ciblée < 1 s sans rechargement.

**Independent Test** : émettre l'event depuis un autre onglet → ligne et KPIs rafraîchis < 1 s.

### Tests US7

- [~] T079 [P] [US7] Étendre `frontend/app/composables/__tests__/useCarbon.test.ts` (déjà créé en T025) : ajouter le scénario complet de réception d'un `entity_updated{carbon_footprint, year=current}` produit par un autre onglet (mock `BroadcastChannel`) → vérifier mise à jour de l'index + footprint en < 1 s simulée.
- [~] T080 [P] [US7] Créer `frontend/tests/e2e/carbone-chat-sync.spec.ts` : ouvrir 2 onglets sur `/carbone` (même compte) → onglet B émettre `useChatEventBus().emit("entity_updated", {entity:"carbon_footprint", year:2026, footprint_id:"<nouveau>", trigger:"manual"})` après mutation backend simulée → onglet A rafraîchit le KPI total et la ligne mutée < 1 s sans rechargement.
- [~] T081 [P] [US7] Créer `frontend/tests/e2e/carbone-chat-sync-source-revoked.spec.ts` : émettre `entity_updated{entity:"source", source_id:X}` où X est référencé par une ligne → la ligne se met à jour avec badge `RevokedSourceBadge` sans refetch global.

### Implémentation US7

- [X] T082 [US7] Vérifier que `useCarbon` (créé en T026) gère bien tous les cas. Si manquant : implémenter la branche `entity_updated{source}` (cf. `contracts/chat-eventbus-sync.md` §Évènements écoutés).
- [~] T083 [US7] Lancer les tests US7 : `pnpm vitest run app/composables/__tests__/useCarbon.test.ts && pnpm playwright test tests/e2e/carbone-chat-sync.spec.ts tests/e2e/carbone-chat-sync-source-revoked.spec.ts` — tout vert.

**Checkpoint US7** : sync chat ↔ carbone opérationnelle.

---

## Phase 10 — User Story 8 : Comparateur facteurs (Priority: P2, désactivé MVP)

**Goal** : présence du composant + badge "Estimation" + switch désactivé avec infobulle.

**Independent Test** : composant rendu + badge visible + switch `disabled` + infobulle "À venir".

### Tests US8

- [X] T084 [P] [US8] Créer `frontend/tests/components/carbone/FactorReferentielSwitch.test.ts` : (a) prop `disabled=true` (forcé MVP) → input switch HTML `disabled` ; (b) badge `carbon.factorSwitch.estimateBadge` visible ; (c) infobulle au survol contient `carbon.factorSwitch.disabledTooltip` ; (d) `aria-disabled="true"`.

### Implémentation US8

- [X] T085 [P] [US8] Créer `frontend/app/components/carbone/FactorReferentielSwitch.vue` qui passe T084. Toujours `disabled=true` au MVP.
- [X] T086 [US8] Étendre `frontend/app/pages/carbone/index.vue` pour insérer `<FactorReferentielSwitch>` entre la grid synthèse et les accordéons.
- [X] T087 [US8] Lancer `pnpm vitest run app/components/carbone/FactorReferentielSwitch.test.ts` — vert.

**Checkpoint US8** : switch présent (désactivé MVP), prêt pour activation backend post-MVP.

---

## Phase 11 — User Story 9 : Export PDF (Priority: P2, dépend F51)

**Goal** : bouton `Exporter PDF` → délègue à F51 (placeholder MVP).

**Independent Test** : bouton visible et cliquable ; au MVP, ouvre une modal d'attente "Disponible avec F51".

### Tests US9

- [X] T088 [P] [US9] Créer `frontend/tests/components/carbone/ExportPdfButton.test.ts` : (a) bouton rendu avec libellé i18n ; (b) clic ouvre une `<UiModal>` avec le message "Export disponible prochainement" si F51 non détecté (feature flag `useFeatureFlag('carbon.exportPdf')` ou simple condition `ready=false` au MVP) ; (c) si F51 détecté → délégation à `useExportPdf({ section: "carbon", year })`.

### Implémentation US9

- [X] T089 [P] [US9] Créer `frontend/app/components/carbone/ExportPdfButton.vue` qui passe T088.
- [X] T090 [US9] Étendre `frontend/app/pages/carbone/index.vue` pour rendre `<ExportPdfButton>` en pied de page synthèse.
- [X] T091 [US9] Lancer `pnpm vitest run app/components/carbone/ExportPdfButton.test.ts` — vert.

**Checkpoint US9** : bouton présent, dégradation gracieuse en attendant F51.

---

## Phase 12 — Polish & Cross-Cutting Concerns

- [ ] T092 [P] Mesurer LCP `/carbone` avec inventaire de 30 lignes en condition 4G via Lighthouse ou Playwright API → confirmer < 1.8 s (SC-007). Documenter le résultat dans `quickstart.md` §6 si besoin.
- [ ] T093 [P] Vérifier l'accessibilité clavier du donut et de la courbe (Tab, flèches, annonce ARIA) sur `/carbone` (SC-008). Corriger les manques en délégant à F40 si bug détecté.
- [ ] T094 [P] Mesurer le temps de réception EventBus → mise à jour UI dans le scénario T080 → confirmer < 1 s (SC-009).
- [ ] T095 [P] Mesurer un recalcul de 30 lignes via `Performance.now()` autour de `recompute` E2E → confirmer < 2 s (SC-004).
- [ ] T096 [P] Implémenter la **virtualisation** de la table de détail si > 100 lignes : utiliser `<UiVirtualList>` (F37) si présent, sinon fallback `v-show` + lazy loading des `<FactorSourcePopover>` au hover. Ajouter un test E2E `carbone-large-inventory.spec.ts` qui seed 150 lignes et vérifie que le DOM rendu reste sous 50 lignes simultanément.
- [ ] T097 [P] Vérifier que `prefers-reduced-motion: reduce` désactive toutes les animations (donut fade-in, drawer slide-in, transitions wizard) sur `/carbone` (test E2E `carbone-reduced-motion.spec.ts`).
- [X] T098 [P] Vérifier que toutes les chaînes affichées sont en français (audit grep `frontend/app/components/carbone/` + `frontend/app/pages/carbone/` pour absence de chaînes hardcodées hors `useT()`).
- [ ] T099 [P] Lancer `cd backend && source .venv/bin/activate && pytest tests/carbon/ --cov=app/carbon --cov-report=term-missing` ; coverage `app/carbon` ≥ 80 %.
- [ ] T100 [P] Lancer `cd frontend && pnpm vitest run --coverage app/components/carbone app/composables/__tests__/useCarbon.test.ts app/composables/__tests__/useCarbonHistory.test.ts app/composables/__tests__/useCarbonEdit.test.ts app/composables/__tests__/useCarbonWizard.test.ts app/lib/__tests__/groupCarbonByScope.test.ts app/lib/__tests__/computeCarbonCoverage.test.ts app/stores/__tests__/carbon.test.ts` ; coverage frontend carbone ≥ 80 %.
- [~] T101 [P] Lancer `make lint` (ruff backend + eslint frontend) ; 0 erreur. **Backend ruff : 0 erreur. Frontend ESLint : config v9 manquante (problème pré-existant hors scope F47).**
- [ ] T102 [P] Smoke quickstart : suivre `quickstart.md` étapes 1 à 4 manuellement ; valider chaque check.
- [X] T103 Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F47 comme `done` et lier vers `specs/047-empreinte-carbone-ui/`.
- [X] T104 [P] Vérifier que `<EditLineDrawer>` réutilise correctement `<ChatBottomSheet>` et qu'aucune saisie inline n'est introduite (revue P10 — grep `<input` dans `components/carbone/` doit être limité aux composants `EmptyStateWizard` placeholder ou inexistant). 

---

## Dependencies — ordre de complétion des user stories

```text
Setup (T001-T006)
  └─► Foundational (T007-T026)
        ├─► US1 (T027-T038)            # MVP livrable
        │     ├─► US2 (T039-T047)       # drilldown traçable
        │     │     └─► US3 (T048-T057) # édition (drawer dépend des accordéons)
        │     ├─► US4 (T058-T064)       # courbe annuelle
        │     ├─► US5 (T065-T070)       # recalcul global
        │     ├─► US6 (T071-T078)       # wizard empty-state (indépendant US2/3/4/5)
        │     └─► US7 (T079-T083)       # sync chat (s'appuie sur EventBus déjà en place)
        ├─► US8 (T084-T087)             # P2 disabled, indépendant
        └─► US9 (T088-T091)             # P2 placeholder, indépendant
        └─► Polish (T092-T104)          # exécutable en parallèle des dernières US
```

**Indépendances** :
- US1 = MVP isolé.
- US2 dépend de US1 (utilise la grid + fond de page).
- US3 dépend de US2 (drawer attaché aux lignes des accordéons).
- US4, US5, US6, US7 dépendent uniquement de la Foundational + US1 (peuvent être livrés en parallèle).
- US8 et US9 (P2) sont indépendants de toutes les autres US.

## Parallel Execution Opportunities

- **Setup** : T002, T003, T004, T005, T006 en parallèle (fichiers indépendants).
- **Foundational backend** : T008 et T009 en parallèle, puis T010+T011 séquentiels, puis T012 vérifie ; idem pour T013→T015→T016 et T017→T020→T021.
- **Foundational frontend** : T023 et T025 en parallèle après T010 (types prêts), puis T024 → T026 séquentiels.
- **US1** : T027–T033 en parallèle (tests), puis T034–T036 en parallèle (composants), puis T037 → T038 séquentiels.
- **US2** : T039–T042 en parallèle, puis T043–T044 en parallèle, puis T045 → T046 → T047.
- **US3** : T048–T052 en parallèle, puis T053–T054 en parallèle, puis T055 → T056 → T057.
- **US4** : T058–T060 en parallèle, puis T061–T062 en parallèle, puis T063 → T064.
- **US5** : T065–T067 en parallèle, puis T068 → T069 → T070.
- **US6** : T071–T074 en parallèle, puis T075–T076 en parallèle, puis T077 → T078.
- **US7** : T079–T081 en parallèle, puis T082 → T083.
- **US8** : T084 en parallèle de tout, puis T085 → T086 → T087.
- **US9** : T088 en parallèle de tout, puis T089 → T090 → T091.
- **Polish** : T092–T102 quasi tous parallèles ; T103 séquentiel en fin.

## Implementation Strategy

1. **MVP = Setup + Foundational + US1** (T001 → T038). Page `/carbone` montre KPI total + donut + delta + couverture. Démontrable.
2. **MVP+ traçabilité** : ajouter US2 (T039-T047). Drilldown par scope avec source.
3. **MVP+ édition** : ajouter US3 (T048-T057). La PME modifie ses données, audit OK.
4. **MVP+ trajectoire** : ajouter US4 (T058-T064). Courbe annuelle.
5. **MVP+ pilotage** : ajouter US5 (T065-T070). Recalcul à la demande.
6. **MVP+ onboarding** : ajouter US6 (T071-T078). Wizard empty-state.
7. **Sync** : ajouter US7 (T079-T083). Chat ↔ UI synchronisés.
8. **P2 placeholders** : ajouter US8 (T084-T087) et US9 (T088-T091) en fin de cycle.
9. **Polish** : T092-T104 en continu pendant les dernières US.

Chaque checkpoint US est livrable et testable **indépendamment** — c'est le principe directeur.
