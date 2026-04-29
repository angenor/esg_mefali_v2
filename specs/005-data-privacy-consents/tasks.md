# Tasks: F05 — Conformité Données Personnelles, Consentements & Devises

**Branch**: `005-data-privacy-consents` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Inputs** : research.md, data-model.md, contracts/openapi-privacy.yaml, contracts/openapi-fx.yaml, quickstart.md.

Légende : `[P]` = parallélisable (fichiers indépendants, pas de dépendance bloquante non terminée). `[USx]` = rattachement à une user story du spec.

---

## Phase 1 — Setup

- [ ] T001 [DEFERRED] Ajouter dépendances backend dans `backend/pyproject.toml` : `apscheduler>=3.10`, `httpx>=0.27`, `zipstream-ng>=1.7`, `cryptography>=42` ; mettre à jour `backend/.venv` via `uv pip install -e .[dev]`.
- [ ] T002 [DEFERRED] [P] Ajouter dépendances frontend dans `frontend/package.json` : `gsap@^3.12`, `@vueuse/core` (déjà présent — vérifier), `marked@^12` pour rendu Markdown politique ; `pnpm install`.
- [ ] T003 [DEFERRED partiel] [P] Étendre `.env.example` à la racine avec `EXCHANGERATE_API_KEY=`, `PURGE_PSEUDONYM_PEPPER=`, `FX_DEFAULT_DISPLAY_CURRENCY=XOF`, `FX_STALE_ALERT_DAYS=7` ; documenter dans `README.md`. (config.py charge déjà ces vars avec defaults non-bloquants.)
- [ ] T004 [DEFERRED] Ajouter validation au démarrage dans `backend/app/core/config.py` : `Settings` Pydantic charge `EXCHANGERATE_API_KEY` (str, ≥ 1) et `PURGE_PSEUDONYM_PEPPER` (str, hex 64 chars) ; faire échouer le boot si manquant.

---

## Phase 2 — Foundational (bloquant pour toutes les US)

- [x] T005 [P] Créer `backend/app/core/currencies.py` — enum `Currency` (XOF, EUR, USD, GHS, NGN, MAD, GBP), constante `PEG_FCFA_EUR = Decimal('655.957')`, helper `inverse_peg()`.
- [x] T006 [P] Créer `backend/app/core/pseudonymize.py` — fonction `pseudonymize(account_id: UUID) -> str` retourne `f"anon_{hmac_sha256(uuid.bytes, pepper).hexdigest()[:16]}"` ; lever si pepper absent.
- [x] T007 Migration Alembic `0005a_audit_purge_jobs.py` (au lieu de `005g_*`) — REPLACE FUNCTION `audit_log_immutable()` pour autoriser UPDATE colonne `user_id` uniquement quand `current_setting('app.purge_context', true) = 'on'`. Trigger `audit_log_immutable_trg` posé. Tests intégration verts.
- [x] T008 Migration `0005a_audit_purge_jobs.py` (combinée avec T007) — table `scheduled_job_run` + UNIQUE(job_name, run_date) + GRANT SELECT au rôle app_user (writes via migrator).
- [ ] T009 [DEFERRED] [P] Créer `backend/app/jobs/scheduler.py` — bootstrap APScheduler.
- [x] T010 [P] Créer `backend/app/services/audit_extension.py` — context manager `purge_context()` posant `SET LOCAL app.purge_context='on'`. Tests intégration verts.

---

## Phase 3 — User Story 4 : Type Money typé (P1) [foundationnel pour US5/US6]

**Goal** : `Money` Pydantic v2 + composable Nuxt utilisable de bout en bout.
**Independent test** : créer `Money(amount=Decimal('1000'), currency=Currency.XOF)`, sérialiser en JSON, hydrater côté front, rendre via `<MoneyDisplay>` ; payload avec devise hors enum est rejeté avec erreur claire.

