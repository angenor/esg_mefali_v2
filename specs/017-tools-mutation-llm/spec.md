# Feature Specification: F17 — Tools de Mutation LLM

**Feature Branch**: `017-tools-mutation-llm`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F17 — Le LLM doit pouvoir effectuer des actions métier (mutations) via tools structurés, avec garde-fous: confirmation destructive, audit log, RLS scoped, jamais sur catalogue.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mise à jour du profil entreprise via langage naturel (Priority: P1)

Une PME demande au LLM "mon CA est de 250M FCFA et j'ai 75 employés" — le LLM extrait et invoque `update_company_profile`. Les champs sont mis à jour, un audit log est écrit avec source_of_change='llm', et l'UI réagit en temps réel.

**Why this priority**: Diminue la friction de saisie. Cas d'usage central de la plateforme PME conversationnelle.

**Independent Test**: Envoyer un message texte → vérifier que l'entreprise a été mise à jour, qu'une ligne audit_log existe avec source_of_change='llm', et qu'un événement EventBus a été émis.

**Acceptance Scenarios**:

1. **Given** une PME connectée avec entreprise existante, **When** elle invoque `update_company_profile({taille_effectifs: 75})`, **Then** l'entreprise est mise à jour, un audit log est écrit, l'événement `entity_updated` est émis.
2. **Given** une mutation sur un champ inexistant, **When** le tool est invoqué, **Then** la validation Pydantic refuse la mutation avec un message clair.

---

### User Story 2 - CRUD projet via LLM (Priority: P1)

Une PME peut dire "crée un projet de panneaux solaires de 50 MW dans le nord du Sénégal pour 5M EUR" → le LLM crée un projet en brouillon. Elle peut aussi mettre à jour un projet ou le supprimer (avec confirmation).

**Why this priority**: Création de projet est l'action métier la plus fréquente après la complétion du profil.

**Independent Test**: Invoquer `create_project` avec un payload valide → projet créé en brouillon. Invoquer `update_project` → mise à jour partielle. Invoquer `delete_project` sans confirmation → demande de confirmation.

**Acceptance Scenarios**:

1. **Given** une PME, **When** `create_project({nom, description, montant_money})` est invoqué, **Then** un projet est créé en statut brouillon, audit log écrit.
2. **Given** un projet existant, **When** `update_project(id, {nom: 'X'})` est invoqué, **Then** le projet est mis à jour avec snapshot avant/après dans audit_log.
3. **Given** un projet existant, **When** `delete_project(id)` est invoqué sans `confirmed=true`, **Then** le tool retourne un payload demandant au LLM d'invoquer `ask_yes_no`.
4. **Given** un projet existant, **When** `delete_project(id, confirmed=true)` est invoqué, **Then** le projet (et candidatures liées) sont supprimés, audit log écrit.

---

### User Story 3 - CRUD candidature via LLM (Priority: P1)

Une PME peut dire "candidate au GCF via BOAD pour mon projet panneaux" → le LLM crée la candidature.

**Why this priority**: Workflow candidatures = cœur de la valeur (financements).

**Independent Test**: `create_candidature(project_id, offre_id)` → candidature créée. `update_candidature_status` → statut changé. `delete_candidature(id, confirmed=true)` → supprimée.

**Acceptance Scenarios**:

1. **Given** un projet et une offre valides, **When** `create_candidature` est invoqué, **Then** une candidature est créée en statut `brouillon`.
2. **Given** une candidature, **When** `update_candidature_status(id, 'acceptee')`, **Then** le statut change, audit log avant/après.
3. **Given** une candidature, **When** `delete_candidature(id)` sans confirmation, **Then** demande de confirmation.

---

### User Story 4 - Confirmation systématique des actions destructives (Priority: P1)

Toute mutation destructive DOIT déclencher un `ask_yes_no` listant les conséquences. Sans `confirmed=true`, l'opération est rejetée par `@destructive`.

**Why this priority**: Garantie d'intégrité non négociable.

**Independent Test**: Invoquer `delete_project` sans `confirmed=true` → résultat structuré demandant confirmation. Avec `confirmed=true` → suppression OK.

