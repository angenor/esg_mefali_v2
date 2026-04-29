# Manual Tests — F05 data-privacy-consents

## Statut session
Implémentation **partielle stratégique** :
- Phase B précédente (5 tasks) : T005/T006/T011/T012 + config.py.
- Phase B (cette session) : Foundational T007/T008/T010 + US2 (Consents) backend complet.
- US1/US3/US5/US6/US7 backend + tout le frontend : **DEFERRED**.

## Tests automatisés couverts (cette session — additions)
- T007 (`audit_log_immutable` trigger + RTBF exception) : `tests/integration/test_audit_purge_context.py` (5 tests verts).
- T008 (`scheduled_job_run` table + UNIQUE) : couvert dans le même fichier.
- T010 (`audit_extension.purge_context()` context manager) : `app/services/audit_extension.py` + tests d'intégration.
- T028 (migration `consent` + RLS + trigger AFTER INSERT account → seed 5 consents) : couvert par 6 tests dans `test_consent_flow.py`.
- T029 (model `Consent`).
- T030 (schemas `ConsentKind`, `ConsentOut`, `ConsentToggleIn`, `ConsentRequiredError`).
- T031 (`consent_service.list_for_account / is_active / toggle`) : 100% coverage.
- T032 (`RequiresConsent` dependency) : `tests/integration/test_requires_consent_decorator.py` (2 tests).
- T033 (API `GET /me/consentements` + `POST /me/consentements/{kind}`).
- T034/T035 (contrat + intégration consent).

Total backend : **267 passed, 5 skipped**, coverage 85.35%, ruff clean.

## Tâches NON implémentées (DEFERRED)

### T001-T002 deps backend/frontend, T003-T004 (.env.example + validation stricte)
DEFERRED — non bloquant ; config.py charge déjà les vars F05 avec defaults non-bloquants.

### T009 scheduler APScheduler
DEFERRED — pas de scheduler runtime. Les jobs `purge_pending_deletions`, `refresh_fx_rates`, `alert_stale_fx` doivent être exécutés manuellement (CLI ou cron OS) en attendant.

### US1 (T055-T070) — Mes données / Export ZIP / RTBF purge
DEFERRED — large périmètre (export ZIP avec manifest hash, deletion_request table, purge_pending_deletions job, FK CASCADE audit, frontend complet). Le trigger purge audit est en place et testé : la mécanique de pseudonymisation est prête.
- **À noter** : la spec dit `UPDATE audit_log SET user_id = pseudonymize(account_id)` avec pseudonymize→string, mais `audit_log.user_id` est UUID FK vers `account_user(id)`. Solution future : ajouter colonne `pseudonymous_user_id TEXT NULL` OU effacer user_id à NULL et stocker le pseudonyme ailleurs. Test actuel valide la mécanique avec `user_id = NULL`.

### US3 (T040-T054) — Politique versionnée + ré-acceptation bottom-sheet
DEFERRED — tables `privacy_policy_version` + `consent_acceptance` + endpoints + middleware Nuxt non implémentés.

### US5 (T016-T027) — FX taux quotidien
DEFERRED — table `fx_rate`, seed peg BCEAO, service `fx_service.convert/get_rate`, jobs `refresh_fx_rates` + `alert_stale_fx` non livrés.

### US6 (T071-T073) — Affichage parallèle PME ↔ fonds
DEFERRED — dépend US5 + frontend MoneyDisplay.

### US7 (T074-T077) — Audit RTBF & pseudonymisation transversal
PARTIELLEMENT FAIT :
- T074 (extension `record_audit` avec consent_kind) : utilise `field='consent_kind'` + `new_value` JSON, sans changement de signature ; testé via test_consent_flow.
- T075 (déterminisme pseudonymize) : déjà couvert en `tests/unit/test_pseudonymize.py`.
- T076/T077 (intégration purge + sécurité) : couverts par `test_audit_purge_context.py`.

### Frontend (T013-T015, T036-T039, T049-T054, T067-T070, T071-T073)
DEFERRED — aucun composant Nuxt livré dans cette session. Stack pnpm prête mais composables/components/pages F05 non créés. À cibler dans une session frontend dédiée.

### Polish (T078-T084)
DEFERRED — README, HSTS, robots, perf export, doc juridique.

## Tests manuels — TODO

### US2 (Consentements) — IMPLÉMENTÉ
- [ ] Vérifier en DB qu'un nouveau register PME crée bien 5 lignes consent (trigger AFTER INSERT account).
- [ ] Toggle Mobile Money via `POST /me/consentements/mobile_money {given:true}` ; constater 1 entry audit_log entity_type='consent'.
- [ ] Endpoint protégé via `Depends(RequiresConsent(ConsentKind.MOBILE_MONEY))` → 403 `{error:'consent_required',kind:'mobile_money'}` quand given=false.
- [ ] Croiser tenants : PME A ne peut PAS lister consents PME B (RLS).

### US3, US5, US6 : non livrés — voir DEFERRED.

### US1 (RTBF / suppression) — partiel : trigger purge OK
- [x] AUTOMATED: UPDATE/DELETE hors purge_context = exception.
- [x] AUTOMATED: UPDATE user_id sous purge_context OK ; UPDATE autre col = exception.
- [ ] À LIVRER : table `deletion_request`, endpoint POST/DELETE `/me/donnees/delete`, job purge_pending_deletions, script verify_purge.py, export ZIP.

## Justification du périmètre
F05 = 84 tâches couvrant DB + scheduler + jobs + 3 services + 5 enums + frontend complet. La session a priorisé le **chemin critique TDD** : poser les fondations bloquantes (trigger audit purge, scheduled_job_run, audit_extension) puis livrer **US2 end-to-end** (la P1 la plus simple et la plus utilisée transversalement). US1/US3/US5/US6 sont chacune des chantiers ≥10 tasks, à reprendre en sessions suivantes en respectant TDD.
