# F16 — Manual tests log

Date : 2026-04-29
Branch : 016-tools-visualisation-inline

## Backend tests

```bash
cd backend && source .venv/bin/activate
pytest -q tests/tools/ --no-cov
# Result: 126 passed (66 F15 + 60 F16)
```

## Coverage F16 backend

```bash
pytest -q tests/tools/test_viz_common.py tests/tools/test_show_kpi_card.py \
  tests/tools/test_show_radar_chart.py tests/tools/test_show_bar_chart.py \
  tests/tools/test_show_line_chart.py tests/tools/test_register_visualisation_tools.py \
  --cov=app.orchestrator.tools._viz_common \
  --cov=app.orchestrator.tools.show_kpi_card \
  --cov=app.orchestrator.tools.show_radar_chart \
  --cov=app.orchestrator.tools.show_bar_chart \
  --cov=app.orchestrator.tools.show_line_chart \
  --no-cov-on-fail
```

Coverage F16 = **98.64%** (target ≥ 80%).

| Module | Cover |
|--------|-------|
| _viz_common.py | 100% |
| show_kpi_card.py | 100% |
| show_radar_chart.py | 98% |
| show_bar_chart.py | 100% |
| show_line_chart.py | 97% |

## Lint

```bash
ruff check app/orchestrator/tools/{_viz_common,show_kpi_card,show_radar_chart,show_bar_chart,show_line_chart,__init__}.py \
  tests/tools/test_{viz_common,show_kpi_card,show_radar_chart,show_bar_chart,show_line_chart,register_visualisation_tools}.py
# All checks passed!
```

## Validation manuelle (REPL)

```python
from decimal import Decimal
from app.orchestrator.tools.show_kpi_card import ShowKpiCardPayload
p = ShowKpiCardPayload(
    label="Empreinte 2025", value=Decimal("45.00"), unit="tCO2e",
    delta={"value": Decimal("-12.0"), "period": "vs 2024"},
    source_ids=[42], alt_text="Description.",
)
# OK : payload validé.
```

Rejets attendus testés automatiquement :
- source_ids vide -> ValidationError
- balises HTML -> ValidationError
- série radar avec values != axes -> ValidationError
- bar > 20 -> ValidationError
- série line > 5 ou points > 50 -> ValidationError

## Scope MVP livré

P1 backend MVP minimal (4 tools obligatoires) :
- show_kpi_card (US1)
- show_radar_chart (US3)
- show_bar_chart (US4)
- show_line_chart (US5)

## Scope DEFERRED

P1 reportés (best-effort F16 follow-up) :
- show_progress_bar (US2)
- show_pie_chart / show_donut_chart (US6)
- show_timeline (US7)
- show_comparison_table (US8)
- show_match_card (US9)

P1 frontend (Vue stubs) DEFERRED :
- ShowKpiCard.vue, ShowRadarChart.vue, ShowBarChart.vue, ShowLineChart.vue
- Extension <ChatMessageRenderer> (T119)

P2 DEFERRED :
- show_map (US11)
- show_mermaid + mermaid_validator (US12)
- US13 réactivité historique (badge "données obsolètes")