- [x] T011 [P] [US4] Créer `backend/app/schemas/money.py` — `Money(BaseModel, model_config=ConfigDict(extra='forbid', frozen=True))`.
- [x] T012 [P] [US4] Test unitaire `backend/tests/unit/test_money.py` — 7 tests verts.
- [ ] T013 [DEFERRED] [P] [US4] Créer `frontend/composables/useMoney.ts`.
- [ ] T014 [DEFERRED] [P] [US4] Créer `frontend/components/money/MoneyDisplay.vue`.
- [ ] T015 [DEFERRED] [P] [US4] Test vitest `frontend/tests/unit/MoneyDisplay.spec.ts`.

---

## Phase 4 — User Story 5 : Taux de change quotidien (P1) [DEFERRED — toutes tâches]

**Goal** : peg sourcé + snapshot quotidien + fallback dernière valeur connue.
**Independent test** : `convert(1000 XOF, EUR)` ≈ 1.524 EUR, `convert(1000 XOF, USD)` cohérent jour J ; couper API → conversion répond toujours avec dernier taux.

- [ ] T016 [US5] Migration Alembic `005e_fx_rate.py` — table `fx_rate` (cf. data-model.md), index `(currency_from, currency_to, captured_at DESC)`, CHECK `currency_from <> currency_to`, RLS `USING (true)` SELECT public, INSERT via fonction SECURITY DEFINER `admin_insert_fx_rate(...)`.
- [ ] T017 [US5] Migration `005h_seed_peg_fcfa_eur.py` — INSERT `Source` (BCEAO décret) statut `verified` ; INSERT 2 lignes `fx_rate` peg `(EUR, XOF, 655.957, is_peg=true, peg_source_id=...)` et inverse `(XOF, EUR, 1/655.957, ...)`.
- [ ] T018 [P] [US5] Créer `backend/app/models/fx.py` — modèle SQLAlchemy 2.x `FxRate` mappé sur la table.
- [ ] T019 [P] [US5] Créer `backend/app/schemas/fx.py` — schéma Pydantic `FxRateOut` conforme `contracts/openapi-fx.yaml`.
- [ ] T020 [US5] Créer `backend/app/services/fx_service.py` — `get_rate(from, to, at?) -> Decimal` (peg court-circuit, sinon `SELECT ... ORDER BY captured_at DESC LIMIT 1`), `convert(money, to, at?) -> Money`.
- [ ] T021 [US5] Créer `backend/app/jobs/refresh_fx_rates.py` — `httpx.AsyncClient` GET `https://v6.exchangerate-api.com/v6/{KEY}/latest/EUR`, parse, INSERT lignes pour USD/GHS/NGN/MAD/GBP via `admin_insert_fx_rate`, wrappé `run_idempotent('refresh_fx_rates', ...)`.
- [ ] T022 [US5] Créer `backend/app/jobs/alert_stale_fx.py` — détecte N derniers `scheduled_job_run` failed consécutifs ≥ `FX_STALE_ALERT_DAYS`, log structuré + (placeholder) email admin.
- [ ] T023 [US5] Enregistrer les jobs dans `backend/app/jobs/scheduler.py` : `refresh_fx_rates` cron `0 3 * * *`, `alert_stale_fx` cron `15 3 * * *`.
- [ ] T024 [P] [US5] Créer `backend/app/api/fx.py` — `GET /fx/rates`, `POST /fx/convert` conformes au contrat OpenAPI ; routeur monté dans `app/main.py`.
- [ ] T025 [P] [US5] Test contrat `backend/tests/contract/test_fx_api.py` — valide schémas request/response contre `openapi-fx.yaml`.
- [ ] T026 [P] [US5] Test intégration `backend/tests/integration/test_fx_refresh.py` — mock httpx, run job, vérifier idempotence (UNIQUE), vérifier insertion 5 paires, simuler échec → status `failed` + pas d'écriture, conversion utilise dernier taux.
- [ ] T027 [P] [US5] Test unitaire `backend/tests/unit/test_fx_service.py` — convert XOF→EUR via peg, EUR→USD via snapshot, `as_of` historique.

---

## Phase 5 — User Story 2 : Consentements granulaires (P1)

