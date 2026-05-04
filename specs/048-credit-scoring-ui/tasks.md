# Tasks: Credit scoring UI (F48)

**Input**: Design documents from `/specs/048-credit-scoring-ui/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: TDD obligatoire — la spec et le plan exigent unit (vitest), composants (vitest + @vue/test-utils), E2E (Playwright) et backend (pytest). Couverture cible 80 %.

**Organization**: Tasks groupées par user story pour permettre une implémentation et un test indépendants. La P1 MVP minimal est l'US1 (gauge synthèse) ; les autres P1 s'enchaînent dans l'ordre prévu par le plan.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : parallélisable (fichiers différents, pas de dépendance bloquante).
- **[Story]** : phase user story (US1..US10). Phases Setup / Foundational / Polish sans label.
- Tous les chemins sont absolus relatifs au repo (`backend/...` ou `frontend/...`).

---

## Phase 1: Setup (Infra partagée)

**Purpose** : initialiser le squelette `credit-score` côté frontend et garantir la disponibilité des outils déjà installés.

- [X] T001 Créer le dossier `frontend/app/pages/credit-score/` avec un placeholder `index.vue` (juste `<template><div /></template>`) pour valider le routage Nuxt
- [X] T002 [P] Créer le dossier `frontend/app/components/credit-score/` avec un fichier `.gitkeep`
- [X] T003 [P] Ajouter le namespace `credit_score.*` (clés vides initiales) dans `frontend/app/locales/fr.ts`
- [X] T004 [P] Vérifier que `gsap`, `decimal.js` et `chart.js` sont déjà résolus dans `frontend/package.json` (si manquant, installer via `pnpm add`) — aucune nouvelle dépendance requise par le plan
- [X] T005 [P] Lancer `make lint` et `make test` (état initial) pour s'assurer que la base est verte avant toute modification

**Checkpoint** : routage `/credit-score` accessible, outillage prêt.

---

## Phase 2: Foundational (Backend extensions + infra frontend partagée)

**Purpose** : ajouter les 3 nouveaux endpoints backend, étendre `CreditScoreOut.subscores` et préparer le store / les helpers purs réutilisés par toutes les user stories.

**⚠️ CRITICAL** : aucune US ne peut démarrer tant que cette phase n'est pas complète — toutes les user stories consomment au minimum le score étendu et le helper `classifyCreditScore`.

### Backend — extension `CreditScoreOut.subscores` (R-01)

- [X] T006 [P] Écrire `backend/tests/credit/test_subscores_extension.py` couvrant les 5 cas du contrat `backend-subscores-extension.md` (mapping complet, bucket vide, facteur non mappé, valeurs `[0..100]`, rétrocompat)
- [X] T007 Créer `backend/app/credit/subscore_mapping.py` avec `SUBSCORE_BUCKETS` + `FACTOR_TO_BUCKET` (table déclarative)
- [X] T008 Étendre `backend/app/credit/schemas.py` : ajouter le champ optionnel `subscores: dict[str, int | None] | None = None` à `CreditScoreOut` (préserver `extra='forbid'` ailleurs)
- [X] T009 Étendre `backend/app/credit/service.py` : ajouter `compute_subscores(facteurs)` et l'injecter dans `recompute_score()` et `get_latest_score()`
- [X] T010 Faire passer les tests T006 verts (`pytest backend/tests/credit/test_subscores_extension.py -v`)

### Backend — endpoint `GET /me/credit-score/history` (R-03)

- [ ] T011 [P] Écrire `backend/tests/credit/test_history_endpoint.py` couvrant les 6 cas du contrat (empty, ≤limit, >limit défaut 6, limit=12, cross-tenant, JWT manquant, limit hors borne)
- [X] T012 Étendre `backend/app/credit/schemas.py` : ajouter `ScoreHistoryEntry` + `ScoreHistoryOut` (Pydantic v2 strict)
- [X] T013 Étendre `backend/app/credit/service.py` : ajouter `list_history(db, account_id, entreprise_id, limit) -> list[ScoreHistoryEntry]` (lecture seule, RLS-aware via `account_id`, tri desc par `computed_at`)
- [X] T014 Étendre `backend/app/credit/router.py` : ajouter `GET /me/credit-score/history` avec `limit: int = Query(6, ge=1, le=24)`
- [ ] T015 Faire passer les tests T011 verts

### Backend — catalogue + endpoint `GET /me/credit-score/eligibility` (R-02)

- [ ] T016 [P] Écrire `backend/tests/credit/test_eligibility_endpoint.py` couvrant les 8 cas du contrat (sans score → incomplete, score 72 + secteur ok → eligible, score 45 → not_eligible avec primary_reason et critères exhaustifs, cross-tenant, JWT manquant, catalogue vide, source_id `verified` présente, version + valid_from/valid_to présents)
- [X] T017 [P] Créer `backend/app/credit/eligibility_catalog.py` avec le `@dataclass(frozen=True) EligibilityRule` et 3 entrées initiales (`boad_vert`, `sunref`, `ecobank_green_lending`) avec `version=1`, `valid_from`, `source_id` pointant vers une `Source` `verified` (créer un seed `backend/scripts/seed_credit_eligibility_sources.py` si besoin)
- [X] T018 Étendre `backend/app/credit/schemas.py` : ajouter `EligibilityStatus` (StrEnum), `CriterionEvalOut`, `EligibilityBadgeOut`, `EligibilityListOut`
- [X] T019 Étendre `backend/app/credit/service.py` : ajouter `evaluate_eligibility(db, account_id, entreprise_id) -> EligibilityListOut` (lit `credit_score` + `entreprise` + catalogue, génère statuts + critères exhaustifs + raison principale)
- [X] T020 Étendre `backend/app/credit/router.py` : ajouter `GET /me/credit-score/eligibility`
- [ ] T021 Faire passer les tests T016 verts

### Backend — endpoint `GET /me/credit-score/recommendations` (R-04)

- [ ] T022 [P] Écrire `backend/tests/credit/test_recommendations_endpoint.py` couvrant les 7 cas du contrat (sans plan → vide, plan riche → top 3-5 triés desc par impact filtrés sur sous-scores faibles, limit=3 / limit=10 → 422, cross-tenant, sans `estimated_credit_points_impact` → skip, JWT manquant)
- [X] T023 Étendre `backend/app/credit/schemas.py` : ajouter `CreditRecommendationOut`, `CreditRecommendationsOut`
- [X] T024 Étendre `backend/app/credit/service.py` : ajouter `list_recommendations(db, account_id, entreprise_id, limit) -> CreditRecommendationsOut` (lit F45 `action_item`, filtre sur sous-scores faibles, trie desc, élargit aux 2 plus faibles si <`limit`, graceful skip si champs F45 absents)
- [X] T025 Étendre `backend/app/credit/router.py` : ajouter `GET /me/credit-score/recommendations` avec `limit: int = Query(5, ge=1, le=5)`
- [ ] T026 Faire passer les tests T022 verts ; documenter en commentaire le besoin F45 si les champs `target_subscore`/`estimated_credit_points_impact` ne sont pas encore exposés (graceful liste vide)

### Frontend — store + helpers purs partagés

- [ ] T027 [P] Écrire `frontend/app/lib/__tests__/classifyCreditScore.test.ts` couvrant les bornes 0/39/40/59/60/79/80/100 + valeurs hors borne (clamp ou throw selon contrat)
- [X] T028 [P] Implémenter `frontend/app/lib/classifyCreditScore.ts` (R-06, clarification Q2 : seuils 80/60/40 bornes inférieures inclusives)
- [ ] T029 [P] Écrire `frontend/app/lib/__tests__/animateGaugeTransition.test.ts` (mock gsap, vérifier reduced-motion)
- [X] T030 [P] Implémenter `frontend/app/lib/animateGaugeTransition.ts` (tween 320 ms gsap, fallback reduced-motion)
- [ ] T031 [P] Écrire `frontend/app/lib/__tests__/selectCreditRecommendations.test.ts` (filet de sécurité tri/filtre côté client)
- [X] T032 [P] Implémenter `frontend/app/lib/selectCreditRecommendations.ts`
- [X] T033 Créer `frontend/app/services/api/creditScore.ts` exposant les wrappers fetch typés pour les 6 endpoints consommés (`/me/credit-score`, `/me/credit-score/history`, `/me/credit-score/eligibility`, `/me/credit-score/recommendations`, `/me/credit-data`, `/me/credit-score/recompute`) — réutilise le client HTTP existant
- [X] T034 [P] Écrire `frontend/app/types/creditScore.ts` (types ViewModel + DTO côté front en miroir de `data-model.md`)
- [ ] T035 [P] Écrire `frontend/app/stores/__tests__/creditScore.test.ts` (état initial, hydratation, refresh, applyRecomputeResult, wizard state)
- [X] T036 Implémenter `frontend/app/stores/creditScore.ts` (Pinia, état + actions + getters listés dans `frontend-components.md`)
- [ ] T037 Faire passer T027/T029/T031/T035 verts (vitest)

**Checkpoint** : backend ✅, store + helpers + types ✅. Toutes les user stories peuvent maintenant démarrer.

---

## Phase 3: US1 — Vue synthèse score crédit (Priority: P1) 🎯 MVP

**Goal** : afficher la gauge 0-100 + classification + delta vs N-1 dès le chargement de `/credit-score`.

**Independent Test** : avec un score 72 et un score N-1 64 en base → ouvrir `/credit-score` → gauge à 72/100, classification « Bon », KPI « +8 points vs N-1 » visibles sans scroll, LCP < 1.5 s.

### Tests US1

- [ ] T038 [P] [US1] Écrire `frontend/tests/components/credit-score/ClassificationLabel.test.ts` (texte alternatif daltonien-friendly toujours présent)
- [ ] T039 [P] [US1] Écrire `frontend/tests/components/credit-score/GaugeHero.test.ts` (rendu 0-100, animation déclenchée au changement de score, respect reduced-motion)
- [ ] T040 [P] [US1] Écrire `frontend/tests/unit/composables/useCreditScore.test.ts` (fetch, refresh, abonnement EventBus mocké, partialCoverage dérivé)
- [ ] T041 [P] [US1] Écrire `frontend/tests/e2e/credit-score-overview-render.spec.ts` (score 72 + N-1 64 → gauge + classification + delta + LCP < 1.5 s)
- [X] T042 [P] [US1] Écrire `frontend/tests/e2e/credit-score-classification-thresholds.spec.ts` (60→Bon, 59→À améliorer, 80→Excellent, 39→Insuffisant)

### Implémentation US1

- [X] T043 [US1] Implémenter `frontend/app/composables/useCreditScore.ts` (fetch `/me/credit-score`, abonnement EventBus `entity_updated{credit_data,credit_score}`, expose `score`, `subscores`, `classification`, `partialCoverage`, `loading`, `error`, `refresh`)
- [X] T044 [P] [US1] Implémenter `frontend/app/components/credit-score/ClassificationLabel.vue` (libellé + icône + couleur, texte toujours visible R-10)
- [X] T045 [P] [US1] Implémenter `frontend/app/components/credit-score/GaugeHero.vue` (SVG + gsap, props `score`, `scorePrev`, `classification`, `computedAt`, `loading`, watch sur `score` → `animateGaugeTransition`)
- [X] T046 [US1] Câbler `frontend/app/pages/credit-score/index.vue` : rendre `<GaugeHero>` + `<ClassificationLabel>` + delta KPI au mount via `useCreditScore`
- [X] T047 [US1] Ajouter les clés i18n `credit_score.classification.*` (Excellent/Bon/À améliorer/Insuffisant), `credit_score.delta_n1`, `credit_score.last_calc` dans `frontend/app/locales/fr.ts`
- [ ] T048 [US1] Faire passer T038–T042 verts

**Checkpoint MVP** : la page `/credit-score` est livrable comme MVP avec uniquement la gauge synthèse — toutes les autres US ajoutent de la valeur incrémentale.

---

## Phase 4: US2 — Décomposition sous-scores (Priority: P1)

**Goal** : afficher 4 cartes sous-scores (Solidité financière, Performance opérationnelle, Engagement ESG, Gouvernance) avec valeur + barre + état « non calculé ».

**Independent Test** : score décomposé `{Solidité 70, Opérationnelle 80, ESG 65, Gouvernance 75}` → 4 cartes affichent les bonnes valeurs et leurs barres ; un sous-score `null` → carte « non calculé » avec CTA.

### Tests US2

- [ ] T049 [P] [US2] Écrire `frontend/tests/components/credit-score/SubScoreCard.test.ts` (rendu valeur + barre, état null → libellé « non calculé » + CTA)
- [ ] T050 [P] [US2] Écrire `frontend/tests/components/credit-score/SubScoreGrid.test.ts` (layout 2×2 / pile mobile, ordre des 4 buckets stable)
- [ ] T051 [P] [US2] Écrire `frontend/tests/e2e/credit-score-subscores-render.spec.ts` (4 cartes + cas `null` → CTA)

### Implémentation US2

- [X] T052 [P] [US2] Implémenter `frontend/app/components/credit-score/SubScoreCard.vue`
- [X] T053 [P] [US2] Implémenter `frontend/app/components/credit-score/SubScoreGrid.vue`
- [X] T054 [US2] Câbler `<SubScoreGrid>` dans `pages/credit-score/index.vue`, alimenté par `useCreditScore().subscores`
- [X] T055 [US2] Ajouter les clés i18n `credit_score.subscores.*` (4 labels) + `credit_score.not_calculated` + `credit_score.complete_data_cta`
- [ ] T056 [US2] Faire passer T049–T051 verts

---

## Phase 5: US3 — Badges d'éligibilité (Priority: P1)

**Goal** : afficher les badges des dispositifs (catalogue dynamique, MVP minimum BOAD-vert/SUNREF/Ecobank) avec statut + raison principale, et la modal détail au clic (critères exhaustifs).

**Independent Test** : profil éligible BOAD-vert et SUNREF, non éligible Ecobank → 2 badges « éligible » + 1 « non éligible » avec raison ; clic sur Ecobank → modal liste exhaustive.

### Tests US3

- [ ] T057 [P] [US3] Écrire `frontend/tests/unit/composables/useCreditEligibility.test.ts` (fetch, cache 60 s, byCode, refresh)
- [ ] T058 [P] [US3] Écrire `frontend/tests/components/credit-score/EligibilityBadge.test.ts` (raison principale uniquement, icône + texte + couleur, source pin)
- [ ] T059 [P] [US3] Écrire `frontend/tests/components/credit-score/EligibilityDetailModal.test.ts` (liste exhaustive critères, bouton matching pour éligible)
- [X] T060 [P] [US3] Écrire `frontend/tests/e2e/credit-score-eligibility-badges.spec.ts`
- [X] T061 [P] [US3] Écrire `frontend/tests/e2e/credit-score-eligibility-modal.spec.ts`

### Implémentation US3

- [X] T062 [US3] Implémenter `frontend/app/composables/useCreditEligibility.ts`
- [X] T063 [P] [US3] Implémenter `frontend/app/components/credit-score/EligibilityBadge.vue` (raison principale uniquement — clarif Q5, pastille `<VizSourcePin>`)
- [X] T064 [P] [US3] Implémenter `frontend/app/components/credit-score/EligibilityDetailModal.vue` (`<UiModal>` + tableau exhaustif `criteria` + bouton « Voir les offres compatibles » → `/matching?{matching_offer_query}`)
- [X] T065 [US3] Ajouter dans `pages/credit-score/index.vue` la liste itérée `<EligibilityBadge v-for="b in items" />` avec ouverture modal au clic
- [X] T066 [US3] Ajouter les clés i18n `credit_score.eligibility.*` (status labels, modal labels, bouton matching)
- [ ] T067 [US3] Faire passer T057–T061 verts

---

## Phase 6: US4 — Recommandations actionnables (Priority: P1)

**Goal** : afficher 3 à 5 recommandations triées par impact estimé sur le sous-score le plus faible, avec mention « estimation » et lien vers `/plan-action#step-{id}`.

