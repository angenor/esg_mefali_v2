# Implementation Plan: Chat Conversational Layer (UI de F12/F13)

**Branch**: `041-chat-conversational-layer` | **Date**: 2026-05-03 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/041-chat-conversational-layer/spec.md`

## Summary

F41 livre la **page `/chat` plein écran** où la PME interagit avec le LLM. C'est l'UI consommatrice du backend chat déjà fourni par F12 (`/me/chat/threads`, `/me/chat/threads/{id}/messages` SSE, `/me/events`) et de l'orchestrateur F14 / mémoire F18. La feature applique strictement l'architecture **haut/bas** (P10) : la zone haute affiche l'historique de bulles asymétriques (LLM gauche, utilisateur droite, viz embed F40) ; la zone basse héberge **soit** l'input texte, **soit** un bottom sheet F39, **soit** une visualisation. Le streaming token-by-token, la sync EventBus vers les pages profil ouvertes (P8), la sidebar des threads, l'onboarding driver.js et la gestion d'erreurs sobres complètent le périmètre MVP.

Approche technique : ~10 composants Vue 3 (`<script setup>`) lazy-loadés, 2 stores Pinia (`useChatStore` pour threads + messages + état de stream ; `useChatEventBus` pour propagation P8), 4 composables (`useChatStream` SSE via `fetch` + `ReadableStream` car le backend POST renvoie un stream — `EventSource` GET-only inutilisable ici, voir research.md ; `useChatScroll` pour le scroll-pinning ; `useChatOnboarding` driver.js ; `useMarkdownStream` pour rendu Markdown tolérant aux fragments). Sécurité : sanitisation stricte via DOMPurify avec allow-list serrée (pas de `<script>`, `<iframe>`, gestionnaires `on*`, `javascript:`). Re-classification freetext : un flag local côté store déclenche `payload_json.force_freetext` au prochain envoi pour que F14 reroute. Le tour driver.js consomme le flag `account.onboarding.chat_seen` (côté account_settings, à exposer par F11 si nécessaire — sinon `localStorage` borné par account_id en fallback documenté). Pas de nouvelle table backend ; pas de nouveau tool LLM. Hors-scope MVP : voix, multi-utilisateur thread, recherche plein-texte, export PDF.

## Technical Context

**Language/Version** : TypeScript 5.x + Vue 3.5 + Nuxt 4 (Composition API, `<script setup>`).

**Primary Dependencies (déjà installées dans `frontend/package.json`)** :
- `pinia ^2.3.0` + `@pinia/nuxt`
- `gsap ^3.12.7` (typing dots, transitions)
- `dompurify ^3.1.7` (sanitize HTML)
- `mermaid ^11.4.1`, `chart.js ^4.4.7`, `leaflet ^1.9.4` (consommés via composants F40)

**Primary Dependencies à ajouter** (déclarées dans le brouillon, à confirmer en research) :
- `markdown-it ^14.x` (parser Markdown tolérant aux fragments)
- `markdown-it-sanitizer` ou `markdown-it-link-attributes` + DOMPurify côté HTML
- `mitt ^3.x` (event bus client minimaliste)
- `driver.js ^1.3.x` (onboarding tour) — version exacte alignée sur F38 si déjà installée
- `@langchain/langgraph` (orchestration front sheet ↔ input ↔ SSE) si la cible front-side est confirmée par research ; sinon machine à états maison `useChatGraph` (alternative simple).

**Storage** : aucun (frontend pur). Persistance via API F12 (PostgreSQL `chat_thread`, `chat_message` déjà existants).

**Testing** :
- Unit + composant : Vitest + `@vue/test-utils` + happy-dom
- Streaming + SSE : tests `useChatStream` avec `ReadableStream` simulé
- Sécurité : tests dédiés sanitisation (XSS payload list dans `tests/chat-sanitize.spec.ts`)
- A11y : axe-core sur `/chat`
- E2E manuel (route démo) : `make frontend` + `/chat`

**Target Platform** : navigateurs evergreen, SSR Nuxt actif. Composants lourds (mermaid, chart.js, leaflet hérités F40) hydratés `<ClientOnly>`. Mobile iOS/Android : safe-area-inset-bottom obligatoire pour l'input.

**Project Type** : Web (frontend Nuxt 4 + backend FastAPI). Cette feature est strictement frontend ; **aucun nouvel endpoint backend** n'est créé. Les contrats consommés sont déjà publiés par F12 et F18.

**Performance Goals** :
- Premier token < 500 ms après envoi (NFR-001 / SC-001)
- Bulle LLM finalisée < 5 s (SC-002)
- Bottom sheet ouvre < 300 ms (SC-003)
- EventBus → page entité < 1 s (SC-004)
- Restitution thread historique < 2 s (SC-010)

**Constraints** :
- P10 strict : aucune primitive interactive (`<input>`, `<button type="submit">`, `<select>`) à l'intérieur d'une bulle ; toute saisie passe par F39 bottom sheet engine.
- P1 strict : citations LLM obligatoirement passées par `<VizSourcePin>` (composant F40), jamais de lien brut sans source.
- P8 strict : pas de boucle EventBus → LLM (les mutations LLM propagées doivent porter une origine `source: "llm"` ignorée par les listeners qui re-déclenchent l'orchestrateur).
- Sanitize blanc-liste stricte ; pas de `dangerouslySetInnerHTML` non-sanitisé.
- Reconnexion SSE déduplication par `sequence_id` côté client.
- Mobile : input non-recouvert par clavier virtuel via CSS `env(safe-area-inset-bottom)` + `100dvh`.

**Scale/Scope** :
- ~10 composants chat + 2 stores + 4 composables + 2 routes (`/chat`, `/chat/[thread_id]`).
- Sidebar : jusqu'à 200 threads (limite API F12 actuelle), virtualisation si > 50.
- Historique d'un thread : jusqu'à plusieurs centaines de messages, scroll virtualisé optionnel (V2 si profilage le justifie ; sinon DOM simple suffit pour MVP).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Toute donnée factuelle introduite pointe-t-elle vers une `Source` `verified` ? | ✅ — feature display ; FR-005 impose les citations en superscript via `<VizSourcePin>` (F40). Aucune assertion factuelle introduite par F41 lui-même. |
| P2 | Multi-tenant RLS | Toute nouvelle table porte-t-elle `account_id` + RLS ? | ✅ N/A — aucune nouvelle table. Les API consommées (F12) appliquent déjà RLS via `app.current_account_id`. |
| P3 | Audit log append-only | Toute mutation est-elle journalisée ? | ✅ N/A — F41 ne mute rien directement. Les mutations LLM passent par les outils F17 qui auditent. |
| P4 | Versioning + snapshot | Référentiels versionnés ? | ✅ N/A — pas de référentiel introduit. |
| P5 | Money typé | `Money = {amount: Decimal, currency}` partout ? | ✅ — les valeurs monétaires affichées dans les bulles passent par les composants viz F40 (déjà conformes). F41 ne formate pas de monnaie nue. |
| P6 | Pivot Indicateur unique | Données ESG comme `Indicateur` ? | ✅ N/A — display uniquement. |
| P7 | Plateforme fermée aux intermédiaires | Pas de rôle Intermédiaire/Bank/Fund ? | ✅ — UI réservée au rôle PME (`get_current_pme` côté API). |
| P8 | Édition manuelle + sync LLM | Sync bidirectionnelle effective ? Mutation manuelle invalide contexte ? | ✅ — FR-013 impose EventBus client + flux `/me/events` SSE F18 ; les listeners filtrent `source: "llm"` pour éviter les boucles. La page profil reflète le DB en moins de 1 s. |
| P9 | Tool-use LLM fiable | Nouveaux tools ? | ✅ N/A — F41 ne définit aucun tool. Elle consomme les intentions d'outil émises par F14 et déclenche le bottom sheet F39 correspondant. |
| P10 | UX bottom sheet | Composants interactifs dans le bottom sheet, jamais inline ? Bouton "Répondre librement" présent ? | ✅ — FR-002 + FR-010 + FR-011. Aucune primitive de saisie n'est admise dans une bulle ; chaque sheet expose explicitement le bouton freetext. |

**Verdict** : ✅ tous gates `pass` ou `N/A`. Pas de violation à justifier dans `Complexity Tracking`.

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter (interchangeable par env).
- Dev local : backend en `.venv`, Postgres seul service dockerisé, frontend en `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + loi ivoirienne 2013-450 + UEMOA 20/2010.
- Langue : français par défaut.

