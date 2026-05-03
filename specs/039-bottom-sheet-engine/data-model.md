# Data Model — F39 Bottom Sheet Engine

**Date** : 2026-05-03
**Portée** : entités côté **frontend** (TypeScript / Pinia / messages chat). Aucune nouvelle table SQL n'est créée par cette feature.

## Vue d'ensemble

F39 ne fait pas de persistance propre : les seules « données » manipulées sont (a) les instructions de tool reçues du backend via le thread de chat, (b) les réponses postées au backend, et (c) un état éphémère côté Pinia. La structure suit donc le contrat F14/F15 et n'introduit aucune divergence.

## Entités

### `ToolInstruction`

Reçue du backend dans un message assistant non répondu.

| Champ | Type | Contraintes |
|------|------|-------------|
| `tool` | union string littérale (closed enum) | ∈ {`ask_qcu`, `ask_qcm`, `ask_yes_no`, `ask_select`, `ask_number`, `ask_date`, `ask_date_range`, `ask_rating`, `ask_file_upload`, `show_form`, `show_summary_card`} |
| `payload` | objet typé par tool | dérivé Pydantic via `pnpm gen:tools` ; voir `contracts/tool-payloads.md` |
| `context` | objet | `{ thread_id: UUID, message_id: UUID }` (id du message tool d'origine, requis pour la traçabilité) |

Source : message assistant d'un thread où le `payload_json.tool` est défini ET aucun message PME n'a été posté ultérieurement dans le thread (R6).

### `ToolResponse`

Émise vers le backend à la soumission.

| Champ | Type | Contraintes |
|------|------|-------------|
| `tool` | string (même valeur que `ToolInstruction.tool`) | requis |
| `value` | spécifique au tool | voir `contracts/tool-payloads.md` (ex. `ask_qcu` → `string` ; `ask_qcm` → `string[]` ; `ask_number` → `{amount: string-decimal, currency?: ISO 4217, unit?: string}` ; `ask_file_upload` → `{doc_id, filename, mime, size}`) |
| `label` | string | récap court humain (ex. « SARL », « 2 options », « Oui ») ; servira au `content` textuel du message PME (FR-012) |
| `metadata?` | objet | facultatif, ex. `{action: "validate" \| "correct" \| "cancel"}` pour `show_summary_card` (FR-013) |

### `SheetState` (Pinia store `chatBottomSheet`)

État éphémère, vide par défaut. Aucun `localStorage`/`sessionStorage` (Q1).

| Champ | Type | Contraintes |
|------|------|-------------|
| `current` | `ToolInstruction \| null` | un seul à la fois (FR-002) |
| `isClosing` | `boolean` | true pendant l'animation `slideDown`, bloque la double soumission |
| `inFlight` | `boolean` | true pendant le POST de soumission, bloque tout second submit (FR-018) |
| `error` | `string \| null` | message d'erreur localisé pour affichage in-sheet |
| `freeTextRequested` | `boolean` | true si « Répondre librement » ou ESC déclenché ; consommé par le pipeline F14 |

### `ChatMessageSubmit` (corps de la requête sortante)

POST `/me/chat/threads/{thread_id}/messages` (contrat F14/F15) :

| Champ | Type | Contraintes |
|------|------|-------------|
| `content` | string | récap textuel humain (`label` ou variante typée), requis non vide |
| `payload_json` | objet | `{ tool, value, label, metadata? }` (= `ToolResponse` complet) ; requis quand le message répond à un tool |
| `context_json` | objet | `{ in_response_to_message_id: UUID, tool: string }` |

Le backend (F15) valide ce body via Pydantic strict (`extra='forbid'`) et historise dans `chat_messages` ; l'audit (P3) est posé automatiquement avec `source_of_change = "manual"` (réponse PME via UI structurée).

## Relations

```
ToolInstruction (DB: chat_messages, role=assistant, payload_json.tool)
        │
        ▼  reconstitué par useChatBottomSheet.open() au mount
SheetState.current
        │
        ▼  submit du wrapper
ToolResponse ──► ChatMessageSubmit ──► POST /me/chat/threads/{id}/messages
                                                │
                                                ▼  (DB: chat_messages, role=pme + audit_log via F14)
```

## Lifecycle / state transitions

```
                     ┌─────────────────────────┐
                     │       Closed (idle)     │
                     └────────────┬────────────┘
       open(tool, payload)         │
                                   ▼
                     ┌─────────────────────────┐
                     │   Opening (slideUp)     │
                     └────────────┬────────────┘
                                   │ animation done
                                   ▼
                     ┌─────────────────────────┐
                     │         Open            │◄────────────┐
                     └────┬──────────┬─────┬───┘             │
   submit                 │          │     │ ESC / Réplique  │
                          │          │     │ libre            │
                          ▼          │     ▼                  │
              ┌────────────────┐     │  ┌─────────────────┐   │
              │  Submitting    │     │  │  ClosingFreeText│   │
              │  (inFlight)    │     │  └────────┬────────┘   │
              └───┬───────┬────┘     │           │            │
       success    │       │ HTTP err │           │ animation  │
                  ▼       ▼          │           ▼            │
       ┌─────────────┐ ┌──────────┐  │   Closed + bascule barre
       │ Closing     │ │ ErrorIn  │  │     texte active +
       │ (slideDown) │ │ Sheet    │──┘     event freetext
       └────┬────────┘ └──────────┘
            ▼
        Closed (idle)
```

Notes :
- `Submitting` ne se termine en `Closing` qu'après réception du 2xx ; en cas d'erreur, retour à `Open` avec message inline.
- `ESC` est ignoré pendant `Submitting` pour éviter une fermeture en plein POST (cohérent avec FR-018).
- Au reload, `Closed (idle)` puis si l'API renvoie un message tool pending, on enchaîne `Opening` directement.

## Validation rules

- Tout payload reçu MUST être validé par le schéma zod généré (`pnpm gen:tools`) avant ouverture du sheet ; un payload invalide loggue une erreur, ferme silencieusement le pending et bascule en saisie libre (le LLM se corrigera).
- Tout `ToolResponse` MUST être validé par son schéma zod avant POST ; un échec local recolle l'erreur au champ pertinent et bloque la soumission.
- `label` MUST être ≤ 100 caractères pour rester lisible dans le fil de discussion.
- Tout texte exogène (option, description, source) MUST passer par `utils/sanitize.ts` avant rendu HTML.

## Aucune migration SQL

Cette feature ne crée ni ne modifie aucune table — toutes les écritures passent par l'API existante de `chat_messages` (F14/F15).