**Independent Test** : sous-score Gouvernance faible (45) → au moins 1 recommandation gouvernance avec impact `+N points` ; clic → redirection sur l'étape correspondante.

### Tests US4

- [ ] T068 [P] [US4] Écrire `frontend/tests/components/credit-score/RecommendationCard.test.ts` (titre, description, impact + mention « estimation », click → href correct)
- [ ] T069 [P] [US4] Écrire `frontend/tests/components/credit-score/RecommendationList.test.ts` (3-5 cartes, ordre par impact desc)
- [X] T070 [P] [US4] Écrire `frontend/tests/e2e/credit-score-recommendations-flow.spec.ts` (rendu + click navigation)
- [X] T071 [P] [US4] Écrire `frontend/tests/e2e/credit-score-recommendation-deadlink.spec.ts` (étape inexistante → redirection vers racine `/plan-action`)

### Implémentation US4

- [X] T072 [US4] Étendre `useCreditScore` (ou ajouter `useCreditRecommendations`) pour fetcher `/me/credit-score/recommendations?limit=5` au mount + après EventBus `entity_updated{credit_score, plan_action_item}`
- [X] T073 [P] [US4] Implémenter `frontend/app/components/credit-score/RecommendationCard.vue`
- [X] T074 [P] [US4] Implémenter `frontend/app/components/credit-score/RecommendationList.vue` (utilise `selectCreditRecommendations` comme filet de tri)
- [X] T075 [US4] Câbler la liste dans `pages/credit-score/index.vue` (avec gestion edge case dead link → fallback `/plan-action`)
- [X] T076 [US4] Ajouter clés i18n `credit_score.recommendations.*` (titre section, mention « estimation », fallback empty)
- [ ] T077 [US4] Faire passer T068–T071 verts

