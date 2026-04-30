# F34 — Manual tests log

Date : 2026-04-29
Branche : 034-extension-guidage-suivi-notifications

## Scope livré (MVP backend)

- `GET /me/candidatures` — liste candidatures non supprimées (slice 200, tri updated_at DESC, dérive `progression_pct` depuis snapshot_json).
- `PATCH /me/candidatures/{id}/status` — transitions libres entre 5 valeurs blanches, audit log.
- Table `notification` (RLS + check kind + index account/created).
- `GET /me/notifications` — pagination limit/offset, filtre unread.
- `PATCH /me/notifications/{id}/read` — idempotent, audit log.
- Service interne `NotificationService.create_for_account` / `list_for_account` / `mark_read`.

## Scope DEFERRED

- `GET /me/extension/offres-recommandees` (US4 du plan) — non livré dans ce MVP. Reportable car indépendant.
- Panneau latéral UI Chrome (slide-in droite, navigateur d'étapes, mini-chat IA).
- Création automatique de candidature au remplissage de formulaire.
- Sauvegarde de progression `form_data` côté backend.
- Push `chrome.notifications` + cycle `chrome.alarms` 6h.
- Comparateur d'offres modal.

## Tests automatisés

```text
backend/tests/integration/notifications/  -> 12 tests, 100% green
backend/tests/integration/candidatures/   -> 12 tests, 100% green
TOTAL  : 24/24 green
COVERAGE app/notifications + app/candidatures : 92.23 %
```

## Scénarios curl (à exécuter une fois la PME loggée et CSRF posé)

### Liste candidatures

```bash
curl -s -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  http://localhost:8000/me/candidatures | jq
# liste de candidatures non supprimées, max 200, triée updated_at DESC
```

### PATCH statut candidature

```bash
curl -s -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -X PATCH http://localhost:8000/me/candidatures/<cid>/status \
  -H "Content-Type: application/json" \
  -d '{"statut":"soumise"}' | jq
# 200 {id, statut, version, updated_at}
# 422 si statut hors enum, 404 si pas owner
```

### Liste notifications

```bash
curl -s -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  http://localhost:8000/me/notifications | jq
# Filtres : ?unread=true&limit=20&offset=0
```

### Marquer notification lue (idempotent)

```bash
curl -s -b cookies.txt -H "X-CSRF-Token: $CSRF" \
  -X PATCH http://localhost:8000/me/notifications/<nid>/read | jq
# 200 {id, read_at}
# Second appel : meme read_at (idempotent)
# 404 si pas owner
```

## Migration

```bash
cd backend && alembic upgrade head   # applique 0023_f34_notification
cd backend && alembic downgrade -1   # rollback (DROP TABLE notification)
```

## Notes

- DB esg_mefali a été drop+recreate (schéma précédent appartenait à un autre projet hors lineage F01-F35) avant `alembic upgrade head`.
- Pas de modification de la table `candidature` ni d'autres tables existantes.
- Audit best-effort : un échec d'audit ne casse pas la mutation principale (cohérent F33).
