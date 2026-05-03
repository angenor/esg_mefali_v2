# F41 — Chat Conversational Layer

UI de la page `/chat` consommatrice de F12 (chat backend) + F18 (memory + `/me/events` SSE).

## Architecture haut/bas (P10)

- **Zone haute** : historique de bulles asymétriques (LLM gauche, utilisateur droite, viz embed F40).
- **Zone basse** : **soit** l'input texte (`MessageInput`), **soit** un bottom sheet F39, **soit** une visualisation. Jamais une primitive interactive dans une bulle.

## Composants

| Fichier | Rôle |
|---|---|
| `components/chat/ChatLayout.vue` | 2-cols desktop, drawer mobile (< 768 px). |
| `components/chat/ChatHeader.vue` | titre thread + `MemoryBadge` + bouton Nouveau chat. |
| `components/chat/ChatHistory.vue` | itère messages, scroll-pinning, intercalation `TypingIndicator`. |
| `components/chat/MessageBubbleUser.vue` | bulle droite, fond `brand-50`, timestamp hover. |
| `components/chat/MessageBubbleAssistant.vue` | bulle gauche, slot dynamique selon `payload.kind` (text / viz / sheet_result / error). Émet `cite-click`, `retry`. |
| `components/chat/MessageMarkdown.vue` | rendu Markdown sanitisé tolérant aux fragments + curseur clignotant. |
| `components/chat/MessageError.vue` | bulle erreur sobre + bouton Réessayer (FR libellé selon `code`). |
| `components/chat/MessageInput.vue` | UiTextarea autoresize + envoi (Cmd/Ctrl+Enter) + attache event-only ; masqué quand sheet ouvert. |
| `components/chat/TypingIndicator.vue` | 3 dots gsap, neutralisé si `prefers-reduced-motion`. |
| `components/chat/ThreadList.vue` | sidebar tri DESC + virtualisation > 50. |
| `components/chat/QuickReplies.vue` | chips ≤ 3 sous la dernière bulle finalisée. |
| `components/chat/MemoryBadge.vue` | badge taille mémoire + modale détail. |

## Stores et composables

| Fichier | Rôle |
|---|---|
| `stores/chat.ts` | store unique : `threads`, `currentThreadId`, `messagesByThread`, `streaming`, `forceFreetextNext`, `errors`, `memorySnapshots`. Actions `loadThreads`, `selectThread`, `newThread`, `sendMessage`, `retry`, `cancelStream`, `handleFrame`, `fetchMemorySnapshot`. |
| `composables/useChatStream.ts` | `fetch` + `ReadableStream` + parse SSE manuel ; dedup `Set<sequence_id>` ; backoff `1/2/4/8s` (max 5). |
| `composables/useChatEventBus.ts` | `mitt` + filtre `ignoreLlmSource` anti-loop P8. |
| `composables/useChatScroll.ts` | scroll-pinning, suspendu si user scrolled-up, reprend < 64 px du bas. |
| `composables/useMarkdownStream.ts` | `markdown-it` + DOMPurify allow-list stricte (R2/R10). |
| `composables/useChatOnboarding.ts` | tour driver.js 4 étapes, flag DB > localStorage fallback. |
| `composables/useChatToolBridge.ts` | écoute `chat:tool-invoke` et `chat:bottom-sheet:dismiss-for-freetext` pour wirer F39 et le store. |
| `plugins/chat-event-source.client.ts` | `EventSource` sur `/me/events`, normalise et publie sur `useChatEventBus`. |

## Machine d'état du streaming

```
idle ──send()──▶ streaming ──tool_invoke──▶ awaiting_sheet ──submit──▶ streaming
   ▲              │                           │
   │ message_done │ error                     │ freetext (force_freetext=true)
   │              ▼                           ▼
   └───────── error / cancelled ◀── abort()  back to streaming via sendMessage
```

## EventBus / sync bidirectionnelle (P8)

- `mitt` instance singleton.
- Frames SSE backend `/me/events` → plugin client → `useChatEventBus.emit(eventType, payload)`.
- Pages profil consomment via `useChatEventBus.on('entity_updated', handler)`.
- Listeners qui re-déclencheraient l'orchestrateur LLM passent `{ ignoreLlmSource: true }` pour ignorer `source === 'llm'`.

## Sécurité (R10)

- Markdown rendu via `markdown-it` `html: false` (HTML inline échappé en texte inerte).
- DOMPurify allow-list :
  - tags : `p, br, hr, strong, em, s, del, code, pre, ul, ol, li, h1-h6, table, thead, tbody, tr, th, td, a, blockquote, sup, sub, span`
  - attrs : `href, rel, target, class, title`
- Hook `afterSanitizeAttributes` ajoute `rel="noopener noreferrer"` + `target="_blank"` aux `<a>`.
- `ALLOWED_URI_REGEXP` : `https:`, `mailto:`, ancres et chemins relatifs uniquement.
- 10 payloads OWASP testés dans `tests/chat/security.spec.ts`.

## Tests

`tests/chat/` — 12 fichiers, 52 tests. Couvre :
- sanitisation Markdown + 10 payloads XSS OWASP
- streaming SSE simulé (frames, dedup, abort, reconnect)
- store : `sendMessage`, `handleFrame`, `retry`, freetext flag
- bus : `ignoreLlmSource`, `off`
- composants : `ChatHistory`, `MessageBubbleAssistant`, `ThreadList`, `QuickReplies`, `MemoryBadge`, `MessageError`

## Endpoints consommés (aucun nouveau backend)

- `GET /me/chat/threads`
- `POST /me/chat/threads`
- `GET /me/chat/threads/{id}/messages`
- `POST /me/chat/threads/{id}/messages` (SSE stream)
- `GET /me/chat/threads/{id}/memory` (F18 — implémentation backend partielle ; UI tolère 404)
- `GET /me/chat/threads/{id}/pending-tool` (F39)
- `GET /me/events` (F18 — SSE)
- `GET/PATCH /me/account/settings` (F11 — flag onboarding ; fallback localStorage si absent)
