# Contract — Orchestrator events (`useChatBottomSheet`)

**Date** : 2026-05-03
**Composant** : `frontend/app/components/chat/bottom-sheet/ChatBottomSheet.vue` + composable `useChatBottomSheet.ts`.

## API publique du composable

```ts
interface UseChatBottomSheet {
  current: Readonly<Ref<ToolInstruction | null>>
  isOpen: ComputedRef<boolean>
  open(instruction: ToolInstruction): Promise<void>
  close(reason: 'submit' | 'freetext' | 'cancel'): Promise<void>
  rebuildFromThread(threadId: string): Promise<void>  // appelée au mount du chat
}
```

- Un seul `current` à la fois (FR-002).
- `open()` rejette si `isOpen.value === true` (le caller doit `close` d'abord).
- `close('freetext')` ET `close('cancel')` émettent l'événement DOM `dismiss-for-freetext` ; `close('submit')` ne l'émet pas.

## Événements émis vers l'extérieur (props/emits ChatBottomSheet)

| Event | Payload | Quand |
|-------|---------|-------|
| `submit` | `ToolResponse` | wrapper a passé sa validation + POST a réussi (2xx) |
| `dismiss-for-freetext` | `{ tool: string, message_id: string }` | bouton « Répondre librement » OU touche `ESC` ; le pipeline F14 doit reclassifier la prochaine entrée texte |
| `cancel` | `{ tool: string, message_id: string }` | uniquement pour `show_summary_card` action « Annuler » (autres tools n'ont pas de cancel explicite ; ils utilisent `dismiss-for-freetext`) |
| `error` | `{ code: string, message: string, retriable: boolean }` | erreur de soumission backend (≠ erreur de validation zod, qui reste in-sheet) |
| `opened` | `{ tool: string, message_id: string }` | après animation `slideUp` complète (utile pour télémétrie NFR-001) |
| `closed` | `{ tool: string, reason: 'submit' \| 'freetext' \| 'cancel' }` | après animation `slideDown` complète |

## Événements écoutés (props ou EventBus)

- `chat:thread-loaded` (depuis F38 shell) → déclenche `rebuildFromThread(threadId)`.
- `chat:tool-instruction` (depuis F14 SSE) → déclenche `open(instruction)` avec validation zod préalable.
- `chat:input-disabled` ↔ piloté par `isOpen` (le shell désactive l'input quand `isOpen=true`, FR-003).

## Garanties d'ordre

- L'animation `slideUp` ne masque pas les listeners clavier (`ESC` fonctionne dès le début de l'animation).
- `submit` est strictement après le `200 OK` du POST ; aucun `closed('submit')` n'est émis sans confirmation backend.
- `dismiss-for-freetext` peut être émis pendant `slideUp` (cas ESC en plein dépliage) — la fermeture s'enchaîne immédiatement et l'event est posté une seule fois.

## Erreurs et résilience

- Si `rebuildFromThread` ne trouve aucun message tool pending, `current` reste `null`, le shell garde la barre input active ; aucun toast.
- Si `rebuildFromThread` trouve un message tool dont le `payload` ne valide pas le schéma zod : log console (niveau `warn`), `current` reste `null`, et le shell active la barre input. Le LLM (F14) sera relancé sur un nouveau tour libre.
- En cas d'erreur réseau pendant `submit`, le sheet reste ouvert avec un message inline FR + bouton « Réessayer ». Le bouton « Répondre librement » reste accessible.
