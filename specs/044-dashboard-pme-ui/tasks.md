# Tasks: Dashboard PME UI (F44)

**Input**: Design documents from `/specs/044-dashboard-pme-ui/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Tests are **REQUIRED** par la constitution (TDD + 80 % coverage). Chaque user story inclut tests vitest (unit/components) puis Playwright (e2e) écrits **avant** l'implémentation.

**Organization**: Tâches groupées par user story pour livraison MVP incrémentale. Toutes les modifications sont **frontend-only** (`frontend/app/`) ; aucun backend touché.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallélisable (fichier différent, pas de dépendance bloquante).
- **[Story]**: US1 → US8 ; pas de label pour Setup / Foundational / Polish.
- Tous les chemins sont absolus côté repo (`frontend/app/...`).

## Path Conventions (rappel plan.md)

- Frontend Nuxt 4 : `frontend/app/{pages,components,composables,stores,lib,locales}`.
- Tests : `frontend/tests/{unit,components,e2e}` (héritage F38/F42/F43) et `frontend/app/composables/__tests__` / `frontend/app/stores/__tests__` (pattern existant pour les composables et stores).
- Backend : **inchangé**.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Préparer l'arborescence et les clés i18n communes à toutes les cartes.

- [X] T001 Créer le dossier `frontend/app/components/dashboard/` (vide pour l'instant) et `frontend/app/lib/` s'il n'existe pas, puis ajouter les fichiers `.gitkeep` pour committer la structure.
- [X] T002 [P] Ajouter dans `frontend/app/locales/fr.ts` un namespace `dashboard.*` avec toutes les clés nécessaires : `welcome.greeting_morning`, `welcome.greeting_evening`, `welcome.last_diagnostic_relative`, `welcome.no_diagnostic`, `welcome.cta_chat`, `cards.scoring.title`, `cards.scoring.empty_message`, `cards.scoring.empty_cta`, `cards.carbon.*`, `cards.credit.*`, `cards.candidatures.*`, `cards.rapports.*`, `cards.action_plan.*`, `cards.intermediaires.*`, `card.error.message`, `card.error.retry`, `export.button`, `export.toast_started`, `export.toast_error`, `export.toast_success`, `action_plan.toggle_error`, `statut.candidature.*`.
- [X] T003 [P] Créer le fichier `frontend/app/lib/dashboardEventMap.ts` qui exporte la table `EVENT_TO_BLOCK_MAP` (cf. research R5) et le type `BlockKey`.
- [X] T004 Vérifier dans `frontend/package.json` la présence d'une bibliothèque QR ; si absente, ajouter `qrcode-vue3` (≤ 10 ko) via `pnpm add qrcode-vue3` puis lancer `pnpm install` (cf. research R7).

**Checkpoint Setup**: Arborescence prête, clés i18n et map d'événements en place, dépendances installées.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Construire les briques transverses utilisées par toutes les cartes (store, composable de fetch, adapter de mapping, composants génériques skeleton/error/empty). Ces tâches doivent être terminées avant qu'aucune carte spécifique ne puisse être livrée.

**⚠️ CRITICAL**: Aucune user story ne peut commencer avant ce checkpoint.

### Tests d'abord (TDD)

- [X] T005 [P] Créer `frontend/app/stores/__tests__/dashboard.test.ts` avec scénarios : (a) `fetchSummary()` met à jour `state.summary`, (b) `fetchSummary({ scope: ['scores'] })` n'écrit que la clé `scores`, (c) `invalidate('carbon')` ajoute la clé à `invalidatedBlocks`, (d) deux `fetchSummary()` simultanés sont serialisés (un seul appel HTTP), (e) `reset()` purge tout. Mock `$fetch`.
- [X] T006 [P] Créer `frontend/app/composables/__tests__/useDashboardSummary.test.ts` avec scénarios : (a) au mount, fetch est appelé une fois ; (b) interval 60 s déclenche fetch périodique ; (c) `document.visibilityState = 'hidden'` met l'interval en pause ; (d) émission `scoring:computed` sur EventBus déclenche `fetchSummary({ scope: ['scores'] })` ; (e) émission d'event inconnu n'a aucun effet ; (f) émission `attestation:emitted` déclenche fetch sur `['rapports','attestations']` ; (g) cleanup `onUnmounted` détache les listeners et clear l'interval.
- [X] T007 [P] Créer `frontend/app/lib/__tests__/mapSummaryToCardViewModels.test.ts` avec scénarios : pour chaque carte (scoring, carbon, credit, candidatures, rapports, actionPlan, intermediaires) tester (a) `summary = null && isLoading = true` → `kind: 'loading'`, (b) bloc vide → `kind: 'empty'` avec `cta` correct, (c) bloc rempli → `kind: 'filled'` avec mapping correct, (d) `blockErrors[block]` non vide → `kind: 'error'` avec `retry` câblé. Vérifier le tri des `next_actions` (priorité haute en premier puis horizon croissant), le filtre attestations actives (`valid_until > now && revoked_at == null`), la limite max 3 candidatures / 3 rapports / 2 attestations / 3 étapes.

### Implémentation foundational

- [X] T008 [P] Implémenter `frontend/app/stores/dashboard.ts` (Pinia) — state `{ summary, generatedAt, blockErrors, loading, invalidatedBlocks }`, actions `fetchSummary`, `invalidate`, `reset`. Lock concurrentiel sur `loading`. Voir `data-model.md` pour la signature exacte. Doit faire passer T005.
- [X] T009 [P] Implémenter `frontend/app/lib/mapSummaryToCardViewModels.ts` — fonction pure typée `(summary, options) => DashboardCardViewModels`. Voir `contracts/frontend-components.md` § C-LIB-1 et `data-model.md` pour les ViewModels. Doit faire passer T007.
- [X] T010 Implémenter `frontend/app/composables/useDashboardSummary.ts` (dépend de T008 + T003) — voir `contracts/frontend-components.md` § C-CMP-1. Inclut : interval 60 s, Page Visibility API, abonnement EventBus via `EVENT_TO_BLOCK_MAP`, garde-fou anti-boucle (cf. C-EVT-3 : ignore les events `source: 'dashboard'` corrélés par id pendant 5 s). Doit faire passer T006.
- [X] T011 [P] Implémenter `frontend/app/composables/useDataExport.ts` — voir C-CMP-2. Dépendance : aucune autre tâche du foundational.
- [X] T012 [P] Créer `frontend/app/composables/__tests__/useDataExport.test.ts` avec scénarios : (a) appel réussi → un seul download déclenché avec nom `esg-mefali-export-YYYY-MM-DD.json` ; (b) double-clic rapide → un seul download ; (c) erreur 5xx → toast erreur sans crash ; (d) re-cliquable après 2 s post-download.
- [X] T013 [P] Créer `frontend/app/components/dashboard/CardSkeleton.vue` — props `lines`, `withChart` ; pulse désactivé via `useReducedMotion()`.
- [X] T014 [P] Créer `frontend/app/components/dashboard/CardErrorState.vue` — props `message`, event `retry`, `role="alert"`.
- [X] T015 [P] Créer `frontend/app/components/dashboard/EmptyCardCTA.vue` — props `cta: { label, href }`, message via slot ou prop.
- [X] T016 [P] Créer `frontend/app/components/dashboard/DashboardGrid.vue` — slot `default`, grille Tailwind responsive (1/2/3 colonnes).
- [X] T017 [P] Créer les tests composants `frontend/tests/components/dashboard/CardSkeleton.test.ts`, `CardErrorState.test.ts`, `EmptyCardCTA.test.ts` (cas affichage + a11y minimal : aria-busy, role="alert", focusable CTA).

**Checkpoint Foundational**: Store, fetch composable, adapter, composants génériques (skeleton/error/empty/grid) sont en place et testés. Les user stories peuvent démarrer en parallèle.

---

## Phase 3: User Story 1 — Vue 360° en 5 secondes (Priority: P1) 🎯 MVP

**Goal**: Afficher après login le bandeau d'accueil + six cartes principales peuplées avec les données de `summary`, navigables au clic, avec squelettes pendant le chargement.

**Independent Test**: Connecter un compte PME pleine de données, ouvrir `/dashboard`, observer (a) le bandeau (raison sociale + dernier diagnostic + bouton chat), (b) six cartes lisibles dans leur état final en < 1,5 s, (c) chaque clic carte → page détail.

### Tests pour User Story 1

- [X] T018 [P] [US1] Créer `frontend/tests/components/dashboard/WelcomeStrip.test.ts` — vérifie : salutation matin/soir selon `Date.now()`, raison sociale rendue, date relative correcte, mention "Aucun diagnostic encore" si `lastDiagnosticAt = null`, lien `/chat` présent.
- [X] T019 [P] [US1] Créer `frontend/tests/components/dashboard/CardScoring.test.ts` — états loading / empty (CTA "Lancer mon premier diagnostic ESG" → `/scoring`) / filled (KPI score global + radar 3 axes + badge VizSourcePin avec compte) / error.
- [X] T020 [P] [US1] Créer `frontend/tests/components/dashboard/CardCarbon.test.ts` — états loading/empty/filled (KPI tCO2e formaté via useMoneyFormat-like, mini line-chart 4 trimestres ; absence de `trend` → KPI seul affiché)/error.
- [X] T021 [P] [US1] Créer `frontend/tests/components/dashboard/CardCredit.test.ts` — gauge 0-100, badges éligibilité, warning orange si `coherenceWarning`, états vides/erreur.
- [X] T022 [P] [US1] Créer `frontend/tests/components/dashboard/CardCandidatures.test.ts` — compteurs en pills par statut, max 3 dernières, libellés FR via map de statuts, états vide/erreur.
- [X] T023 [P] [US1] Créer `frontend/tests/components/dashboard/CardRapports.test.ts` — 3 rapports + 2 attestations actives (filtrage validité), QR mini cliquable vers `/verify/{publicId}`, états vide/erreur.
- [ ] T024 [P] [US1] Créer `frontend/tests/e2e/dashboard-full-data.spec.ts` (Playwright) — scénario S1 du quickstart : compte plein → 6 cartes visibles, chaque clic carte → navigation vers la page détail attendue ; LCP mesuré < 1,5 s sur réseau simulé.

### Implémentation User Story 1

- [X] T025 [P] [US1] Implémenter `frontend/app/components/dashboard/WelcomeStrip.vue` — voir C-COMP-1. Lit `useEntrepriseProfile()` pour la raison sociale. Bouton `<NuxtLink to="/chat">` stylé `btn-primary`. Doit faire passer T018.
- [X] T026 [P] [US1] Implémenter `frontend/app/components/dashboard/CardScoring.vue` — voir C-COMP-3. Réutilise `<VizKPICard>`, `<VizRadarChart>` (mode compact), `<VizSourcePin>`. Doit faire passer T019.
- [X] T027 [P] [US1] Implémenter `frontend/app/components/dashboard/CardCarbon.vue` — `<VizKPICard>` + `<VizLineChart>` compact. Doit faire passer T020.
- [X] T028 [P] [US1] Implémenter `frontend/app/components/dashboard/CardCredit.vue` — `<VizGaugeChart>` + `<UiBadge>` par éligibilité + warning orange. Doit faire passer T021.
- [X] T029 [P] [US1] Implémenter `frontend/app/components/dashboard/CardCandidatures.vue` — pills compteurs + liste 3 dernières avec libellé FR. Doit faire passer T022.
- [X] T030 [P] [US1] Implémenter `frontend/app/components/dashboard/CardRapports.vue` — 2 sous-blocs (rapports / attestations) + QR mini via `qrcode-vue3` (lien `/verify/{publicId}`). Doit faire passer T023.
- [X] T031 [US1] Modifier `frontend/app/pages/dashboard.vue` — conserver la branche `EmptyStateLanding` si `completionPct < 50`, ajouter dans la branche `else` : `<WelcomeStrip>`, `<DashboardGrid>` contenant les 6 cartes (`CardScoring`, `CardCarbon`, `CardCredit`, `CardCandidatures`, `CardRapports`, `CardActionPlan` placeholder pour l'instant), branchement `useDashboardSummary()` pour fournir les VMs. Dépend de T010 + T025-T030. Doit faire passer T024.
- [X] T032 [US1] Implémenter le mapping de libellés statut candidature dans `frontend/app/lib/candidatureStatutLabels.ts` (consommé par CardCandidatures et l'adapter). Clés alimentées par T002.

**Checkpoint US1 (MVP)**: Compte plein → dashboard 6 cartes visibles, navigation OK, squelettes pendant fetch, LCP < 1,5 s. **C'est le MVP livrable.**

---

## Phase 4: User Story 2 — Cocher étape plan d'action (Priority: P1)

**Goal**: Permettre la complétion d'une étape de plan d'action directement depuis la carte du dashboard, avec persistance backend, refresh ciblé du bloc et émission EventBus.

**Independent Test**: Compte avec ≥ 4 étapes pending, cocher la 1re sur le dashboard → spinner mini < 1 s → étape disparaît, 4ᵉ apparaît ; reload page → persistance OK ; vérifier audit log.

### Tests pour User Story 2

- [ ] T033 [P] [US2] Créer `frontend/tests/components/dashboard/CardActionPlan.test.ts` — vérifie : 3 étapes max affichées, ordre tri (priorité haute d'abord puis horizon ASC), checkbox cliquable, optimistic update (case grisée + spinner), succès → callback `onComplete`, erreur 5xx → revert + toast (mock toast).
- [ ] T034 [P] [US2] Créer `frontend/app/composables/__tests__/useActionStepToggle.test.ts` (composable interne au CardActionPlan) — vérifie : appel `PATCH /me/action-plan/steps/{id}` avec body `{ status: 'done' }`, traque l'id en mémoire 5 s pour anti-boucle, émet event `action_step:completed` sur EventBus avec `source: 'dashboard'`, déclenche `store.invalidate('next_actions')` + `store.fetchSummary({ scope: ['next_actions'] })`.
- [ ] T035 [P] [US2] Créer `frontend/tests/e2e/dashboard-action-plan-toggle.spec.ts` — scénario S3 du quickstart.

### Implémentation User Story 2

- [ ] T036 [US2] Implémenter `frontend/app/composables/useActionStepToggle.ts` — appelle PATCH, gère optimistic update, émet event, traque l'id 5 s. Dépend de T010. Doit faire passer T034.
- [ ] T037 [US2] Implémenter `frontend/app/components/dashboard/CardActionPlan.vue` — voir C-COMP-3. Utilise `useActionStepToggle`, gère revert visuel sur erreur via `useToast`. Dépend de T036. Doit faire passer T033.
- [ ] T038 [US2] Câbler `CardActionPlan` dans `pages/dashboard.vue` (remplacer le placeholder posé en T031) — passer le VM `vms.actionPlan`. Doit faire passer T035.

**Checkpoint US2**: La 7ᵉ user story du flux quotidien (cocher une étape sans changer de page) fonctionne. Le mécanisme de mutation locale + invalidation + sync chat est éprouvé.

---

## Phase 5: User Story 3 — État vide intelligent (Priority: P1)

**Goal**: Garantir qu'aucune carte n'affiche "0" sec ou "—" sec sur compte vierge ; chaque carte propose un CTA contextuel d'invitation.

**Independent Test**: Créer un compte vierge (profil ≥ 50 % mais aucun calcul), ouvrir `/dashboard`, vérifier 6 cartes en mode CTA (cf. quickstart S2).

### Tests pour User Story 3

- [ ] T039 [P] [US3] Étendre `frontend/app/lib/__tests__/mapSummaryToCardViewModels.test.ts` (déjà créé en T007) — ajouter un test paramétré "compte vierge" qui valide pour chaque carte le label CTA et la href cible exacte (cf. data-model § règles de mapping).
- [ ] T040 [P] [US3] Créer `frontend/tests/e2e/dashboard-empty-account.spec.ts` — scénario S2 du quickstart, assertion stricte "aucune carte n'affiche le caractère '0' ou '—' isolé".

### Implémentation User Story 3

- [ ] T041 [US3] Vérifier que `mapSummaryToCardViewModels.ts` (T009) émet bien `kind: 'empty'` avec les bonnes hrefs par carte. Si T009 omettait des cas, compléter : Scoring → `/scoring`, Carbone → `/carbone`, Crédit → `/credit-score`, Candidatures → `/candidatures`, Rapports → `/rapports`, Plan d'action → `/plan-action`. Doit faire passer T039.
- [ ] T042 [US3] Vérifier `EmptyCardCTA.vue` (T015) : affiche message + CTA-bouton, ne rend jamais "0" ou "—". Ajuster styles si besoin pour différencier visuellement de l'état "filled" (icône d'invitation, fond plus clair). Doit faire passer T040.

**Checkpoint US3**: Primo-utilisateurs voient un dashboard accueillant et orientant. Aucune carte vide anxiogène.

---

## Phase 6: User Story 4 — Export de données (Priority: P1)

**Goal**: Permettre le téléchargement en un clic du JSON d'export du compte, avec anti double-clic et nom de fichier daté.

**Independent Test**: Cliquer "Exporter mes données", vérifier téléchargement `esg-mefali-export-AAAA-MM-JJ.json` valide ; second clic rapide → un seul fichier (cf. quickstart S4).

### Tests pour User Story 4

- [ ] T043 [P] [US4] Créer `frontend/tests/components/dashboard/ExportButton.test.ts` — vérifie disabled pendant download, toast succès/erreur, événement `exported` émis.
- [ ] T044 [P] [US4] Créer `frontend/tests/e2e/dashboard-export.spec.ts` — scénario S4 du quickstart (download + contenu JSON + cloisonnement compte).
- [ ] T045 [P] [US4] Créer `frontend/tests/e2e/dashboard-export-double-click.spec.ts` — vérifier qu'un double-clic rapide ne génère qu'un seul download (FR-021).

### Implémentation User Story 4

- [ ] T046 [P] [US4] Implémenter `frontend/app/components/dashboard/ExportButton.vue` — voir C-COMP-7. Utilise `useDataExport()` (T011). Doit faire passer T043.
- [ ] T047 [US4] Intégrer `<ExportButton>` dans `pages/dashboard.vue` — placement haut-droite (au-dessus de la grille ou dans le bandeau, à droite). Doit faire passer T044 et T045.

**Checkpoint US4**: Conformité RGPD art. 20 / UEMOA 20/2010 (portabilité) accessible en 1 clic depuis la page d'accueil.

---

## Phase 7: User Story 5 — Carte attestations vérifiables (Priority: P1)

**Goal**: Sur la carte "Rapports & attestations", afficher les attestations actives avec QR mini cliquable vers `/verify/{publicId}`.

**Independent Test**: Compte avec ≥ 2 attestations actives, vérifier les QR sur la carte et que le clic ouvre la page publique de vérification.

### Tests pour User Story 5

- [ ] T048 [P] [US5] Étendre `frontend/tests/components/dashboard/CardRapports.test.ts` (T023) — ajouter un cas "≥ 2 attestations actives" : QR rendus, lien `/verify/{publicId}` exact, attestation expirée filtrée, attestation révoquée jamais affichée.
- [ ] T049 [P] [US5] Créer un test unitaire `frontend/app/lib/__tests__/mapSummaryToCardViewModels.test.ts` (en complément T007) couvrant le filtre attestations actives (`valid_until > now && revoked_at == null`) avec faux Now.

### Implémentation User Story 5

- [ ] T050 [US5] S'assurer que `CardRapports.vue` (T030) intègre le sous-bloc attestations avec QR (via `qrcode-vue3` ajouté en T004). Lien `<NuxtLink to="/verify/{publicId}">`. Doit faire passer T048.
- [ ] T051 [US5] S'assurer que l'adapter `mapSummaryToCardViewModels.ts` (T009/T041) filtre correctement les attestations expirées et révoquées. Doit faire passer T049.

**Checkpoint US5**: Les preuves vérifiables (sortie monétisable de la plateforme) sont visibles dès l'accueil et accessibles en lecture publique.

---

## Phase 8: User Story 6 — Affichage source pour chaque donnée ESG (Priority: P2)

**Goal**: Sur les cartes ESG (scoring, carbone), un badge `<VizSourcePin>` cliquable ouvre la liste des sources documentaires.

**Independent Test**: Carte ESG avec scoring sur 4 documents → badge "(source)" → liste des 4 documents (titre + date).

### Tests pour User Story 6

- [ ] T052 [P] [US6] Étendre `frontend/tests/components/dashboard/CardScoring.test.ts` (T019) — vérifier présence de `<VizSourcePin :count="sourceCount">`, le clic ouvre un popover/modal listant les sources (mock).
- [ ] T053 [P] [US6] Idem pour `CardCarbon.test.ts` (T020).

### Implémentation User Story 6

- [ ] T054 [US6] Vérifier la présence de `<VizSourcePin>` dans `CardScoring.vue` (T026) et `CardCarbon.vue` (T027). Si l'API de `<VizSourcePin>` (livrée par F40) ne supporte pas l'ouverture d'une liste, ajouter un wrapper `<DashboardSourceList>` léger (composant) qui consomme l'event `pin:click`. Doit faire passer T052 et T053.

**Note** : la donnée `sources_by_indicator` ou équivalent doit être présente dans `summary.scores[*]` / `summary.carbon[*]`. Si F32 ne la fournit pas (à vérifier en T0), dégrader proprement (afficher juste le compte de sources sans liste détaillée et tracer un TODO post-MVP plutôt que d'inventer un endpoint backend).

**Checkpoint US6**: Le principe constitutionnel P1 (sourçage) est matérialisé visuellement sur les cartes principales.

---

## Phase 9: User Story 7 — Carte intermédiaires recommandés (Priority: P2)

**Goal**: Carte secondaire affichant une mini-Leaflet avec 3 pins de fonds/banques recommandés, lien vers `/matching`.

**Independent Test**: Compte avec profil complet + ≥ 1 projet → carte visible avec 3 pins ; sans projet → carte masquée.

### Tests pour User Story 7

- [ ] T055 [P] [US7] Créer `frontend/tests/components/dashboard/CardIntermediaires.test.ts` — vérifie : composant non monté si `hasProjet = false`, fetch lazy `/me/matching/recommendations?limit=3`, états loading/empty/filled/error, pins rendus dans `<VizLeafletMap>`, lien `/matching`.
- [ ] T056 [P] [US7] Créer `frontend/tests/e2e/dashboard-card-failure-isolation.spec.ts` — vérifie qu'une erreur 5xx sur `/me/matching/recommendations` n'affecte pas les 6 cartes principales (FR-020 / SC-010).

### Implémentation User Story 7

- [ ] T057 [P] [US7] Implémenter `frontend/app/components/dashboard/CardIntermediaires.vue` — voir C-COMP-3 spécifique. Utilise `<VizLeafletMap>` (F40) avec `disable-pan` et `height="160px"`. Lazy-fetch via `useFetch('/me/matching/recommendations?limit=3', { lazy: true, server: false })`. Doit faire passer T055.
- [ ] T058 [US7] Intégrer `<CardIntermediaires>` dans `pages/dashboard.vue` avec garde-fou `v-if="hasProjet"` (lit `useProjetsStore().count > 0` ou équivalent existant côté F43). Doit faire passer T056.

**Checkpoint US7**: La découverte d'opportunités de financement est amorcée depuis l'accueil sans surcharger le compte vierge.

---

## Phase 10: User Story 8 — Refresh automatique sync chat (Priority: P2)

**Goal**: Quand un calcul d'arrière-plan se termine (ex. scoring lancé depuis chat), le bloc concerné de la carte se met à jour sans intervention en < 90 s.

**Independent Test**: Dashboard ouvert, déclencher un nouveau scoring depuis le chat (autre onglet), vérifier que la carte ESG se met à jour seule en < 90 s (cf. quickstart S5).

### Tests pour User Story 8

- [ ] T059 [P] [US8] Étendre `frontend/app/composables/__tests__/useDashboardSummary.test.ts` (T006) avec un cas "polling déclenche fetch après 60 s simulés" (vitest fake timers).
- [ ] T060 [P] [US8] Créer `frontend/tests/e2e/dashboard-chat-sync.spec.ts` — scénario S5 cas A : émission d'event chat dans le même onglet → carte ESG mise à jour en < 2 s (mock backend pour renvoyer la nouvelle valeur).

### Implémentation User Story 8

- [ ] T061 [US8] Vérifier que `useDashboardSummary.ts` (T010) implémente bien : (a) interval 60 s + visibility API (déjà couvert T006), (b) abonnement aux 9 events de la table EVENT_TO_BLOCK_MAP (T003), (c) garde-fou anti-boucle 5 s. Si manquant, compléter. Doit faire passer T059 et T060.

**Checkpoint US8**: La cohérence chat ↔ dashboard est garantie en temps quasi-réel sur le même onglet, et en < 90 s entre onglets/sessions.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: A11y, perf, SSR squelettes, robustesse, qualité code, documentation.

- [ ] T062 [P] Audit a11y avec axe-core sur `/dashboard` plein et vide — corriger toutes violations AA (titres `<h2>` par carte, `aria-busy` sur cartes en chargement, `role="alert"` sur erreurs, focus visible sur tous les liens, contrast ratios).
- [ ] T063 [P] Optimiser SSR : valider que les squelettes sont rendus côté serveur (Lighthouse mobile sur `/dashboard` avec compte plein → LCP < 1,5 s). Si KO, activer `useFetch` côté serveur pour le premier fetch summary (la session middleware permet l'auth côté serveur). Cf. research R9.
- [ ] T064 [P] Vérifier performance scroll mobile : ouvrir devtools mobile (375 px), scroller la grille empilée, profiler → 60 fps maintenu (SC-008). Optimiser si nécessaire (lazy-load mini-charts hors viewport via `IntersectionObserver`).
- [ ] T065 [P] Anti-overflow : vérifier sur viewport 320×568 (le plus petit raisonnable) qu'aucune carte ne déborde horizontalement ; ajuster `min-w-0` / troncature où nécessaire.
- [ ] T066 [P] Compléter `frontend/app/locales/fr.ts` si des clés ont été oubliées pendant l'implémentation des cartes — relancer les tests composants pour confirmer.
- [ ] T067 [P] Vérifier que `useDashboardStore.reset()` est appelé sur logout (compléter `frontend/app/stores/auth.ts` si l'instruction n'y figure pas) — cloisonnement strict entre comptes, FR-019.
- [ ] T068 Lancer `pnpm lint` et corriger toute violation introduite ; lancer `pnpm vitest run` et `pnpm playwright test` complets — tout doit passer (couverture ≥ 80 % sur le code F44 nouveau).
- [ ] T069 [P] Mettre à jour `docs_et_brouillons/features/00-INDEX.md` : passer F44 de `draft` à `ready` (ou statut équivalent du dépôt) avec lien vers `specs/044-dashboard-pme-ui/`.
- [ ] T070 Tester manuellement les 7 scénarios du `quickstart.md` en env local et reporter dans une checklist `specs/044-dashboard-pme-ui/quickstart-validation.md` (créer le fichier).

**Checkpoint Polish**: Feature livrable, conforme constitution (P1, P2, P5, P8 vérifiés), conforme spec quality checklist.

---

## Dependencies

```
Setup (T001–T004)
    ↓
