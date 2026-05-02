# F12 - Manual tests (a derouler humainement)

Date: 2026-04-29

## Pre-requis
- DB Postgres a jour : `cd backend && source .venv/bin/activate && alembic upgrade head`
- Backend lance : `uvicorn app.main:app --reload`
- Frontend lance (optionnel) : `pnpm dev`
- Compte PME enregistre + login (cookies + CSRF)

## US1 - Lister mes projets verts
- [ ] `GET /me/projets` -> 200, `{ items: [], total: 0, page: 1, limit: 25 }`.
- [ ] Filtre statut : `?statut=brouillon` -> filtre applique.
- [ ] Filtre type_impact : `?type_impact=mitigation_carbone` -> filtre applique.
- [ ] Pagination : `?page=2&limit=10`.

## US2 - Creer un projet
- [ ] `POST /me/projets` body minimal `{ "nom": "Eolien rural" }` -> 201, version=1, statut=null.
- [ ] Avec champs complets (types_impact, maturite, montant_recherche XOF, indicateurs) -> 201.
- [ ] Champ inconnu rejette -> 422 (extra=forbid).
- [ ] Currency JPY -> 422.

## US3 - Editer un projet
- [ ] `PATCH /me/projets/{id}` sans `If-Match` -> 428.
- [ ] `PATCH` avec `If-Match: 1` body `{"description": "x"}` -> 200, version=2, audit_log +1 ligne.
- [ ] `PATCH` avec `If-Match: 1` apres v2 -> 409, code=version_conflict.
- [ ] Sync LLM : ouvrir SSE `GET /me/projets/events`, faire un PATCH -> message `projet.updated` recu.

## US4 - Dupliquer
- [ ] `POST /me/projets/{id}/duplicate` -> 201, nom = "<orig> (copie)", statut=brouillon, audit "duplicated_from" present.
- [ ] Documents NON copies (verifier `GET /me/projets/{copy_id}/documents` vide).

## US5 - Supprimer
- [ ] `DELETE /me/projets/{id}` sur projet brouillon -> 204.
- [ ] Faire transition vers `finance` puis DELETE sans header -> 409 `delete_protected`.
- [ ] DELETE avec `X-Confirm: true` -> 204.
- [ ] Apres delete, `GET /me/projets/{id}` -> 404.

## US6 - Transition de statut
- [ ] `POST /me/projets/{id}/transition?to=en_recherche_financement` avec If-Match -> 200, statut updated, audit +1.
- [ ] Statut invalide -> 422.

## US7 - Documents projet
- [ ] `POST /me/projets/{id}/documents` multipart : PDF 1 MB, type=faisabilite -> 201.
- [ ] PDF 30 MB -> 413 size_too_large.
- [ ] Mime application/x-msdownload -> 415 mime_not_allowed.
- [ ] Type=invalid -> 422.
- [ ] `GET /me/projets/{id}/documents` -> liste contenant le doc.
- [ ] `GET .../documents/{doc_id}/download` -> 200, Content-Type=application/pdf, Content-Disposition.
- [ ] `DELETE .../documents/{doc_id}` -> 204.
- [ ] Uploader 50 docs : 51e -> 409 too_many_documents.

## RLS multi-tenant
- [ ] Compte A cree projet P1.
- [ ] Compte B login + `GET /me/projets/{P1}` -> 404 (RLS).
- [ ] Compte B `GET /me/projets/{P1}/documents/{doc}/download` -> 404.

## Audit
- [ ] Apres create + 2 patches + delete, requete admin sur audit_log :
  - 1 ligne `projet.created` (notes)
  - 2 lignes per-field changes
  - 1 ligne `projet.deleted`

## SSE
- [ ] `GET /me/projets/events` ouvre une connexion ; un PATCH dans un autre onglet emet `projet.updated`.

## SC validation
- SC-001 : creer 3 projets + duplicate + delete via UI < 10 min.
- SC-002 : 5 documents (PDF+Word+image) ok.
- SC-003 : SSE bidirectionnel verifie.
- SC-004 : transition audited.
- SC-005 : duplicate sans docs.
- SC-006 : RLS strict tenant A vs B.