**Goal** : table consent + endpoints toggle + décorateur `@requires_consent` + bottom sheet.
**Independent test** : nouvelle PME → essentiels seulement actifs ; toggle Mobile Money OFF → endpoint protégé renvoie 403 `{error:'consent_required',kind:'mobile_money'}` + UI ouvre `ConsentToggleSheet`.

- [x] T028 [US2] Migration Alembic `0005b_consent_table.py` — table `consent`, RLS PME, trigger `updated_at`, **trigger AFTER INSERT account → seed 5 consents** (innovation par rapport à la spec : garantit invariant pour TOUS nouveaux comptes, pas seulement existants).
- [x] T029 [P] [US2] Créer `backend/app/models/consent.py` — modèle SQLAlchemy `Consent`.
- [x] T030 [P] [US2] Créer `backend/app/schemas/consent.py` — enum `ConsentKind`, schémas.
- [x] T031 [US2] Créer `backend/app/services/consent_service.py` — `list_for_account`, `is_active`, `toggle` avec audit. 100% coverage.
- [x] T032 [US2] Créer `backend/app/decorators/requires_consent.py` — `RequiresConsent(kind)` Depends FastAPI ; 2 tests intégration verts.
- [x] T033 [P] [US2] Créer `backend/app/api/routes/privacy.py` — `GET /me/consentements`, `POST /me/consentements/{kind}`.
- [x] T034 [P] [US2] Test contrat ; 422 si kind inconnu vérifié.
- [x] T035 [P] [US2] Test intégration `backend/tests/integration/test_consent_flow.py` — 6 tests verts (toggle ON/OFF, audit_log entry, payload extra rejeté, kind invalide rejeté, auth required).
- [ ] T036 [DEFERRED] [P] [US2] Créer `frontend/composables/useConsent.ts`.
- [ ] T037 [DEFERRED] [P] [US2] Créer `frontend/components/privacy/ConsentToggleSheet.vue`.
- [ ] T038 [DEFERRED] [P] [US2] Créer `frontend/pages/me/consentements.vue`.
- [ ] T039 [DEFERRED] [P] [US2] Test E2E `frontend/tests/e2e/consents.spec.ts`.

---

## Phase 6 — User Story 3 : Politique de confidentialité versionnée (P1) [DEFERRED — toutes tâches]

**Goal** : page publique versionnée + ré-acceptation lors de refonte majeure via bottom sheet bloquante.
**Independent test** : visiteur non authentifié voit `/politique-confidentialite` ; admin publie v2.0.0 `is_major=true` → PME redirigée vers ré-acceptation au prochain login.

- [ ] T040 [US3] Migration Alembic `005c_privacy_policy_version.py` — table `privacy_policy_version` + INSERT v1.0.0 draft initial.
- [ ] T041 [US3] Migration `005d_consent_acceptance.py` — table `consent_acceptance` (PK composite) + RLS + index `account_id`.
- [ ] T042 [P] [US3] Créer `backend/app/models/policy.py` — `PrivacyPolicyVersion`, `ConsentAcceptance`.
- [ ] T043 [P] [US3] Créer `backend/app/schemas/policy.py` — `PolicyVersionOut`, `PolicyAcceptanceIn`.
- [ ] T044 [US3] Créer `backend/app/services/policy_service.py` — `get_current()`, `publish_new_version(content_md, version, is_major)` (réutilise helper F04 + `record_audit('admin')`), `requires_reacceptance(account_id)`, `accept(account_id, policy_version_id)`.
- [ ] T045 [P] [US3] Créer `backend/app/api/policy.py` — `GET /politique-confidentialite` (sans auth), `POST /me/policy-acceptance` (auth) ; routeur monté ; CORS public pour la GET.
- [ ] T046 [P] [US3] Créer `backend/app/api/admin/policy.py` — `POST /admin/policies` (admin only) appelant `publish_new_version`.
- [ ] T047 [P] [US3] Test contrat `backend/tests/contract/test_policy_api.py` — endpoints conformes.
- [ ] T048 [P] [US3] Test intégration `backend/tests/integration/test_policy_versioning.py` — publication majeure invalide acceptations, middleware refuse l'accès jusqu'à acceptation.
- [ ] T049 [P] [US3] Créer `frontend/pages/politique-confidentialite.vue` — page publique (no auth middleware) rendant `content_md` via `marked`, version visible.
- [ ] T050 [P] [US3] Mettre à jour `frontend/public/robots.txt` — `Allow: /politique-confidentialite` indexable.
- [ ] T051 [P] [US3] Créer `frontend/composables/usePolicyAcceptance.ts` — fetch dernière version, état d'acceptation utilisateur.
- [ ] T052 [P] [US3] Créer `frontend/components/privacy/PolicyReacceptSheet.vue` — bottom sheet bloquante (no escape close), liste des changements, bouton « Accepter » → `POST /me/policy-acceptance`.
- [ ] T053 [P] [US3] Créer `frontend/middleware/policy-acceptance.global.ts` — middleware Nuxt qui, si `requires_reacceptance`, redirige toute page authentifiée vers route avec sheet ouverte.
- [ ] T054 [P] [US3] Test E2E `frontend/tests/e2e/policy-reaccept.spec.ts` — admin publie majeure, PME login → sheet bloquante, accepter → accès rétabli.

