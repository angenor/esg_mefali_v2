# Quickstart — F08 Catalogue Fonds, Intermédiaires & Offres

## Pré-requis

- Backend `.venv` actif (Python 3.12+).
- Postgres+pgvector dockerisé (`docker compose up -d db`).
- Frontend `pnpm install` exécuté.
- F01–F07 mergées.

## 1. Migration

```bash
cd backend
source .venv/bin/activate
alembic upgrade head    # applique 008_xxxx_catalog_fonds_offre
```

## 2. Lancer backend & frontend

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && pnpm dev    # http://localhost:3000
```

## 3. Smoke admin (curl)

```bash
ADMIN_TOKEN="<jwt-admin>"

# 3.1 Créer un Fonds GCF (draft)
curl -X POST http://localhost:8000/admin/fonds/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GCF",
    "organisation": "Green Climate Fund",
    "type": "multilateral",
    "thematique": ["climat","adaptation","attenuation"],
    "instruments": ["don","prêt concessionnel","garantie"],
    "plafond_money": {"amount":"250000000","currency":"USD"},
    "plancher_money": {"amount":"10000000","currency":"USD"},
    "eligibilite_geo": ["CI","SN","BJ","BF","ML","NE","TG","GW"],
    "submission_mode": "rolling",
    "criteres_json": [
      {"key":"min_project_size","operator":"min","value":"10000000","unit":"USD","source_id":"<gcf-policy-source-uuid>"}
    ],
    "documents_requis_json": [
      {"document_id":"funding_proposal","label":"Funding Proposal","type":"technique","required":true}
    ],
    "frais_json": {},
    "delais_json": {"instruction_jours": 365},
    "source_ids": ["<gcf-policy-source-uuid>"]
  }'

# 3.2 Publier (publish gate vérifie source verified)
curl -X POST http://localhost:8000/admin/fonds/{id}/publish \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "If-Match: <etag>"

# 3.3 Créer Intermédiaire BOAD (draft → published)
curl -X POST http://localhost:8000/admin/intermediaires/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BOAD",
    "type": "NIE",
    "pays": ["BJ","BF","CI","ML","NE","SN","TG","GW"],
    "frais_json": {"origination_pct": 1.5, "marge_pct": 2.0},
    "delais_json": {"instruction_jours": 90, "decaissement_jours": 60},
    "criteres_json": [
      {"key":"min_project_size","operator":"min","value":"2000000","unit":"USD","source_id":"<boad-source>"}
    ],
    "documents_requis_json": [
      {"document_id":"business_plan","label":"Business Plan","type":"financier","required":true}
    ],
    "source_ids": ["<boad-source>"]
  }'

# 3.4 Créer Accreditation BOAD ↔ GCF
curl -X POST http://localhost:8000/admin/accreditations/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "intermediaire_id": "<boad-id>",
    "fonds_id": "<gcf-id>",
    "valid_from": "2018-03-01",
    "plafond_money": {"amount":"500000000","currency":"USD"},
    "source_id": "<gcf-board-doc-source>"
  }'

# 3.5 Créer Offre "GCF via BOAD"
curl -X POST http://localhost:8000/admin/offres/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fonds_id": "<gcf-id>",
    "intermediaire_id": "<boad-id>",
    "name": "GCF via BOAD",
    "accepted_languages": ["fr","en"],
    "criteres_offre_specifiques": [],
    "documents_specifiques": [],
    "frais_specifiques": {},
    "delais_specifiques": {},
    "source_ids": ["<gcf-policy-source-uuid>"]
  }'

# 3.6 Lire le calcul effective
curl http://localhost:8000/admin/offres/{offre-id}/effective \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Réponse attendue (extrait) :
# {
#   "fonds_layer": { "criteres": [{"key":"min_project_size","operator":"min","value":"10000000",...}], ... },
#   "intermediaire_layer": { "criteres": [{"key":"min_project_size","operator":"min","value":"2000000",...}], ... },
#   "criteres_effectifs": [{"key":"min_project_size","operator":"min","value":"10000000","unit":"USD",...}],  // max(10M, 2M)
#   "documents_effectifs": [...],   // UNION
#   "frais_effectifs": {"amount":"...","currency":"..."},
#   "delais_effectifs_jours": 455,
#   "accepted_languages": ["fr","en"],
#   "deadline": null,
#   "effective_warning": []
# }

# 3.7 Comparateur
curl http://localhost:8000/admin/fonds/{gcf-id}/intermediaires \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 3.8 Bulk recheck
curl -X POST http://localhost:8000/admin/offres/recheck-status \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 4. Smoke PME (catalog public)

```bash
PME_TOKEN="<jwt-pme>"

# Liste offres publiques (exclut draft/archived/outdated)
curl http://localhost:8000/catalog/offres?pays=CI \
  -H "Authorization: Bearer $PME_TOKEN" | jq

# Détail Offre avec effective embedded
curl http://localhost:8000/catalog/offres/{offre-id} \
  -H "Authorization: Bearer $PME_TOKEN" | jq
```

## 5. Tests

```bash
# Backend
cd backend && pytest -v tests/unit/test_effective_calculator.py
pytest -v tests/integration/test_admin_offres.py

# Frontend
cd frontend && pnpm test:unit
pnpm test:e2e   # Playwright smoke
```

## 6. UI admin — flux

1. `/admin/fonds` → liste paginée + recherche trigram + bouton "+ Nouveau" → bottom sheet.
2. `/admin/fonds/[id]` → détail + bouton "Modifier" (bottom sheet) + bouton "Publier" (publish gate).
3. `/admin/fonds/[id]/comparator` → tableau aligné multi-Offres dérivées.
4. `/admin/intermediaires` → idem.
5. `/admin/accreditations` → liste filtrée par fonds/inter/active_at + création via bottom sheet.
6. `/admin/offres` → liste avec badge `needs_refresh` → action "Actualiser" → POST `/refresh`.
7. `/admin/offres/[id]` → vue `EffectiveTree` arbre 2 niveaux avec `effective_warning` mis en évidence.

## 7. Observabilité

- Logs FastAPI (uvicorn) — chaque endpoint admin trace `audit_log` avec diff.
- `audit_log` consultable via `GET /admin/audit?entity=offre&id={id}` (F04 endpoint existant).
