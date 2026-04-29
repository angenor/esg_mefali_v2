# Tests manuels — F07 catalog-sources-management

Date : 2026-04-29
Branche : `007-catalog-sources-management`
Scope implémenté : Phase 1 + Phase 2 partiel (canonicalize, http_probe, permissions, schemas, service create + duplicate detection, router POST/GET) ; tests TDD complets ; couverture 86 %.

## Tests manuels recommandés (US1)

### 1. Créer une source via API (admin)

Pré-requis :
- Backend up : `cd backend && uvicorn app.main:app --reload`
- Postgres up via `docker compose up -d postgres`
- Compte admin (utiliser `app/scripts/seed_admin.py` ou la fixture `admin_client` des tests).

```bash
# Login admin (récupère cookies de session + CSRF token)
curl -i -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"Sup3rSecret!Pass"}' \
  -c cookies.txt

# Récupérer le CSRF token depuis cookies.txt (cookie mefali_csrf)
CSRF=$(grep mefali_csrf cookies.txt | awk '{print $7}')

# Créer une source (URL avec utm_source qui doit être strippé)
curl -i -X POST http://localhost:8000/admin/sources \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" \
  -b cookies.txt \
  -d '{
    "url": "http://www.example.com/doc/?utm_source=newsletter",
    "title": "Document Test",
    "publisher": "ACME"
  }'
```

Attendu :
- HTTP 201
- `source.canonical_url == "https://example.com/doc"` (https forcé, www. retiré, utm_source retiré, slash final retiré).
- `source.verification_status == "pending"`.
- `head_warning` à `null` (probe désactivé en route synchrone) ou message si activé.

### 2. Tentative de doublon → 409

Renvoyer la même requête (même URL, même page) → HTTP 409 avec :
```json
{
  "detail": {
    "code": "duplicate_source",
    "message": "Une source avec cette URL canonique et cette page existe déjà.",
    "existing_id": "<uuid>"
  }
}
```

### 3. URL invalide → 422

```bash
curl -i -X POST http://localhost:8000/admin/sources \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" \
  -b cookies.txt \
  -d '{"url":"not-a-url","title":"x","publisher":"y"}'
```

Attendu : HTTP 422 (validation Pydantic HttpUrl).

### 4. Accès non-admin → 403/401

```bash
curl -i http://localhost:8000/admin/sources \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/x","title":"t","publisher":"p"}' \
  -X POST
```

Attendu : HTTP 401 (no auth) ou 403 (auth non-admin).

### 5. GET /admin/sources/{id} → 200/404

```bash
curl -i -b cookies.txt http://localhost:8000/admin/sources/<id>
# 404 si UUID inconnu
curl -i -b cookies.txt http://localhost:8000/admin/sources/00000000-0000-0000-0000-000000000000
```

## Q1 — Single-admin mode strict (résolu Phase A)

Le module `app.catalog.sources.permissions.assert_can_verify` lève une
HTTPException(409, code="self_verification_forbidden") quand `actor_id ==
captured_by`. Le route `POST /admin/sources/{id}/verify` (US2, **différé en
P2**) appellera ce helper. Les tests unitaires `test_permissions.py`
couvrent les deux cas (auto-validation refusée, cross-admin OK).

## Régression F01–F06

- 332 tests passent (302 baseline + 30 nouveaux F07).
- Coverage globale : 86.56 % (≥ 80 % cible).
- Migration `0007_sources_canonical_url` applique `unaccent` + colonne
  `canonical_url` + trigger `BEFORE INSERT/UPDATE` qui copie `url` →
  `canonical_url` quand celle-ci est NULL (rétro-compatibilité avec
  `app.services.source_service.create_pending` F03).
- Adaptation tests F03 : URLs hardcodées rendues uniques pour respecter
  l'index `ux_source_canonical_url_page`.
