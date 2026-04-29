# Quickstart — F16 Tools de Visualisation Inline

## Prérequis

- Branche : `016-tools-visualisation-inline`.
- F13/F14/F15 mergées sur main.
- Backend `.venv` activé : `cd backend && source .venv/bin/activate`.

## Smoke test backend

```bash
cd backend && source .venv/bin/activate
pytest -q tests/tools/test_show_kpi_card.py
pytest -q tests/tools/test_register_visualisation_tools.py
```

## Validation manuelle d'un payload (Python REPL)

```python
from decimal import Decimal
from app.orchestrator.tools.show_kpi_card import ShowKpiCardPayload

# OK
p = ShowKpiCardPayload(
    label="Empreinte 2025",
    value=Decimal("45.00"),
    unit="tCO2e",
    delta={"value": Decimal("-12.0"), "period": "vs 2024"},
    source_ids=[42],
    alt_text="Empreinte carbone 2025 : 45 tCO2e, -12% vs 2024.",
)
print(p.model_dump_json(indent=2))

# Rejet : pas de source_ids
try:
    ShowKpiCardPayload(
        label="x", value=Decimal("1"), unit="u",
        source_ids=[], alt_text="a",
    )
except Exception as e:
    print("REJECTED:", e)

# Rejet : XSS
try:
    ShowKpiCardPayload(
        label="<script>", value=Decimal("1"), unit="u",
        source_ids=[1], alt_text="a",
    )
except Exception as e:
    print("REJECTED:", e)
```

## Suite F16 complète

```bash
cd backend && source .venv/bin/activate
pytest -q tests/tools/ --cov=app/orchestrator/tools --cov-report=term-missing
ruff check app/orchestrator/tools/ tests/tools/
```

Cible couverture : ≥ 80 % sur `app/orchestrator/tools/show_*.py` et `_viz_common.py`.

## Démarrage app (vérifier l'enregistrement)

```python
from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools import register_response_tools, register_visualisation_tools

register_response_tools()       # F15
register_visualisation_tools()  # F16

assert "show_kpi_card" in TOOL_REGISTRY
assert "show_radar_chart" in TOOL_REGISTRY
print(sorted(TOOL_REGISTRY.keys()))
```

## Frontend (best-effort MVP)

```bash
cd frontend
pnpm dev
```

Le composant Vue `<ShowKpiCard>` doit s'afficher avec :
- valeur + unité grandes ;
- delta coloré ;
- pictogramme source cliquable (`<SourceCite :source-ids>`) ;
- `aria-label="{alt_text}"` + `role="img"`.

## Vérifier le bundle

```bash
cd frontend
pnpm build
ls -lh .output/public/_nuxt/ | head
# chart.js, leaflet, mermaid doivent être dans des chunks séparés
```
