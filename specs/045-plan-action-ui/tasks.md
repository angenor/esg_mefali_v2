# Tasks: Plan d'action ESG UI (F45)

**Input**: Design documents from `/specs/045-plan-action-ui/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Tests **REQUIS** par la constitution (TDD + 80 % coverage). Chaque user story inclut tests vitest (unit/components) puis Playwright (e2e) écrits **avant** l'implémentation.

**Organization**: Tâches groupées par user story pour livraison MVP incrémentale. Toutes les modifications sont **frontend-only** (`frontend/app/`) ; aucun backend touché — F31 expose déjà tout ce qu'il faut.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallélisable (fichier différent, pas de dépendance bloquante).
- **[Story]**: US1 → US12 ; pas de label pour Setup / Foundational / Polish.
- Tous les chemins sont relatifs à la racine repo.

## Path Conventions (rappel plan.md)

- Frontend Nuxt 4 : `frontend/app/{pages,components,composables,stores,lib,types,locales}`.
- Tests : `frontend/tests/{components,e2e}`, et `frontend/app/composables/__tests__` / `frontend/app/stores/__tests__` / `frontend/app/lib/__tests__` (pattern existant F44).
- Backend : **inchangé**.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Préparer l'arborescence, les types miroir backend et les clés i18n.

- [X] T001 Créer le dossier `frontend/app/components/plan-action/` et `frontend/app/pages/plan-action/` (avec un `.gitkeep` temporaire dans `pages/plan-action/` pour committer la structure).
- [X] T002 [P] Créer `frontend/app/types/actionPlan.ts` qui exporte les types miroir des schemas F31 : `Priority`, `StepStatus`, `Category`, `Horizon`, `ActionStep`, `ActionPlan`, `ActionStepPatchPayload`, `PlanFilters`, `TimelineBucket`, `TimelineBucketViewModel`, `TimelineViewModel`, `StepCardViewModel`, `CompletionStats` — exactement comme défini dans `data-model.md` § 1 et § 2.
- [X] T003 [P] Étendre `frontend/app/locales/fr.ts` avec le namespace complet `planAction.*` listé dans `contracts/frontend-components.md` (titres, filtres, statuts, priorités, empty states, regenerate, history, errors, card.*).
- [X] T004 [P] Créer `frontend/app/lib/__tests__/mapPlanToTimelineBuckets.test.ts` (fichier vide pour l'instant — sera rempli en T010 pour TDD).

**Checkpoint Setup**: Arborescence prête, types TS alignés sur F31, clés i18n en place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Briques transverses (store Pinia, helper de mapping, composables de base, primitives nouvelles si nécessaire) utilisées par toutes les US. Doivent être terminées avant qu'aucune US ne puisse démarrer.

**⚠️ CRITICAL** : Aucune user story ne peut commencer avant le checkpoint de cette phase.

### Tests d'abord (TDD)

- [X] T005 [P] Créer `frontend/app/stores/__tests__/actionPlan.test.ts` couvrant : (a) `fetchPlan()` met à jour `state.plan` et `lastFetchedAt` ; (b) cache 60 s — second `fetchPlan()` ne refait pas d'appel HTTP sauf `force=true` ; (c) deux fetches concurrents serialisés (un seul appel) ; (d) `applyOptimisticPatch(id, { status: 'done' })` applique l'overlay UI immédiat puis remplace par la réponse PATCH 200 ; (e) `applyOptimisticPatch` rollback complet sur erreur 500 ; (f) **file FIFO** : deux patchs successifs sur le même `step_id` sont appliqués séquentiellement ; (g) `invalidateStep(id)` re-fetch et remplace **uniquement** la step ciblée ; (h) `regenerate(12)` pose et lève `regenerating`, remplace le plan ; (i) `setFilters` / `setHorizonView` mettent à jour le state. Mock `$fetch`.
- [X] T006 [P] Créer `frontend/app/composables/__tests__/useActionPlan.test.ts` couvrant : (a) au mount, `fetchPlan()` est appelé une fois ; (b) abonnement à `useChatEventBus` reçoit `entity_updated{action_step}` → `invalidateStep` ; (c) reçoit `entity_updated{action_plan}` → `fetchPlan(force=true)` ; (d) garde-fou anti-boucle : un event reçu < 500 ms après une émission locale sur le même `step_id` est ignoré ; (e) cleanup `onBeforeUnmount` désouscrit. Mock `useChatEventBus` et store.
- [X] T007 [P] Créer `frontend/app/composables/__tests__/useActionPlanFilters.test.ts` couvrant : (a) parse de `?priority=haute&status=todo&horizon=12` → `PlanFilters` valide ; (b) valeurs invalides ignorées (`?priority=zzz` → priority=[]) ; (c) UUID invalide pour `responsible` → null ; (d) multi-valeurs `priority=haute,moyenne` → tableau ; (e) `setFilters` met à jour `route.query` via `router.replace` ; (f) objet vide → URL sans query string ; (g) ordre stable des clés. Mock `useRoute`/`useRouter`.
- [X] T008 [P] Créer `frontend/app/composables/__tests__/useActionPlanCompletion.test.ts` couvrant : (a) `done=3, total=10` → `percent=30` ; (b) `total=0` → `hasData=false`, `percent=0` ; (c) horizon=6 filtre les steps avant calcul ; (d) overlays optimistes (`stepStates[id].optimisticOverlay.status='done'`) sont pris en compte dans le calcul.
- [X] T009 [P] Étendre les tests existants `frontend/app/composables/__tests__/useActionStepToggle.test.ts` (créé en F44) pour couvrir : (a) file FIFO par `step_id` (deux toggles rapides → mutations séquentielles) ; (b) deux `step_id` différents en parallèle restent indépendants ; (c) erreur sur la première mutation annule **toute** la file pour ce `step_id`. **Vérifier** que les tests F44 existants ne régressent pas.
- [X] T010 [P] Remplir `frontend/app/lib/__tests__/mapPlanToTimelineBuckets.test.ts` (créé vide en T004) avec : (a) plan avec étapes à `+30j`, `+5mois`, `+10mois`, `+18mois`, `+30mois` → buckets `lt3m`, `3to6m`, `6to12m`, `12to24m`, `12to24m` (cap) ; (b) étape sans `horizon_at` → bucket `unscheduled` ; (c) ordre stable des buckets dans le résultat (lt3m, 3to6m, 6to12m, 12to24m, unscheduled) ; (d) chaque bucket porte `rangeStart`/`rangeEnd` cohérents avec `generated_at`.

### Implémentation foundational

- [X] T011 [P] Implémenter `frontend/app/lib/mapPlanToTimelineBuckets.ts` — fonction pure typée `(plan: ActionPlan) => TimelineViewModel`. Règles de bucketing du `data-model.md` § 2.3. Doit faire passer T010.
- [X] T012 [P] Implémenter `frontend/app/lib/mapStepToCardViewModel.ts` — fonction pure `(step: ActionStep, ctx: { reducedMotion: boolean, t: TFn, sources: Record<string, Source> }) => StepCardViewModel`. Calcule labels i18n, tones de badge selon priorité/statut, `horizonRelative`, `responsibleLabel`, `sourceLink`. Pas de test dédié (tests via composants).
- [X] T013 Implémenter `frontend/app/stores/actionPlan.ts` (Pinia) — state, getters, actions exactement selon `data-model.md` § 3. Inclut : cache 60 s, file FIFO `pendingMutations`, garde anti double-clic `regenerating`, anti-boucle EventBus 500 ms. Doit faire passer T005.
- [X] T014 Implémenter `frontend/app/composables/useActionPlan.ts` (dépend T013) — fetch initial + abonnement EventBus via `useChatEventBus`. Voir `contracts/frontend-components.md` et `contracts/chat-eventbus-sync.md`. Doit faire passer T006.
- [X] T015 [P] Implémenter `frontend/app/composables/useActionPlanFilters.ts` — parse/serialize URL query, validation. Doit faire passer T007.
- [X] T016 [P] Implémenter `frontend/app/composables/useActionPlanCompletion.ts` — KPI réactif. Doit faire passer T008.
- [X] T017 Étendre `frontend/app/composables/useActionStepToggle.ts` (existant F44) avec la file FIFO par `step_id`. **Conserver** la signature publique pour ne pas casser la mini-card du dashboard. Doit faire passer T009.
- [X] T018 [P] Vérifier la disponibilité d'un composant modale (`<UiModal>` ou usage de `<ChatBottomSheet display="modal">`) dans F37/F39 ; si **absent**, créer `frontend/app/components/ui/UiModal.vue` minimal (focus trap, Esc, clic extérieur, `role="dialog"`, `aria-modal`) et son test `frontend/tests/components/ui/UiModal.test.ts`. Sinon, documenter la décision en commentaire dans `RegenerateModal.vue` (T046).
- [X] T019 [P] Créer le helper E2E `frontend/tests/e2e/helpers/seed-action-plan.ts` exposant `seedPmeWithActionPlan(page, { stepsCount, withScoring, withGaps })` (calque F44 `seedPmeWithSummary`) — login + POST scoring + POST `/me/action-plan/generate`. Documenter les cas d'usage attendus par les specs E2E suivantes.

**Checkpoint Foundational**: Store, composables, helpers de mapping et helpers de test seed sont opérationnels. Les user stories peuvent démarrer en parallèle.

---

## Phase 3: User Story 1 — Visualiser ma feuille de route en timeline (Priority: P1) 🎯 MVP

**Goal**: Afficher la timeline horizontale (verticale < 768 px) avec jalons colorés par priorité, animation gsap stagger 80 ms (désactivée si `prefers-reduced-motion`), tooltips au survol.

**Independent Test**: Connecter un compte PME avec un plan de 5+ étapes réparties sur 3/6/12/24 mois, ouvrir `/plan-action`, vérifier que la timeline s'affiche en < 2 s, jalons colorés selon priorité, hover → titre.

### Tests pour User Story 1

- [X] T020 [P] [US1] Créer `frontend/tests/components/plan-action/TimelineHorizontal.test.ts` couvrant : (a) rendu avec 5 buckets fournis → 5 colonnes ; (b) chaque jalon coloré selon `priority` du step ; (c) tooltip natif (`title`) ou `<UiTooltip>` contient le titre ; (d) `reducedMotion=true` → pas de classe d'animation ; (e) émission de `select-step` au clic ; (f) responsive : viewport mobile mock → `data-orientation="vertical"`.
- [X] T021 [P] [US1] Créer `frontend/tests/e2e/plan-action-timeline-render.spec.ts` (Playwright) couvrant scénario US1 du quickstart : seed plan 5+ étapes (helper T019), ouvrir `/plan-action`, attendre `[data-testid="timeline"]`, vérifier ≥ 1 jalon par bucket, mesurer LCP < 1,5 s sur 4G simulé.
- [X] T022 [P] [US1] Créer `frontend/tests/e2e/plan-action-reduced-motion.spec.ts` : avec `page.emulateMedia({ reducedMotion: 'reduce' })`, vérifier que la timeline rend sans animation stagger (jalons visibles immédiatement, aucun `transform: translateY` en cours).

### Implémentation User Story 1

- [X] T023 [US1] Créer `frontend/app/components/plan-action/TimelineHorizontal.vue` selon `contracts/frontend-components.md` § `<TimelineHorizontal>`. Layout horizontal SVG axial + jalons HTML positionnés en `%`, bascule verticale via classes Tailwind responsive. Stagger gsap 80 ms désactivé si `useReducedMotion()`. a11y : chaque jalon est un `<button>` focusable. Doit faire passer T020.
- [X] T024 [US1] Créer `frontend/app/pages/plan-action/index.vue` minimal : middleware `auth`, mount du store, fetch initial via `useActionPlan()`, rendu d'un squelette + `<TimelineHorizontal>` quand `plan` chargé. Suffisant pour valider US1 ; les autres composants seront ajoutés au fil des US.
- [X] T025 [US1] Câbler T024 avec `useActionPlanStore.timelineViewModel` (calcul via `mapPlanToTimelineBuckets`). Doit faire passer T021 et T022.

**Checkpoint US1**: La timeline s'affiche, animée, responsive, avec données réelles. La page `/plan-action` est navigable mais minimale.

---

## Phase 4: User Story 2 — Filtrer et trier la liste d'étapes (Priority: P1)

**Goal**: Afficher la liste de cards filtrables (priorité / statut / horizon / responsable) avec filtres persistés dans l'URL ; tri par défaut priorité décroissante puis horizon ascendant ; filtrage client < 50 ms ; URL invalide ignorée silencieusement.

**Independent Test**: Avec 10+ étapes, sélectionner « priorité haute » → seules les étapes haute apparaissent et l'URL devient `/plan-action?priority=haute`. Recharger l'URL → filtre pré-appliqué.

### Tests pour User Story 2

- [X] T026 [P] [US2] Créer `frontend/tests/components/plan-action/StepFilters.test.ts` couvrant : (a) chaque filtre toggle émet `change` avec le delta ; (b) bouton « Réinitialiser » apparaît si ≥ 1 filtre actif et émet `reset` ; (c) `responsibleOptions` rendus dans le dropdown ; (d) a11y : `role="group"`, labels associés.
- [X] T027 [P] [US2] Créer `frontend/tests/e2e/plan-action-filter-url.spec.ts` couvrant : (a) seed 10 étapes mixtes, cliquer filtre `priorité=haute` → URL devient `?priority=haute` et liste filtrée ; (b) ouverture directe de `?priority=haute&status=todo` → filtres pré-sélectionnés ; (c) `?priority=zzz` → page rendue sans erreur, filtre ignoré, liste complète.

### Implémentation User Story 2

- [X] T028 [US2] Créer `frontend/app/components/plan-action/StepFilters.vue` selon `contracts/frontend-components.md` § `<StepFilters>`. Doit faire passer T026.
- [X] T029 [US2] Intégrer `<StepFilters>` dans `pages/plan-action/index.vue` (T024). Brancher sur `useActionPlanFilters()`. Implémenter le tri par défaut (priorité haute → moyenne → basse, puis `horizon_at` croissant) dans un computed qui produit la liste affichée. Doit faire passer T027.

**Checkpoint US2**: La liste est filtrable et triée, URL persistée et robuste aux query strings invalides.

---

## Phase 5: User Story 3 — Modifier rapidement le statut d'une étape (Priority: P1)

**Goal**: Cocher une étape la bascule `todo`↔`done` de façon optimiste avec rollback sur échec ; bouton « Modifier » ouvre un bottom sheet `<EditStatusSheet>` (statut + responsable) qui ferme par Esc / clic extérieur.

**Independent Test**: Cocher une étape `todo` → UI passe immédiatement à `done`, recharger la page → persistance OK. Bottom sheet : ouvrir, modifier responsable, valider → carte mise à jour.

### Tests pour User Story 3

- [X] T030 [P] [US3] Créer `frontend/tests/components/plan-action/StepCard.test.ts` couvrant : (a) tous les champs FR-008 visibles ou « Non renseigné » ; (b) émission `toggle-status` à la coche, `open-edit` au clic « Modifier » ; (c) `step.isLoading=true` → checkbox disabled + spinner ; (d) `step.error` → badge erreur ; (e) source pin cliquable émet `open-source` avec `indicateurId` ; (f) a11y : `aria-busy` selon loading, bouton `aria-haspopup="dialog"`.
- [X] T031 [P] [US3] Créer `frontend/tests/components/plan-action/EditStatusSheet.test.ts` couvrant : (a) ouvert avec `step` fourni, champs pré-remplis ; (b) submit désactivé si aucun champ modifié ; (c) émission `submit` avec `ActionStepPatchPayload` minimal (uniquement champs modifiés) ; (d) `Esc` et clic extérieur émettent `close` ; (e) focus trap actif via `<ChatBottomSheet>` (réutilisé).
- [X] T032 [P] [US3] Créer `frontend/tests/e2e/plan-action-toggle-optimistic.spec.ts` : seed plan, cliquer checkbox sur étape `todo`, vérifier (a) UI à `done` en < 100 ms, (b) requête PATCH envoyée, (c) après reload la persistance est OK.
- [X] T033 [P] [US3] Créer `frontend/tests/e2e/plan-action-toggle-rollback.spec.ts` : intercepter `PATCH /me/action-plan/steps/*` pour renvoyer 500, cliquer la checkbox, vérifier (a) UI revient à `todo`, (b) toast erreur visible, (c) la barre de progression est re-synchronisée.
- [X] T034 [P] [US3] Créer `frontend/tests/e2e/plan-action-edit-sheet.spec.ts` : ouvrir sheet, modifier statut → `doing`, valider, vérifier la carte rafraîchie ; ré-ouvrir, fermer par Esc → état inchangé.

### Implémentation User Story 3

- [X] T035 [US3] Créer `frontend/app/components/plan-action/StepCard.vue` selon `contracts/frontend-components.md` § `<StepCard>`. Réutilise `<UiCard>`, `<UiBadge>`, `<UiCheckbox>`, `<UiButton>`, `<VizSourcePin>`. Câble `useActionStepToggle()` pour la checkbox. Doit faire passer T030, T032, T033.
- [X] T036 [US3] Créer `frontend/app/components/plan-action/EditStatusSheet.vue` selon contrat. Encapsule `<ChatBottomSheet>` + `<ShowForm>`. Validation : au moins un champ modifié pour activer submit. Doit faire passer T031, T034.
- [X] T037 [US3] Intégrer `<StepCard>` (rendu en liste) et `<EditStatusSheet>` dans `pages/plan-action/index.vue`. Câble `responsibleOptions` depuis le getter du store. Émet `action_step:locally_updated` sur le bus après PATCH 200 (cf. `chat-eventbus-sync.md`).

**Checkpoint US3**: Mutations rapides + édition riche fonctionnelles. Optimistic + rollback solides. P8 (sync bidirectionnelle) respectée.

---

## Phase 6: User Story 4 — Suivre la progression globale (Priority: P1)

**Goal**: Afficher en haut de page une barre de progression et un KPI `X / Y étapes — Z %` qui se mettent à jour à chaque coche / régénération sans rechargement.

**Independent Test**: Plan 3/10 done → KPI `3 / 10` `30 %`. Cocher une étape → KPI passe à `4 / 10` `40 %` instantanément.

### Tests pour User Story 4

- [X] T038 [P] [US4] Créer `frontend/tests/components/plan-action/ProgressHeader.test.ts` couvrant : (a) `stats={done:3,total:10,percent:30,hasData:true}` → texte « 3 / 10 » et « 30 % » et barre à 30 % ; (b) `hasData=false` → affiche « — » au lieu d'un pourcentage ; (c) version affichée ; (d) a11y : `aria-valuenow`, `aria-valuemax`, `role="progressbar"`.

### Implémentation User Story 4

- [X] T039 [US4] Créer `frontend/app/components/plan-action/ProgressHeader.vue` selon contrat. Doit faire passer T038.
- [X] T040 [US4] Intégrer `<ProgressHeader>` dans `pages/plan-action/index.vue`, alimenté par `useActionPlanCompletion()`. Vérifier (couvert par T032/T033/T034) que la coche d'étape met à jour le KPI sans reload.

**Checkpoint US4**: Indicateur de progression réactif et a11y-conforme.

---

## Phase 7: User Story 5 — Régénérer son plan d'action (Priority: P1)

**Goal**: Bouton « Régénérer mon plan » → modale de confirmation avec sélecteur horizon (6/12/24) + avertissement explicite sur le versionnement → sur confirmation, POST F31 et remplacement du plan ; bouton désactivé pendant l'appel (anti double-clic).

**Independent Test**: Cliquer « Régénérer » → modale → choisir 12 mois → confirmer → version v+1 affichée en quelques secondes ; double-clic ne déclenche qu'une requête.

### Tests pour User Story 5

- [X] T041 [P] [US5] Créer `frontend/tests/components/plan-action/RegenerateModal.test.ts` couvrant : (a) `open=true` → modale visible avec avertissement i18n ; (b) sélecteur radio 6/12/24, défaut sur `defaultHorizon` ; (c) émission `confirm(horizon)` avec la valeur choisie ; (d) `busy=true` désactive le bouton confirm ; (e) émission `cancel` à la fermeture ; (f) Esc / clic extérieur → `cancel` ; (g) `role="dialog"` + `aria-modal="true"`.
- [X] T042 [P] [US5] Créer `frontend/tests/e2e/plan-action-regenerate.spec.ts` : seed plan v=1, cliquer « Régénérer », sélectionner 6 mois, confirmer, vérifier (a) requête `POST /me/action-plan/generate?horizon=6`, (b) plan v=2 affiché.
- [X] T043 [P] [US5] Créer `frontend/tests/e2e/plan-action-regenerate-double-click.spec.ts` : retarder la réponse backend de 1 s, double-cliquer « Confirmer » dans la modale, vérifier qu'**une seule** requête POST est envoyée et que la modale reste sur place jusqu'à résolution.
- [X] T044 [P] [US5] Créer `frontend/tests/e2e/plan-action-regenerate-error.spec.ts` : intercepter POST avec 500, confirmer, vérifier (a) toast erreur, (b) plan courant intact, (c) `regenerating` levé (bouton à nouveau cliquable).

### Implémentation User Story 5

- [X] T045 [US5] Créer `frontend/app/components/plan-action/RegenerateModal.vue` selon contrat. Réutilise `<UiModal>` (T018) ou `<ChatBottomSheet display="modal">`. Doit faire passer T041.
- [X] T046 [US5] Intégrer `<RegenerateModal>` dans `pages/plan-action/index.vue` ; brancher sur `actionPlanStore.regenerate()` (qui pose/lève `regenerating` et fait le POST). Émettre `action_plan:regenerated` sur le bus à succès. Doit faire passer T042–T044.

**Checkpoint US5**: Régénération en libre-service, anti double-clic, échec géré proprement.

---

## Phase 8: User Story 6 — Sélectionner l'horizon affiché (Priority: P1)

**Goal**: Toggle `6 / 12 / 24` mois au-dessus de la timeline qui filtre l'affichage (timeline + liste + KPI) sans modifier le plan stocké ; sélection persiste pendant la session.

**Independent Test**: Plan multi-horizons, basculer sur « 6 mois » → seules les étapes ≤ 6 mois visibles dans timeline ET liste, KPI recalculé.

### Tests pour User Story 6

- [X] T047 [P] [US6] Créer `frontend/tests/components/plan-action/HorizonToggle.test.ts` : trois boutons rendus (6/12/24), `modelValue=12` → bouton 12 actif (`aria-pressed="true"`), clic → émission `update:modelValue`. a11y : `role="tablist"`.
- [X] T048 [P] [US6] Créer `frontend/tests/e2e/plan-action-horizon-toggle.spec.ts` : seed plan multi-horizons, basculer sur 6 → vérifier que seules les étapes ≤ 6 mois sont visibles dans timeline ET liste, et que le KPI reflète le sous-ensemble.

### Implémentation User Story 6

- [X] T049 [US6] Créer `frontend/app/components/plan-action/HorizonToggle.vue` selon contrat. Doit faire passer T047.
- [X] T050 [US6] Intégrer `<HorizonToggle>` dans `pages/plan-action/index.vue` lié à `actionPlanStore.horizonView`. Vérifier que `visibleSteps` (getter) applique bien le filtre temporel (cf. `data-model.md` § 2.3 tableau toggle). Doit faire passer T048.

**Checkpoint US6**: Filtre temporel synchronisé sur les trois surfaces (timeline, liste, KPI).

---

## Phase 9: User Story 7 — Empty state pas encore de scoring (Priority: P1)

**Goal**: Si la PME n'a pas de scoring, `/plan-action` affiche un empty state explicite avec CTA `/scoring` ; aucun appel à la génération.

**Independent Test**: Compte PME sans scoring → ouvrir `/plan-action` → voir l'empty state avec bouton actif vers `/scoring`.

### Tests pour User Story 7

- [X] T051 [P] [US7] Créer `frontend/tests/components/plan-action/EmptyNoScoring.test.ts` : titre, body, CTA i18n, lien `/scoring`, `<UiEmptyState>` rendu.
- [X] T052 [P] [US7] Créer `frontend/tests/e2e/plan-action-empty-no-scoring.spec.ts` : seed PME sans scoring (`withScoring: false`), ouvrir `/plan-action`, vérifier empty state et CTA navigant vers `/scoring`.

### Implémentation User Story 7

- [X] T053 [US7] Créer `frontend/app/components/plan-action/EmptyNoScoring.vue` (encapsule `<UiEmptyState>`). Doit faire passer T051.
- [X] T054 [US7] Dans `useActionPlan.ts` (T014) : sur 404 du `GET /me/action-plan`, appeler le helper de détection de scoring (cf. `contracts/frontend-api-consumption.md` § C4 — fallback : si l'endpoint exact F23 n'existe pas, utiliser un check direct via store scoring si exposé, sinon afficher empty state générique avec deux CTA). Renvoyer un état typé `{ kind: 'no_scoring' | 'no_gaps' | 'error' | 'ok' }` au composant page.
- [X] T055 [US7] Brancher `<EmptyNoScoring>` dans `pages/plan-action/index.vue` selon le state retourné par T054. Doit faire passer T052.

**Checkpoint US7**: Empty state scoring fonctionnel, débloque le funnel.

---

## Phase 10: User Story 8 — Empty state pas de gaps (Priority: P1)

**Goal**: Scoring complet sans gap exploitable → message de célébration sobre.

**Independent Test**: Seed PME avec scoring sans gap → empty state célébration sur `/plan-action`.

### Tests pour User Story 8

- [X] T056 [P] [US8] Créer `frontend/tests/components/plan-action/EmptyNoGaps.test.ts` : titre célébration, body, absence de CTA destructif (uniquement « Re-générer le scoring » optionnel).
- [X] T057 [P] [US8] Créer `frontend/tests/e2e/plan-action-empty-no-gaps.spec.ts` : seed PME `withScoring: true, withGaps: false`, vérifier message célébration affiché, pas d'erreur.

### Implémentation User Story 8

- [X] T058 [US8] Créer `frontend/app/components/plan-action/EmptyNoGaps.vue` (encapsule `<UiEmptyState>`). Doit faire passer T056.
- [X] T059 [US8] Brancher `<EmptyNoGaps>` dans `pages/plan-action/index.vue` selon `kind === 'no_gaps'` (T054). Doit faire passer T057.

**Checkpoint US8**: Empty state célébration distinct de US7.

---

## Phase 11: User Story 9 — Synchronisation avec le chat (Priority: P1)

**Goal**: Mutation côté chat (`entity_updated{action_step}`) → la card concernée se rafraîchit en < 1 s, sans re-render global.

**Independent Test**: Émettre l'event via console, observer la card cible se rafraîchir (re-fetch ciblé visible dans Network).

### Tests pour User Story 9

- [X] T060 [P] [US9] Créer `frontend/tests/e2e/plan-action-chat-sync.spec.ts` : ouvrir `/plan-action`, exposer `useChatEventBus` à `window` pour le test, émettre `entity_updated{action_step, id}`, vérifier que (a) un seul GET `/me/action-plan` est ré-émis, (b) la card cible affiche la nouvelle valeur, (c) les autres cards restent identitaires (pas re-rendues — vérifier via attribut data-instance ou snapshot DOM).

### Implémentation User Story 9

- [X] T061 [US9] Vérifier que `useActionPlan.ts` (T014) implémente bien la souscription EventBus + l'invalidation ciblée + le garde anti-boucle 500 ms (déjà couvert par T006). Étendre si nécessaire pour exposer `__chatBus` en mode dev/test (cf. quickstart). Doit faire passer T060.
- [X] T062 [US9] Vérifier que les mutations locales (`StepCard` toggle, `EditStatusSheet` submit, `RegenerateModal` confirm) émettent bien sur le bus (`action_step:locally_updated`, `action_plan:regenerated`) selon `chat-eventbus-sync.md`. Si non câblé en T037/T046, ajouter ici. Pas de nouveau test (couvert par T032/T034/T042 + T060).

**Checkpoint US9**: Sync bidirectionnelle chat ↔ plan-action opérationnelle, P8 respectée.

---

## Phase 12: User Story 10 — Détail d'une étape (Priority: P1)

**Goal**: Chaque card affiche tous les champs (titre, desc, priorité, horizon, statut, responsable, source) ; clic sur le pin source ouvre la fiche indicateur ou affiche un fallback discret « source non disponible ».

**Independent Test**: Card avec source liée → clic ouvre `/scoring/indicateurs/{id}`. Card sans source → fallback texte.

### Tests pour User Story 10

- [X] T063 [P] [US10] Étendre `frontend/tests/components/plan-action/StepCard.test.ts` (T030) avec scénarios additionnels : (a) `indicateurId=null` → pas de pin source, libellé « source non disponible » discret ; (b) `indicateurId` valide → pin cliquable avec href correct.
- [X] T064 [P] [US10] Créer `frontend/tests/e2e/plan-action-source-link.spec.ts` : cliquer le pin source d'une carte → vérifier navigation vers `/scoring/indicateurs/{id}` (page existante F23).

### Implémentation User Story 10

- [X] T065 [US10] Vérifier que `<StepCard>` (T035) gère le fallback `indicateurId=null` selon `contracts/frontend-components.md` et FR-025. Étendre si nécessaire. Doit faire passer T063, T064.

**Checkpoint US10**: Toutes les cards sont complètes et traçables (P1 sourcing). MVP P1 terminé.

---

## Phase 13: User Story 11 — Historique des versions (Priority: P2 — différé)

**Goal**: Drawer lecture seule listant les versions antérieures du plan. Différé en P2 ; nécessite probablement un endpoint backend `GET /me/action-plan/versions` non livré par F31.

### Décision

- [X] T066 [US11] Vérifier dans `backend/app/action_plan/routes.py` et `service.py` si une route de listing des versions existe (ex. `GET /me/action-plan/versions` ou paramètre `?version=` sur la route existante). **DÉCISION** : aucune route de listing des versions n'est exposée par F31 (seules `POST /me/action-plan/generate`, `GET /me/action-plan`, `PATCH /me/action-plan/steps/{id}` existent — cf. `backend/app/action_plan/routes.py`). US11 est donc **différée hors scope F45** ; entrée de backlog créée dans `docs_et_brouillons/features/00-INDEX.md` § F45. T067–T070 ne sont pas exécutées dans cette phase.

### Tests (si T066 confirme la disponibilité)

- [ ] T067 [P] [US11] Créer `frontend/tests/components/plan-action/HistoryDrawer.test.ts` : props `versions[]`, rendu lecture seule, fermeture par Esc, a11y.
- [ ] T068 [P] [US11] Créer `frontend/tests/e2e/plan-action-history.spec.ts` : régénérer plan (US5), ouvrir drawer, vérifier ≥ 2 versions visibles, anciennes non modifiables.

### Implémentation (si T066 confirme)

- [ ] T069 [US11] Créer `frontend/app/components/plan-action/HistoryDrawer.vue`. Doit faire passer T067.
- [ ] T070 [US11] Intégrer `<HistoryDrawer>` dans `pages/plan-action/index.vue` derrière flag `featureFlags.history` (env var ou simple `true` si endpoint dispo). Doit faire passer T068.

**Checkpoint US11**: Soit livré derrière flag, soit explicitement différé avec entrée de backlog créée.

---

## Phase 14: User Story 12 — Export PDF (Priority: P2 — différé)

**Goal**: Bouton « Exporter en PDF » qui appelle le backend de génération. Différé jusqu'à livraison F51.

- [X] T071 [US12] Créer `frontend/app/components/plan-action/ExportPlanButton.vue` masqué derrière flag `PUBLIC_FEATURE_PLAN_EXPORT_PDF` (env var Nuxt). Bouton désactivé + message « Bientôt disponible » par défaut. Aucun appel backend tant que le flag est désactivé. Pas de test E2E tant que F51 n'est pas livrée ; un test unit minimal valide le rendu désactivé.
- [X] T072 [P] [US12] Créer `frontend/tests/components/plan-action/ExportPlanButton.test.ts` : avec flag off → bouton disabled + tooltip « Bientôt disponible » ; avec flag on → bouton actif déclenche `$fetch` (mock) et nomme le fichier `plan-action-{date}.pdf`.

**Checkpoint US12**: Bouton en place derrière flag, prêt à être activé dès livraison F51.

---

## Phase 15: Polish & Cross-cutting concerns

**Purpose**: Finitions qualité (perf, a11y, doc, intégration F44).

- [ ] T073 [P] Modifier `frontend/app/components/dashboard/CardActionPlan.vue` (livré F44) pour qu'elle lise `useActionPlanStore` au lieu de fetcher en propre (cf. research R5). Mettre à jour les tests F44 existants `frontend/tests/components/dashboard/CardActionPlan.test.ts` en conséquence (mock du store). Vérifier la non-régression du parcours dashboard.
- [ ] T074 [P] Mesurer la performance : exécuter Lighthouse en local sur `/plan-action` avec un plan de 50 étapes, vérifier LCP < 1,5 s p95 (NFR-001). Documenter dans `quickstart.md` les chiffres obtenus.
- [ ] T075 [P] Audit a11y : exécuter `axe` (ou Playwright a11y) sur `/plan-action` plein, empty no-scoring, empty no-gaps, sheet d'édition ouvert. Corriger toute violation AA. Ajouter un test E2E `frontend/tests/e2e/plan-action-a11y.spec.ts`.
- [ ] T076 [P] Vérifier que **toutes** les chaînes user-facing passent par `useT()` (pas de hardcode FR). Grep `frontend/app/components/plan-action/*.vue` et `frontend/app/pages/plan-action/index.vue` pour des chaînes FR oubliées.
- [ ] T077 [P] Vérifier la coverage vitest sur les fichiers nouveaux (`useActionPlan*`, `actionPlan` store, `mapPlanToTimelineBuckets`, `mapStepToCardViewModel`) : `pnpm test --coverage --coverage.include='app/composables/useActionPlan*.ts' --coverage.include='app/stores/actionPlan.ts' --coverage.include='app/lib/mapPlanToTimelineBuckets.ts'` ≥ 80 %. Compléter les tests manquants si seuil non atteint.
- [ ] T078 [P] Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F45 comme `done` (pattern F44).
- [ ] T079 Créer `specs/045-plan-action-ui/quickstart-validation.md` documentant le résultat des smoke tests manuels (US1 → US10), avec captures d'écran si possible (pattern F44).
- [ ] T080 Vérifier que `make lint` et `make test` passent sans erreur sur la branche `045-plan-action-ui`.

**Checkpoint Polish**: Feature prête pour merge sur `main`. Tous les tests passent, coverage ≥ 80 %, a11y AA, perf NFR-001 validée.

---

## Dependencies

```text
Phase 1 (Setup)              ─┐
Phase 2 (Foundational)        ├─► T001-T004 → T005-T010 → T011-T019
                              │
Phase 3 (US1)  ←──────────────┤   T020-T025 (timeline)
Phase 4 (US2)  ←──────────────┤   T026-T029 (filtres)         ├─ peuvent partir en parallèle
Phase 5 (US3)  ←──────────────┤   T030-T037 (toggle + sheet)  │  une fois Foundational terminé
Phase 6 (US4)  ←──────────────┤   T038-T040 (progress)        │
Phase 7 (US5)  ←──────────────┤   T041-T046 (regenerate)      │
Phase 8 (US6)  ←──────────────┤   T047-T050 (horizon toggle)  │
Phase 9 (US7)  ←──────────────┤   T051-T055 (empty no scoring)│
Phase 10 (US8) ←──────────────┤   T056-T059 (empty no gaps)   │
Phase 11 (US9) ←──────────────┤   T060-T062 (chat sync)       ┘  dépend de US3 + US5 pour les émissions locales
Phase 12 (US10) ←─────────────┤   T063-T065 (détail / source) — dépend de US3 (StepCard livrée)
Phase 13 (US11) ←─────────────┤   T066-T070 (history) — différé sauf si endpoint dispo
Phase 14 (US12) ←─────────────┤   T071-T072 (export PDF) — derrière flag
                              │
Phase 15 (Polish)             └─► T073-T080 — après les US livrées
```

**Note** : US3 et US5 émettent les events locaux ; US9 (chat sync) doit attendre que ces émissions soient câblées (T037, T046) pour son test E2E T060. US10 dépend de `<StepCard>` (T035).

## Parallel execution examples

Une fois Foundational terminé (T001-T019), les groupes suivants peuvent partir en parallèle :

- **Branche A (timeline + filtres)** : T020-T025 + T026-T029 — un dev frontend.
- **Branche B (interactions étapes)** : T030-T037 — un dev frontend (clé du MVP).
- **Branche C (régénération)** : T041-T046 — un dev frontend.
- **Branche D (empty states + horizon)** : T038-T040 + T047-T050 + T051-T059 — un dev frontend.
- **Sync + sourcing** : T060-T065 — à exécuter après merge des branches A/B/C/D.
- **Polish** : T073-T080 — en parallèle après MVP.

## Implementation Strategy — MVP first

1. **MVP minimum viable** = Foundational + US1 (timeline) + US3 (toggle/edit) + US4 (progress) + US7+US8 (empty states) + US10 (détail).
2. **MVP complet (P1)** = + US2 (filtres) + US5 (régénération) + US6 (horizon) + US9 (chat sync).
3. **Itération suivante (P2)** = US11 (history, conditionnel) + US12 (export PDF, conditionnel F51).

Chaque user story P1 reste **indépendamment testable** : on peut couper à n'importe quelle US et avoir une page utilisable.
