# Quickstart — F09

## Setup local

```bash
cd backend
source .venv/bin/activate
alembic upgrade head        # applique la migration F09
pytest tests/catalog/       # tous tests F09 verts
```

```bash
cd frontend
pnpm install
pnpm dev                    # http://localhost:3000/admin/catalogue/indicateurs
```

## Seed minimal (F09)

Script : `backend/app/scripts/seed_f09_minimal.py`

1. Sources verified (F07) :
   - `ADEME Base Carbone v23` (verified)
   - `GCF Project Eligibility Manual 2024` (verified)
2. 3 Indicateurs publiés :
   - `WASTE_RECYCLED_PCT` (E, percentage)
   - `EMPLOYEES_HEADCOUNT` (S, numeric)
   - `ANTI_CORRUPTION_POLICY` (G, boolean)
3. 1 Référentiel `ESG_MEFALI_V1` (interne) avec poids 30/30/40 sur les 3 indicateurs, somme = 100, formula `weighted_sum`, sources GCF.
4. 2 Critères :
   - blocking : `EMPLOYEES_HEADCOUNT <= 200` (owner=fonds BOAD)
   - warning : `WASTE_RECYCLED_PCT >= 30` (owner=referentiel ESG_MEFALI_V1)
5. 1 Document Requis : `Statuts juridiques` (juridique, owner=fonds BOAD)
6. 5 Facteurs d'émission ADEME :
   - `ELEC_MIX_CI_KWH` 0.456 kgCO2e/kWh CI scope 2
   - `DIESEL_TRANSPORT_L` 2.491 kgCO2e/L mondial scope 1
   - `GASOLINE_TRANSPORT_L` 2.31 kgCO2e/L mondial scope 1
   - `WASTE_LANDFILL_KG` 0.5 kgCO2e/kg mondial scope 3
   - `ELEC_MIX_FR_KWH` 0.057 kgCO2e/kWh FR scope 2

## Smoke tests

```bash
# Helper get_referentiel
python -c "from app.catalog.referentiels.service import get_referentiel; print(get_referentiel('ESG_MEFALI'))"

# Helper get_facteur
python -c "from app.catalog.facteurs_emission.lookup import get_facteur; print(get_facteur('ELEC_MIX_CI_KWH', pays_iso2='CI'))"

# DSL evaluate
python -c "from app.catalog.criteres.dsl import evaluate; print(evaluate({'op':'>=','left':{'indicateur':'WASTE_RECYCLED_PCT'},'right':{'literal':30}}, {'WASTE_RECYCLED_PCT': 45}))"
```

## Critères d'acceptance MVP

- `pytest -k publish_validator` vert : SC-004.
- `pytest -k dsl_parser` vert (10 cas) : SC-005.
- `pytest -k rls_catalogue` vert : FR-011.
- `pnpm test:e2e indicateurs.crud.spec` vert : US1 end-to-end.
