# Contracts — Simulateur API extensions (F51)

Ces contrats étendent F27. Tous les schémas Pydantic v2 ont `extra='forbid'`.

## 1. `POST /me/simulations` (existant — F27, rappel)

Calcule une simulation **transitoire** (non sauvegardée). Réponse contient `mensualites`, `cout_total`, `economie_estimee`, `co2_evite_t`, `decomposition_pct`, `formula_refs`.

Body :

```jsonc
{
  "projet_id": "uuid|null",
  "offre_id": "uuid|null",
  "hypotheses": {
    "montant": { "amount": "150000", "currency": "EUR" },
    "duree_mois": 60,
    "type_investissement": "renouvelable_solaire",
    "part_subvention_pct": 30
  }
}
```

> Pour F51, `projet_id` et `offre_id` peuvent être `null` (mode exploration sans projet réel).

## 2. `POST /me/simulations/save` (NOUVEAU)

Sauvegarde une simulation calculée (snapshot des inputs + outputs). Auth : PME.

Body :

```jsonc
{
  "label": "Solaire 150k 60 mois",
  "projet_id": "uuid|null",
  "offre_id": "uuid|null",
  "hypotheses": { /* identique à POST /me/simulations */ },
  "results": { /* identique au response de POST /me/simulations */ }
}
```

Comportement :

- Le serveur **revérifie** les `results` en relançant le calcul (sécurité — les résultats client peuvent être manipulés). Si écart > tolérance numérique, 422 `results_tampered`.
- Cap 50 simulations actives → 409 `quota_exceeded`.
- Audit `record_audit(entity='simulation_savee', field='id', source='manual')`.

Response 201 :

```jsonc
{
  "id": "uuid",
  "label": "Solaire 150k 60 mois",
  "created_at": "ts"
}
```

## 3. `GET /me/simulations` (NOUVEAU)

Liste historique. Auth : PME. Filtre `deleted_at IS NULL`.

Query : `limit` [1..50] default 20, `cursor` (post-MVP).

Response 200 :

```jsonc
{
  "items": [
    {
      "id": "uuid",
      "label": "Solaire 150k 60 mois",
      "projet_id": "uuid|null",
      "offre_id": "uuid|null",
      "hypotheses": { ... },
      "results_summary": {
        "cout_total": { "amount": "151827", "currency": "EUR" },
        "co2_evite_t": "8.5"
      },
      "created_at": "ts"
    }
  ],
  "count": 1,
  "next_cursor": null
}
```

## 4. `GET /me/simulations/{id}` (NOUVEAU)

Détail simulation sauvegardée pour réouvrir/comparer.

Response 200 :

```jsonc
{
  "id": "uuid",
  "label": "Solaire 150k 60 mois",
  "projet_id": "uuid|null",
  "offre_id": "uuid|null",
  "hypotheses": { ... },
  "results": { ... },
  "created_at": "ts"
}
```

Erreurs : 404 si supprimée ou cross-tenant.

## 5. `DELETE /me/simulations/{id}` (NOUVEAU — soft-delete)

Auth : PME. Pose `deleted_at=now()`. Audit `field='deleted_at', source='manual'`.

Response 204.

## 6. `POST /me/simulations/comparator` (existant — F27)

Inchangé. Permet de comparer une simulation contre N offres.

---

## Erreurs communes

| Code HTTP | `code` | Cas |
|---|---|---|
| 400 | `invalid_hypotheses` | `montant ≤ 0`, `duree_mois ≤ 0`, `part_subvention_pct ∉ [0,100]` |
| 401/403 | (cf. matching) | |
| 404 | `simulation_not_found` | id inexistant ou supprimé |
| 409 | `quota_exceeded` | > 50 simulations actives |
| 422 | `results_tampered` | divergence entre results client et recompute serveur |