---

## Phase 7 — User Story 1 : Page « Mes données » (P1) [DEFERRED — toutes tâches] — dépend US2 (consent) et US7 (audit RTBF)

**Goal** : résumé + export ZIP + demande suppression différée 30j annulable + purge effective.
**Independent test** : PME télécharge ZIP < 30 s, demande suppression, annule, refait demande, J+30 → 0 ligne tenant-scoped restante (script de vérification).

- [ ] T055 [US1] Migration Alembic `005b_deletion_request.py` — table `deletion_request` (cf. data-model.md), `effective_at` GENERATED, RLS PME.
- [ ] T056 [US1] Migration FK CASCADE — script `005i_cascade_audit.py` audite toutes les tables tenant-scoped existantes (issues F01–F04) et ajoute `ON DELETE CASCADE` depuis `account` si manquant ; échoue avec liste claire si table inconnue détectée.
- [ ] T057 [P] [US1] Créer `backend/app/models/deletion.py` — `DeletionRequest`.
- [ ] T058 [P] [US1] Créer `backend/app/schemas/deletion.py` — `DeletionRequestOut`, `DataSummaryOut`.
- [ ] T059 [US1] Créer `backend/app/services/deletion_service.py` — `request(account_id)`, `cancel(account_id)`, `execute_purge(account_id)` qui : (a) ouvre transaction, (b) `purge_context()`, (c) UPDATE `audit_log SET user_id=pseudonymize(account_id) WHERE account_id=...`, (d) DELETE depuis `account` (CASCADE), (e) supprime fichiers physiques, (f) révoque attestations actives, (g) invalide refresh tokens, (h) `record_audit('admin', event='purge_executed')`.
- [ ] T060 [US1] Créer `backend/app/services/export_service.py` — `build_zip_stream(account_id)` qui itère catégories (entreprise, projets, candidatures, scores, attestations, documents, conversations, audit), écrit `entities/{type}.json`, copie pièces jointes dans `files/`, calcule hash SHA-256 par fichier, écrit `manifest.json` final ; exclut `password_hash`.
- [ ] T061 [P] [US1] Créer `backend/app/api/privacy.py` (compléter) — `GET /me/donnees/summary`, `GET /me/donnees/export` (StreamingResponse), `POST /me/donnees/delete`, `DELETE /me/donnees/delete`.
- [ ] T062 [US1] Créer `backend/app/jobs/purge_pending_deletions.py` — sélectionne `deletion_request WHERE status='requested' AND effective_at <= now()`, appelle `deletion_service.execute_purge(...)`, wrappé `run_idempotent('purge_pending_deletions', ...)`. Cron `0 4 * * *`.
- [ ] T063 [P] [US1] Créer `backend/scripts/verify_purge.py` — CLI `python scripts/verify_purge.py <account_id>` qui énumère toutes les tables tenant-scoped et vérifie 0 ligne ; sortie code ≠ 0 si résidus.
- [ ] T064 [P] [US1] Test contrat `backend/tests/contract/test_privacy_api.py` — endpoints `summary`, `export`, `delete`, `delete cancel` conformes `openapi-privacy.yaml`.
- [ ] T065 [P] [US1] Test intégration `backend/tests/integration/test_export_zip.py` — fixture compte avec données complètes, export ZIP < 30 s, manifest présent, hashes corrects, `password_hash` absent.
- [ ] T066 [P] [US1] Test intégration `backend/tests/integration/test_purge_flow.py` — request → cancel → request → exécution purge → `verify_purge.py` retourne 0 ; audit_log porte pseudonyme `anon_*`.
- [ ] T067 [P] [US1] Créer `frontend/composables/useDeletion.ts` + `useDataSummary.ts`.
- [ ] T068 [P] [US1] Créer `frontend/components/privacy/DataSummaryCard.vue`, `frontend/components/privacy/ExportProgress.vue`, `frontend/components/privacy/DeletionConfirmSheet.vue` (bottom sheet gsap, double confirmation, affichage du J+30).
- [ ] T069 [P] [US1] Créer `frontend/pages/me/donnees.vue` — assemble summary, export, deletion.
- [ ] T070 [P] [US1] Test E2E `frontend/tests/e2e/me-donnees.spec.ts` — visite, export téléchargé, request delete, cancel, vérifier état UI.