**Acceptance Scenarios**:

1. **Given** un tool destructif, **When** invoqué sans `confirmed=true`, **Then** retourne `{requires_confirmation: true, message: '...', impact: [...]}`.
2. **Given** un tool destructif, **When** invoqué avec `confirmed=true`, **Then** la mutation s'exécute.

---

### User Story 5 - Aucune mutation possible sur le catalogue (Priority: P1)

Le registry de tools rôle PME ne contient AUCUN tool de mutation sur le catalogue (Fonds, Intermédiaires, Offres, Référentiels, Indicateurs, Sources, Skills, Templates).

**Why this priority**: Intégrité du catalogue = intégrité du référentiel ESG.

**Independent Test**: Lister les tools rôle PME → aucun tool nommé `update_referentiel`, `update_fonds`, etc.

**Acceptance Scenarios**:

1. **Given** un user PME, **When** il liste les tools de mutation, **Then** aucun tool catalogue n'est présent.
2. **Given** un LLM tente d'invoquer `update_referentiel`, **When** le registry PME est consulté, **Then** le tool n'existe pas → erreur claire.

---

### User Story 6 - Attacher un document à une entité (Priority: P2)

`attach_document(entity_type, entity_id, doc_id)` → liaison auditée.

**Acceptance Scenarios**:

1. **Given** un projet et un document, **When** `attach_document` est invoqué, **Then** la liaison est créée et auditée.

---

### User Story 7 - Recalculer un score ESG (Priority: P2)

`recompute_score(entity_id, referentiel_id)` → invoque service F23 (mock acceptable).

**Acceptance Scenarios**:

1. **Given** une PME, **When** `recompute_score` est invoqué, **Then** F23 est appelé.

---

### User Story 8 - Génération / révocation d'attestation (Priority: P2)

`generate_attestation(score_id)` ; `revoke_attestation(id, reason)` (destructif).

**Acceptance Scenarios**:

1. **Given** un score, **When** `generate_attestation`, **Then** F30 appelé.
2. **Given** une attestation, **When** `revoke_attestation(id, reason, confirmed=true)`, **Then** révoquée.

---

### User Story 9 - Génération de dossier candidature (Priority: P2)

`generate_dossier(candidature_id, language)` → F26.

**Acceptance Scenarios**:

1. **Given** une candidature complète, **When** `generate_dossier(...)`, **Then** F26 appelé.

---

### User Story 10 - UNDO court d'une mutation idempotente (Priority: P2)

`POST /me/audit-log/{id}/revert` annule une mutation idempotente dans les 10 secondes.

**Acceptance Scenarios**:

1. **Given** une mutation idempotente < 10s, **When** revert appelé, **Then** valeur précédente restaurée + nouveau audit log.
2. **Given** une mutation > 10s, **When** revert appelé, **Then** erreur 410 (expiré).
3. **Given** une mutation create/delete, **When** revert appelé, **Then** erreur 400 (non revertible).

### Edge Cases

- Tentative cross-tenant (user PME A invoque tool avec ID PME B) → 404 (RLS), audit log d'incident.
- Spam (>10 mutations LLM/min/user) → rate limit, erreur 429.
- Mutation avec champ extra non déclaré → validation Pydantic refuse (strict mode).
- Mutation avec FK invalide → erreur claire avant écriture DB.
- Tool destructif invoqué deux fois `confirmed=true` → second appel = 404 (idempotence).
- `generate_dossier` long (30s+) → MVP : appel synchrone avec timeout, message clair.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST exposer 11 tools de mutation déclarés via `@tool` avec schémas Pydantic stricts (`extra='forbid'`, types fermés, FK existence) :
  - `update_company_profile(fields)`
  - `create_project(fields)`, `update_project(id, fields)`, `delete_project(id, confirmed=False)`
  - `create_candidature(project_id, offre_id)`, `update_candidature_status(id, status)`, `delete_candidature(id, confirmed=False)`
  - `attach_document(entity_type, entity_id, doc_id)`
  - `recompute_score(entity_id, referentiel_id)`
  - `generate_attestation(score_id)`, `revoke_attestation(id, reason, confirmed=False)`
  - `generate_dossier(candidature_id, language)`
