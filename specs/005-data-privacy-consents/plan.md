# Implementation Plan: F05 — Conformité Données Personnelles, Consentements & Devises

**Branch**: `005-data-privacy-consents` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-data-privacy-consents/spec.md`

## Summary

Livrer la conformité données personnelles (page Mes données, export ZIP, suppression différée 30 jours, consentements granulaires, politique versionnée publique, audit log RTBF avec pseudonymisation) et le socle devises (type `Money` typé, peg fixe FCFA-EUR 655,957 sourcé, snapshot quotidien `fx_rate` via exchangerate-api.com avec fallback gracieux, composant frontend `<MoneyDisplay>`).

Approche technique : entités SQLAlchemy 2.x sous RLS F02, audit via helpers F04 (extension contrôlée du trigger snapshot_immutable pour autoriser l'`UPDATE` ciblé de la colonne pseudonymisée), service Pydantic v2 `Money` strict, jobs APScheduler embarqués dans FastAPI avec table `scheduled_job_run` pour idempotence, page Nuxt 4 publique pour la politique avec versioning F04, bottom sheets gsap pour toggles consentement et confirmation suppression et écran de ré-acceptation politique.

## Technical Context

**Language/Version** : Python 3.12 (backend), TypeScript 5.x sur Nuxt 4 / Vue 3 (frontend)
**Primary Dependencies** :
- Backend : FastAPI, Pydantic v2 (`extra='forbid'`), SQLAlchemy 2.x async, Alembic, APScheduler, httpx, cryptography (HMAC-SHA256)
- Frontend : Nuxt 4, Vue 3 Composition API, Pinia, UnoCSS/Tailwind, gsap (bottom sheets), `@nuxt/content` ou rendu Markdown statique pour la politique

**Storage** : PostgreSQL 16 + extension pgvector (déjà active). Nouvelles tables sous RLS multi-tenant ; `fx_rate` et `privacy_policy_version` en lecture publique authentifiée.

**Testing** : pytest + pytest-asyncio + httpx.AsyncClient + factory_boy ; vitest + @nuxt/test-utils ; playwright pour E2E (export, toggle consent, ré-acceptation policy).

**Target Platform** : serveur Linux (FastAPI + uvicorn), navigateurs evergreen (Chrome ≥ 110, Firefox ≥ 110, Safari ≥ 16). Hébergement Europe / Afrique de l'Ouest.

**Project Type** : web application (backend + frontend séparés).

**Performance Goals** :
- Export complet ≤ 30 s pour compte typique (≤ 50 Mo).
- Conversion `Money` ≤ 200 ms en lecture cache.
- Page politique de confidentialité ≤ 500 ms (statique côté Nuxt).

**Constraints** :
- TLS 1.3 + HSTS en production (NFR-001).
- Aucun secret applicatif ni `password_hash` dans l'export utilisateur (NFR-005).
- API exchangerate-api.com en tier gratuit (1500 req/mois) → un appel/jour suffit.
- Trigger F04 `snapshot_immutable` à étendre pour autoriser uniquement la colonne `user_id` à être mise à jour quand `current_setting('app.purge_context', true) = 'on'`.

**Scale/Scope** : MVP ~ 100 PME ; ~ 10 catégories d'entités exportables ; 5 types de consentement non essentiels ; 7 devises supportées (XOF, EUR, USD, GHS, NGN, MAD, GBP).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | Le peg FCFA-EUR 655,957 est-il sourcé via une `Source` `verified` ? La politique de confidentialité (corpus juridique) cite-t-elle ses sources ? | ✅ peg lié à une `Source` BCEAO/UEMOA `verified` (FK `fx_rate.peg_source_id` pour la ligne du peg). Politique = corpus rédactionnel propre, pas une affirmation chiffrée — sources juridiques citées en bas de page. |
| P2 | Multi-tenant RLS | Les tables `consent`, `deletion_request`, `consent_acceptance` portent-elles `account_id` + politique RLS ? `fx_rate` et `privacy_policy_version` sont-elles correctement classées comme catalogue partagé ? | ✅ `consent`, `deletion_request`, `consent_acceptance` → `account_id` NOT NULL + RLS `USING account_id = current_setting('app.current_account_id')::uuid`. `fx_rate` et `privacy_policy_version` = catalogue partagé en lecture publique authentifiée (RLS `USING true` en SELECT, INSERT réservé Admin via fonction). `scheduled_job_run` = table interne admin (pas multi-tenant). |
| P3 | Audit log append-only | Toggles de consentement, demandes/annulations/exécutions de suppression, refresh fx, purge → tous journalisés ? `source_of_change` ∈ {manual, llm, import, admin} ? | ✅ helper `record_audit` de F04 réutilisé. `manual` pour toggles consent et demandes utilisateur. `admin` pour purge effective et refresh fx. INSERT only ; UPDATE de `user_id` autorisé exclusivement en contexte de purge via flag de session `app.purge_context='on'`, justifié pour RTBF (FR-015). |
| P4 | Versioning + snapshot | `privacy_policy_version` versionnée via `publish_new_version` ? `fx_rate` versionnée temporellement (`captured_at` + `valid_from/valid_to` pour le peg) ? | ✅ `privacy_policy_version` utilise `publish_new_version` (F04) avec `is_major BOOL`. `fx_rate` porte `(currency_from, currency_to, rate, captured_at, valid_from, valid_to NULL)` ; le peg fixe est inséré comme ligne spéciale `valid_from=2026-01-01, valid_to=NULL` pouvant être versionnée si la BCEAO modifie la parité. |
| P5 | Money typé | `Money` Pydantic v2 strict défini dans cette feature ? `Decimal` partout, `float` interdit ? Affichage parallèle PME ↔ fonds disponible ? | ✅ Pydantic v2 `Money(BaseModel, model_config=ConfigDict(extra='forbid'))` avec `amount: Decimal`, `currency: Currency` (enum fermé). Service `FxService` + `convert()` retournent `Decimal`. Composant `<MoneyDisplay :show-conversion="'XOF'">` pour US6. |
| P6 | Pivot Indicateur unique | Cette feature manipule-t-elle des données ESG ? | ✅ Non applicable — F05 ne touche aucun indicateur ESG. |
| P7 | Plateforme fermée | Cette feature crée-t-elle un rôle Intermédiaire/Bank/Fund ? Politique publique = exception légitime ? | ✅ Aucun rôle nouveau. La page `/politique-confidentialite` est explicitement publique pour respecter l'obligation d'information RGPD (seule exception au principe « plateforme fermée »). Aucun webhook ni flux push vers tiers. |
| P8 | Édition manuelle + sync LLM | Champs alimentés par le LLM dans cette feature ? | ✅ Non applicable au MVP — toggles consentement, demandes de suppression et politique sont 100 % manuels/admin. Aucun tool LLM ne mute ces champs en F05. |
| P9 | Tool-use LLM fiable | Nouveaux tools LLM dans cette feature ? | ✅ Non applicable — F05 ne livre aucun tool LLM. Les services backend `consent_service`, `deletion_service`, `fx_service` sont des services applicatifs, exposés ultérieurement comme tools si besoin (hors scope F05). |
| P10 | UX bottom sheet | Toggles consent, confirm delete, ré-acceptation politique vivent-ils en bottom sheet ? | ✅ Trois bottom sheets gsap : `ConsentToggleSheet`, `DeletionConfirmSheet`, `PolicyReacceptSheet`. Aucun composant interactif inline. Bouton « Répondre librement » non requis ici car flux non conversationnel. |

**Statut global** : ✅ Tous les gates passent. Aucun violation, aucune dérogation.

### Contraintes techniques (rappel)

- Backend dans `backend/.venv`, Postgres seul service Docker, frontend `pnpm dev`.
- Hébergement prod : Europe / Afrique de l'Ouest.
- Conformité RGPD + 2013-450 + UEMOA 20/2010 = objet même de la feature.
- Langue : interface française par défaut. Politique fournie en FR au MVP.

## Project Structure

### Documentation (this feature)

```text
specs/005-data-privacy-consents/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi-privacy.yaml
│   └── openapi-fx.yaml
├── checklists/
│   └── requirements.md
└── tasks.md           # produit par /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── privacy.py            # /me/donnees/{summary,export,delete}, /me/consentements
│   │   ├── policy.py             # /politique-confidentialite (lecture), /admin/policies (publish)
│   │   └── fx.py                 # /fx/rates, /fx/convert
│   ├── models/
│   │   ├── consent.py            # Consent, DeletionRequest, ConsentAcceptance
│   │   ├── policy.py             # PrivacyPolicyVersion
│   │   ├── fx.py                 # FxRate
│   │   └── jobs.py               # ScheduledJobRun
│   ├── schemas/
│   │   ├── money.py              # Money Pydantic, Currency enum
│   │   ├── consent.py
│   │   ├── deletion.py
│   │   ├── policy.py
│   │   └── fx.py
│   ├── services/
│   │   ├── consent_service.py    # toggle, list, @requires_consent
│   │   ├── deletion_service.py   # request, cancel, execute_purge, pseudonymize_audit
│   │   ├── export_service.py     # ZIP+manifest+files
│   │   ├── policy_service.py     # publish_new_version, check_acceptance
│   │   ├── fx_service.py         # get_rate, convert, refresh_rates
│   │   └── audit_extension.py    # update trigger conditions for purge context
│   ├── jobs/
│   │   ├── scheduler.py          # APScheduler bootstrap
│   │   ├── purge_pending_deletions.py
│   │   ├── refresh_fx_rates.py
│   │   └── alert_stale_fx.py
│   ├── decorators/
│   │   └── requires_consent.py
│   └── core/
│       ├── pseudonymize.py       # HMAC-SHA256 + pepper
│       └── currencies.py         # Currency enum, peg constant
├── alembic/versions/
│   ├── 005a_consent_tables.py
│   ├── 005b_deletion_request.py
│   ├── 005c_privacy_policy_version.py
│   ├── 005d_consent_acceptance.py
│   ├── 005e_fx_rate.py
│   ├── 005f_scheduled_job_run.py
│   ├── 005g_extend_audit_trigger_for_purge.py
│   └── 005h_seed_peg_fcfa_eur.py
└── tests/
    ├── contract/                 # contrats API
    ├── integration/              # purge, export, refresh fx
    └── unit/                     # Money, pseudonymize, requires_consent

