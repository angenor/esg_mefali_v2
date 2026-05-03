# Tasks — F41 Chat Conversational Layer

**Feature** : `specs/041-chat-conversational-layer/`
**Branche** : `041-chat-conversational-layer`

> **Convention** : `[P]` = parallélisable (fichiers indépendants, aucune dépendance ouverte). `[USx]` = appartient à la story Sx du `spec.md`. Tous les chemins sont absolus relativement au repo root. La feature est purement frontend ; aucun fichier backend n'est modifié.

---

## Phase 1 — Setup

- [X] T001 Vérifier le statut de F12/F18 backend (endpoints `/me/chat/threads*`, `/me/events`, `/me/chat/threads/{id}/memory`) avec un `curl` smoke depuis `make backend` ; documenter le statut dans `specs/041-chat-conversational-layer/quickstart.md` si écart constaté.
- [X] T002 [P] Ajouter les dépendances frontend dans `frontend/package.json` : `markdown-it@^14.1.0`, `mitt@^3.0.1`, `driver.js@^1.3.1` (vérifier non-doublon avec celles déjà installées) puis `pnpm install` depuis `frontend/`.
- [X] T003 [P] Ajouter les types TypeScript : `pnpm add -D @types/markdown-it` dans `frontend/`.
- [X] T004 [P] Créer la structure de dossiers : `frontend/app/components/chat/`, `frontend/app/pages/chat/`, `frontend/tests/chat/` (mkdir + .gitkeep si vide).

## Phase 2 — Foundational (bloque toutes les stories)

- [X] T005 [P] Créer les types partagés du module chat dans `frontend/app/types/chat.ts` (interfaces `ChatThreadSummary`, `ChatMessage`, `MessagePayload` union, `StreamingState`, `ChatError`, `EventBusEvent`, `MemorySnapshot`, frames SSE) — référence `specs/041-chat-conversational-layer/data-model.md`.
- [X] T006 [P] Implémenter `frontend/app/composables/useMarkdownStream.ts` : parse `markdown-it` (CommonMark + GFM tables) + DOMPurify allow-list stricte (cf. `research.md` R2 + R10). Exporter `render(content: string): string`.
- [X] T007 [P] Implémenter `frontend/app/composables/useChatEventBus.ts` (mitt) : `on`, `emit`, filtre anti-loop pour `source === 'llm'` côté listeners qui re-déclencheraient l'orchestrateur ; bridge avec store Pinia (R3).
- [X] T008 [P] Implémenter `frontend/app/composables/useChatStream.ts` : `fetch` + `ReadableStream` + `TextDecoderStream` ; parse frames SSE (`event:`, `data:`, `id:`, ligne vide) ; dedup `Set<sequence_id>` ; backoff reconnect 1/2/4/8 s (max 5) ; expose `start(url, body)` et `abort()` (R1, R6).
- [X] T009 [P] Implémenter `frontend/app/composables/useChatScroll.ts` : `ResizeObserver` + détection user-scrolled-up ; `scrollToBottom()` avec respect de `prefers-reduced-motion`.
- [X] T010 Créer le store `frontend/app/stores/chat.ts` (`useChatStore`) — state : `threads`, `currentThreadId`, `messagesByThread`, `streaming`, `forceFreetextNext`, `errors`. Actions : `loadThreads`, `selectThread`, `newThread`, `sendMessage`, `retry`, `cancelStream`, `clearForceFreetext`. Dépend de T005, T008. Référence `data-model.md` §1.4.
- [X] T011 [P] Créer le plugin `frontend/app/plugins/chat-event-source.client.ts` qui ouvre un `EventSource` sur `/me/events` et publie chaque frame dans `useChatEventBus()` avec mapping des `event_*` → `EventBusEvent` (R3, F18).
- [ ] T012 [P] Créer une page d'archive `frontend/app/pages/dev/chat-fixtures.vue` (dev-only, à `dev/`) avec scénarios de test : message simple, message avec viz, message en erreur, message avec tool_invoke. Sert de fixture manuelle pour les stories suivantes.

## Phase 3 — User Story 1 (P1) Conversation textuelle libre avec streaming

**Goal** : Envoyer un message texte, voir la réponse LLM se construire token-by-token dans une bulle gauche.
**Independent test** : Ouvrir `/chat`, taper « Bonjour », `Cmd+Enter`, vérifier bulle droite + premier token < 500 ms + finalisation < 5 s + curseur clignotant + scroll-pinning.

