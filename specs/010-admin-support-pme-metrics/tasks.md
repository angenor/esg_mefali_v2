# Tasks: Support PME Admin & Métriques Admin

**Feature**: 010-admin-support-pme-metrics
**Branch**: `010-admin-support-pme-metrics`
**Total tasks**: 57 (Phase 9 ajoute T051–T057 suite à /speckit-analyze ; MVP P1 = T001..T045 + T051..T054 + T057 = 50 tâches)

Légende :
- `[P]` = parallélisable (fichiers indépendants).
- `[USx]` = appartient à la User Story x.
- TDD : tests d'abord (RED) puis implémentation (GREEN).

---

## Phase 1 — Setup

- [x] T001 [P] Backend dossiers créés (`app/admin/{routes,services}`, `app/email/templates`, `app/llm`).
- [ ] T002 [P] [DEFERRED] Frontend Nuxt — pas de couche Vue dans cette livraison.
- [x] T003 [P] `httpx`, `cachetools` déjà présents dans `requirements.txt` ; `tenacity` [DEFERRED] (utilisé par retry email US3).
- [ ] T004 [P] [DEFERRED] env vars Resend/cache TTL — TTL lu via `os.environ.get('ADMIN_DASHBOARD_CACHE_TTL', '60')` côté code, mais pas encore listé dans `.env.example`.

## Phase 2 — Foundational (bloque toutes les US)

- [ ] T005 [DEFERRED] migration `010_a_llm_usage_log`.
- [ ] T006 [DEFERRED] migration `010_b_llm_pricing`.
- [ ] T007 [DEFERRED] migration `010_c_email_delivery_log`.
- [ ] T008 [DEFERRED] migration `010_d_attestation_revocation_columns` (table `attestation` non encore créée par F30).
- [ ] T009 [DEFERRED] migration `010_e_accounts_search_indexes` (pg_trgm) — search ILIKE simple suffit en MVP.
- [ ] T010 [DEFERRED] modèle `LlmUsageLog`.
- [ ] T011 [DEFERRED] modèle `LlmPricing`.
- [ ] T012 [DEFERRED] modèle `EmailDeliveryLog`.
- [ ] T013 [DEFERRED] extension modèle `Attestation` (table introduite par F30).
- [x] T014 `require_admin` (alias F02 `get_current_admin`) + whitelist documentée + test unit (`tests/unit/admin/test_deps.py`).
- [x] T015 `audit_admin_view` + enum `AdminViewSection` (7 valeurs) + fail-closed (`app/audit/admin_view.py`).
- [x] T016 [P] `mask_pii` (email/tel/IBAN/CIN) + test unit (`app/admin/services/pii_filter.py`, `tests/unit/admin/test_pii_filter.py`).
- [x] T017 `EmailSender` Protocol + `ConsoleEmailSender` + stub `ResendEmailSender` (`app/email/sender.py`) + test unit. Implémentation Resend httpx [DEFERRED].
- [ ] T018 [DEFERRED] retry email (dépend de T012 `email_delivery_log`).
- [ ] T019 [P] [DEFERRED] templates Jinja (dépend de T017 full + US3/US4).
- [ ] T020 [DEFERRED] hook `log_llm_usage` (dépend de T010).

## Phase 3 — User Story 1 — Vue lecture seule des comptes PME (P1)

**Goal** : `/admin/pme` liste paginée + recherche, `/admin/pme/{id}` fiche lecture seule.
**Independent test** : un admin authentifié charge la liste, filtre, ouvre une fiche en < 2s sans aucun bouton d'édition.

- [x] T021 [P] [US1] `tests/integration/admin/test_pme_list.py` (4 tests : auth requise, PME forbidden, admin OK, search no-match).
- [x] T022 [P] [US1] `tests/integration/admin/test_pme_detail.py` (4 tests : 404, 200+audit_view, 422 enum, 403 PME).
- [x] T023 [US1] `pme_view.list_accounts` (offset+ILIKE) dans `app/admin/services/pme_view.py`. Keyset/pg_trgm [DEFERRED].
- [x] T024 [US1] `pme_view.get_account_detail` (agrège account+users ; sections projets/candidatures/scores/attestations vides en attendant F11/F12/F23/F30 ; appelle `audit_admin_view` fail-closed).
- [x] T025 [US1] Routes `GET /admin/pme` et `GET /admin/pme/{id}` dans `app/admin/routes/pme.py`, montées avant les wildcards F06.
- [ ] T026..T030 [DEFERRED] Frontend Nuxt + E2E Playwright.

## Phase 4 — User Story 2 — Chaque consultation admin est tracée (P1)

**Goal** : chaque GET admin produit une ligne `audit_log admin_view`, visible côté PME, sans PII admin.
**Independent test** : un admin charge `/admin/pme/{id}?section=projets` → SQL retourne 1 ligne audit avec `section='projets'`, `source_of_change='admin'`, sans IP.

