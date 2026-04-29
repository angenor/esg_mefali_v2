# Tests manuels F11 — Profil Entreprise

A jouer hors session de codage automatique.

## Backend uniquement (curl/HTTPie)

| # | Tâche | Scénario | Procédure |
|---|---|---|---|
| M01 | T020 / US1 | Profil vide | `curl -H "Authorization: Bearer TOKEN" :8000/me/entreprise` → 200, fields nullable, version=1. |
| M02 | T021 / US2 | Édition manuelle effectifs | `curl -X PATCH -H "If-Match: 1" -d '{"taille_effectifs":75}' :8000/me/entreprise` → 200, version=2. |
| M03 | T021 / US2 | Édition CA money | `curl -X PATCH -H "If-Match: 2" -d '{"taille_ca":{"amount":250000000,"currency":"XOF"}}' :8000/me/entreprise` → 200. |
| M04 | T022 / US6 | Conflit version stale | Ouvrir 2 sessions PME ; PATCH avec If-Match=2 deux fois → 1er 200, 2nd 409. |
| M05 | T023 / US5 | Complétude | `curl :8000/me/entreprise/completeness` → `{percentage, missing_required_for_features}`. |
| M06 | T024 / US2 | Liste sectors | `curl :8000/me/entreprise/sectors` → tableau ≥ 30 codes. |
| M07 | T025 / RLS | Cross-account leak | Token user account A → écriture impossible sur entreprise account B. |
| M08 | T026 / Audit | Audit traces | Après PATCH multi-champs, query audit_log → N entries (un par champ), source_of_change=manual. |
| M09 | T036 / US3 | SSE updates | Connecter `:8000/me/entreprise/events` ; PATCH dans une autre session → événement reçu. |

## Frontend (DEFERRED)

Tests UI (page Nuxt `/profil/entreprise`, badges provenance, SSE refresh, bottom sheet mobile) seront ajoutés lorsque la phase frontend sera livrée.
