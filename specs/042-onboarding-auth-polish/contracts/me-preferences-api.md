# Contract — `/me/preferences` (F42)

**Module** : `app/users/router.py` (extension)
**Auth** : requise (cookie session valide), RLS appliquée — un utilisateur ne lit/modifie que ses propres préférences.

---

## `GET /me/preferences`

Retourne les préférences de l'utilisateur authentifié. Crée la ligne avec valeurs par défaut si absente (upsert idempotent en lecture).

### Réponse 200

```json
{
  "onboarding_state": "pending",
  "onboarding_state_updated_at": "2026-05-03T18:42:11.123456+00:00"
}
```

### Schéma Pydantic (sortie)

```python
from typing import Literal
from datetime import datetime
from pydantic import BaseModel

OnboardingState = Literal["pending", "completed", "skipped", "dismissed"]

class UserPreferencesOut(BaseModel):
    model_config = {"extra": "forbid"}
    onboarding_state: OnboardingState
    onboarding_state_updated_at: datetime
```

### Erreurs

| Status | Cas | Body |
|---|---|---|
| 401 | Pas de session valide | `{"detail":"unauthenticated"}` |

---

## `PATCH /me/preferences`

Met à jour partiellement les préférences. Pour le MVP, seul `onboarding_state` est modifiable.

### Requête

```json
{
  "onboarding_state": "completed"
}
```

### Schéma Pydantic (entrée)

```python
class UserPreferencesPatch(BaseModel):
    model_config = {"extra": "forbid"}
    onboarding_state: OnboardingState | None = None
```

`extra='forbid'` rejette tout champ inconnu (P9 esprit + protection générale).

### Réponse 200

Même schéma que `GET /me/preferences` après mise à jour.

### Effets de bord

- `onboarding_state_updated_at = now()` si `onboarding_state` change.
- `audit_log` reçoit un événement `entity='user_preferences', field='onboarding_state', old=<prev>, new=<value>, source_of_change='manual'`.
- Pas de notification, pas d'événement SSE.

### Erreurs

| Status | Cas | Body |
|---|---|---|
| 400 | `onboarding_state` hors enum | `{"detail":"invalid_onboarding_state"}` |
| 401 | Pas de session | `{"detail":"unauthenticated"}` |
| 422 | Champ inconnu (rejet `extra='forbid'`) | détail Pydantic |

### Idempotence

`PATCH` avec la valeur courante de `onboarding_state` ne met pas à jour `updated_at` ni n'écrit dans l'audit_log (no-op).

---

## Tests d'intégration

| Cas | Attendu |
|---|---|
| `GET` sans session | 401 |
| `GET` avec session — première fois | 200 + ligne créée par défaut, `state=pending` |
| `GET` deuxième fois | 200 + même valeur, pas de duplication de ligne |
| `PATCH` `state=completed` | 200, ligne mise à jour, audit_log écrit |
| `PATCH` `state=invalid_value` | 400 |
| `PATCH` `state=completed` puis `PATCH` même valeur | 200, pas de second événement audit |
| RLS : `PATCH` puis usurpation tenant | 404 sur `GET` du second compte (les préférences ne fuient pas) |

---

## Compatibilité front

Le store Pinia `userPreferences` consomme cet endpoint :

```ts
// frontend/app/stores/userPreferences.ts
export const useUserPreferencesStore = defineStore('userPreferences', () => {
  const state = ref<OnboardingState>('pending')
  const updatedAt = ref<string | null>(null)
  const loaded = ref(false)

  async function load() {
    const r = await $fetch<UserPreferencesOut>('/me/preferences')
    state.value = r.onboarding_state
    updatedAt.value = r.onboarding_state_updated_at
    loaded.value = true
  }
  async function set(next: OnboardingState) {
    if (state.value === next) return
    const r = await $fetch<UserPreferencesOut>('/me/preferences', {
      method: 'PATCH', body: { onboarding_state: next },
    })
    state.value = r.onboarding_state
    updatedAt.value = r.onboarding_state_updated_at
  }
  return { state, updatedAt, loaded, load, set }
})
```