- [x] T031 [US2] Couvert par `test_pme_detail.py::test_get_pme_detail_emits_admin_view_audit` + `test_get_pme_detail_invalid_section_422`. Test exhaustif 7 sections [PARTIAL].
- [ ] T032 [US2] [DEFERRED] Projection PME `/me/audit-log` (dépend frontend F32).
- [x] T033 [US2] Fail-closed : `audit_admin_view` lève si audit insert None ; route remappe en HTTP 503.
- [x] T034 [US2] `section` validé via Pydantic enum `AdminViewSection` (FastAPI Query) ; audit branché dans le service.
- [ ] T035 [US2] [DEFERRED] Widget Vue.

## Phase 5 — User Story 3 — Reset password admin (P1)

**Goal** : POST reset envoie un email Resend avec token 1h ; deux audits ; aucun token retourné.

- [ ] T036..T040 [DEFERRED] US3 reset password admin — dépend de T012 `email_delivery_log`, T017 Resend full, T018 retry. À livrer en F10.1.

## Phase 6 — User Story 4 — Révocation / régénération attestation (P1)

**Goal** : POST revoke positionne `revoked_*` + audit + notification PME ; second appel = 409.

- [ ] T041..T045 [DEFERRED] US4 revoke/regenerate attestation — dépend de F30 (table `attestation`) + T013. À livrer en F10.1 ou conjointement avec F30.

## Phase 7 — User Story 5 — Tableau de bord agrégé (P2)

**Goal** : `/admin/dashboard` 5 blocs en < 1.5s avec cache 60s.

- [~] T046..T049 [PARTIAL/DEFERRED] US5 dashboard. Primitive cache TTL 60s + invalidate livrée (`app/admin/services/dashboard_stats.py` + tests unit). Agrégats SQL + routes + front [DEFERRED].

## Phase 8 — User Story 6 — Coûts LLM (P3, light)

**Goal** : endpoint usage par jour + graphique.

- [ ] T050 [DEFERRED] US6 LLM usage chart — dépend T010/T011.

## Phase 9 — Cross-cutting (gaps remontés par /speckit-analyze)

- [~] T051+T052 [PARTIAL/DEFERRED] AdminWhitelistGuard — whitelist documentée dans `app/admin/deps.py` ; middleware enforcement [DEFERRED] (à activer avec US3/US4).
- [ ] T053+T054 [DEFERRED] mask_pii sur attestation publique — dépend de F30.
- [ ] T055 [DEFERRED] /admin/email-deliveries — dépend T012.
- [ ] T056 [DEFERRED] Test perf SC-005 — dépend de F11/F12 (projets/candidatures).
- [ ] T057 [DEFERRED] PmeAuditFeed.vue — dépend de F32.

---

## Dépendances entre phases

```
Phase 1 (Setup T001-T004)
  ↓
Phase 2 (Foundational T005-T020) — BLOQUE toutes les US
  ↓
Phase 3 (US1) ──┬─ Phase 4 (US2 — dépend de T015 + route US1)
                ├─ Phase 5 (US3 — dépend de T017/T018)
                ├─ Phase 6 (US4 — dépend de T013 + T017/T018 + cache T047 pour invalidation)
                ├─ Phase 7 (US5 — dépend de T010..T013)
                └─ Phase 8 (US6 — dépend de T010/T011 + Phase 7)
```

## Parallélisation conseillée

- T001..T004 en parallèle.
- T005..T013 en parallèle (migrations + modèles, fichiers indépendants).
- T016, T019 en parallèle.
- US1 vues front (T026..T028) en parallèle entre elles.
- US3 et US4 peuvent être développées en parallèle après Phase 2.

## Implementation strategy — MVP

- **MVP minimal** = Phases 1 + 2 + US1 + US2 + US3 + US4 (T001..T045 = 45 tâches).
- US5 (T046..T049) et US6 (T050) sont stretch goals MVP+.
- Chaque US est livrable indépendamment (US1 testable seule, US3 testable sans US4, etc.).

## Independent test criteria (rappel)

- US1 : `/admin/pme` liste + ouverture fiche < 2s, zéro bouton d'édition.
- US2 : 100 % des GET admin produisent une ligne `admin_view` ; PME voit la trace.
- US3 : reset password en < 2 min ; aucun token retourné par l'API ; 2 audits.
- US4 : revoke propage en < 60s à `/verify/{id}` ; idempotent (409 second appel).
- US5 : dashboard < 1.5s P95 + cache 60s.
- US6 : graphique journalier tokens + coût Money typé.

## Polish & cross-cutting

- [ ] T051 (post-tasks ajouté si > 50) — laissé vide pour l'instant : à instancier en `/speckit-implement` si la phase polish est nécessaire (couverture 80 %, lint, audit log review, doc admin).
