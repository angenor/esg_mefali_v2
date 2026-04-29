# F24 — Rapport de Conformité PDF (MVP)

**Branch**: `024-rapport-conformite-pdf` | **Date**: 2026-04-29
**Source**: `docs_et_brouillons/features/24-rapport-conformite-pdf.md`
**Dependencies**: F03 (sources), F04 (audit/versioning), F09 (référentiels), F11 (entreprise), F23 (scoring multi-référentiels).

## Objectif MVP

Permettre à une PME authentifiée de **générer un rapport PDF de conformité** consolidant ses scores ESG sur 1..N référentiels publiés, avec couverture, score global, radar par pilier, lacunes et annexe sources F03.

Scope MVP livré (P1) :
- US1 — Sélection des référentiels.
- US2 — Visualisation : score global + radar par pilier (image PNG/SVG).
- US3 — Points forts (indicateurs couverts ≥ médiane).
- US4 — Lacunes simples (indicateurs manquants/sous seuils, pas de priorisation LLM).
- US6 — Annexe Sources auto-générée (réutilise `build_sources_appendix`).
- US7 — En-tête identité PME + horodatage + rapport_id unique.
- US8 — Génération en français.
- US9 — Téléchargement immédiat + historique persistant.

Reporté **[DEFERRED]** :
- US5 — Annexe méthodologie technique exhaustive (renvoi simple en MVP).
- Lacunes priorisées par impact LLM (US4 avancé).
- Layout multi-référentiels avancé / templating personnalisable.
- Liens hypertextes cliquables, polices custom intégrées.
- EN.

## User Stories MVP

| ID | Story | Test indépendant |
|----|-------|------------------|
| US1 | Choisir référentiels via API | POST `/me/rapports/conformite` body `{referentiels:["esg_mefali"]}` → 201 |
| US2 | Score global + radar par pilier | PDF contient image radar + score numérique |
| US3 | Section Points forts | PDF liste indicateurs couverts |
| US4 | Section Lacunes | PDF liste indicateurs manquants + raison |
| US6 | Annexe Sources | PDF contient annexe sources verifiees |
| US7 | Couverture identité PME | PDF page 1 = nom PME + date + UUID rapport |
| US8 | Texte FR | `lang='fr'` par défaut, contenu FR |
| US9 | Historique | GET `/me/rapports` liste les rapports, GET `/me/rapports/{id}/download` télécharge |

## Exigences fonctionnelles MVP

- **FR-001** : Service `app.rapports.service.generate_rapport(db, *, account_id, entity_type='entreprise', entity_id, referentiels, language='fr', user_id) -> dict` → renvoie `{rapport_id, file_path, generated_at, ...}` et persiste les bytes du PDF.
- **FR-002** : Stack PDF — **reportlab** programmatique (Python pur, pas de dépendance native système). MVP : pas de WeasyPrint pour éviter cairo/pango sur dev macOS.
- **FR-003** : Rendering radar via **matplotlib** (Agg backend) → PNG embarqué via `reportlab.platypus.Image`.
- **FR-004** : Endpoint `POST /me/rapports/conformite` body `{entity_type?, entity_id, referentiels:[code], language?}` → 201 `{rapport_id, download_url, generated_at, referentiels}`. Synchrone.
- **FR-005** : Table `rapport_genere(id UUID pk, account_id UUID FK account, entity_type TEXT, entity_id UUID, referentiels TEXT[], language TEXT, file_path TEXT, file_size_bytes INT, score_snapshot_json JSONB, generated_at TIMESTAMPTZ, generated_by UUID FK account_user)`. RLS tenant_isolation (calque F23).
- **FR-006** : `GET /me/rapports` liste les rapports du PME.
- **FR-007** : `GET /me/rapports/{id}/download` retourne `application/pdf`.
- **FR-008** : Annexe sources via `build_sources_appendix` (F03). Sources déduites de `score_calculation.details_json.sources_used`.
- **FR-009** : Audit append-only via `record_audit` (entity_type='rapport_genere', field='generate').
- **FR-010** : Stockage : `settings.rapport_storage_dir` (défaut `var/rapports/{account_id}/{rapport_id}.pdf`).

## Exigences non-fonctionnelles

- **NFR-001** : Génération synchrone < 10s pour ESG Mefali + 3 référentiels.
- **NFR-002** : PDF lisible noir & blanc.
- **NFR-003** : Aucune fuite cross-tenant (RLS + filtre WHERE).
- **NFR-004** : Couverture tests ≥ 80 % sur le code F24 ajouté.

## Success Criteria

- **SC-001** : POST génère un PDF non vide téléchargeable.
- **SC-002** : Annexe sources liste les sources verifiées dédupliquées.
- **SC-003** : RLS empêche un PME B de lire un rapport PME A (404).
- **SC-004** : Score snapshot JSON présent → reproductibilité.
- **SC-005** : Audit log contient une ligne `rapport_genere/generate` par génération.

## Constitution gates

| Principe | Statut |
|----------|--------|
| P1 Sourçage | OK Annexe sources F03 |
| P2 RLS | OK tenant_isolation sur `rapport_genere` |
| P3 Audit | OK record_audit |
| P4 Versioning snapshot | OK score_snapshot_json + referentiel_version |
| P5 Money typé | N/A |
| P6 Pivot indicateur | OK |
| P7 Plateforme fermée | OK require_pme |
| P8 Édition manuelle | OK |
| P9 Tool LLM | N/A |
| P10 UX bottom sheet | N/A backend |
