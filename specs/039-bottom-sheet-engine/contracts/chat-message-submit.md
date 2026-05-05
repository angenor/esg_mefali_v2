# Contract — Sortie POST `/me/chat/threads/{thread_id}/messages`

**Date** : 2026-05-03
**Direction** : frontend (`useBottomSheetSubmit`) → backend (F14/F15).

## Endpoint

`POST /me/chat/threads/{thread_id}/messages`

## Headers

- `Content-Type: application/json`
- `Authorization: Bearer <jwt>` (cookie de session ou bearer selon la convention du shell)
- `X-CSRF-Token` si requis par la convention nuxt-security en place.

## Request body

```json
{
  "content": "✓ SARL",
  "payload_json": {
    "tool": "ask_qcu",
    "value": "sarl",
    "label": "SARL"
  },
  "context_json": {
    "in_response_to_message_id": "5b6c7e3a-...-uuid",
    "tool": "ask_qcu"
  }
}
```

Règles :
- `content` MUST être ≤ 100 caractères (FR-012, lisibilité du fil).
- `payload_json` MUST être conforme au `ToolResponse` du tool concerné (cf. `tool-payloads.md`) ; le backend rejette `extra='forbid'` (P9).
- `context_json.in_response_to_message_id` MUST référencer le message assistant pending — sinon 422.

## Response 200

```json
{
  "id": "8f9a...-uuid",
  "thread_id": "...",
  "role": "pme",
  "content": "✓ SARL",
  "created_at": "2026-05-03T16:42:11Z"
}
```

À réception du 200, le frontend déclenche `close('submit')` et émet `submit` (cf. `orchestrator-events.md`). Le LLM réagit ensuite via SSE de F14 (hors scope F39).

## Erreurs

| Code | Cause | UI |
|------|-------|----|
| 400 | payload zod-valide front mais rejeté backend (drift) | toast erreur + log ; régénérer `pnpm gen:tools` |
| 401 | session expirée | redirige login (gestion globale shell) |
| 404 | `thread_id` ou `in_response_to_message_id` introuvable | message inline « Conversation introuvable » + bouton « Recommencer » qui efface le sheet |
| 409 | message tool déjà résolu (race) | ferme le sheet sans erreur visible (la conversation est à jour, on suit) |
| 413 | (uniquement upload) fichier trop gros — seulement si on bypass le check client | message inline FR |
| 422 | validation backend (Pydantic) | message inline mappé sur le champ source si possible |
| 5xx | erreur serveur | toast + bouton Réessayer ; pas de retry auto (R7) |

## Idempotence et déduplication

- Pas d'`Idempotency-Key` côté F39 ; la déduplication repose sur `inFlight` (R7) + désactivation du bouton « Valider ».
- Le backend (F14) gère le cas race avec 409 si le tool est déjà résolu — le frontend ferme proprement.

## Cas particulier `ask_file_upload`

L'upload du fichier passe par un endpoint dédié (cf. `tool-payloads.md`) ; ce contrat reste valable pour le **message PME final** une fois `doc_id` obtenu. Donc deux requêtes en séquence : (1) upload binaire → renvoie `doc_id` ; (2) POST message PME avec `payload_json.value = {doc_id, ...}`.

## Cas particulier `show_summary_card` — action « Corriger »

Le message PME est posté avec `payload_json.value = { action: "correct" }`. Aucun upload, pas d'écriture autre. Le frontend émet ensuite `dismiss-for-freetext` pour réactiver l'input texte ; le LLM consomme ce message et reclassifie librement.