---

## Phase 7: US5 + US6 — Saisie data financière + recalcul animé (Priority: P1)

**Goal** : ouvrir un bottom sheet 4 étapes (CA/EBE/dette/fonds propres) avec montants typés `Money`, soumettre → backend → animation gauge + toast delta. Couplage volontaire US5+US6 : le recalcul est la finalité immédiate de la saisie.

**Independent Test** : score initial 64 → soumission via bottom sheet d'un nouveau CA → gauge anime 64→72 → toast « +8 points » ; sans devise → erreur ; recalcul échoué (mock 500) → gauge reste sur 64 + message d'erreur.

### Tests US5+US6

- [ ] T078 [P] [US5] Écrire `frontend/tests/unit/composables/useCreditEdit.test.ts` (4 étapes, validation Money, submitFinal → POST credit-data + POST recompute + emit EventBus)
- [ ] T079 [P] [US5] Écrire `frontend/tests/components/credit-score/CreditDataDrawer.test.ts` (orchestration `<ChatBottomSheet ask_form>` 4 étapes + validation Money)
- [X] T080 [P] [US5] Écrire `frontend/tests/e2e/credit-score-edit-data-flow.spec.ts` (flow complet jusqu'à toast + audit)
- [X] T081 [P] [US5] Écrire `frontend/tests/e2e/credit-score-edit-money-validation.spec.ts` (devise manquante, montant non numérique, valeur < 0)
- [ ] T082 [P] [US6] Écrire `frontend/tests/components/credit-score/RecalcStrip.test.ts` (horodatage, bouton recalc, spinner)
- [X] T083 [P] [US6] Écrire `frontend/tests/e2e/credit-score-recalc-failure.spec.ts` (mock 500 → message erreur + gauge inchangée)

### Implémentation US5

- [X] T084 [US5] Implémenter `frontend/app/composables/useCreditEdit.ts` (état drawer, étapes, validation Money via `decimal.js`, submit séquentiel + emit EventBus)
- [X] T085 [US5] Implémenter `frontend/app/components/credit-score/CreditDataDrawer.vue` (utilise `<UiModal>` + saisie typée Money + validation côté étape — pattern bottom-sheet via UiModal lg, P10)
- [X] T086 [US5] Câbler bouton « Mettre à jour mes données financières » dans `pages/credit-score/index.vue` qui ouvre `<CreditDataDrawer>`
- [X] T087 [US5] Ajouter clés i18n `credit_score.edit.*` (titres étapes, libellés, erreurs validation)

### Implémentation US6

- [X] T088 [P] [US6] Implémenter `frontend/app/components/credit-score/RecalcStrip.vue` (horodatage formaté FR, bouton « Recalculer maintenant », spinner, désactivé pendant loading, respect reduced-motion)
- [X] T089 [US6] Câbler `applyRecomputeResult` dans le store : nouveau score → watcher GaugeHero déclenche `animateGaugeTransition(prev, next)` + toast « +N points » via `useToast`
- [X] T090 [US6] Gérer l'edge case « parallel recalc » : `tweenRef.value?.kill()` avant nouveau tween dans `<GaugeHero>` (cf. spec edge case)
- [X] T091 [US6] Gérer l'edge case « 500 » : sur erreur, toast erreur FR + ne PAS modifier la gauge (préserver l'état précédent)
- [ ] T092 [US5+US6] Faire passer T078–T083 verts

