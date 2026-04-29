# Quickstart — F07 Catalog Sources Management

## Pré-requis

- F01–F06 mergées sur `main` (ce qui est le cas).
- Postgres 16 + extension `unaccent` autorisée.
- `.venv` Python 3.11 activé pour le backend ; `pnpm` + Node 22 pour le frontend.

## Migration

```bash
cd backend
source .venv/bin/activate
alembic upgrade head   # applique 007_xxx_sources_indices_canonical.py
```

La migration :

- Crée `EXTENSION IF NOT EXISTS unaccent`.
- Ajoute `source.canonical_url TEXT`, backfill via fonction Python `canonicalize_url`, `NOT NULL`.
- Ajoute la contrainte `CHECK (verification_status <> 'verified' OR verified_by IS DISTINCT FROM captured_by)`.
- Crée `ux_source_canonical_url_page` (unique).
- Crée la colonne générée `search_vector` + index GIN.
- Indexes secondaires `idx_source_verification_status`, `idx_source_publisher`.

## Seed minimal (3 sources)

```bash
python -m app.scripts.seed_sources_demo
```

Le script crée 3 sources de référence (UEMOA, GCF, ADEME) et un compte admin secondaire (`admin2@esg-mefali.local`) si inexistant, puis vérifie 1 des 3 (cross-admin).

## Lancer le back

```bash
uvicorn app.main:app --reload --port 8000
```

Vérifier : `GET http://localhost:8000/api/admin/sources` (avec JWT admin).

## Lancer le front

```bash
cd frontend
pnpm install
pnpm dev   # http://localhost:3000
```

Pages clés :

- `/admin/sources` — liste filtrable.
- `/admin/sources/new` — formulaire de création.
- `/admin/sources/{id}` — édition.
- `/admin/sources/{id}/impact` — vue d'impact.
- `/admin/unsourced-claims` — claims non sourcés.
- `/sources/{id}` — page publique read-only (sans login).

## Scénario E2E manuel

1. Avec compte `admin@esg-mefali.local` : créer source "Taxonomie UEMOA 2024" (URL valide).
2. Tenter de la valider → erreur `409 SAME_USER_NOT_ALLOWED`.
3. Switch vers `admin2@...` → bouton "Valider" actif → cliquer → statut `verified`.
4. `GET /sources/{id}` (sans cookie) → page publique 200 avec header `X-Robots-Tag: noindex`.
5. Modifier `notes` → pas de bump version. Modifier `version` → bump (`current_version` += 1).
6. Marquer `outdated` → page publique reste accessible avec badge.
7. Tenter `DELETE` → refusé tant qu'objets dépendants. Cliquer "Impact" → compteurs.

## Tests

```bash
# backend
pytest -q app/tests/catalog/sources --cov=app/catalog/sources --cov-report=term-missing

# frontend (unit)
pnpm test

# E2E
pnpm exec playwright test tests/e2e/admin-sources.spec.ts
```

Cible coverage : ≥ 80%.
