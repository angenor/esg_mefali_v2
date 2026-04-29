# F06 — Manual tests log

Date : 2026-04-29.

## Périmètre couvert (automatisé)

Backend P1 + P2 (US1, US2, US4 strict ; US3 différé frontend ; US5+US6 backend uniquement).

### Tests automatisés (35 admin tests, 302 total, 86.53 % cov)

- `tests/unit/admin/test_etag_helpers.py` — make_etag, parse_if_match, assert_version_match.
- `tests/unit/admin/test_pagination_helpers.py` — encode/decode cursor base64, build_page.
- `tests/unit/admin/test_publish_gate.py` — verify_sources_or_422 (4 cas).
- `tests/unit/admin/test_registry.py` — EntityRegistry CRUD, demo_indicator boot side-effect.
- `tests/integration/admin/test_admin_middleware.py` — 401 anon, 403 PME, 200 admin, 404 unknown entity.
- `tests/integration/admin/test_publish_flow.py` — 422 missing source, 200 verified, 409 already published.
- `tests/integration/admin/test_etag_concurrency.py` — 412 sans/wrong If-Match, 200 correct, new version sur edit published.
- `tests/integration/admin/test_audit_admin.py` — 3 mutations (create/update/publish) → 3 audit_log avec source_of_change='admin'.
- `tests/integration/admin/test_search_stats.py` — search 422 short q, search grouped, stats counters.

## Tests manuels (à effectuer post-deploy)

Aucun test manuel exécuté dans cette session. Les contrats OpenAPI peuvent être validés via :

```bash
# Smoke check § 7 quickstart.md
curl -X POST localhost:8000/auth/login -d '{"email":"admin@example.com","password":"…"}'
curl -X POST localhost:8000/admin/demo_indicator/ -H "Cookie: …" -H "X-CSRF-Token: …" \
  -d '{"name":"X","source_id":"<UUID verified>"}'
curl -X POST localhost:8000/admin/demo_indicator/<id>/publish -H "If-Match: \"v1\"" …
```

## Frontend (différé)

Toute l'US3 (composants AdminListPage, AdminFormPage, useAdminDraft, etc.) ainsi que
T019-T021 (layout admin Vue), T028-T034 (composables/components/E2E US2 frontend),
T040-T042 (component tests US3), T049-T050 (search bar Vue), T053-T054 (sidebar stats),
T058 (a11y E2E) sont **différés [DEFERRED]** : le backend complet permet déjà à F07 d'avancer ;
le frontend admin sera consolidé lors de F07/F10. La middleware admin existante
(`frontend/app/middleware/admin.ts`) couvre l'US1 minimaliste (404 si non admin).

## Régression F01-F05

- 302 tests, 5 skipped, 0 failed.
- Coverage 86.53 % (≥ 80 %).
- F04 audit / F03 sources / F02 RLS verts.