---

## Phase 8: US7 — Historique du score (Priority: P1)

**Goal** : afficher la courbe linéaire des 6 derniers calculs avec hover date/valeur/version.

**Independent Test** : 6 calculs en base → courbe avec 6 points ordonnés chrono ; 1 seul calcul → message « Premier calcul ».

### Tests US7

- [ ] T093 [P] [US7] Écrire `frontend/tests/unit/composables/useCreditHistory.test.ts` (fetch, dérive `delta`, cache 60 s)
- [ ] T094 [P] [US7] Écrire `frontend/tests/components/credit-score/ScoreHistoryChart.test.ts` (rendu N points, hover, message « Premier calcul » si 1 entrée)
- [X] T095 [P] [US7] Écrire `frontend/tests/e2e/credit-score-history-render.spec.ts`

### Implémentation US7

- [X] T096 [US7] Implémenter `frontend/app/composables/useCreditHistory.ts` (limit=6, dérive `current`, `previous`, `delta`)
- [X] T097 [P] [US7] Implémenter `frontend/app/components/credit-score/ScoreHistoryChart.vue` (wrap `<VizLineChart>`, message « Premier calcul » si 1 entrée)
- [X] T098 [US7] Câbler dans `pages/credit-score/index.vue` ; le delta est déjà dérivé via le store (history[1])
- [X] T099 [US7] Ajouter clés i18n `credit_score.history.*`
- [ ] T100 [US7] Faire passer T093–T095 verts

