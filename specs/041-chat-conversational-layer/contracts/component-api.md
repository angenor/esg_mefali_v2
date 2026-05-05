# Contrat — API publique des composants chat F41

Tous les composants exposent des **props strictement typées** et émettent des events nommés. Ils respectent P10 (aucune primitive de saisie inline dans une bulle assistant).

## `ChatLayout.vue`

Mise en page deux colonnes (sidebar + main).

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `threadId` | `string \| null` | `null` | thread courant |

**Slots** : `header`, `history`, `input` (composition libre) ; **emit** : aucun. Responsive : sidebar masquée < 768 px (drawer).

## `ChatHeader.vue`

| Prop | Type | Default |
|------|------|---------|
| `thread` | `ChatThreadSummary \| null` | `null` |

**Emit** : `(e: 'new-chat')` — déclenche création thread vide.

Affiche `MemoryBadge` à droite.

## `ChatHistory.vue`

| Prop | Type |
|------|------|
| `messages` | `ChatMessage[]` |
| `streaming` | `StreamingState \| null` |

**Emit** :
- `(e: 'retry', messageId: string)` — relance la requête depuis une bulle erreur.
- `(e: 'cite-click', sourceId: string)` — délègue au popover viz F40.

Implémente le scroll-pinning : autoscroll bottom **sauf** si `useChatScroll` détecte `userScrolledUp === true`.

## `MessageBubbleUser.vue`

| Prop | Type |
|------|------|
| `message` | `ChatMessage` |

Rendu droite, fond `brand-50`, timestamp visible au hover. Aucun event.

## `MessageBubbleAssistant.vue`

| Prop | Type |
|------|------|
| `message` | `ChatMessage` |
| `isStreaming` | `boolean` |

Slots dynamiques selon `message.payload?.kind` :
- pas de payload → `<MessageMarkdown>`
- `kind: 'viz'` → délègue à `<Viz*>` F40 selon `tool`
- `kind: 'error'` → `<MessageError>`

**Emit** :
- `(e: 'cite-click', sourceId: string)`
- `(e: 'retry', messageId: string)`

**Contrainte P10** : aucune primitive interactive de saisie. Les seuls éléments cliquables admis sont les liens externes sanitisés et les pins de source `<VizSourcePin>`.

## `MessageMarkdown.vue`

| Prop | Type | Default |
|------|------|---------|
| `content` | `string` | — |
| `streaming` | `boolean` | `false` |

Rendu via `useMarkdownStream` : `markdown-it` parse → DOMPurify allow-list → `v-html`. Curseur clignotant injecté en fin si `streaming === true`. Aucun event.

## `MessageError.vue`

| Prop | Type |
|------|------|
| `error` | `ChatError` |

**Emit** : `(e: 'retry')`.

## `MessageInput.vue`

| Prop | Type | Default |
|------|------|---------|
| `disabled` | `boolean` | `false` |
| `placeholder` | `string` | `'Posez votre question…'` |

**Emit** :
- `(e: 'submit', payload: { content: string; files?: File[]; forceFreetext: boolean })`
- `(e: 'attach', files: FileList)`

Comportement :
- `<UiTextarea>` autoresize 1–6 lignes (F37)
- `Cmd/Ctrl + Enter` déclenche `submit`
- `Enter` simple = newline
- Bouton attache (icône paperclip) ouvre `<input type=file>` caché — délègue à F22 (upload) en post-MVP, MVP : juste l'event `attach`
- Visible **uniquement** quand `useChatBottomSheet().isOpen === false`

## `TypingIndicator.vue`

3 dots animés `gsap.to(...)`. Aucune prop, aucun event.

## `ThreadList.vue`

| Prop | Type |
|------|------|
| `threads` | `ChatThreadSummary[]` |
| `currentId` | `string \| null` |

**Emit** :
- `(e: 'select', threadId: string)`
- `(e: 'new-chat')`

Tri par `lastMessageAt` DESC. Virtualisation `vue-virtual-scroller` si `threads.length > 50`.

## `QuickReplies.vue` (P2)

| Prop | Type |
|------|------|
| `suggestions` | `string[]` (≤ 3) |

**Emit** : `(e: 'pick', suggestion: string)`.

Visible **seulement** quand la dernière bulle assistant est finalisée et que l'input est vide.

## `MemoryBadge.vue` (P2)

| Prop | Type |
|------|------|
| `snapshot` | `MemorySnapshot \| null` |

**Emit** : `(e: 'open')` — ouvre une modale F37 listant les entrées.

## Composables — signatures publiques

```ts
function useChatStore(): {
  state: { threads, currentThreadId, messagesByThread, streaming, ... }
  loadThreads(): Promise<void>
  selectThread(id: string): Promise<void>
  newThread(): Promise<string>
  sendMessage(args: { content: string; payload?: MessagePayload | null; forceFreetext?: boolean }): Promise<void>
  retry(messageId: string): Promise<void>
  cancelStream(): void
}

function useChatStream(opts: { onFrame: (frame: SSEFrame) => void; onError: (err: ChatError) => void }):
  { start(url: string, body: object): Promise<void>; abort(): void }

function useChatScroll(historyEl: Ref<HTMLElement | null>):
  { userScrolledUp: Ref<boolean>; scrollToBottom(): void }

function useChatEventBus():
  { on(event: string, fn: (e: EventBusEvent) => void): () => void;
    emit(event: string, payload: EventBusEvent): void }

function useChatOnboarding():
  { maybeStart(): Promise<void>; markSeen(): Promise<void> }

function useMarkdownStream(): { render(content: string): string }   // sanitize inclus
```

## Garanties non-fonctionnelles

- Tous les composants **lazy-loadés** via Nuxt auto-imports + `defineAsyncComponent` quand pertinent.
- `<ClientOnly>` autour des composants viz embeds (mermaid/leaflet) hérités F40.
- `prefers-reduced-motion` désactive `gsap` (typing indicator statique).
- Tous les libellés utilisateur en **français**.