- [X] T013 [P] [US1] Implémenter `frontend/app/components/chat/MessageMarkdown.vue` (sanitisation via T006, curseur clignotant si `streaming === true`).
- [X] T014 [P] [US1] Implémenter `frontend/app/components/chat/MessageBubbleUser.vue` (bulle droite, fond `brand-50`, timestamp hover).
- [X] T015 [US1] Implémenter `frontend/app/components/chat/MessageBubbleAssistant.vue` (slot dynamique selon `payload.kind`, P10 : aucune primitive interactive ; émet `cite-click`, `retry`). Dépend de T013.
- [X] T016 [P] [US1] Implémenter `frontend/app/components/chat/TypingIndicator.vue` (3 dots gsap, neutralisé si `prefers-reduced-motion`).
- [X] T017 [US1] Implémenter `frontend/app/components/chat/ChatHistory.vue` : itère `messages`, gère scroll-pinning via T009, branche événement `cite-click`/`retry`, intercale `TypingIndicator` quand `streaming != null` et premier token absent. Dépend de T014, T015, T016.
- [X] T018 [P] [US1] Implémenter `frontend/app/components/chat/MessageInput.vue` : `<UiTextarea>` (F37) autoresize 1–6 lignes, bouton envoi, attache (event seulement, upload réel hors-scope), `Cmd/Ctrl+Enter`, masqué quand bottom sheet ouvert (lit `useChatBottomSheet().isOpen`).
- [X] T019 [US1] Implémenter `frontend/app/components/chat/ChatLayout.vue` (deux colonnes, sidebar masquée < 768 px en drawer, slots `header`/`history`/`input`).
- [X] T020 [US1] Implémenter `frontend/app/pages/chat/index.vue` : redirige vers `/chat/{lastThreadId}` ou crée un thread vide via `useChatStore().newThread()`.
- [X] T021 [US1] Implémenter `frontend/app/pages/chat/[thread_id].vue` : compose `ChatLayout` avec `ChatHistory` + `MessageInput`, charge messages au mount via `selectThread`, branche `submit` → `sendMessage`, gère `payload.kind === 'viz'` côté assistant en délégant aux composants F40 dans T015.
- [X] T022 [US1] Câbler le scroll-pinning safe-area mobile dans `frontend/app/pages/chat/[thread_id].vue` : `100dvh`, `padding-bottom: env(safe-area-inset-bottom)` sur l'input, `ResizeObserver` côté `ChatHistory` (R7).
- [X] T023 [P] [US1] Tester `frontend/tests/chat/MessageMarkdown.spec.ts` : payloads XSS (`<script>`, `onerror`, `javascript:`) tous neutralisés ; Markdown partiel (`**bold` non clos) ne crashe pas ; cas streaming reproduit.
- [X] T024 [P] [US1] Tester `frontend/tests/chat/useChatStream.spec.ts` : SSE simulé (frames token séquentielles), dedup `sequence_id`, reconnect backoff exponentiel après échec, abort propre.
- [X] T025 [P] [US1] Tester `frontend/tests/chat/ChatHistory.spec.ts` : scroll-pinning reste suspendu après scroll-up utilisateur, reprend après retour bas.

**Checkpoint** : MVP minimal viable atteint. La PME peut converser en texte avec le LLM.

## Phase 4 — User Story 2 (P1) Interaction structurée via bottom sheet

**Goal** : Quand le LLM invoque un tool nécessitant un contrôle dédié, l'input se masque et un bottom sheet F39 s'ouvre. Bouton « Répondre librement » revient au texte avec re-classification.
**Independent test** : Provoquer un `event: tool_invoke` (kind `ask_qcu`), vérifier ouverture sheet < 300 ms + masquage input ; cliquer « Répondre librement », vérifier retour input et flag freetext propagé.

- [X] T026 [US2] Étendre `useChatStream` (T008) pour dispatcher l'event `tool_invoke` vers `useChatBottomSheet().open(tool, args)` et marquer `streaming.state = 'awaiting_sheet'` dans `useChatStore`. Modifier `frontend/app/composables/useChatStream.ts` + `frontend/app/stores/chat.ts`.
- [X] T027 [US2] Ajouter dans `useChatBottomSheet` (existant `frontend/app/composables/useChatBottomSheet.ts`) la transition de fermeture : sur validation du sheet, le store reçoit le résultat et le repousse comme `MessagePayload.kind = 'sheet_result'` via `sendMessage`. Vérifier que la sheet existante respecte cette API ; sinon adapter `frontend/app/stores/chatBottomSheet.ts`.
- [X] T028 [US2] Ajouter dans `MessageInput.vue` (T018) la lecture réactive `useChatBottomSheet().isOpen` qui masque l'input via `v-if`.
- [X] T029 [US2] Ajouter le bouton « Répondre librement » dans le header du bottom sheet (composant existant F39, `frontend/app/components/chat/bottom-sheet/...`) : ferme la sheet, vide la sélection, positionne `useChatStore().forceFreetextNext = true` ; assurer que le prochain `sendMessage` injecte `context_json: { force_freetext: true }`.
- [X] T030 [P] [US2] Tester `frontend/tests/chat/useChatBottomSheetIntegration.spec.ts` : `tool_invoke` ouvre la sheet ; bouton freetext → `forceFreetextNext === true` ; envoi suivant porte `context_json.force_freetext = true`.

