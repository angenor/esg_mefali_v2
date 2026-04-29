# Tasks: Attestation Vérifiable (F30)

**Input**: Design documents from `/specs/030-attestation-verifiable/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: TDD requis (≥ 80 % de couverture sur signature et vérification).

**Organization**: tâches groupées par user story.

## Format

`- [ ] [TaskID] [P?] [Story?] Description avec chemin de fichier`

## Phase 1 — Setup

- [ ] T001 Créer le module `backend/app/attestations/` avec un `__init__.py` vide.
- [ ] T002 Créer le squelette du dossier de tests `backend/tests/attestations/__init__.py`.

## Phase 2 — Foundational (bloquant)

- [ ] T010 Créer la migration Alembic `backend/alembic/versions/0020_f30_attestations.py` avec la table `attestations`, les indices et la policy RLS définis dans `data-model.md`.
- [ ] T011 [P] Créer le modèle SQLAlchemy `backend/app/models/attestation.py` (classe `Attestation`).
- [ ] T012 [P] Créer le script `backend/app/scripts/generate_attestation_keys.py` qui génère une paire Ed25519 et imprime la seed hex à coller dans `.env`.
- [ ] T013 [P] Étendre `backend/app/config.py` (settings actuel) pour exposer `attestation_private_key_hex: str | None` et `attestation_storage_root: str` (default : `./var/attestations`).

## Phase 3 — User Story 1 : Générer une attestation signée (P1)

**Goal** : `POST /me/attestations` retourne une attestation persistée + PDF + signature.
**Independent test** : `pytest backend/tests/attestations/test_router_me.py::test_generate_*`.

- [ ] T020 [P] [US1] Tests `backend/tests/attestations/test_crypto.py` : `canonicalize`, `compute_hash`, `sign`, `verify` (round-trip + tampering rejet).
- [ ] T021 [P] [US1] Tests `backend/tests/attestations/test_pdf_builder.py` : génération renvoie un fichier PDF non vide avec QR.
- [ ] T022 [US1] Implémenter `backend/app/attestations/crypto.py` : `load_private_key_from_env`, `load_public_key`, `pubkey_fingerprint`, `canonicalize_document`, `compute_document_hash`, `sign_document`, `verify_signature`. Lever `KeyNotConfiguredError` si seed manquante.
- [ ] T023 [US1] Implémenter `backend/app/attestations/pdf_builder.py` : `render_attestation_pdf(attestation_dict, qr_url) -> bytes` avec `reportlab` + `qrcode`.
- [ ] T024 [US1] Implémenter `backend/app/attestations/schemas.py` : `GenerateRequest`, `RevokeRequest`, `AttestationOut`, `PublicVerification`, `PubkeyOut` (Pydantic v2, `extra='forbid'`).
- [ ] T025 [US1] Implémenter `backend/app/attestations/service.py::AttestationService.generate(...)` : lit scores existants, construit document canonique, signe, génère PDF, persiste via `LocalStorage`, insère row, journalise `attestation.generated` via `record_audit`. 422 si scores absents, 503 si clé non configurée.
- [ ] T026 [US1] Implémenter `backend/app/attestations/router.py::POST /me/attestations` (FastAPI, `Depends(current_account)`).
- [ ] T027 [US1] Brancher le router dans `backend/app/main.py` (`include_router`).
- [ ] T028 [US1] Tests d'intégration `backend/tests/attestations/test_router_me.py::test_generate_*` (succès, scores manquants → 422, clé absente → 503).

## Phase 4 — User Story 2 : Page publique de vérification (P1)

**Goal** : `GET /verify/{public_id}` (HTML + JSON) + `GET /verify/_pubkey`.
**Independent test** : `pytest backend/tests/attestations/test_router_verify.py`.

- [ ] T030 [US2] Implémenter `AttestationService.get_public(public_id)` : lookup hors RLS, retourne `PublicVerification` (statut calculé).
- [ ] T031 [US2] Implémenter `AttestationService.read_pdf_bytes(attestation)` à partir de `LocalStorage`.
- [ ] T032 [US2] Implémenter `router.GET /verify/_pubkey` retournant `pubkey_hex`, `pubkey_fingerprint`, `algorithm='ed25519'`.
- [ ] T033 [US2] Implémenter `router.GET /verify/{public_id}/json` (non auth) retournant `PublicVerification`.
- [ ] T034 [US2] Implémenter `router.GET /verify/{public_id}` (HTML) via `Jinja2Templates` (template minimaliste `backend/app/attestations/templates/verify.html`).
- [ ] T035 [US2] Implémenter `router.GET /verify/{public_id}/download` retournant `application/pdf` du fichier original.
- [ ] T036 [US2] Ajouter un middleware/filtre rate-limit IP simple (compteur in-memory, 60 req/min) appliqué aux routes `/verify/*`.
- [ ] T037 [US2] Tests `backend/tests/attestations/test_router_verify.py` : 200 active/expired/revoked, 404 inconnu, 429 sur burst, vérification externe avec `pubkey_hex`.

## Phase 5 — User Story 3 : Révocation par la PME (P1)

- [ ] T040 [US3] Implémenter `AttestationService.revoke_by_pme(account, attestation_id, reason)` : 404 si autre tenant (RLS), 409 si déjà révoquée, journalise `attestation.revoked` (`source_of_change='manual'`).
- [ ] T041 [US3] Implémenter `router.POST /me/attestations/{id}/revoke`.
- [ ] T042 [US3] Tests `backend/tests/attestations/test_router_me.py::test_revoke_*`.

## Phase 6 — User Story 4 : Révocation par un admin (P1)

- [ ] T050 [US4] Implémenter `AttestationService.revoke_by_admin(admin_account, attestation_id, reason)` : journalise `attestation.revoked` (`source_of_change='admin'`).
- [ ] T051 [US4] Implémenter `router.POST /admin/attestations/{id}/revoke` avec `require_role('admin')`.
- [ ] T052 [US4] Tests `backend/tests/attestations/test_router_admin.py`.

## Phase 7 — User Story 5 : Historique attestations (P2)

- [ ] T060 [US5] Implémenter `AttestationService.list_for_account(account, limit, offset)` (RLS) avec statut calculé.
- [ ] T061 [US5] Implémenter `router.GET /me/attestations` + `router.GET /me/attestations/{id}/download`.
- [ ] T062 [US5] Tests `backend/tests/attestations/test_router_me.py::test_list_*`.

## Phase 8 — User Story 6 : Expiration (P2)

- [ ] T070 [US6] Implémenter `backend/app/attestations/jobs.py::expire_attestations()` (CLI) : log structuré, pas de mutation.
- [ ] T071 [US6] Test unitaire `backend/tests/attestations/test_service.py::test_status_calculation`.

## Phase 9 — Polish & Cross-cutting

- [ ] T080 Vérifier `pytest --cov=app/attestations` ≥ 80 %.
- [ ] T081 Lint backend (`ruff check backend/app/attestations`).
- [ ] T082 Vérifier non-régression F23/F29 (`pytest backend/tests/scoring backend/tests/credit -q`).

## Dependencies

- Phase 1 → Phase 2 → Phase 3 → (Phase 4, Phase 5 en parallèle) → Phase 6 → (Phase 7, Phase 8) → Phase 9.
- US1 livre l'MVP. US2 requise pour la valeur métier. US3/US4 requises pour la confiance.

## Parallel Opportunities

- T011, T012, T013 parallélisables une fois T010 prêt.
- T020, T021 (tests) parallélisables.

## Implementation Strategy

1. MVP minimal vert : Phases 1-3 (génération signée + persistance + audit).
2. Vérifiable de l'extérieur : Phase 4 (page publique).
3. Confiance : Phases 5-6 (révocation PME et admin).
4. Bonus : Phases 7-8 (historique + expiration informationnelle).
5. Polish : Phase 9.

## Deferred (post-MVP)

- Frontend Nuxt riche.
- Tools LLM `generate_attestation` / `revoke_attestation`.
- Intégration F26.
- Multi-langue.
- Notifications de révocation.
- Rotation automatique des clés.
