# F09 — Manual tests log

Branch : `009-catalog-referentiels-indicateurs`
Date   : 2026-04-29

## Backend smoke

```bash
docker ps --filter name=esg_mefali_postgres
# → Up (healthy)

cd backend && source .venv/bin/activate
alembic upgrade head
# → Running upgrade 0008 -> 0009_f09_catalog OK
```

DB tables / EXCLUDE constraints :

```text
indicateur 0
referentiel 0
referentiel_indicateur 0
critere 0
document_requis 0
facteur_emission 0
indicateur_source 0
referentiel_source 0
EXCLUDE: ['template_logical_no_overlap', 'indicateur_logical_no_overlap',
          'referentiel_logical_no_overlap', 'critere_logical_no_overlap',
          'document_requis_logical_no_overlap', 'facteur_emission_logical_no_overlap']
```

## Routes loaded

`from app.main import app` → `97 routes` (vs 87 baseline F08).
New `/admin/indicateurs`, `/admin/referentiels`, `/admin/criteres`,
`/admin/documents-requis`, `/admin/facteurs-emission` mounted before generic
`crud_router`.

## Test runs

| Run | Command | Result |
|---|---|---|
| Baseline (F01-F08) | `pytest` | 368 passed, 5 skipped |
| DSL parser/sandbox | `pytest tests/unit/catalog/criteres` | 18 passed |
| F09 catalog | `pytest tests/integration/catalog tests/unit/catalog tests/integration/admin/test_audit_versioning_chain_f09.py tests/integration/admin/test_rls_catalogue_f09.py` | 60 passed |
| Full suite | `pytest --cov` | 422 passed, 5 skipped, coverage **83.08 %** |
| Ruff | `ruff check .` | All checks passed |

## F04 EXCLUDE regression check

After re-applying F09 :

- `indicateur_logical_no_overlap` ✅
- `critere_logical_no_overlap` ✅
- `facteur_emission_logical_no_overlap` ✅
- `template_logical_no_overlap` ✅ (preserved untouched)

Test `tests/integration/test_versioning_overlap.py::test_overlap_rejected_per_table[*]`
adapted to the new schema (code/pillar NOT NULL, source_id on facteur_emission +
critere) — all 4 parametrized cases pass.

## Seed

```bash
python -m app.scripts.seed_f09_minimal
# Seed OK : referentiel=<uuid>, facteur=<uuid>
```

## Smoke helpers

```python
from app.catalog.referentiels.service import get_referentiel
get_referentiel(db, "ESG_BASE")
# → published v1 (post-seed)

from app.catalog.facteurs_emission.lookup import get_facteur
get_facteur(db, "ELEC")
# → world facteur (pays_iso2 IS NULL)
```

## Notes

- F09 modifie le schéma F01 placeholder (`indicateur` etc.) : nouvelles colonnes
  obligatoires (`code`, `pillar`), suppression de `source_id` direct au profit
  d'une jonction `indicateur_source`. La downgrade F09 recrée les placeholders
  pour préserver le chemin de downgrade jusqu'à la base.
- Vues `v_<entity>_verified` recréées avec la nouvelle topologie (DISTINCT JOIN
  via la jonction pour `v_indicateur_verified`).
- Frontend Nuxt (T017-T020, T036-T037, T047-T048, T052, T065, T070-T071) : non
  livré — backend complet, à compléter en phase suivante.
- Tests E2E Playwright différés.