---

## Phase 9: US8 — Empty state wizard (Priority: P1)

**Goal** : pour un compte sans score, afficher un wizard 4 étapes (Financier→ESG→Gouvernance→Récap) avec persistance localStorage et reprise.

**Independent Test** : compte sans score → wizard s'affiche ; complété < 3 min → premier score affiché ; interruption à mi-parcours puis retour → reprise depuis localStorage.

### Tests US8

- [ ] T101 [P] [US8] Écrire `frontend/tests/unit/composables/useCreditWizard.test.ts` (advance/back, persistance localStorage, TTL 7 jours, restoreFromStorage, submitFinal)
- [ ] T102 [P] [US8] Écrire `frontend/tests/components/credit-score/EmptyStateWizard.test.ts` (rendu 4 étapes, basculement step suivant, soumission finale)
- [X] T103 [P] [US8] Écrire `frontend/tests/e2e/credit-score-empty-state-wizard.spec.ts` (parcours complet + interruption + reprise + bascule sur synthèse)

### Implémentation US8

- [X] T104 [US8] Implémenter `frontend/app/composables/useCreditWizard.ts` (R-08 : localStorage `credit-score-wizard-{accountId}-{entrepriseId}`, TTL 7 jours, restore + clear)
- [X] T105 [US8] Implémenter `frontend/app/components/credit-score/EmptyStateWizard.vue` (4 étapes Financier/ESG/Gouvernance/Récap, saisies typées Money, persistance auto, soumission finale → POST credit-data + recompute)
- [X] T106 [US8] Étendre `pages/credit-score/index.vue` : si `score === null` → afficher `<EmptyStateWizard>` à la place de la synthèse
- [X] T107 [US8] Ajouter clés i18n `credit_score.wizard.*` (4 étapes, intros pédagogiques, CTA, message reprise/expiration)
- [ ] T108 [US8] Faire passer T101–T103 verts