## Project Structure

### Documentation (this feature)

```text
specs/041-chat-conversational-layer/
├── plan.md              # This file
├── research.md          # Phase 0 output (SSE POST stream, markdown partial, EventBus, langgraph front)
├── data-model.md        # Phase 1 output (entités UI / store)
├── quickstart.md        # Phase 1 output (lancer + tester /chat)
├── contracts/
│   ├── chat-api.consumed.md      # endpoints F12/F18 consommés (référence, non-créés ici)
│   └── component-api.md          # API publique des composants chat
├── checklists/
│   └── requirements.md  # créé par /speckit-specify
└── tasks.md             # généré par /speckit-tasks
```

### Source Code (repository root)

```text
frontend/app/
├── components/
│   └── chat/
│       ├── ChatLayout.vue              # 2-cols : sidebar + main
│       ├── ChatHeader.vue              # titre thread + MemoryBadge + bouton Nouveau chat
│       ├── ChatHistory.vue             # virtualisation simple, scroll-pinning
│       ├── MessageBubbleUser.vue       # bulle droite
│       ├── MessageBubbleAssistant.vue  # bulle gauche, slot dynamique (texte / viz / erreur)
│       ├── MessageMarkdown.vue         # rendu Markdown sanitisé tolérant aux fragments
│       ├── MessageError.vue            # bulle erreur sobre + bouton Réessayer
│       ├── MessageInput.vue            # textarea autoresize + attache + bouton envoi
│       ├── TypingIndicator.vue         # 3 dots gsap
│       ├── ThreadList.vue              # sidebar (Nouveau chat, threads passés)
│       ├── QuickReplies.vue            # chips P2
│       └── MemoryBadge.vue             # badge top + modale détail
├── composables/
│   ├── useChatStream.ts                # fetch + ReadableStream + parse SSE + dedup sequence_id
│   ├── useChatScroll.ts                # scroll-pinning (autoscroll suspendu si user scrolled-up)
│   ├── useChatOnboarding.ts            # driver.js 4 étapes, flag persisté
│   ├── useChatEventBus.ts              # mitt + bridge Pinia ; ignore { source: 'llm' } pour éviter loop
│   └── useMarkdownStream.ts            # markdown-it tolerant + DOMPurify
├── stores/
│   └── chat.ts                         # threads, currentThread, messages, streamingState
├── pages/
│   ├── chat/
│   │   ├── index.vue                   # redirige vers dernier thread ou crée un thread vide
│   │   └── [thread_id].vue             # thread spécifique
└── plugins/
    └── chat-event-source.client.ts     # branche /me/events SSE → useChatEventBus

frontend/tests/
└── chat/
    ├── ChatHistory.spec.ts
    ├── MessageMarkdown.spec.ts         # cas Markdown partiel + payload XSS
    ├── useChatStream.spec.ts           # SSE simulé, dedup, reconnect backoff
    └── useChatEventBus.spec.ts         # propagation, no-loop guard
```

**Structure Decision** : option 2 (Web app, frontend + backend) confirmée. F41 ajoute uniquement sous `frontend/app/components/chat/`, `frontend/app/composables/`, `frontend/app/stores/chat.ts`, `frontend/app/pages/chat/`. Aucun fichier backend modifié — les contrats consommés sont déjà publiés par F12 (chat) et F18 (memory + `/me/events`).

## Complexity Tracking

> **Aucun gate constitutionnel violé** — section laissée vide volontairement.