frontend/
├── pages/
│   ├── politique-confidentialite.vue        # publique
│   ├── me/donnees.vue
│   └── me/consentements.vue
├── components/
│   ├── privacy/
│   │   ├── ConsentToggleSheet.vue
│   │   ├── DeletionConfirmSheet.vue
│   │   ├── PolicyReacceptSheet.vue
│   │   ├── DataSummaryCard.vue
│   │   └── ExportProgress.vue
│   └── money/
│       └── MoneyDisplay.vue
├── composables/
│   ├── useConsent.ts
│   ├── useDeletion.ts
│   ├── useMoney.ts
│   └── usePolicyAcceptance.ts
├── stores/
│   └── privacy.ts                 # Pinia
├── middleware/
│   └── policy-acceptance.global.ts
└── tests/
    ├── unit/
    └── e2e/                       # Playwright
```

**Structure Decision** : web application (Option 2) — backend FastAPI + frontend Nuxt 4 séparés, conformément à la stack imposée par la constitution. Toute la logique sensible (consentements, suppression, pseudonymisation, scheduler) reste côté backend ; le frontend ne porte que l'UI bottom-sheet, les composables et l'interception du middleware policy.

## Complexity Tracking

> Aucune violation à justifier. Tous les gates passent.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (aucune) | — | — |