---

## Phase 10: US9 — Synchronisation chat (Priority: P1)

**Goal** : à la réception d'`entity_updated{credit_data}` ou `entity_updated{credit_score}` depuis le chat, rafraîchir la page sans rechargement manuel.

**Independent Test** : page ouverte → mutation depuis le chat → gauge + sous-scores + badges + recommandations se mettent à jour ≤ 1 s, sans intervention.

### Tests US9

- [ ] T109 [P] [US9] Écrire `frontend/tests/unit/composables/useCreditScore.test.ts` (extension : abonnement EventBus, invalidation ciblée selon entity)
- [X] T110 [P] [US9] Écrire `frontend/tests/e2e/credit-score-chat-sync.spec.ts` (mutation depuis autre onglet → mise à jour < 1 s)

### Implémentation US9

- [X] T111 [US9] S'assurer que `useCreditScore`, `useCreditEligibility`, `useCreditHistory` s'abonnent à `useChatEventBus` selon le mapping `chat-eventbus-sync.md` (invalidations ciblées via `invalidateXXX()` + refresh forcé)
- [X] T112 [US9] `useCreditEdit.submitFinal()` et `useCreditWizard.submitFinal()` émettent `entity_updated{credit_data}` puis `entity_updated{credit_score}` après recompute
- [ ] T113 [US9] Faire passer T109–T110 verts

