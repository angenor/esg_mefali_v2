# Manual Tests — F24 Rapport Conformité PDF

Date: 2026-04-29
Branch: 024-rapport-conformite-pdf

## Smoke local

```bash
cd backend && .venv/bin/python -c "
import uuid
from datetime import UTC, datetime
from app.rapports.radar import render_radar_png, is_png
from app.rapports.pdf_builder import build_pdf, is_pdf, RapportPayload, ReferentielSection, IndicatorEntry

png = render_radar_png({'E': 70, 'S': 80, 'G': 60})
assert is_png(png) and len(png) > 100

payload = RapportPayload(
    rapport_id=uuid.UUID('00000000-0000-0000-0000-000000000001'),
    entreprise_name='Acme SA',
    generated_at=datetime(2026,4,29,10,0,tzinfo=UTC),
    language='fr',
    sections=[ReferentielSection(
        code='ESG_MEFALI', version=1, score_global=72.5, coverage_ratio=0.8,
        scores_by_pillar={'E':70,'S':75,'G':72},
        points_forts=[IndicatorEntry(code='IND01', pillar='E', contribution=80.0)],
        lacunes=[IndicatorEntry(code='IND02', pillar='S', reason='value_absent')],
    )],
    sources_appendix_md='# Annexe Sources\n\n- ACME report — World Bank — v1\n',
)
pdf = build_pdf(payload)
assert is_pdf(pdf) and len(pdf) > 1000
print('OK PDF', len(pdf), 'bytes')
"
```

Résultat : OK PDF ~58 KB.

## Tests automatiques

```bash
.venv/bin/pytest tests/rapports/ --cov=app.rapports
```

- **56 tests passés**, 0 échec.
- Couverture totale module `app.rapports` : **82.35 %** (>=80 % requis).
  - radar.py : 100 %
  - pdf_builder.py : 98 %
  - schemas.py : 97 %
  - service.py : 69 % (paths DB + write filesystem couverts en intégration future)
  - router.py : 44 % (tests auth gate uniquement ; endpoints exigent JWT PME)

## Régression

```bash
.venv/bin/pytest tests/scoring tests/rapports tests/test_health.py
```

- **127 passés**, 0 échec.

## Endpoints exposés (vérifié via /openapi.json)

- `POST /me/rapports/conformite` (201, body `RapportCreateIn`).
- `GET /me/rapports` (200, `RapportListOut`).
- `GET /me/rapports/{rapport_id}/download` (FileResponse application/pdf).

## À tester manuellement après migration DB (out-of-scope MVP unitaire)

- [ ] `alembic upgrade head` crée la table `rapport_genere` avec RLS.
- [ ] POST avec un JWT PME génère un PDF + ligne `rapport_genere` + ligne `audit_log`.
- [ ] GET list ne renvoie que les rapports du tenant.
- [ ] GET download renvoie 404 quand rapport_id appartient à un autre PME.
- [ ] GET download renvoie le bon fichier sinon (Content-Type application/pdf).
