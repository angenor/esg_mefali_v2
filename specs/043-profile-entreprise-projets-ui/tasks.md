---

description: "Task list — F43 Profil Entreprise & Projets UI"
---

# Tasks: Profil Entreprise & Projets — UI (F43)

**Input**: Design documents from `/specs/043-profile-entreprise-projets-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED for this feature (NFR-003 : couverture ≥ 80 % ; constitution exige TDD pour les composables, services et composants critiques). Les tests sont écrits AVANT l'implémentation, doivent ÉCHOUER, puis verts.

**Organization**: Tâches groupées par user story pour livraison incrémentale et test indépendant.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : peut s'exécuter en parallèle (fichiers différents, aucune dépendance bloquante).
- **[Story]** : story concernée (US1…US6) ; absent pour Setup, Foundational, Polish.

## Path Conventions

- Frontend Nuxt 4 : `frontend/app/...` et `frontend/tests/...`.
- Backend FastAPI : `backend/app/...` (lecture seule pour F43, aucune modif applicative).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dépendances et structure de fichiers nouvelles.

- [X] T001 Ajouter la dépendance `decimal.js` dans `frontend/package.json` (block `dependencies`) et exécuter `pnpm install` à la racine `frontend/`
- [X] T002 [P] Créer le squelette de répertoire `frontend/app/components/profil/` avec un `index.ts` (re-export futur) dans `frontend/app/components/profil/index.ts`
- [X] T003 [P] Créer le fichier `frontend/app/data/countries-iso2.ts` avec la liste ISO 3166-1 alpha-2 ordonnée (UEMOA en tête, puis CEDEAO, puis alphabétique) — source à citer en commentaire (UN/LOCODE)
- [X] T004 [P] Étendre `frontend/app/locales/fr.ts` avec les namespaces `profil.entreprise.*` et `profil.projets.*` selon `contracts/frontend-components.md` § 5
- [X] T005 [P] Créer le squelette `frontend/tests/components/profil/` (dossier vide + `.gitkeep`) et `frontend/tests/e2e/profil-*` (placeholders)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: composables et utilitaires partagés par toutes les stories. Bloquent toute story.

⚠️ **CRITICAL** : aucune story ne démarre tant que Phase 2 n'est pas verte.

- [X] T006 [P] Écrire les tests vitest de `useDecimal` dans `frontend/app/composables/__tests__/useDecimal.test.ts` (couvre add, multiply, format XOF/EUR/USD, convertXofEur peg `655.957`, sérialisation Decimal → string)
- [X] T007 Implémenter `frontend/app/composables/useDecimal.ts` (wrapping `decimal.js`, constante `PEG_XOF_EUR = '655.957'`, helpers `format`, `convertXofEur`) ; T006 doit passer
- [X] T008 [P] Écrire les tests de `ConflictDialog.vue` (props/emits, focus initial sur « Garder ma valeur », role alertdialog) dans `frontend/tests/components/profil/ConflictDialog.test.ts`
- [X] T009 Implémenter `frontend/app/components/profil/ConflictDialog.vue` (3 choix, focus trap, gsap fade-in 150 ms) ; T008 doit passer
- [X] T010 [P] Étendre le store Pinia entreprise pour porter `data`, `version`, `saving`, `errors`, `conflict`, `pendingChanges` (rétro-compatible avec `completionPct`) dans `frontend/app/stores/entreprise.ts`
- [X] T011 [P] Créer le store `frontend/app/stores/projets.ts` (state, actions `loadList`, `loadOne`, `create`, `patchField`, `softDelete`, gestion `version`) selon `data-model.md` § 2.2
- [X] T012 [P] Tests vitest des stores `entreprise` et `projets` dans `frontend/app/stores/__tests__/entreprise.test.ts` et `frontend/app/stores/__tests__/projets.test.ts` (mock `$fetch`, vérifie 200/409/422)
- [X] T013 [P] Auditer `frontend/app/pages/projets/` ; si placeholder, supprimer le répertoire et nettoyer toute référence dans `frontend/app/components/shell/TheSidebar.vue` et `TheBottomNav.vue` (pointer vers `/profil/projets`)

**Checkpoint**: utilitaires Decimal, conflit dialog, stores et nav sont prêts → US1–US6 peuvent démarrer.

---

## Phase 3: User Story 1 — Profil entreprise vue/édition autosave (Priority: P1) 🎯 MVP

**Goal** : permettre à une PME de consulter et compléter son profil entreprise par sections, avec autosave silencieux et indicateur de complétion.

**Independent Test** : se connecter, ouvrir `/profil/entreprise`, modifier une raison sociale, attendre 800 ms → toast « Enregistré » ; recharger → la valeur persiste ; la barre de complétion progresse.

### Tests for User Story 1 ⚠️

- [X] T014 [P] [US1] Tests vitest de `useEntrepriseProfile` (debounce 800 ms, AbortController, gestion 200/409/422/5xx, retry exponentiel, `flushNow`) dans `frontend/app/composables/__tests__/useEntrepriseProfile.test.ts`
- [X] T015 [P] [US1] Tests de `SectionCard.vue` (toggle lecture/édition, émission `update:field`) dans `frontend/tests/components/profil/SectionCard.test.ts`
- [X] T016 [P] [US1] Tests de `EntrepriseHeader.vue` (binding pourcentage + tooltip champs manquants) dans `frontend/tests/components/profil/EntrepriseHeader.test.ts`
- [X] T017 [P] [US1] Test E2E Playwright `frontend/tests/e2e/profil-entreprise-autosave.spec.ts` : login fixture → modifie raison sociale → reload → valeur persiste → toast affiché
- [X] T018 [P] [US1] Test E2E Playwright `frontend/tests/e2e/profil-entreprise-completeness.spec.ts` : remplir 5 champs → vérifier passage 30 % → 80 %

### Implementation for User Story 1

- [X] T019 [US1] Implémenter `frontend/app/composables/useEntrepriseProfile.ts` (debounce 800 ms, AbortController par section, mapping erreurs, retry exponentiel 250→4000 ms) ; T014 doit passer
- [X] T020 [P] [US1] Implémenter `frontend/app/components/profil/EntrepriseHeader.vue` (`UiProgress` + tooltip champs manquants + bouton « Historique »)
- [X] T021 [P] [US1] Implémenter `frontend/app/components/profil/SectionCard.vue` (mode lecture/édition, slot fields, émission `update:field`, focus auto sur premier champ en édition)
- [X] T022 [P] [US1] Implémenter `frontend/app/components/profil/SectionEditor.vue` (orchestre les `UiFormField` selon descripteurs de section, gère `aria-describedby` pour les erreurs)
- [X] T023 [US1] Créer la page `frontend/app/pages/profil/entreprise.vue` (5 SectionCard pour Identité, Taille, Localisation, Gouvernance, Pratiques ; SSR via `useAsyncData(() => useEntrepriseStore().loadAll())`)
- [X] T024 [US1] Brancher la bannière persistante « Modifications non sauvegardées » via `UiToast` sticky quand `useEntrepriseProfile` détecte une 5xx persistante
- [X] T025 [US1] Vérifier l'accessibilité clavier (tab order, focus trap, lecteurs d'écran) sur `pages/profil/entreprise.vue` et corriger les écarts (NFR WCAG 2.1 AA)

**Checkpoint** : US1 fonctionne et passe T017–T018.

---

## Phase 4: User Story 2 — Money typé + multi-pays (Priority: P1)

**Goal** : `MoneyField` Decimal/devise + `CountryMultiSelect` ISO2 cluster UEMOA, intégrés à la page entreprise.

**Independent Test** : saisir CA `50000000` XOF → conversion `≈ 76 224,91 €` ; sélectionner BJ + CI dans zones d'opération → persistées en ISO2 ; saisir un pays libre → refus.

### Tests for User Story 2 ⚠️

- [X] T026 [P] [US2] Tests de `MoneyField.vue` (Decimal in/out, devise XOF/EUR/USD, conversion live XOF↔EUR, USD sans conversion live, jamais de Number) dans `frontend/tests/components/profil/MoneyField.test.ts`
- [X] T027 [P] [US2] Tests de `CountryMultiSelect.vue` (ordre UEMOA en tête, recherche par nom, refus pays hors liste) dans `frontend/tests/components/profil/CountryMultiSelect.test.ts`

### Implementation for User Story 2

- [X] T028 [P] [US2] Implémenter `frontend/app/components/profil/MoneyField.vue` (UiNumber + UiSelect devise + affichage parallèle XOF/EUR via `useDecimal`)
- [X] T029 [P] [US2] Implémenter `frontend/app/components/profil/CountryMultiSelect.vue` (consomme `data/countries-iso2.ts`, UiMultiSelect)
- [X] T030 [US2] Câbler `MoneyField` dans la section Taille (champ `taille_ca`) et `CountryMultiSelect` dans la section Localisation (champs `localisation_siege_pays_iso2` et `zones_operation_pays_iso2`) au sein de `frontend/app/pages/profil/entreprise.vue`

**Checkpoint** : US2 fonctionne ; saisie monétaire et géographique strictement typées.

---

## Phase 5: User Story 3 — Liste projets + wizard création (Priority: P1)

**Goal** : `/profil/projets` liste les projets, propose empty state et wizard 4 étapes pour créer un projet, page détail consultable.

**Independent Test** : compte sans projet → empty state ; cliquer « Nouveau projet » → 4 étapes complétables en ≤ 3 min ; carte créée immédiatement ; clic sur carte → page détail affichant Identité, Description, Localisation, Budget, Documents.

### Tests for User Story 3 ⚠️

- [X] T031 [P] [US3] Tests de `ProjetCard.vue` (rendu nom/statut/secteur/date/score badge couleur, sous-badge candidature) dans `frontend/tests/components/profil/ProjetCard.test.ts`
- [X] T032 [P] [US3] Tests de `ProjetEmptyState.vue` (affichage CTA, émission `create`) dans `frontend/tests/components/profil/ProjetEmptyState.test.ts`
- [X] T033 [P] [US3] Tests de `useProjetWizard` (validation Zod par step, `canAdvance`, `submit` payload conforme `ProjetCreate`) dans `frontend/app/composables/__tests__/useProjetWizard.test.ts`
- [X] T034 [P] [US3] Tests de `ProjetWizard.vue` (4 steps, focus trap, transitions gsap, erreurs par step) dans `frontend/tests/components/profil/ProjetWizard.test.ts`
- [X] T035 [P] [US3] Tests de `useProjet` (autosave, conflict 409, soft delete) dans `frontend/app/composables/__tests__/useProjet.test.ts`
- [X] T036 [P] [US3] Test E2E `frontend/tests/e2e/profil-projets-wizard.spec.ts` : empty → wizard → submit → carte présente
- [X] T037 [P] [US3] Test E2E `frontend/tests/e2e/profil-projets-detail.spec.ts` : clic carte → page détail charge les sections

### Implementation for User Story 3

- [X] T038 [US3] Implémenter `frontend/app/composables/useProjetWizard.ts` (state Zod par step, mapping vers `ProjetCreate`)
- [X] T039 [US3] Implémenter `frontend/app/composables/useProjet.ts` (debounced patch, version, conflict, fetch détail)
- [X] T040 [P] [US3] Implémenter `frontend/app/components/profil/ProjetCard.vue` (badge statut localisé, badge score couleur selon paliers vert/orange/rouge)
- [X] T041 [P] [US3] Implémenter `frontend/app/components/profil/ProjetEmptyState.vue` (UiEmptyState + illustration `assets/images/empty-projets.svg` placeholder à fournir)
- [X] T042 [P] [US3] Implémenter `frontend/app/components/profil/ProjetWizardStep1.vue` (nom + description, validation Zod min 3 / max 120 nom)
- [X] T043 [P] [US3] Implémenter `frontend/app/components/profil/ProjetWizardStep2.vue` (secteur + type_impact via UiSelect)
- [X] T044 [P] [US3] Implémenter `frontend/app/components/profil/ProjetWizardStep3.vue` (CountryMultiSelect mono-pays + région libre obligatoire + lat/lng optionnels conditionnels)
- [X] T045 [P] [US3] Implémenter `frontend/app/components/profil/ProjetWizardStep4.vue` (MoneyField budget + UiNumber horizon mois)
- [X] T046 [US3] Implémenter `frontend/app/components/profil/ProjetWizard.vue` (orchestre les 4 steps, gsap transition, ESC = confirm-close)
- [X] T047 [US3] Mettre à jour `frontend/app/pages/profil/projets/index.vue` (liste cards, empty state, bouton « Nouveau projet » → ProjetWizard)
- [X] T048 [US3] Créer `frontend/app/pages/profil/projets/[id].vue` (5 sections : Identité, Description, Localisation, Budget, Documents — réutilise `SectionCard`)

**Checkpoint** : US3 fonctionne ; création + détail validés.

---

## Phase 6: User Story 4 — Sync chat ↔ profil avec conflit (Priority: P1)

**Goal** : mutation chat propagée à l'UI ouverte en < 2 s avec flash ; conflit chat ↔ user → ConflictDialog 3 choix.

**Independent Test** : ouvrir profil dans un onglet, déclencher mutation via chat dans un autre → flash visible < 2 s ; reproduire en éditant localement → dialogue avec 3 options.

### Tests for User Story 4 ⚠️

- [X] T049 [P] [US4] Tests d'intégration `useEntrepriseProfile` × `useChatEventBus` (event entity_updated → re-fetch + flash) dans `frontend/app/composables/__tests__/useEntrepriseProfile.eventbus.test.ts`
- [X] T050 [P] [US4] Tests d'intégration équivalents pour `useProjet` dans `frontend/app/composables/__tests__/useProjet.eventbus.test.ts`
- [X] T051 [P] [US4] Test E2E `frontend/tests/e2e/profil-conflict-chat-sync.spec.ts` : émission programmatique d'event sur le bus → flash UI ; édition locale + event sur même champ → dialogue 3 choix

### Implementation for User Story 4

- [X] T052 [US4] Étendre `useEntrepriseProfile.ts` pour souscrire à `useChatEventBus` (handler `onEntityUpdated`, détection chevauchement champ, flash via `useToast`)
- [X] T053 [US4] Étendre `useProjet.ts` symétriquement (filtrage par `entity_id`)
- [X] T054 [US4] Brancher `ConflictDialog` dans `pages/profil/entreprise.vue` et `pages/profil/projets/[id].vue` via téléport racine ; câbler `resolveConflict('mine'|'theirs'|'cancel')`
- [X] T055 [US4] Vérifier que la mutation locale ne déclenche pas de self-echo (filtrage `origin_request_id` documenté en `contracts/chat-eventbus-sync.md` § 4)

**Checkpoint** : sync bidirectionnelle vérifiée ; aucun écrasement silencieux.

---

## Phase 7: User Story 5 — Documents projet + soft delete (Priority: P1)

**Goal** : téléverser des documents projet (PDF/JPG/PNG/DOCX/XLSX, ≤ 25 Mo) avec aperçu ; supprimer un projet de manière réversible avec confirmation.

**Independent Test** : ouvrir un projet → téléverser un PDF → aperçu présent ; rejeter `.txt` ; supprimer projet → confirmation → carte disparaît de la liste active.

### Tests for User Story 5 ⚠️

- [X] T056 [P] [US5] Tests de `ProjetDocuments.vue` (upload OK, MIME refusé, taille refusée, miniature image) dans `frontend/tests/components/profil/ProjetDocuments.test.ts`
- [X] T057 [P] [US5] Test E2E `frontend/tests/e2e/profil-projets-delete-restore.spec.ts` : suppression + confirmation + disparition de la liste active

### Implementation for User Story 5

- [X] T058 [US5] Implémenter `frontend/app/components/profil/ProjetDocuments.vue` (UiFileUpload, validation MIME/size cliente, miniatures images / icônes pour PDF/DOCX/XLSX, suppression item)
- [X] T059 [US5] Câbler `ProjetDocuments` dans `frontend/app/pages/profil/projets/[id].vue` (section Documents)
- [X] T060 [US5] Ajouter le bouton « Supprimer » avec UiModal de confirmation dans `frontend/app/pages/profil/projets/[id].vue` ; appel `useProjetsStore().softDelete(id)` puis redirect `/profil/projets`

**Checkpoint** : US5 fonctionne ; documents et soft delete couverts.

---

## Phase 8: User Story 6 — Historique audit (Priority: P2)

**Goal** : drawer latéral listant les modifications passées d'une section (audit log).

**Independent Test** : modifier la raison sociale → cliquer « Historique » sur la section Identité → drawer affiche l'entrée avec auteur/ts/source/old/new.

### Tests for User Story 6 ⚠️

- [X] T061 [P] [US6] Tests de `HistoryDrawer.vue` (rendu liste, pagination cursor, badge source) dans `frontend/tests/components/profil/HistoryDrawer.test.ts`
- [X] T062 [P] [US6] Test E2E `frontend/tests/e2e/profil-history-drawer.spec.ts` : modif → drawer ouvert → entrée présente

### Implementation for User Story 6

- [X] T063 [US6] Implémenter `frontend/app/components/profil/HistoryDrawer.vue` (consomme `GET /me/audit-log?entity=...&entity_id=...`, pagination cursor, badge source manual/llm/import/admin, gsap slide-in 200 ms)
- [X] T064 [US6] Câbler le bouton « Historique » dans `EntrepriseHeader.vue` et au-dessus de chaque `SectionCard.vue` ; brancher l'ouverture/fermeture du drawer dans les pages profil
- [X] T065 [US6] Ajouter un bouton « Historique » sur la page détail projet (`pages/profil/projets/[id].vue`) avec `entity='projet'` et `entityId=route.params.id`

**Checkpoint** : US6 fonctionne ; traçabilité visible côté UI.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T066 [P] Vérifier la couverture vitest (`pnpm vitest run --coverage`) ≥ 80 % sur `app/components/profil/**` et les composables ajoutés ; ajuster les tests faibles
- [ ] T067 [P] Audit Lighthouse mobile sur `/profil/entreprise` et `/profil/projets` ; ajuster les images / lazy-load pour viser LCP < 1 s (SC-001)
- [ ] T068 [P] Audit a11y (axe-core via Playwright) sur les 3 pages profil ; corriger les violations critiques et sérieuses (NFR WCAG 2.1 AA)
- [ ] T069 [P] Vérifier `prefers-reduced-motion` sur ProjetWizard, ConflictDialog, HistoryDrawer ; remplacer gsap par instant-snap quand actif
- [ ] T070 Mettre à jour `frontend/README.md` (section « Profil entreprise & projets ») et `docs/CODEMAPS/frontend.md` si présent
- [ ] T071 Exécuter le quickstart `specs/043-profile-entreprise-projets-ui/quickstart.md` de bout en bout en local et noter les écarts
- [ ] T072 Lancer `make lint` et `make test` à la racine ; corriger toute régression introduite côté frontend

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** : aucune dépendance.
- **Phase 2 (Foundational)** : dépend de Phase 1 ; bloque toutes les stories.
- **Phase 3 (US1)** : MVP — démarre dès Phase 2 verte.
- **Phase 4 (US2)** : indépendante d'US1 mais s'intègre à la même page → coordonner T030 avec T023.
- **Phase 5 (US3)** : indépendante d'US1/US2.
- **Phase 6 (US4)** : dépend d'US1 et US3 (pour avoir des écrans à synchroniser) ; ou MOCK les composables sans pages si développé en parallèle.
- **Phase 7 (US5)** : dépend d'US3 (page détail projet).
- **Phase 8 (US6)** : dépend d'US1 (boutons Historique sur sections entreprise) et marginalement US3.
- **Phase 9 (Polish)** : dépend de US1 + US3 minimum (MVP).

### Within Each Story

- Tests d'abord (RED), implémentation (GREEN), refactor.
- Composables avant pages.
- Composants avant pages qui les consomment.

### Parallel Opportunities

- T002–T005 (Setup) en parallèle.
- T008, T010, T011, T012, T013 (Foundational [P]) en parallèle.
- Au sein d'US3, T040–T045 peuvent s'écrire en parallèle (composants distincts).
- US3, US5, US6 peuvent être développées par 3 personnes différentes après US1 + Phase 2.

---

## Parallel Example: User Story 1

```bash
# Tests d'US1 lancés en parallèle :
Task: "Tests vitest useEntrepriseProfile in frontend/app/composables/__tests__/useEntrepriseProfile.test.ts"
Task: "Tests SectionCard.vue in frontend/tests/components/profil/SectionCard.test.ts"
Task: "Tests EntrepriseHeader.vue in frontend/tests/components/profil/EntrepriseHeader.test.ts"
Task: "E2E autosave in frontend/tests/e2e/profil-entreprise-autosave.spec.ts"
Task: "E2E completeness in frontend/tests/e2e/profil-entreprise-completeness.spec.ts"

# Composants UI d'US1 en parallèle après T019 :
Task: "Implémenter EntrepriseHeader.vue"
Task: "Implémenter SectionCard.vue"
Task: "Implémenter SectionEditor.vue"
```

---

## Implementation Strategy

### MVP First (US1 seulement)

1. Phase 1 + 2 (Setup + Foundational).
2. Phase 3 (US1) → arrêt + validation manuelle (quickstart) → démo.
3. Permet déjà à une PME d'ouvrir et compléter son profil entreprise.

### Incremental Delivery

1. Setup + Foundational → fondations prêtes.
2. US1 → démo profil entreprise éditable.
3. US2 → enrichit US1 (Money + pays).
4. US3 → projets gérables.
5. US4 → sync chat ↔ profil.
6. US5 → documents + soft delete.
7. US6 → historique audit (P2).
8. Polish + quickstart → release.

### Parallel Team Strategy

- Dev A : US1 + US2 (page entreprise complète).
- Dev B : US3 + US5 (projets + documents).
- Dev C : US4 (sync) + US6 (historique).

---

## Notes

- Toutes les tâches mentionnent un chemin de fichier précis — un agent peut les exécuter sans contexte additionnel.
- `[P]` = fichiers différents, pas de dépendance bloquante.
- Tests écrits AVANT (RED → GREEN → REFACTOR) ; chaque US doit être verte avant de passer à la suivante.
- Aucun changement backend planifié dans cette feature ; toute découverte de défaut côté backend remonte une issue F11/F12 distincte (R7 : endpoint FX USD post-MVP).
- Commit après chaque tâche ou groupe logique cohérent.