**Checkpoint** : Saisies structurées opérationnelles, conformité P10 vérifiée.

## Phase 5 — User Story 3 (P1) Synchronisation bidirectionnelle profil ↔ chat

**Goal** : Mutation LLM propagée aux pages profil ouvertes en < 1 s, sans boucle EventBus → LLM.
**Independent test** : Profil ouvert dans onglet A, chat dans onglet B ; conversation déclenche mutation `entreprise.effectif=12` ; profil reflète sans rechargement.

- [X] T031 [US3] Étendre `useChatStream` (T008) pour dispatcher l'event `mutation` (frame backend) vers `useChatEventBus().emit('entity_updated', {...source: 'llm'})`. Modifier `frontend/app/composables/useChatStream.ts`.
- [X] T032 [P] [US3] Côté pages profil existantes (`frontend/app/pages/profil.vue` et autres consommateurs P8), ajouter un listener `useChatEventBus().on('entity_updated', refreshIfMatches)`. Audit + edit minimal des pages concernées (ne pas refactorer l'existant).
- [X] T033 [US3] Dans `MessageBubbleAssistant.vue` (T015), afficher un indicateur sobre (icône `arrow-path` + tooltip « Profil mis à jour ») quand un message contient une mutation propagée — sans déclencher de re-LLM.
- [X] T034 [P] [US3] Tester `frontend/tests/chat/useChatEventBus.spec.ts` : `emit({source: 'llm'})` n'invoque PAS un listener marqué « LLM-trigger » ; les listeners UI passifs reçoivent bien l'event.

**Checkpoint** : P8 (sync bidirectionnel) effectivement vérifié.

## Phase 6 — User Story 4 (P1) Gestion des conversations passées

**Goal** : Sidebar listant les threads, sélection ré-hydrate l'historique, « Nouveau chat » crée un fil vide.

- [X] T035 [P] [US4] Implémenter `frontend/app/components/chat/ThreadList.vue` (tri DESC `lastMessageAt`, virtualisation `vue-virtual-scroller` si > 50, `select` + `new-chat` events).
- [X] T036 [US4] Implémenter `frontend/app/components/chat/ChatHeader.vue` (titre thread, bouton « Nouveau chat », slot pour `MemoryBadge`).
- [X] T037 [US4] Brancher `ThreadList` + `ChatHeader` dans `ChatLayout.vue` (T019) ; câbler `select` → `useRouter().push('/chat/' + id)`, `new-chat` → `useChatStore().newThread()` puis push.
- [X] T038 [P] [US4] Test `frontend/tests/chat/ThreadList.spec.ts` : tri, virtualisation au-delà de 50, événements emit.

**Checkpoint** : Persistance et navigation des threads opérationnelles.

## Phase 7 — User Story 5 (P1) Visualisations dans les bulles LLM

**Goal** : `payload.kind === 'viz'` rend le composant F40 approprié, largeur élargie, accessibilité.

- [X] T039 [US5] Compléter `MessageBubbleAssistant.vue` (T015) avec un switch sur `payload.tool` qui mappe vers `<VizKPICard>`, `<VizLineChart>`, `<VizAreaChart>`, `<VizBarChart>`, `<VizStackedBarChart>`, `<VizRadarChart>`, `<VizGaugeChart>`, `<VizPieChart>`, `<VizDonutChart>`, `<VizMermaidRenderer>`, `<VizDataTable>`, `<VizLeafletMap>` (composants F40). Largeur élargie via classe CSS dédiée.
- [X] T040 [US5] Garantir `<ClientOnly>` autour de `VizMermaidRenderer` et `VizLeafletMap` dans la bulle (SSR safety).
- [X] T041 [P] [US5] Test `frontend/tests/chat/MessageBubbleAssistantViz.spec.ts` : pour chaque `tool`, le bon composant est rendu ; payload invalide → fallback `MessageError`.

**Checkpoint** : Visualisations inline opérationnelles.

## Phase 8 — User Story 6 (P1) Onboarding du premier chat

- [X] T042 [P] [US6] Implémenter `frontend/app/composables/useChatOnboarding.ts` : lecture du flag `account_settings.onboarding_chat_seen` (endpoint F11 si dispo, sinon fallback `localStorage` clé `chat.onboarding.seen.{accountId}`) ; `maybeStart()` lance driver.js avec 4 étapes (input texte, attache, sidebar, exemple bottom sheet) ; `markSeen()` persiste (R5).
- [X] T043 [US6] Brancher `useChatOnboarding().maybeStart()` dans `frontend/app/pages/chat/[thread_id].vue` au `onMounted` (uniquement si flag absent).
- [X] T044 [P] [US6] Test `frontend/tests/chat/useChatOnboarding.spec.ts` : flag absent → tour démarre ; flag présent → tour ne démarre pas ; `markSeen` persiste correctement.

**Checkpoint** : Premier accès guidé.

## Phase 9 — User Story 7 (P1) Erreurs LLM et reprise

- [X] T045 [P] [US7] Implémenter `frontend/app/components/chat/MessageError.vue` (libellé FR sobre selon `code`, bouton « Réessayer » émettant `retry`).
- [X] T046 [US7] Étendre `useChatStream` (T008) pour transformer chaque frame `event: error` (et chaque échec post-2-retries du backoff) en `ChatError` ajouté au store via `errors[messageId]`. Modifier `frontend/app/composables/useChatStream.ts` + `frontend/app/stores/chat.ts`.
- [X] T047 [US7] Implémenter `useChatStore().retry(messageId)` : récupère `retryOf` dans `errors`, supprime la bulle erreur, relance `sendMessage` avec le contenu original.
- [X] T048 [US7] Brancher `MessageBubbleAssistant.vue` (T015) pour afficher `MessageError` quand `payload.kind === 'error'` ; câbler `retry` → `useChatStore().retry(messageId)`.
- [X] T049 [P] [US7] Test `frontend/tests/chat/useChatErrorRetry.spec.ts` : timeout simulé → bulle erreur ; click retry → resend avec contenu identique ; succès remplace la bulle erreur par la réponse.

**Checkpoint** : Robustesse erreurs vérifiée.

## Phase 10 — User Story 8 (P2) Suggestions / quick replies

- [X] T050 [P] [US8] Implémenter `frontend/app/components/chat/QuickReplies.vue` (≤ 3 chips, `pick` event).
- [X] T051 [US8] Brancher dans `ChatHistory.vue` (T017) : afficher `QuickReplies` sous la dernière bulle assistant **finalisée** uniquement quand input vide ; suggestions extraites du `payload.suggestions?` ou liste statique [`Continuer`, `Reformuler`, `Donne un exemple`].
- [X] T052 [P] [US8] Test `frontend/tests/chat/QuickReplies.spec.ts` : visibilité conditionnelle ; click chip → `sendMessage` avec contenu chip.

## Phase 11 — User Story 9 (P2) Indicateur de mémoire

- [X] T053 [P] [US9] Implémenter `frontend/app/components/chat/MemoryBadge.vue` (lecture taille via `MemorySnapshot`, click ouvre modale F37 listant `entries`).
- [X] T054 [US9] Ajouter `useChatStore().fetchMemorySnapshot(threadId)` (`GET /me/chat/threads/{id}/memory`) avec cache simple ; mettre à jour à chaque event SSE `memory_updated` (provient de T011).
- [X] T055 [US9] Intégrer `MemoryBadge` dans `ChatHeader.vue` (T036) ; ouvrir la modale via `useToast` ou modal F37.
- [X] T056 [P] [US9] Test `frontend/tests/chat/MemoryBadge.spec.ts` : taille reflétée ; click → modal ouverte avec entrées.

## Phase 12 — Polish & Cross-cutting

- [ ] T057 [P] Audit a11y `axe-core` sur `/chat` : 0 violations sérieuses, contraste ≥ 4.5:1, focus management cohérent (sidebar drawer mobile, bottom sheet retour focus). Documenter dans `specs/041-chat-conversational-layer/quickstart.md` §smoke checklist.
- [ ] T058 [P] Audit performance : Lighthouse `/chat`, vérifier LCP < 2 s, INP < 200 ms ; profiler streaming sur 200 tokens.
- [X] T059 [P] Tests sécurité : suite XSS dans `frontend/tests/chat/security.spec.ts` couvrant les 10 payloads OWASP ; vérifier qu'aucun n'exécute de code.
- [X] T060 [P] Mettre à jour `frontend/app/types/chat.ts` exports + JSDoc public ; vérifier `pnpm typecheck` vert.
- [X] T061 [P] Mettre à jour `frontend/README.md` ou doc dédiée `frontend/docs/chat.md` : architecture haut/bas, EventBus, machine d'états streaming.
- [ ] T062 Vérifier coverage `pnpm vitest run --coverage tests/chat` ≥ 80 % (gate projet).
- [ ] T063 Smoke manuel complet selon `specs/041-chat-conversational-layer/quickstart.md` §1–9 ; cocher chaque item dans la PR.
- [X] T064 [P] Vérifier qu'aucun fichier backend n'a été modifié (`git diff --stat origin/main -- backend/`) — F41 doit rester pure-frontend.

---

## Dependency graph

```
Setup (T001-T004)
        │
        ▼
Foundational (T005-T012)
        │
        ▼
US1 (T013-T025) ──── checkpoint MVP
        │
        ├──▶ US2 (T026-T030)        [bottom sheet]
        ├──▶ US3 (T031-T034)        [event bus sync]
        ├──▶ US4 (T035-T038)        [thread sidebar]
        ├──▶ US5 (T039-T041)        [viz embed]
        ├──▶ US6 (T042-T044)        [onboarding]
        └──▶ US7 (T045-T049)        [error + retry]
                    │
                    ▼
        US8 (T050-T052)  US9 (T053-T056)   [P2]
                    │
                    ▼
            Polish (T057-T064)
```

US2 à US7 sont **indépendantes** de US1 d'un point de vue contractuel mais consomment toutes le store T010 et `MessageBubbleAssistant` T015 — d'où la barrière US1 avant les autres P1.

## Parallel execution examples

- **Phase 1 — Setup** : T002, T003, T004 lancés en parallèle (pas T001 qui est un prérequis de smoke).
- **Phase 2 — Foundational** : T005–T009 + T011–T012 tous parallélisables ; T010 dépend de T005 + T008.
- **Phase 3 — US1** : T013, T014, T016, T018, T023, T024, T025 parallélisables ; T015 dépend de T013 ; T017 dépend de T014/T015/T016 ; T019 dépend de T017/T018 ; T020/T021 séquentiels après T019 ; T022 après T021.
- **P2 stories (US8, US9)** : entièrement parallélisables une fois US4 (`ChatHeader`) et US5 (`MessageBubbleAssistant` complet) terminées.

## Implementation strategy — MVP first

1. **MVP cible** = US1 seule (T001 → T025). À la fin de cette tranche, la PME peut converser en texte ; toute autre interaction passera par re-formulation libre. Critère d'arrêt MVP : SC-001, SC-002 atteints.
2. **Wave 2 (P10 + P8 honorés)** : US2 + US3 (T026 → T034). Bottom sheet et sync EventBus deviennent opérationnels — c'est le minimum pour respecter la constitution sur le périmètre Chat complet.
3. **Wave 3 (UX complète P1)** : US4 + US5 + US6 + US7 (T035 → T049). Sidebar, viz inline, onboarding, gestion d'erreurs.
4. **Wave 4 (nice-to-have P2)** : US8 + US9 (T050 → T056).
5. **Polish & gate** : T057 → T064. Coverage + a11y + perf + smoke avant PR.

## Total task count

- **64 tasks** au total
- Setup : 4 ; Foundational : 8 ; US1 : 13 ; US2 : 5 ; US3 : 4 ; US4 : 4 ; US5 : 3 ; US6 : 3 ; US7 : 5 ; US8 : 3 ; US9 : 4 ; Polish : 8.
- **Tâches `[P]` (parallélisables)** : 33 (≈ 52 %).

## Independent test criteria recap

| Story | Test indépendant en une phrase |
|-------|---------------------------------|
| US1 | Envoi texte + premier token < 500 ms + finalisation < 5 s + curseur clignotant + scroll-pinning. |
| US2 | `tool_invoke` ouvre sheet < 300 ms ; bouton « Répondre librement » revient au texte avec re-classification. |
| US3 | Mutation LLM se reflète dans une page profil ouverte sans rechargement < 1 s, sans boucle EventBus. |
| US4 | Sidebar liste threads ; click ancien thread ré-hydrate < 2 s ; « Nouveau chat » crée un fil vide. |
| US5 | Réponse LLM avec viz → composant F40 rendu en bulle gauche élargie, accessible. |
| US6 | Premier accès `/chat` lance driver.js 4 étapes ; second accès sans tour. |
| US7 | Timeout backend → bulle erreur sobre + bouton « Réessayer » fonctionnel. |
| US8 | 2-3 chips visibles sous la dernière bulle finalisée quand input vide ; click → message envoyé. |
| US9 | Badge taille mémoire visible top ; click ouvre modal détail. |