---

## Phase 8 — User Story 6 : Affichage parallèle PME ↔ fonds (P2) [DEFERRED — toutes tâches]

**Goal** : `<MoneyDisplay :show-conversion>` affiche montant principal + conversion.
**Independent test** : offre 10 000 EUR consultée par PME XOF → rendu « 10 000 EUR (≈ 6 559 570 FCFA) ».

- [ ] T071 [P] [US6] Étendre `frontend/components/money/MoneyDisplay.vue` — quand `:show-conversion` fournie, fetch `POST /fx/convert` via `useMoney`, affiche montant secondaire avec libellé « ≈ ».
- [ ] T072 [P] [US6] Étendre `frontend/composables/useMoney.ts` — méthode `convert(money, to, asOf?)` cache local 60s.
- [ ] T073 [P] [US6] Test E2E `frontend/tests/e2e/money-display-conversion.spec.ts` — page test rend montant + conversion, vérifie ordre EUR principal puis XOF estimation.

---

## Phase 9 — User Story 7 : Audit log RTBF & pseudonymisation (P2) [transversal — partiellement couvert par US1]

**Goal** : tout toggle consent et toute demande/annulation/exécution suppression journalisés ; pseudonymisation déterministe à la purge.
**Independent test** : 1) toggler 5 consentements crée 5 entries audit avec `consent_kind` et `source_of_change='manual'` ; 2) cycle request/cancel/request crée 3 entries distinctes ; 3) après purge, ancien `user_id` dans audit_log = `anon_<16hex>`.

- [x] T074 [P] [US7] Extension `record_audit` : utilisation `field='consent_kind'` + `new_value` JSON (sans changement de signature) — testé via test_consent_flow.
- [x] T075 [P] [US7] Test unitaire `backend/tests/unit/test_pseudonymize.py` — déterminisme + format vérifiés (4 tests).
- [x] T076 [P] [US7] Test intégration purge : `tests/integration/test_audit_purge_context.py::test_audit_update_user_id_under_purge_context_ok`.
- [x] T077 [P] [US7] Test sécurité : `test_audit_update_other_column_under_purge_raises` + `test_audit_delete_always_raises` + `test_audit_update_outside_purge_context_raises`.

---

## Phase 10 — Polish & Cross-Cutting Concerns [DEFERRED — toutes tâches]

