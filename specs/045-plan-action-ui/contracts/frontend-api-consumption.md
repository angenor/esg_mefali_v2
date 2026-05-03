# Contract — Frontend API consumption (F45)

Endpoints **consommés** (pas créés) par cette feature. Aucun nouveau endpoint backend ne sera défini.

## C1 — `GET /me/action-plan`

**Source** : F31 — `backend/app/action_plan/routes.py:108`

**Quand** : à l'ouverture de `/plan-action` si cache > 60 s ou inexistant ; à la régénération réussie ; sur event chat `entity_updated{action_plan}`.

**Auth** : JWT Bearer (cookie httpOnly + middleware Nuxt `auth.ts`).

**Réponse 200** : `ActionPlanRead` (cf. `data-model.md` § 1).

**Réponse 404** : `{ "detail": "Aucun plan d'action généré." }` → l'UI déclenche la logique d'empty state (US7 ou US8 selon présence scoring).

**Réponse 401** : middleware Nuxt redirige vers `/login`.

**Réponse 5xx** : `<CardErrorState>` (réutilisé F44) avec bouton « Réessayer ».

## C2 — `POST /me/action-plan/generate?horizon={6|12|24}`

**Source** : F31 — `backend/app/action_plan/routes.py:66`

**Quand** : confirmation de la modale « Régénérer mon plan » (US5).

**Auth** : JWT Bearer.

**Query** : `horizon` ∈ {6, 12, 24} (validation UI préalable).

**Réponse 201** : `ActionPlanRead` du nouveau plan (version v+1). Le store remplace intégralement `plan` et lève `regenerating`.

**Réponse 422** : `{ "detail": "Aucun ScoreCalculation disponible." }` ou similaire → toast d'erreur, le plan courant reste intact.

**Réponse 5xx** : toast d'erreur, le plan courant reste intact, `regenerating` levé.

**Garde anti double-clic** : `store.regenerating === true` désactive le bouton et bloque la modale.

## C3 — `PATCH /me/action-plan/steps/{step_id}`

**Source** : F31 — `backend/app/action_plan/routes.py:131`

**Quand** :
- Cocher checkbox d'une `StepCard` (`{ status: 'done' }` ou `{ status: 'todo' }`).
- Validation du bottom sheet `<EditStatusSheet>` (`{ status, responsible_user_id }`).

**Auth** : JWT Bearer.

**Body** : `ActionStepPatch` — au moins un champ requis (`status` ou `responsible_user_id`). Champ supplémentaire → 422 (Pydantic `extra='forbid'`).

**Réponse 200** : `ActionStepRead` mis à jour. Le store remplace `plan.steps[id]` par la réponse, lève `stepStates[id].loading`.

**Réponse 404** : `{ "detail": "Étape introuvable." }` (couvre cross-tenant, conformément à la constitution P2). UI : rollback optimiste + toast « Cette étape n'existe plus ou n'est pas accessible. ».

**Réponse 422** : validation échouée. UI : rollback optimiste + toast détaillé.

**Réponse 5xx** : rollback optimiste + toast « Mise à jour impossible, réessayez. ».

**Mise à jour optimiste** : `store.applyOptimisticPatch(id, patch)` :
1. Pousse la mutation dans `pendingMutations[id]`.
2. Si aucune mutation déjà en vol pour cet `id`, applique l'overlay UI immédiatement et lance le PATCH.
3. À résolution, dépile et lance la suivante de la file (ou raz si vide).
4. En erreur, **annule toute la file** pour cet `id`, restaure l'état avant overlay, affiche un toast.

## C4 — `GET /me/scoring/calculations/last` (lecture conditionnelle)

**Source** : F23 — endpoint à confirmer en Phase 2 (le nom exact peut être `/me/scoring/last` ou `/me/scoring/current`).

**Quand** : uniquement si `GET /me/action-plan` renvoie 404 — pour différencier US7 (pas de scoring) de US8 (scoring sans gaps).

**Réponse 200** : payload scoring, l'UI déclenche US8 (« pas de gaps détectés »).

**Réponse 404** : l'UI déclenche US7 (« lancez votre scoring »).

**Note** : si l'endpoint exact n'est pas confirmé, fallback Phase 2 → afficher un empty state générique « Aucun plan d'action » avec deux CTA : « Lancer le scoring » et « Régénérer le plan ».

## C5 — Événements EventBus chat

| Event | Direction | Schéma |
|---|---|---|
| `entity_updated` | Chat → page | `{ entity_type: 'action_step' \| 'action_plan', entity_id: string }` |
| `action_step:locally_updated` | Page → autres | `{ step_id: string, patch: { status?: StepStatus, responsible_user_id?: string \| null } }` |
| `action_plan:regenerated` | Page → autres | `{ plan_id: string, version: number }` |

**Voir** : [chat-eventbus-sync.md](./chat-eventbus-sync.md) pour le détail.

## C6 — Endpoints **non** consommés (P2 différé)

- `POST /me/action-plan/export-pdf` (US12) : **non livré** au MVP. Le bouton `<ExportPlanButton>` est gardé masqué derrière un flag d'environnement `PUBLIC_FEATURE_PLAN_EXPORT_PDF` jusqu'à livraison F51.
- `GET /me/action-plan/versions` (US11) : **probablement à ajouter en Phase 2** côté backend si le drawer historique est livré dans le MVP. Sinon, US11 reste P2 différé.

## Hors scope explicite

- Aucune création ni modification d'endpoint backend dans cette feature.
- Aucune modification de schéma OpenAPI existant.
- Aucune migration Alembic.
