# F22 — Manual Tests Log

**Feature**: 022-documents-upload-ocr
**Branch**: 022-documents-upload-ocr
**Date**: 2026-04-29

## Status

- ✅ Spec / Plan / Tasks / Analyze : verts (commit `bf63d8a`)
- ✅ Migration `0015_f22_document_entreprise` : créée et chargée par alembic (head)
- ✅ Code livré : validators, ocr_service, documents_service, route /me/entreprise/documents, register dans main.py
- ✅ Unit tests : 35 verts, couverture 96.15 % (validators 100 %, ocr_service 94 %)
- ✅ Lint ruff : propre sur tout le code et les tests F22
- ⚠️ Tests d'intégration (`tests/integration/entreprise/test_documents_api.py`) : **NON exécutés** car la DB locale est dans un état incohérent **pré-existant à F22**.

## DB blocker pré-existant

Lors de l'exécution de `pytest tests/integration/entreprise/test_entreprise_endpoints.py` (test baseline F11) :

```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
relation "account_user" does not exist
```

`alembic current` rapporte `0013_f18_chat_message_embedding_index` mais
`\dt` montre des tables d'un schéma v1 totalement étranger (action_items,
action_plans, badges, ... aucune table `account`/`account_user`/`entreprise`).

→ La DB a été remplacée/corrompue avant F22. Aucun test d'intégration F11–F21
ne peut s'exécuter dans cet état. Ce blocker doit être résolu hors F22 (drop
et recréation de la base + `alembic upgrade head`), puis les tests
d'intégration F22 (déjà rédigés et marqués `@requires_db`) s'exécuteront
automatiquement.

## Smoke tests prévus (à rejouer après reset DB)

| # | Action | Attendu |
|---|--------|---------|
| 1 | Register PME + GET /me/entreprise + POST /me/entreprise/documents (PDF natif, type=statuts) | 201, ocr_status="done", text_content non vide |
| 2 | POST avec mime application/x-msdownload | 415, code=mime_not_allowed |
| 3 | POST avec doc_type="inconnu" | 422, code=doc_type_invalid |
| 4 | POST 51e document | 409, code=too_many_documents |
| 5 | GET /me/entreprise/documents | items[] avec uniquement docs du compte courant |
| 6 | GET /documents/{id}/download | bytes == fichier source, content-type == mime origine |
| 7 | DELETE /documents/{id} | 204 ; doc absent du listing ; row a deleted_at IS NOT NULL |
| 8 | Compte B GET /documents/{id_doc_A} | 404 not_found (RLS / filtre account_id) |
| 9 | Upload JPG | 201, ocr_status="deferred", ocr_error="mvp_image_unsupported" |
| 10 | Upload .docx ou .xlsx | 201, ocr_status="deferred", ocr_error="mvp_office_unsupported" |

## Commandes vérification

```bash
cd backend
.venv/bin/pytest -q tests/services/test_ocr_service.py \
                   tests/entreprise/test_documents_validators.py \
                   --cov=app.entreprise.documents_validators \
                   --cov=app.services.ocr_service
.venv/bin/ruff check app/entreprise app/services/ocr_service.py \
                     app/api/routes/entreprise_documents.py \
                     alembic/versions/0015_f22_document_entreprise.py
```

## Scope MVP livré

- US1 (upload + isolation account) : **livré** (impl + tests intégration prêts)
- US2 (list / get / download / delete soft) : **livré**
- US3 (extraction texte natif PDF, deferred sur image/Office) : **livré**

Pas de scope partiel volontaire ; le DB blocker n'est pas du scope F22.