- [ ] T078 [P] Documenter dans `README.md` la section « Conformité RGPD/UEMOA » : page Mes données, consentements, politique versionnée, suppression 30j, chiffrement at-rest natif, TLS 1.3 + HSTS.
- [ ] T079 [P] Configurer HSTS dans `backend/app/main.py` middleware (en prod) et reverse proxy doc dans `docs/ops/tls.md`.
- [ ] T080 [P] Ajouter checklist OPS `docs/ops/privacy-launch.md` : alias `privacy@esg-mefali.com` configuré, validation juridique politique, pepper généré et stocké, source BCEAO du peg vérifiée.
- [ ] T081 [P] Mettre à jour `frontend/public/robots.txt` final + `sitemap.xml` minimal listant `/politique-confidentialite`.
- [ ] T082 [P] Mesure de performance `backend/tests/perf/test_export_perf.py` — fixture 50 Mo de données, export < 30 s.
- [ ] T083 [P] Audit de couverture : `pytest --cov=app --cov-fail-under=80` côté backend ; `pnpm test --coverage` ≥ 80% côté frontend.
- [ ] T084 [P] Mettre à jour `docs_et_brouillons/features/00-INDEX.md` — marquer F05 livré.

---

## Dependency Graph (story-level)

```
Setup (P1) ──► Foundational (P2) ──► US4 (Money) ──► US5 (FX)
                                       │              │
                                       ├──► US2 (Consents) ──┐
                                       ├──► US3 (Policy)     ├──► US1 (Mes données) ──► US7 (RTBF) ──► Polish
                                       └──► US6 (parallel display) ◄── US5
```

- US4 et US5 doivent être livrées avant US6 (qui consomme `convert`).
- US2 doit être livrée avant US1 pour que la purge connaisse les consentements à purger.
- US7 finalise les tests transversaux (déjà partiellement couverts par US1+US2) ; n'introduit pas de code applicatif neuf hors helper `record_audit` étendu.

## Parallel Execution Examples

- À l'issue de Phase 2 : T011/T013/T014 (US4 backend+front en parallèle), T018/T019/T024 (US5), T029/T030/T036/T037 (US2), T042/T043/T049/T052 (US3) peuvent démarrer simultanément sur des fichiers disjoints.
- Les tests `[P]` (T012, T015, T025-T027, T034-T035, T039, T047-T048, T054, T064-T066, T070, T073, T075-T077) tournent en parallèle dans la CI.

## MVP Scope Suggested

**MVP minimal (livraison séquentielle recommandée)** : Phase 1 → Phase 2 → US4 → US5 → US2 → US3 → US1 → US7 → Polish.

**MVP « light » si pression** : US4 + US5 + US2 + US1 (sans politique versionnée fine) — couvre obligation export + suppression + consentements ; US3 et US7 dans la foulée.

## Independent Test Criteria — récapitulatif

- **US4** : `Money` créable et sérialisable, devise hors enum rejetée.
- **US5** : `convert(1000 XOF, EUR) ≈ 1.524 EUR`, fallback sans API.
- **US2** : toggle persiste, endpoint protégé renvoie 403 structuré.
- **US3** : visiteur anonyme voit la page, ré-acceptation déclenchée par publication majeure.
- **US1** : export ZIP valide < 30 s, purge J+30 confirmée par script.
- **US6** : affichage parallèle EUR + XOF rendu correctement.
- **US7** : pseudonymisation déterministe et update audit limité à `user_id`.

---

**Total tasks** : 84
- Setup : 4
- Foundational : 6
- US4 (Money) : 5 — dont 4 [P]
- US5 (FX) : 12 — dont 7 [P]
- US2 (Consents) : 12 — dont 9 [P]
- US3 (Policy) : 15 — dont 11 [P]
- US1 (Mes données) : 16 — dont 9 [P]
- US6 (parallel display) : 3 — tous [P]
- US7 (RTBF) : 4 — tous [P]
- Polish : 7 — tous [P]

Format validation : tous les tasks utilisent `- [ ] Tnnn [P?] [USx?] description avec chemin de fichier`.
