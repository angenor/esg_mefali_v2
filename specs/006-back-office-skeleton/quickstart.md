# Quickstart — F06 Back-Office Skeleton

## Prérequis

- F01-F05 mergées sur `main` (DB + RLS + sources verified + audit + versioning + consents).
- `.env` configuré avec `DB_PASSWORD`, `JWT_SECRET`.
- Postgres dockerisé (`docker compose up -d db`).
- Backend `.venv` activé (`pip install -e backend[dev]`).
- Frontend `pnpm install` à jour.

## 1. Migration de démo

```bash
cd backend
alembic revision -m "F06 demo_indicator + pg_trgm"
# Edit revision : add demo_indicator + indices trigram + RLS
alembic upgrade head
```

Vérifier :

```bash
psql -h localhost -U esg -d esg_mefali -c "\d demo_indicator"
psql -h localhost -U esg -d esg_mefali -c "SELECT * FROM pg_extension WHERE extname='pg_trgm';"
```

## 2. Lancer backend

```bash
uvicorn app.main:app --reload --port 8000
```

Endpoints exposés (vérifier via `/docs`) :

- `GET/POST /admin/demo_indicator/`
- `GET/PUT /admin/demo_indicator/{id}`
- `POST /admin/demo_indicator/{id}/publish`
- `GET /admin/demo_indicator/{id}/versions`
- `GET /admin/search?q=...`
- `GET /admin/stats/catalog`

## 3. Lancer frontend

```bash
cd frontend
pnpm dev
```

Visiter `http://localhost:3000/admin` :

- Avec compte `admin` : layout admin + sidebar.
- Avec compte `pme` : 403 et redirection `/`.

## 4. Walk-through draft → published

1. Login admin.
2. Aller `/admin/demo_indicator` → cliquer "Nouveau".
3. Remplir nom, description, sélectionner une `Source` (statut `verified` si tu en as une, sinon créer une source en F03 puis la faire vérifier par un second admin — gate F03).
4. Sauvegarder en `draft`. Observer la sauvegarde locale (devtools → localStorage `admin:draft:demo_indicator:new:<userId>`).
5. Sur la fiche, cliquer "Publier" :
   - Si la source est `pending` → 422 listant la source manquante.
   - Si verified → 200, statut `published`.
6. Vérifier `audit_log` :
   ```sql
   SELECT entity_type, action, source_of_change, user_id
   FROM audit_log
   WHERE entity_type='demo_indicator'
   ORDER BY timestamp DESC LIMIT 5;
   ```
   On doit voir `create`, `update`, `publish`, tous avec `source_of_change='admin'`.
7. Modifier l'objet `published` → confirmation "v2", sauvegarde → version 2 créée, ancienne en `outdated`.
8. `GET /admin/demo_indicator/{id}/versions` → 2 entrées, la plus récente en `published`, l'ancienne en `outdated`.

## 5. Tests

```bash
# backend
pytest backend/tests/contract/admin -v
pytest backend/tests/integration/admin -v
pytest backend/tests/unit/admin -v

# frontend
cd frontend
pnpm test:unit
pnpm test:component
pnpm test:e2e -- --grep "admin"
```

## 6. Ajouter une nouvelle entité catalogue (handoff F07/F08/F09/F20)

Dans `backend/app/<feature>/admin_registration.py` :

```python
from app.admin.registry import registry, EntitySpec
from .models import Source                # SQLAlchemy
from .schemas import SourceRead, SourceCreate, SourceUpdate
from .relations import sources_of as sources_relation

registry.register(EntitySpec(
    name="sources",
    table=Source,
    read_schema=SourceRead,
    create_schema=SourceCreate,
    update_schema=SourceUpdate,
    sources_relation=sources_relation,    # peut renvoyer [self] pour Source elle-même
    searchable_fields=("title", "publisher", "doi"),
    sidebar_section="Sources",
))
```

L'inclusion du registry suffit ; aucun nouveau routeur, aucun composant Vue à dupliquer.

## 7. Smoke check final

- [ ] `/admin` accessible admin, 403 PME.
- [ ] CRUD demo_indicator complet (create draft, update, publish, edit→v2).
- [ ] Pagination cursor visible avec ≥ 51 entités (charger fixture).
- [ ] `/admin/search?q=test` renvoie résultats groupés.
- [ ] `/admin/stats/catalog` renvoie compteurs par section.
- [ ] `audit_log` contient bien toutes les mutations admin.
- [ ] LocalStorage draft restaure après refresh.
- [ ] If-Match mismatch → 412.
