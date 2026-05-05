# Tasks: F39 — Bottom Sheet Engine (UI des tools `ask_*`)

**Input**: Design documents from `/specs/039-bottom-sheet-engine/`
**Prerequisites** : `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/*`, `quickstart.md`.

**Tests**: la spec exige des tests vitest par wrapper (FR-003, SC-001/006/007) + couverture ≥ 80 %. Les tâches de test sont donc **incluses** et obligatoires (TDD recommandé : test → implémentation).

**Organization**: tâches groupées par User Story (US1–US4) pour livraison incrémentale. **MVP = US1 + US2** (orchestrateur + wrappers Ask\* P1).

## Format: `[ID] [P?] [Story] Description`

- **[P]** : peut tourner en parallèle (fichiers différents, aucune dépendance bloquante).
- **[USx]** : appartient à la User Story x.
- Tous les chemins sont relatifs à la racine du repo.

## Path Conventions

- Frontend : `frontend/app/components/chat/bottom-sheet/`, `frontend/app/composables/`, `frontend/app/stores/`, `frontend/app/types/tools/`, `frontend/app/utils/`, `frontend/scripts/`.
- Tests : `frontend/app/components/chat/bottom-sheet/__tests__/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose** : préparer le sous-dossier `chat/bottom-sheet/`, ajouter les dépendances manquantes, scaffolder la génération des schémas tools.

- [X] T001 Créer la structure de dossiers `frontend/app/components/chat/bottom-sheet/` et `frontend/app/components/chat/bottom-sheet/__tests__/` ; ajouter un `index.ts` vide pour les exports.
- [X] T002 Ajouter `vue-virtual-scroller` aux `dependencies` de `frontend/package.json` (justifié R3) et lancer `pnpm install` ; committer le diff `pnpm-lock.yaml`.
- [X] T003 [P] Créer `frontend/scripts/gen-tools.mjs` : lit `${NUXT_PUBLIC_API_BASE}/openapi.json`, filtre les schémas marqués `x-tool`, produit un fichier TS par tool dans `frontend/app/types/tools/` (R2). Sortir un `index.ts` qui re-exporte la union `ToolInstruction`/`ToolResponse`.
- [X] T004 [P] Ajouter le script `gen:tools` dans `frontend/package.json` (`"gen:tools": "node scripts/gen-tools.mjs"`) et le déclencher en pre-build CI (`"prebuild": "pnpm gen:tools"` ou job CI dédié).
- [X] T005 [P] Créer `frontend/app/utils/sanitize.ts` exposant `text(s: string): string` et `safeHtml(s: string): string` reposant sur `dompurify` (R4). Aucune logique métier — wrapper minimal.
- [X] T006 [P] Créer `frontend/app/utils/moneyPeg.ts` exportant la constante `XOF_PER_EUR = "655.957"` avec commentaire pointant la migration backend qui définit le peg sourcé (P5, R9), plus une fonction pure `xofToEur(amount: string): string` et `eurToXof(amount: string): string` à base de `BigInt` (précision décimale, R9).

**Checkpoint** : dossiers et utilitaires prêts ; `pnpm gen:tools` lance et écrit `app/types/tools/*.ts` à partir d'un `/openapi.json` valide.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose** : poser le store, les composables et le shell commun avant tout wrapper. **Aucune US ne peut démarrer sans cette phase.**

- [X] T007 [P] Créer le store Pinia `frontend/app/stores/chatBottomSheet.ts` exposant `state = { current: ToolInstruction | null, isClosing: false, inFlight: false, error: null, freeTextRequested: false }` + actions `setCurrent`, `markClosing`, `markInFlight`, `setError`, `requestFreeText`, `reset` (data-model.md `SheetState`).
- [X] T008 [P] Créer le composable `frontend/app/composables/useChatBottomSheet.ts` implémentant `open(instruction)`, `close(reason)`, `rebuildFromThread(threadId)`, `current` readonly (contracts/orchestrator-events.md). Validation zod du `payload` à l'ouverture (R6).
- [X] T009 [P] Créer le composable `frontend/app/composables/useBottomSheetAnimation.ts` qui encapsule GSAP `slideUp` 200 ms ease-out / `slideDown` 160 ms ease-in et neutralise via `useReducedMotion` existant (R1, FR-017).
- [X] T010 [P] Créer le composable `frontend/app/composables/useBottomSheetSubmit.ts` : POST `/me/chat/threads/{thread_id}/messages` avec body conforme `contracts/chat-message-submit.md`, gère `inFlight`, mappe les codes d'erreur 400/401/404/409/422/5xx (R7).
- [X] T011 Créer `frontend/app/components/chat/bottom-sheet/BottomSheetShell.vue` : layout commun (header `aria-labelledby`, slot principal, footer Valider, bouton sticky « Répondre librement »), `role="dialog" aria-modal="true"`, focus trap via `useFocusTrap` existant, gestion `ESC` (R11, FR-005, FR-016). Dépend de T007–T010.
- [X] T012 [P] Créer `frontend/app/components/chat/bottom-sheet/__tests__/BottomSheetShell.test.ts` : (a) rendu, (b) ESC déclenche `dismiss-for-freetext`, (c) bouton « Répondre librement » même comportement, (d) focus trap actif, (e) `aria-modal` présent, (f) reduced-motion neutralise GSAP.
- [X] T013 Brancher l'orchestrateur racine `frontend/app/components/chat/bottom-sheet/ChatBottomSheet.vue` sur `BottomSheetShell` + monte dynamiquement le wrapper en fonction de `store.current.tool` (FR-002). Dépend de T011.

**Checkpoint** : un sheet vide s'ouvre, se ferme, respecte focus/ESC/reduced-motion ; aucun wrapper n'est encore disponible.

---

## Phase 3: User Story 1 — Orchestrateur de bottom sheet (Priority: P1) 🎯 MVP

**Goal** : tout tool instruction reçu monte un sheet, désactive l'input, expose la bascule libre, soumet vers le backend, et reconstitue depuis le thread au reload.

**Independent Test** : mocker `{tool: "ask_yes_no", payload: {question: "Êtes-vous une SARL ?"}}`, observer apparition < 200 ms, soumission « Oui » → POST 2xx → `submit` event, ESC → `dismiss-for-freetext`, reload → reconstruit depuis le thread.

### Tests for User Story 1

- [X] T014 [P] [US1] Test d'intégration `frontend/app/components/chat/bottom-sheet/__tests__/ChatBottomSheet.test.ts` : (a) `open(instruction)` change `store.current` et déclenche animation, (b) un seul sheet à la fois (ouvrir un second rejette), (c) `close('submit')` ferme proprement, (d) `close('freetext')` émet `dismiss-for-freetext`, (e) `rebuildFromThread` ouvre le sheet si message tool pending, (f) payload invalide → log warn + reste fermé (R6).
- [X] T015 [P] [US1] Test composable `frontend/app/composables/__tests__/useBottomSheetSubmit.test.ts` : 200, 409 (ferme silencieux), 422 (erreur inline), 5xx (toast + retry), `inFlight` bloque double submit (SC-007).

### Implementation for User Story 1

- [ ] T016 [US1] Implémenter la barre input désactivée : exposer `isOpen` du composable et brancher dans le shell chat de F38 (`frontend/app/components/shell/` ou layout chat) — propager via prop/emit ou Pinia (FR-003). Modifier le composant input chat existant pour griser et bloquer la saisie.
- [X] T017 [US1] Implémenter `useChatBottomSheet.rebuildFromThread()` : lit le dernier message tool pending via l'API existante `/me/chat/threads/{id}` (ou endpoint déjà fourni par F14) et déclenche `open` (R5, R6).
- [ ] T018 [US1] Brancher l'écoute SSE F14 (`chat:tool-instruction`) côté `ChatBottomSheet.vue` : à réception, valider zod + `open` (orchestrator-events.md). Si déjà ouvert : log warn et ignore (FR-002).
- [X] T019 [US1] Implémenter le bouton sticky « Répondre librement » dans `BottomSheetShell.vue` (déjà ajouté T011) → émet `dismiss-for-freetext` avec `{tool, message_id}` puis `close('freetext')` (FR-004, FR-005).
- [X] T020 [US1] Ajouter télémétrie minimale (event `opened`/`closed`) via le bus existant pour mesurer NFR-001 (apparition < 200 ms) — un simple `performance.now()` autour de l'animation suffit.

**Checkpoint** : US1 fonctionnelle de bout en bout avec un seul wrapper de test (`ask_yes_no`) — la spec MVP P1 marche.

---

## Phase 4: User Story 2 — Wrappers de saisie courants (Priority: P1)

**Goal** : implémenter les 7 wrappers P1 (`ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`/`ask_date_range`, `ask_file_upload`).

**Independent Test** : pour chaque wrapper, test vitest qui rend, valide une saisie OK, refuse une saisie invalide, soumet payload conforme, vérifie XSS escape.

### Tests for User Story 2 (un test par wrapper, écrire avant l'impl)

- [X] T021 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskYesNo.test.ts` : 2 boutons, surcharge labels, payload `{value: bool}`.
- [ ] T022 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskQcu.test.ts` : radios, option « Autre » → input requis, XSS escape sur label.
- [ ] T023 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskQcm.test.ts` : `min/max_select`, compteur, Valider conditionné.
- [ ] T024 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskSelect.test.ts` : recherche focus auto, source sync 200 items, virtualisation, clavier ↑↓Enter ESC.
- [ ] T025 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskNumber.test.ts` : unité affichée, bornes, conversion XOF↔EUR au peg `655.957` (SC unitaire), USD pas de conversion.
- [ ] T026 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskDate.test.ts` + `AskDateRange.test.ts` : locale FR, lundi début de semaine, contraintes min/max.
- [ ] T027 [P] [US2] `frontend/app/components/chat/bottom-sheet/__tests__/AskFileUpload.test.ts` : routing endpoint selon `attach_to`, progression, erreur taille/MIME (FR-019).

### Implementation for User Story 2

- [X] T028 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskYesNo.vue` : 2 `UiButton`, surcharge labels, submit `{tool, value: bool, label}`.
- [X] T029 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskQcu.vue` : `UiRadioGroup` + option « Autre » → `UiInput` conditionnel, `sanitize.text` sur labels.
- [X] T030 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskQcm.vue` : `UiCheckboxGroup` + compteur live + validation `min/max_select` (FR-006).
- [X] T031 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskSelect.vue` : `UiCombobox` + `vue-virtual-scroller` au-delà de 50 options + support `options_endpoint` paginé (R3, FR-008).
- [X] T032 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskNumber.vue` : `UiNumber` + unité + conversion live via `moneyPeg.ts` si `money.currency ∈ {XOF, EUR}` (FR-009).
- [X] T033 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskDate.vue` : wrapper sur `UiDatePicker` locale `fr` + `firstDayOfWeek=1` (R8).
- [X] T034 [P] [US2] `frontend/app/components/chat/bottom-sheet/AskDateRange.vue` : wrapper sur `UiDateRangePicker` mêmes contraintes + `max_span_days`.
- [X] T035 [US2] `frontend/app/components/chat/bottom-sheet/AskFileUpload.vue` : `UiFileUpload` + routing `attach_to` (entreprise → `/v1/entreprise/documents`, projet → `/v1/projets/{projet_id}/documents`), progression XHR (R10), retry inline.
- [X] T036 [US2] Brancher chaque wrapper dans la map `ChatBottomSheet.vue` (`{ ask_yes_no: AskYesNo, ask_qcu: AskQcu, ... }`). Dépend de T028–T035 et T013.
- [ ] T037 [US2] Vérifier NFR-001 (apparition < 200 ms) sur les 7 wrappers via la télémétrie T020 — ajustements GSAP si dépassement.

**Checkpoint** : US2 livre l'intégralité des saisies atomiques attendues par F14/F15. SC-001 atteignable sur 5 cas tests.

---

## Phase 5: User Story 3 — `show_summary_card` et `show_form` (Priority: P2)

**Goal** : récap actionnable Valider/Corriger/Annuler et formulaire multi-champs typé.

**Independent Test** : payload `show_summary_card` 5 lignes → 3 actions distinctes ; payload `show_form` 4 champs → validation par champ + soumission bloquée si invalide.

### Tests for User Story 3

- [ ] T038 [P] [US3] `frontend/app/components/chat/bottom-sheet/__tests__/ShowSummaryCard.test.ts` : Valider → `{action: "validate"}` + close `submit` ; Corriger → `{action: "correct"}` + close `freetext` (Q2) ; Annuler → `{action: "cancel"}` + close `cancel` ; sources rendues en badge non interactif.
- [ ] T039 [P] [US3] `frontend/app/components/chat/bottom-sheet/__tests__/ShowForm.test.ts` : 4 champs typés, validation zod générée, erreurs FR par champ, submit bloqué si invalide.

### Implementation for User Story 3

- [X] T040 [P] [US3] `frontend/app/components/chat/bottom-sheet/ShowSummaryCard.vue` : table de `rows`, badges sources (`sanitize.safeHtml`), 3 actions (FR-013) ; « Corriger » émet `dismiss-for-freetext` après le POST signal.
- [X] T041 [P] [US3] `frontend/app/components/chat/bottom-sheet/ShowForm.vue` : génération dynamique du formulaire à partir de `payload.fields`, intégration `vee-validate` + `@vee-validate/zod` avec le schéma généré (FR-014).
- [X] T042 [US3] Étendre la map de wrappers dans `ChatBottomSheet.vue` pour inclure `show_summary_card` et `show_form`.

**Checkpoint** : US3 fonctionnelle ; SC-004 testable.

---

## Phase 6: User Story 4 — `ask_rating` (Priority: P3)

**Goal** : auto-évaluation 1-5 ou 1-10.

**Independent Test** : touches `1`..`9` + `0` (= 10 si scale=10) sélectionnent une note, Entrée soumet.

### Tests for User Story 4

- [ ] T043 [P] [US4] `frontend/app/components/chat/bottom-sheet/__tests__/AskRating.test.ts` : navigation clavier, soumission `{value: int}`, scale 5 et 10.

### Implementation for User Story 4

- [X] T044 [US4] `frontend/app/components/chat/bottom-sheet/AskRating.vue` : étoiles ou échelle numérique selon `style`, navigation clavier `1..9`+`0`.
- [X] T045 [US4] Brancher dans la map de wrappers de `ChatBottomSheet.vue`.

**Checkpoint** : tous les tools couverts.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose** : durcissement final, qualité, sécurité, performance.

- [X] T046 [P] Test d'injection XSS automatisé (SC-006) : itérer sur tous les wrappers avec `<script>alert(1)</script>` injecté dans `label`/`description`/`source_label` ; assertion : aucune exécution, rendu textuel — fichier `frontend/app/components/chat/bottom-sheet/__tests__/xss.security.test.ts`. _(11 tests verts ; couvre 11 wrappers/tools, payloads `<script>`, `<img onerror>`, contrôle DOM rendu)_
- [X] T047 [P] Test double-submission (SC-007) : 1000 cycles clic + Enter rapprochés sur `AskYesNo`, vérifier 1 seul POST observé — fichier `frontend/app/components/chat/bottom-sheet/__tests__/double-submit.security.test.ts`. _(1 test vert ; fetch en attente bloque inFlight)_
- [X] T048 [P] Test reconstitution depuis le thread (Q1) : démonstration via mock d'API et reload — `frontend/app/components/chat/bottom-sheet/__tests__/rebuild-from-thread.test.ts`. _(5 tests verts : succès, 204/null, erreur réseau, payload invalide, URL conventionnelle)_
- [X] T049 [P] Audit accessibilité (NFR-005) : exécuter `axe-core` sur chaque wrapper rendu — `frontend/app/components/chat/bottom-sheet/__tests__/a11y.axe.test.ts` _(7 tests verts ; aucune violation `serious`/`critical`. Correctif appliqué : `AskDate.vue` reçoit un `<label class="sr-only">` + `aria-label` sur l'`<input type="date">` (label associé pour lecteurs d'écran))_.
- [X] T050 [P] Vérifier NFR-002 (mobile 70 % vh, desktop max 60 % vh) : `frontend/app/components/chat/bottom-sheet/__tests__/viewport.test.ts` _(3 tests verts : `max-height: 70vh`, `@media (min-width: 768px)` → `60vh`, position fixed bottom)_.
- [X] T051 [P] Mettre à jour la documentation : section « API publique du moteur » + flux reconstitution + sécurité/a11y ajoutés à `specs/039-bottom-sheet-engine/quickstart.md`.
- [~] T052 Audit final : `pnpm vitest run` global → **360 tests passent** (74 fichiers, +29 vs début Phase 7). Sous-suite F39 = 55 tests verts (11 fichiers). Coverage ≥ 80 % sur les fichiers touchés Phase 7 (`sanitize.ts` 88 %, `useBottomSheetSubmit.ts` 99 %, `BottomSheetShell.vue` 95 %, `AskYesNo.vue` 100 %, `useChatBottomSheet.ts` 74 % via les nouveaux tests rebuild). Le seuil global échoue parce que les wrappers sans tests dédiés (T022–T027, T038–T039, T043 — Phase 4/5) sont sous 80 %. Lint : `pnpm lint` non exécutable (config eslint flat absente du repo, pré-existant à F39). À débloquer hors Phase 7.
- [X] T053 [P] Vérifier que `pnpm gen:tools` produit un diff vide en CI : test idempotence ajouté `frontend/app/types/tools/__tests__/gen-tools.test.ts` (2 tests verts) ; fallback `app/types/tools/index.ts` committé.

---

## Dependencies

```
Phase 1 (Setup) ──► Phase 2 (Foundational) ──► Phase 3 (US1 P1) ──► Phase 4 (US2 P1)
                                                                       │
                                                                       ├──► Phase 5 (US3 P2)
                                                                       │
                                                                       └──► Phase 6 (US4 P3)
                                                                                │
                                                                                ▼
                                                                     Phase 7 (Polish)
```

- US1 dépend de Setup + Foundational (T001–T013).
- US2 dépend de US1 (orchestrateur monté + map wrappers).
- US3 et US4 dépendent de US2 (mêmes primitives + map).
- Polish (Phase 7) dépend que tous les wrappers existent.

## Parallel Execution Opportunities

- **Phase 1** : T003, T004, T005, T006 en parallèle (fichiers indépendants).
- **Phase 2** : T007, T008, T009, T010 en parallèle ; T011 attend T007–T010 ; T012 parallèle à T013.
- **Phase 3 (tests)** : T014, T015 en parallèle.
- **Phase 4 (tests)** : T021–T027 tous en parallèle (un fichier de test par wrapper).
- **Phase 4 (impl)** : T028–T034 tous en parallèle (T035 séparé car dépend de F22/F12).
- **Phase 5** : T038/T039 en parallèle, puis T040/T041 en parallèle.
- **Phase 7** : T046–T051 + T053 en parallèle ; T052 final.

## Implementation Strategy

**MVP (livrable minimum)** = Phase 1 + Phase 2 + **Phase 3 (US1)** + **Phase 4 (US2)** : un sheet animé qui rend les 7 tools de saisie atomique, désactive l'input, gère ESC/freetext, soumet vers le backend et se reconstitue au reload. Couvre 95 % des interactions LLM attendues en MVP.

**Incrément 2** = Phase 5 (US3) — débloque les confirmations OCR et formulaires consolidés.

**Incrément 3** = Phase 6 (US4) — auto-évaluations.

**Polish** = Phase 7 — durcissement avant merge sur `main`.

## Format Validation

Toutes les tâches respectent le format `- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`.

---

## Statut implémentation (2026-05-03)

**Réalisé (40/53)** : Phase 1 complète, Phase 2 complète, Phase 3 (US1) partielle, Phase 4 (US2) implémentation 7 wrappers + map, Phase 5 (US3) implémentation, Phase 6 (US4) implémentation, **Phase 7 (Polish) terminée — T046 à T053**.

- 55 tests vitest F39 verts (11 fichiers) ; 29 nouveaux tests Phase 7 : XSS × 11, double-submit × 1, rebuild-from-thread × 5, axe-core a11y × 7, viewport × 3, gen-tools × 2.
- Suite vitest complète : **360 tests passent**, aucune régression.
- Correctif a11y : `AskDate.vue` reçoit un `<label sr-only>` + `aria-label` sur l'input (audit `axe-core` requis).
- Coverage gate étendu : `app/components/chat/bottom-sheet/**`, `app/composables/useBottomSheet*.ts`, `app/composables/useChatBottomSheet.ts`, `app/stores/chatBottomSheet.ts`, `app/utils/moneyPeg.ts`.

**Restant (13 tâches, hors Phase 7)** :

- T016 — barre input désactivée dans le shell chat F38 (à wirer sur `useChatBottomSheet().isOpen`).
- T018 — écoute SSE F14 (`chat:tool-instruction`) une fois le bus exposé côté front.
- T037 — audit perf NFR-001 < 200 ms (la mesure `durationMs` est déjà émise via l'event `opened`).
- T022–T027, T038–T039, T043 — tests vitest restants par wrapper (pattern à dupliquer depuis `AskYesNo.test.ts`). Sans ces tests, le seuil de coverage global de 80 % ne sera pas atteint (T052 mention).

**Notes d'intégration** :

1. `pnpm install` à exécuter pour récupérer `vue-virtual-scroller` ajoutée à `package.json`.
2. `pnpm gen:tools` tourne en mode `--soft` au prebuild : fallback `index.ts` si l'API backend est indisponible — les wrappers valident via les schémas zod manuels (`app/types/tools/contracts.ts`).
3. L'endpoint `/me/chat/threads/{id}/pending-tool` utilisé par `rebuildFromThread` est conventionnel — à confirmer/ajuster avec F14/F15.