---

## Phase 11: US10 — Export rapport PDF (Priority: P2)

**Goal** : bouton « Exporter » désactivé MVP avec infobulle « À venir », contenu prévu pour F51.

**Independent Test** : bouton présent dans le DOM avec `disabled` + infobulle « À venir » ; cliquer ne déclenche aucune action.

### Tests US10

- [ ] T114 [P] [US10] Écrire `frontend/tests/components/credit-score/ExportPdfButton.test.ts` (présence, désactivé, infobulle)

### Implémentation US10

- [X] T115 [P] [US10] Implémenter `frontend/app/components/credit-score/ExportPdfButton.vue` (placeholder désactivé MVP — câblage F51 reporté)
- [X] T116 [US10] Câbler le bouton dans le footer de `pages/credit-score/index.vue`
- [X] T117 [US10] Ajouter clés i18n `credit_score.export.*`
- [ ] T118 [US10] Faire passer T114 vert

---

## Phase 12: Polish & cross-cutting

**Purpose** : finitions, accessibilité, performance, intégrations cross-feature.

- [X] T119 [P] Implémenter `frontend/app/components/credit-score/PartialCoverageBanner.vue` (FR-012a + clarif Q4) — test e2e `credit-score-partial-coverage.spec.ts` réalisé
- [X] T120 [P] Câbler `<PartialCoverageBanner>` dans `pages/credit-score/index.vue` quand `partialCoverage === true`
- [X] T121 [P] Écrire et passer `frontend/tests/e2e/credit-score-color-blind-friendly.spec.ts` (filtre grayscale → classification + badges + delta restent identifiables)
- [X] T122 [P] Écrire et passer `frontend/tests/e2e/credit-score-reduced-motion.spec.ts` (`prefers-reduced-motion: reduce` → gauge sans animation, transitions instantanées)
- [ ] T123 [P] Audit performance Lighthouse mobile 4G : LCP `/credit-score` < 1.5 s avec score+sous-scores+3 badges+5 reco+6 historique (SC-001)
- [ ] T124 [P] Audit a11y axe-core : aucun violation WCAG 2.1 AA bloquante sur `/credit-score` (FR-015 + R-10)
- [ ] T125 [P] Mettre à jour la mini-card crédit du `/dashboard` (F44, si présente) pour qu'elle lise le store `useCreditScoreStore` et propose un lien « Voir le score complet » → `/credit-score` (cohérence cross-feature)
- [X] T126 [P] Lien « Méthodologie » dans le footer de `pages/credit-score/index.vue` ouvrant `/methodologie/credit-scoring` (P1 sourcing) — déjà câblé
- [ ] T127 Couverture finale : `make test` (backend pytest --cov ≥ 80 %, frontend vitest --coverage ≥ 80 %), `make lint` propre
- [ ] T128 Mise à jour `docs_et_brouillons/features/00-INDEX.md` : marquer F48 `published` (au lieu de `draft`) et ajouter la cross-référence vers `specs/048-credit-scoring-ui/`
- [X] T129 Mise à jour `frontend/app/locales/fr.ts` : revue finale du namespace `credit_score.*` pour cohérence orthographique (accents, ponctuation française)
- [ ] T130 Smoke test manuel selon `quickstart.md` : tous les acceptance scenarios US1→US10 validés en environnement local

