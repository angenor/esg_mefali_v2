# Feature Specification: F12 — Profil → Projets (CRUD, duplication, statuts, documents projet)

**Feature ID**: 012-profile-projets
**Phase**: 2 — Profil PME
**Dependencies**: F01 (foundations), F02 (auth + RLS), F04 (audit + versioning), F11 (entreprise)
**Branch**: `main` (sériel single-worktree)
**Date**: 2026-04-29

## Vision

L'entité **Projet** est l'objet réel de la candidature au financement (0..N par entreprise).
Cette feature livre la vue **Profil → Projets** côté PME : liste, création, édition, duplication,
suppression, gestion du statut, et upload des documents projet (étude de faisabilité, business plan,
étude d'impact, lettres de soutien, photos), avec audit per-field, versioning optimiste, RLS multi-tenant
et events SSE — strictement aligné sur les patterns de F11 (`/me/entreprise`).

## User Stories

### US1 — Lister mes projets verts (P1)
La PME peut lister ses projets via `GET /me/projets` (filtres `statut`, `type_impact`, pagination).

### US2 — Créer un projet (P1)
`POST /me/projets` ; champs identité, types_impact[], maturité, montant_recherche (Money typé), durée,
structure_financement[], indicateurs_impact_json, localisation projet, statut initial `brouillon`.

### US3 — Éditer un projet (P1)
`PATCH /me/projets/{id}` (If-Match version) avec audit per-field + version++ + event SSE.

### US4 — Dupliquer un projet (P2)
`POST /me/projets/{id}/duplicate` → copie tous les champs sauf id ; nom suffixé `(copie)` ;
statut forcé à `brouillon` ; **documents non copiés** (économie stockage) ; audit `duplicate`.

### US5 — Supprimer un projet (P2)
`DELETE /me/projets/{id}` (soft-delete via `deleted_at`). Garde-fou : si statut `finance` ou
`en_execution`, double confirmation côté UI (header `X-Confirm: true`). Audit `delete`.

### US6 — Gérer le statut (P1)
`POST /me/projets/{id}/transition?to=...` parmi {brouillon, en_recherche_financement, finance,
en_execution, cloture}. Transitions libres mais auditées.

### US7 — Uploader des documents projet (P1)
- `POST /me/projets/{id}/documents` (multipart) : type ∈ {faisabilite, business_plan, etude_impact,
  lettre_soutien, photo, autre} ; mime whitelist (PDF, Word, Excel, images) ; taille ≤ 25 MB ;
  ≤ 50 docs par projet.
- `GET /me/projets/{id}/documents` (liste).
- `GET /me/projets/{id}/documents/{doc_id}/download` (binary stream).
- `DELETE /me/projets/{id}/documents/{doc_id}`.
Stockage local : `backend/storage/projets/{account_id}/{projet_id}/{doc_id}.{ext}` derrière une
abstraction `Storage` (préparation MinIO/S3).

### US8 — Comportements LLM proactifs (P3, hors-scope)
Reporté à F17/F21.

## Exigences fonctionnelles

- **FR-001** — Enrichissement table `projet` (déjà créée en F01) :
  - `objectif_environnemental TEXT NULL`
  - `types_impact TEXT[] NULL` (multi-select)
  - `duree_mois INT NULL` (≥ 0)
  - `structure_financement_arr TEXT[] NULL` (`subvention, pret_concessionnel, equity, blending`)
  - `localisation_pays_iso2 CHAR(2) NULL`, `localisation_ville TEXT NULL`
  - Conserve colonnes historiques (`type_impact`, `structure_financement`, `localisation`).
  - Index `ix_projet_account_statut` sur `(account_id, statut)`.
  - CHECK statut ∈ {brouillon, en_recherche_financement, finance, en_execution, cloture}.
  - CHECK maturite ∈ {ideation, pre_faisabilite, pilote, scale, replication}.

- **FR-002** — Endpoints REST `/me/projets` : list, get, create, patch, duplicate, delete, transition.

- **FR-003** — Audit append-only via `record_audit(entity_type='projet')` per-field + versioning
  optimiste avec header `If-Match`. `source_of_change` ∈ {manual, llm, import, admin}.

- **FR-004** — Nouvelle table `document_projet` :
  `id`, `projet_id`, `account_id`, `name`, `original_filename`, `mime_type`, `size_bytes`,
  `type` enum (faisabilite, business_plan, etude_impact, lettre_soutien, photo, autre),
  `storage_path`, `uploaded_by`, `source_of_change`, `version`, `deleted_at`, timestamps.
  RLS active (account_id) ; index sur `projet_id`.

- **FR-005** — Endpoints documents (cf. US7).

- **FR-006** — Couche `Storage` (Protocol + impl `LocalStorage`). Future swap MinIO sans
  changement de signature.

- **FR-007** — Whitelist mime upload : PDF, Word (doc/docx), Excel (xls/xlsx), images (jpeg/png/webp).

- **FR-008** — `duplicate` : ne copie PAS les documents ; suffixe nom `(copie)` ; statut → `brouillon`.

- **FR-009** — Events SSE `projet.created/updated/deleted/transitioned/document.added/document.deleted`.

- **FR-010** — Validation `indicateurs_impact_json` : tableau d'objets `{key:str, value:number, unit:str}`.

- **FR-011** — Cascade suppression : marquage `archived` côté candidatures à implémenter dans F25.
  En F12 : la suppression projet est soft (`deleted_at`) et ne touche pas aux candidatures.

## Exigences non-fonctionnelles

- **NFR-001** — Upload PDF 10 MB < 5 s (FTTH local).
- **NFR-002** — Pagination liste : page=1, limit=25 par défaut, max 100.
- **NFR-003** — RLS strictement appliqué (`projet`, `document_projet`) — test contract.
- **NFR-004** — Couverture backend ≥ 80 % sur `app/projets/` et `app/storage/`.
- **NFR-005** — `indicateurs_impact_json` validé par schéma JSON strict.

## Constitution Check (Module 0)

| # | Principe | Status |
|---|----------|--------|
| P1 | Sourçage anti-hallucination | ✅ |
| P2 | Multi-tenant RLS | ✅ |
| P3 | Audit append-only | ✅ |
| P4 | Versioning + snapshot | ✅ |
| P5 | Money typé | ✅ |
| P6 | Pivot Indicateur | ✅ |
| P7 | Plateforme fermée PME/Admin | ✅ |
| P8 | Édition manuelle + sync LLM | ✅ |
| P9 | Tool-use LLM fiable | N/A |
| P10 | UX bottom sheet | ✅ |

## Success Criteria

- **SC-001** — Créer 3 projets + duplicate + delete via UI < 10 min.
- **SC-002** — Upload 5 documents (PDF + Word + image) OK.
- **SC-003** — Sync LLM bidirectionnelle (PATCH → SSE event).
- **SC-004** — Transition auditée (1 ligne `audit_log`).
- **SC-005** — `duplicate` produit projet identique sauf id/statut/nom, sans docs.
- **SC-006** — RLS : compte A ne voit pas projets/documents compte B.

## Hors-scope MVP

- OCR documents (F22).
- Versioning par document (post-MVP).
- Parent/child projets (F25).
- MinIO/S3 (post-MVP).
- Multilingue (FR uniquement).
- Antivirus clamav (post-MVP).

## Clarifications retenues (auto, sans humain)

Logged in `.cc-runtime/logs/clarify-12.log` :

- **CL-1** Cascade candidatures à la suppression projet : **NE PAS toucher aux candidatures en F12**
  (option la plus restrictive, principe P4 préserver snapshots). F25 introduira `archived`.
- **CL-2** Documents lors du duplicate : **non copiés** (recommandation du brouillon FR-008).
- **CL-3** Suppression d'un projet `finance`/`en_execution` : **autorisée avec header `X-Confirm: true`**
  obligatoire (option simple/testable, MVP).
- **CL-4** Limites docs : **50 docs × 25 MB hard limit** (FR-004 brouillon).
- **CL-5** Schéma `indicateurs_impact_json` : **liste d'objets `{key, value, unit}`** (option testable).
- **CL-6** Stockage : **local FS** sous `backend/storage/projets/...`, gitignored, abstraction `Storage`.
- **CL-7** Mime whitelist : PDF / doc / docx / xls / xlsx / jpeg / png / webp.
