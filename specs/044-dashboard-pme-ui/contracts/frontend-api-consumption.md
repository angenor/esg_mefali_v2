# Contract — Endpoints backend consommés par F44

**Date** : 2026-05-03
**Status** : Phase 1 — référence des contrats existants. **Aucune modification backend.**

## C-API-1 — `GET /me/dashboard/summary`

**Source** : F32 (`backend/app/dashboard/router.py`).
**Auth** : JWT PME (middleware `get_current_pme`).
**RLS** : appliqué via `account_id` dérivé du token.

### Request

- Headers : `Authorization: Bearer <jwt>`, `Accept: application/json`.
- Query params : aucun.
- Body : aucun.

### Response 200

Corps : `DashboardSummaryOut` (cf. `backend/app/dashboard/schemas.py`). Forme résumée :

```json
{
  "account_id": "uuid",
  "scores": [
    {
      "referentiel_code": "GCF",
      "referentiel_version": 2,
      "score_global": "62.50",
      "coverage_ratio": "0.84",
      "computed_at": "2026-05-01T10:00:00Z"
    }
  ],
  "carbon": [
    { "year": 2025, "total_tco2e": "120.4", "computed_at": "2026-04-22T08:00:00Z" }
  ],
  "credit_score": {
    "solvabilite": 70,
    "impact_vert": 65,
    "combine": 68,
    "methodologie_version": 1,
    "coherence_warning": false,
    "computed_at": "2026-04-30T12:00:00Z"
  },
  "candidatures": {
    "counters_by_statut": { "en_cours": 2, "soumise": 1 },
    "total": 3,
    "recent": [
      { "id": "uuid", "projet_id": "uuid", "offre_id": "uuid", "statut": "en_cours",
        "soumission_at": null, "created_at": "2026-04-15T09:00:00Z" }
    ]
  },
  "rapports": {
    "total": 5,
    "recent": [
      { "id": "uuid", "entity_type": "scoring", "entity_id": "uuid",
        "referentiels": ["GCF", "IFC"], "language": "fr",
        "generated_at": "2026-04-25T14:00:00Z" }
    ]
  },
  "attestations": {
    "active": 2,
    "revoked": 0,
    "recent": [
      { "id": "uuid", "public_id": "uuid",
        "generated_at": "2026-04-20T09:00:00Z",
        "valid_until": "2027-04-20T00:00:00Z",
        "revoked_at": null }
    ]
  },
  "next_actions": [
    { "id": "uuid", "title": "Compléter le bilan carbone Q1",
      "category": "carbone", "priority": "haute", "status": "pending",
      "horizon_at": "2026-05-15" }
  ],
  "generated_at": "2026-05-03T08:00:00Z"
}
```

### Errors

- `401` : token absent / expiré → redirect `/login` (middleware front).
- `403` `{ code: 'no_account', ... }` : utilisateur sans `account_id` → afficher message d'erreur global "Compte non rattaché à une PME, contactez le support".
- `5xx` : retry léger (1 essai), sinon `state.blockErrors['*']` global → page d'erreur avec bouton "Réessayer".

### Audit

Chaque appel logue `audit_log { action: 'dashboard_view', source_of_change: 'manual' }` côté backend (best-effort, n'affecte pas la réponse).

---

## C-API-2 — `GET /me/data/export`

**Source** : F32 (`backend/app/dashboard/router.py`).
**Auth** : JWT PME.

### Request

- Headers : `Authorization: Bearer <jwt>`, `Accept: application/json`.
- Query params : aucun.

### Response 200

Corps : `DataExportOut` — JSON complet du compte (entreprise, projets, candidatures, scores, carbone, crédit, rapports, attestations, consentements, plan d'action, `exported_at`). Volume typique : 50–500 ko.

### Comportement UI

1. Bouton désactivé pendant la requête (FR-021).
2. Réception du JSON → construction d'un `Blob('application/json')`.
3. Création d'un `<a download="esg-mefali-export-YYYY-MM-DD.json">` et clic programmatique.
4. Bouton réactivé après 2 s post-download.

### Errors

- `401` / `403` : idem C-API-1.
- `5xx` : toast erreur "Export impossible, réessayez plus tard." Aucune perte d'état.

### Audit

Chaque appel logue `audit_log { action: 'data_export', source_of_change: 'manual' }`.

---

## C-API-3 — `PATCH /me/action-plan/steps/{step_id}`

**Source** : F31 (`backend/app/action_plan/router.py`). **Endpoint déjà existant.**
**Auth** : JWT PME, RLS via `account_id`.

### Request

- Headers : `Authorization: Bearer <jwt>`, `Content-Type: application/json`.
- Path param : `step_id` (UUID).
- Body :

```json
{ "status": "done" }
```

(Le seul champ mutable depuis cette feature est `status`. Le composant `CardActionPlan` n'expose pas la modification de titre/horizon — cela relève de la page détail F46.)

### Response 200

Corps : étape mise à jour avec son nouveau `status` et nouveau `version`.

### Errors

- `404` : étape inexistante ou cross-tenant → toast "Étape introuvable", re-fetch du bloc.
- `409 Conflict` : version désynchronisée (l'étape a déjà été modifiée ailleurs) → re-fetch du bloc, ne pas afficher d'erreur agressive (l'utilisateur voulait juste cocher).
- `5xx` : toast "Action impossible, réessayez", revert visuel (la case redevient décochée).

### Comportement UI (optimistic update)

1. Clic checkbox → composant marque l'étape comme "en cours de complétion" (case grisée, spinner mini).
2. Envoi PATCH.
3. Sur succès : `useDashboardStore.invalidate('next_actions')` puis `refresh(['next_actions'])` ; émission event `action_step:completed` sur `useChatEventBus`.
4. Sur erreur : revert + toast.

### Audit

`audit_log { entity: 'action_plan_step', field: 'status', old: 'pending', new: 'done', source_of_change: 'manual' }`.

---

## C-API-4 — `GET /me/matching/recommendations?limit=3` (carte intermédiaires P2)

**Source** : F25 (`backend/app/matching/router.py`). À vérifier en T0 — si endpoint absent, dégrader la carte en "indisponible" (et créer un ticket pour F25). **Aucun nouveau backend dans cette feature.**

### Response attendue (forme prévue)

```json
{
  "recommendations": [
    { "id": "uuid", "label": "BOAD", "type": "fond",
      "lat": 12.6392, "lng": -8.0029, "score": 0.78 }
  ]
}
```

### Comportement UI

- Lazy fetch au mount de `CardIntermediaires`.
- Si `404` ou réponse vide → `kind: 'empty'`.
- Si `5xx` → `kind: 'error'` avec retry, sans casser les autres cartes.

---

## Récapitulatif

| ID | Endpoint | Méthode | Fournisseur | Mutation ? |
|----|----------|---------|-------------|------------|
| C-API-1 | `/me/dashboard/summary` | GET | F32 (existant) | non |
| C-API-2 | `/me/data/export` | GET | F32 (existant) | non |
| C-API-3 | `/me/action-plan/steps/{id}` | PATCH | F31 (existant) | oui (status) |
| C-API-4 | `/me/matching/recommendations` | GET | F25 (existant ou dégradable) | non |

**Aucun nouveau endpoint à livrer dans F44.**