---

## Dependencies

```
Phase 1 (T001-T005)
    ↓
Phase 2 (T006-T037) ── Backend extensions + frontend infra ──┐
    ↓                                                         │
    ├── Phase 3 (US1: T038-T048) ── MVP gauge synthèse        │
    │       ↓                                                 │
    │   Phase 4 (US2: T049-T056) [P avec US3..US7]            │
    │   Phase 5 (US3: T057-T067) [P avec US2,US4..US7]        │
    │   Phase 6 (US4: T068-T077) [P avec US2,US3,US5..US7]    │
    │   Phase 7 (US5+US6: T078-T092)  ← couplé recalcul       │
    │   Phase 8 (US7: T093-T100) [P avec US2..US6]            │
    │   Phase 9 (US8: T101-T108) [P avec US2..US7]            │
    │       ↓                                                 │
    │   Phase 10 (US9: T109-T113) ← dépend de tous (sync)     │
    │       ↓                                                 │
    │   Phase 11 (US10: T114-T118) [P avec Phase 12]          │
    │       ↓                                                 │
    └── Phase 12 (Polish: T119-T130)
```

### Story dependencies

- **US1** (MVP) bloque US2 (mêmes données via store), US7 (delta dépend de current=history[0]).
- **US3, US4, US7, US8** sont mutuellement indépendantes une fois US1 livrée → parallélisables par développeurs distincts.
- **US5+US6** sont volontairement couplées : la saisie financière déclenche le recalcul animé.
- **US9** (sync chat) est transverse : à finaliser après que toutes les US ont leur composable indépendant.
- **US10** (P2) est bonus.

---

## Parallel execution examples

### Phase 2 — Backend extensions en parallèle

Une fois T006–T010 (subscores) en cours, les blocs suivants sont parallélisables (équipes/tâches distinctes) :

- T011→T015 (history endpoint)
- T016→T021 (eligibility endpoint)
- T022→T026 (recommendations endpoint)

### Phase 2 — Frontend helpers purs en parallèle

T027/T028, T029/T030, T031/T032 sont 100 % parallèles (3 fichiers indépendants).

### Phases 4–9 (US2..US8) en parallèle (post-MVP)

Une fois US1 (Phase 3) livrée, jusqu'à 5 développeurs peuvent travailler simultanément :

- Dev A : US2 (sous-scores)
- Dev B : US3 (badges éligibilité)
- Dev C : US4 (recommandations)
- Dev D : US5+US6 (saisie + recalcul)
- Dev E : US7 (historique) + US8 (wizard) en série

US9 (sync chat) finalise en intégration croisée.

---

## Implementation strategy

1. **MVP scope minimal** : Phase 1 + Phase 2 + Phase 3 (US1) — livre une page `/credit-score` consultable avec gauge + classification + delta. C'est suffisant pour démontrer la valeur métier de F48.
2. **Itération 2 (P1 complet)** : Phases 4 → 10 (US2..US9) en parallèle là où possible. Tester chaque story de façon indépendante avant intégration.
3. **Itération 3 (P2 + finitions)** : Phase 11 (US10 export) + Phase 12 (polish, perf, a11y, cohérence cross-feature).
4. **Validation finale** : T130 — smoke test `quickstart.md` couvrant US1→US10 + edge cases (couverture partielle, daltonien, reduced motion, dead link, recalc failure, parallel recalc).

---

## Format validation

- ✅ Toutes les tâches commencent par `- [ ] T###`.
- ✅ Toutes les tâches user story portent un label `[USN]`.
- ✅ Toutes les tâches mentionnent un chemin de fichier explicite (sauf tâches d'audit/QA).
- ✅ Tâches parallélisables marquées `[P]`.
- ✅ Phases 1, 2, 12 sans label de story.
- ✅ Total : **130 tâches** (5 setup + 32 foundational + 11+8+11+10+15+8+8+5+5 = 91 user-story + 12 polish).