Foundational (T005–T017) — store + composable summary + adapter + composants génériques
    ↓
┌────────────────────────────────────────────────────────────────┐
│  US1 (T018–T032) ── MVP                                         │
│  US2 (T033–T038) ── dépend de T010 (useDashboardSummary)         │
│  US3 (T039–T042) ── dépend de T009 + T015                        │
│  US4 (T043–T047) ── dépend de T011 (useDataExport)               │
│  US5 (T048–T051) ── dépend de T030 (CardRapports)                │
│  US6 (T052–T054) ── dépend de T026 + T027                        │
│  US7 (T055–T058) ── dépend de T031                               │
│  US8 (T059–T061) ── dépend de T010                               │
└────────────────────────────────────────────────────────────────┘
    ↓
Polish (T062–T070)
```

**Story independence** : US1 livre l'ossature (page + 5 cartes statiques + une 6ᵉ placeholder). US2-US8 enrichissent indépendamment et peuvent être livrées dans un ordre ajustable selon les priorités produit. **MVP minimal expédiable = Setup + Foundational + US1 + US3** (vue 360° + état vide intelligent), avec US2/US4/US5 en première itération suivante.

## Parallel Execution Examples

**Foundational** (T005–T017) — après T001–T004 :
- Lancer en parallèle : T005, T006, T007 (tests TDD), T013, T014, T015, T016 (composants génériques), T017 (tests composants génériques) — tous fichiers distincts.
- Puis T008, T009, T011 en parallèle (3 implémentations indépendantes), suivis de T010 (dépend de T008).

**US1** (T018–T032) :
- Tests T018–T024 tous parallélisables.
- Implémentations T025–T030 toutes parallélisables (composants distincts) — démarrer dès que T010 est prêt.
- T031 séquentiel (dépend de T025–T030).
- T032 parallèle à T031.

**US2 / US4 / US7 / US8** : peuvent être travaillés simultanément par 4 développeurs après US1 (chaque story touche un fichier composant différent).

## Implementation Strategy

1. **Sprint 1 (MVP)** — Setup + Foundational + US1 + US3 (T001–T032 + T039–T042). Livrable : dashboard 6 cartes navigables + état vide propre. Permet une démo utilisateur complète sur le coup d'œil 5 secondes et l'onboarding nouveau compte.
2. **Sprint 2 — Interactions et conformité** — US2 (cocher étape) + US4 (export RGPD) + US5 (attestations QR). Livrable : page d'accueil "vivante" et conforme portabilité.
3. **Sprint 3 — Sourçage et découverte** — US6 (badge sources) + US7 (carte intermédiaires) + US8 (sync auto chat). Livrable : conformité P1 visible + engagement matching.
4. **Sprint 4 — Polish** — A11y, perf SSR, mobile, lint, doc.

## Validation finale

Avant de marquer F44 comme `done`, vérifier :

- [ ] Tous les SC du `spec.md` sont mesurés et atteints (cf. tableau quickstart § "Validation des success criteria").
- [ ] La spec quality checklist (`checklists/requirements.md`) reste 100 % verte.
- [ ] Les gates Constitution Check (`plan.md`) restent tous ✅ (re-check post-implémentation).
- [ ] Couverture ≥ 80 % sur le code F44 nouveau (`pnpm vitest run --coverage`).
- [ ] Aucun warning Lighthouse mobile critique sur `/dashboard`.
- [ ] PR review par un second développeur.