- **FR-002**: Le système MUST fournir un décorateur `@destructive` qui rejette toute exécution sans `confirmed=True` et retourne un payload demandant `ask_yes_no` au LLM.
- **FR-003**: Le système MUST fournir un décorateur `@audited` qui appelle `record_audit(...)` automatiquement avec `source_of_change='llm'`, snapshot avant/après, tool name, user_id.
- **FR-004**: Toutes les mutations MUST s'exécuter dans une session Postgres avec `app.current_account_id` set (RLS).
- **FR-005**: Pour chaque mutation réussie, l'EventBus MUST émettre `entity_updated` avec entity_type, entity_id, tool_name.
- **FR-006**: Le système MUST exposer `POST /me/audit-log/{id}/revert` qui restaure la valeur précédente pour mutations idempotentes < 10s.
- **FR-007**: Validation Pydantic stricte (`extra='forbid'`, types stricts, enums fermés, vérification FK).
- **FR-008**: Le sélecteur de tools (F14) MUST exposer les mutations contextuellement (Profil/Entreprise → update_company_profile ; Profil/Projets → CRUD projet ; Candidatures → CRUD candidature).
- **FR-009**: Le registry tools rôle PME MUST NOT contenir de tool mutation catalogue.
- **FR-010**: Le système MUST limiter à 10 mutations LLM/minute/user (429 au-delà).

### Non-Functional Requirements

- **NFR-001**: Latence d'une mutation simple < 500ms (P95).
- **NFR-002**: 100% des mutations auditées + 100% RLS appliqué.
- **NFR-003**: La confirmation destructive ne doit JAMAIS être contournable.
- **NFR-004**: Fenêtre UNDO strictement 10 secondes.

### Key Entities

- **Tool de mutation**: handler décoré `@tool @destructive? @audited`, schéma Pydantic d'entrée, payload structuré de sortie.
- **Audit log entry**: ligne `audit_log` (F04) avec `source_of_change='llm'`, `tool_name`, `entity_type`, `entity_id`, `old_value` (jsonb), `new_value` (jsonb), `user_id`, `created_at`.
- **EventBus event**: `entity_updated` consommé par UI (F13).
- **Tool registry PME**: ensemble exclusif de tools dispo pour rôle PME.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Les tools de mutation P1 (update_company_profile, CRUD projet, CRUD candidature, garde destructive, registry sans catalogue) fonctionnent end-to-end avec audit log + EventBus.
- **SC-002**: `delete_project` sans confirmation rejeté → après ask_yes_no positif → suppression OK (test e2e).
- **SC-003**: Tentative cross-tenant → 404, audit log d'incident.
- **SC-004**: UNDO `update_company_profile` rétablit l'avant-état en < 1s.
- **SC-005**: Tool catalogue absent du registry PME (test).
- **SC-006**: 95% des mutations P1 < 500ms backend.
- **SC-007**: 100% des mutations génèrent une ligne audit_log.
- **SC-008**: 0 fuite cross-tenant dans la suite de tests.

## Assumptions

- F04 (audit), F11 (entreprise), F12 (projets/candidatures), F14 (registry), F15 (ask_yes_no) sont mergés et stables.
- `record_audit` (F04) est disponible avec `source_of_change`.
- L'EventBus F13 est dispo (`emit('entity_updated', payload)`).
- F23/F26/F30 non livrés → tools P2 utiliseront stubs ou seront [DEFERRED].
- Le rôle user PME est connu via `current_user.role` et le compte via `current_user.account_id`.
- Rate limiting in-process acceptable en MVP, Redis post-MVP.

## Hors-scope MVP

- Mutations catalogue par admins via LLM.
- Multi-step transactions atomiques.
- Mutation différée.
- UNDO sur create/delete.
- Tools P2 (US6-US10) si budget dépassé — implémenter au moins US1-US5 (P1).
