# Contract — Chat EventBus Sync (F46)

Synchronisation entre la page `/scoring` et le chat conversationnel (F41) via le bus `useChatEventBus`. Tous les évènements sont **typés**, **synchrones côté front** (aucun WebSocket ajouté), et **idempotents** côté récepteur.

## 1. Évènements consommés (chat → /scoring)

### `entity_updated`

```ts
type ChatEventEntityUpdated = {
  type: 'entity_updated'
  entity_type: 'indicateur' | 'score_calculation' | 'entreprise' | 'projet'
  entity_id: string
  source: 'manual' | 'tool' | 'llm' | 'import' | 'admin'
  ts: string // ISO-8601
  meta?: {
    referentiel_code?: string
    field?: string
    indicateur_code?: string
  }
}
```

Comportement côté `useScoring` :

| `entity_type` | Action |
|---|---|
| `indicateur` | Re-fetch `summaries` (light) **et** `details[currentRef]` + `history[currentRef]`. Si `meta.indicateur_code` est connu et qu'aucun référentiel chargé ne le contient, ne rien faire. |
| `score_calculation` | Re-fetch `details[currentRef]` + `history[currentRef]`. Pas de re-fetch summaries (les autres référentiels n'ont pas changé). |
| `entreprise` | Si `meta.field` correspond à un champ du `SCORING_INDICATEUR_TO_ENTREPRISE_PATH` → re-fetch summaries + détails du référentiel courant. Sinon ignorer. |
| `projet` | Ignoré au MVP (le scoring projet est post-MVP). |

Toutes les invalidations sont **debounced 200 ms** (un même tour LLM peut émettre plusieurs events).

### `open_chat_for_indicateur`

Évènement **émis** par `<MissingIndicatorsList>` ou par `<IndicateurDrawer>` (cas non-éditable) **vers** le chat (sens scoring → chat ; détaillé en §2).

## 2. Évènements émis (/scoring → chat)

### `open_chat_for_indicateur`

```ts
type OpenChatForIndicateur = {
  type: 'open_chat_for_indicateur'
  indicateur_code: string
  referentiel_code: string
  source: 'scoring_page'
}
```

Reçu par F41 ; ouvre le panneau chat avec un message d'amorçage du type « Aidez-moi à compléter l'indicateur {code} pour le référentiel {ref} ».

### `entity_updated` (auto-émis après mutations locales)

Après une `editIndicateur` réussie, le store émet **dans cet ordre** :

1. `entity_updated{entity_type: 'indicateur', entity_id: <indicateur_id>, source: 'manual', meta: {indicateur_code, referentiel_code}}`
2. `entity_updated{entity_type: 'score_calculation', entity_id: <new_calc_id>, source: 'manual', meta: {referentiel_code}}`

Après une `recompute(refCode)` réussie :

- `entity_updated{entity_type: 'score_calculation', entity_id: <new_calc_id>, source: 'manual', meta: {referentiel_code}}`

## 3. Garanties

- **Idempotence** : recevoir le même event deux fois → un seul re-fetch grâce au cache TTL 60 s + clé d'idempotence interne (`ts + entity_id`).
- **Pas de loop** : un event émis localement n'est pas re-consommé par soi-même (filtré sur `source === 'manual'` + flag interne `_localEmission`).
- **Ordre** : si plusieurs events arrivent dans un même tick, le store les traite dans l'ordre de réception, mais un seul re-fetch effectif est lancé par référentiel cible.
- **Erreurs** : si un re-fetch déclenché par event échoue, le store met à jour `errorByRef[refCode]` et expose un toast non bloquant ; la page reste sur l'état connu précédent.

## 4. Tests

- Unit : `frontend/tests/unit/composables/useScoring.test.ts` — vérifie l'invalidation correcte selon `entity_type` + `meta.field`.
- E2E : `frontend/tests/e2e/scoring-chat-sync.spec.ts` — ouvre `/scoring`, déclenche dans le chat (via fixture API directe) une mutation indicateur, et vérifie que la page se rafraîchit sans clic utilisateur.
