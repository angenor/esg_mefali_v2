# F25 — Matching Projet <-> Offre — Manual Test Log

Date : 2026-04-29
Branche : `025-matching-projet-offre`
Scope livré : MVP P1 backend (US1, US2, US3, US4, US7)
Scope reporté : US5 (alertes), US6 (filtres riches), US8 (tool LLM), frontend Nuxt.

## Résultats automatisés

| Étape | Commande | Résultat |
|---|---|---|
| Tests unitaires F25 | `pytest backend/tests/unit/matching` | 46 passed |
| Couverture `app.matching` | `--cov=app.matching` | 81.66% (>= 80%) |
| Lint ruff | `ruff check app/matching tests/unit/matching` | All checks passed |
| Régression unit globale | `pytest backend/tests/unit --ignore=test_migration_smoke.py` | 411 passed |
| Routes enregistrées | inspection `app.routes` | 4 routes F25 OK |

Détail couverture :

```
app/matching/__init__.py             100%
app/matching/candidature_service.py  100%
app/matching/heuristics.py            97%
app/matching/router.py                 0%   (intégration FastAPI différée — DB requise)
app/matching/schemas.py              100%
app/matching/service.py               89%
TOTAL                                 81.66%
```

Note : `router.py` non couvert en unit car les endpoints nécessitent un client FastAPI + DB Postgres + contexte RLS. La logique métier est couverte via les services purs ; les endpoints sont validés par l'enregistrement effectif des routes au boot de l'app.

## Routes enregistrées (vérifiées via `app.main`)

```
GET  /me/projets/{projet_id}/matching
GET  /me/projets/{projet_id}/matching/{offre_id}
GET  /me/fonds/{fonds_id}/intermediaires-comparator
POST /me/projets/{projet_id}/candidatures
```

## Tests manuels recommandés (DB Postgres up)

1. Login PME -> token JWT.
2. GET `/me/projets/{id}/matching` -> 200 avec `items[].fonds_score, intermediaire_score, score_global = min(...)`.
3. GET `/me/projets/{id}/matching/{offre_id}` -> 200 avec critères couverts/manquants par couche, `documents_requis`, `frais_effectifs` (Money), `delais_effectifs_jours`.
4. GET `/me/fonds/{fid}/intermediaires-comparator?projet_id=...` -> 200 avec liste comparée triée.
5. POST `/me/projets/{id}/candidatures` body `{"offre_id":"..."}` -> 201 `{candidature_id, snapshot_hash, statut:"brouillon"}` + ligne `audit_log` créée.
6. RLS : autre PME non-owner -> 404 `projet_not_found`.

## Conformité Module 0

- P1 sourçage : `source_ids` propagés via service depuis fonds/intermediaire dans le snapshot.
- P2 RLS : `/me/*` filtre strictement par `account_id` du JWT (`get_current_pme`).
- P3 audit append-only : `record_audit('candidature', 'create', source_of_change=manual)` à chaque POST.
- P4 versioning + snapshot : `snapshot_json` figé avec hash SHA-256 sur JSON canonicalisé.
- P5 Money typé : conversion FCFA-EUR via `PEG_FCFA_EUR=655.957`.
- P7 plateforme fermée : routes PME-only.
