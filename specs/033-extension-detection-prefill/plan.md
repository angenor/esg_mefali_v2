# Implementation Plan: F33 — Extension Chrome — Détection sites & pré-remplissage IA

**Branch**: `033-extension-detection-prefill` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)

## Summary

Livrer le MVP backend de l'extension Chrome ESG Mefali :

1. Trois endpoints PME `/extension/*` (GET url-patterns, GET profile-summary, POST suggest-field).
2. Routes admin pour gérer la table `url_pattern` (CRUD + activation) + table `field_mapping_intermediaire` avec seed initial.
3. Squelette extension Chrome Manifest V3 minimaliste (manifest, popup login, content script bandeau, i18n FR/EN) — livré comme fichiers statiques, sans pipeline de build ni tests JS automatisés.

`suggest-field` réutilise le client LLM existant (F18) avec fallback texte court si indisponible. Auth via `get_current_pme`. Audit append-only via `record_audit` (helper F04).

## Technical Context

- **Language**: Python 3.11 (backend), JavaScript ES2022 (extension Chrome)
- **Backend**: FastAPI + SQLAlchemy 2.x + Alembic
- **DB**: PostgreSQL 16 + RLS (F02), pgvector (F18)
- **Tests**: pytest + httpx TestClient
- **Auth**: `get_current_pme` (F02), `get_current_admin` (F06)
- **Audit**: `record_audit` (F04), action `extension.{view_patterns|profile_summary|suggest_field|admin_pattern_*}`
- **Extension**: Manifest V3, vanilla JS (pas de bundler), `chrome.storage.local`, `chrome.i18n`
- **LLM**: client existant `app.llm_client` (F18) avec fallback texte court si indisponible

## Constitution Check

| # | Principe | Application | Status |
|---|----------|-------------|--------|
| P1 | Sourçage anti-hallucination | Suggestions IA non-factuelles (textes libres descriptifs) — pas d'assertion ESG/finance ⇒ pas de `cite_source` requis. Patterns d'URL liés à des Offres déjà sourcées (F08). | OK |
| P2 | RLS multi-tenant strict | Tous les endpoints `/extension/*` derrière `get_current_pme` ; `profile-summary` filtre `account_id`. | OK |
| P3 | Audit append-only | `record_audit` invoqué pour chaque endpoint (best-effort wrapper). | OK |
| P4 | Versioning | N/A. | OK |
| P5 | Money typé | N/A. | OK |
| P6 | Indicateur unique | N/A. | OK |
| P7 | Plateforme fermée intermédiaires | Endpoints `/extension/*` PME-only. Admin manage routes sous `/admin/url-patterns`. | OK |
| P8 | Édition manuelle + sync | Bandeau & form-fill non agressifs (overlay, pas de modif du DOM original). | OK |
| P9 | Tool-use LLM fiable | `suggest-field` : prompt simple + Pydantic out + retry 1x + fallback. | OK |
| P10 | UX bottom sheet | N/A (extension hors scope chat). | OK |

## Project Structure

```text
backend/app/extension/
├── __init__.py
├── router.py              # /extension/* (PME)
├── admin_router.py        # /admin/url-patterns/* (Admin)
├── schemas.py
├── service.py
├── url_matcher.py         # logique regex/wildcard
└── seed_field_mappings.py

backend/alembic/versions/
└── f033_url_patterns_field_mapping.py

backend/tests/extension/
├── __init__.py
├── conftest.py
├── test_url_patterns.py
├── test_profile_summary.py
├── test_suggest_field.py
├── test_admin_url_patterns.py
└── test_url_matcher.py

extension/                 # nouveau dossier racine repo
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── popup.js
├── popup.css
├── _locales/fr/messages.json
├── _locales/en/messages.json
└── README.md
```

## Phase 0 — Research

- Réutilise `get_current_pme` (cf. `app/api/routes/privacy.py`) et `record_audit` (cf. F23/F30).
- Modèles existants `Account`, `Entreprise`, `Projet` pour `profile-summary` (inspecter `app/models/`).
- Pas de table `url_pattern` ni `field_mapping_intermediaire` actuellement → migration Alembic nouvelle.
- LLM client : `app/llm_client.py` (F18) — appel asynchrone court, max ~200 tokens.
- CORS : autoriser l'origine `chrome-extension://*` dans le middleware (`app/middleware/`).
- Pattern admin : suivre les `f08_*` admin routers (cf. `app/admin/`).

## Phase 1 — Design & Contracts

### Tables (nouvelles)

**`url_pattern`** :
- `id` UUID PK
- `pattern` TEXT NOT NULL (wildcard ou regex)
- `pattern_type` ENUM(`wildcard`, `regex`) NOT NULL
- `nature` ENUM(`fonds`, `intermediaire`) NOT NULL
- `fonds_id` UUID NULL FK→`fonds`
- `intermediaire_id` UUID NULL FK→`intermediaire`
- `offre_id` UUID NULL FK→`offre`
- `is_active` BOOLEAN DEFAULT true
- `preferred_language` VARCHAR(2) NULL
- `created_at`, `updated_at` TIMESTAMP

**`field_mapping_intermediaire`** :
- `id` UUID PK
- `intermediaire_id` UUID NOT NULL FK→`intermediaire`
- `mapping_json` JSONB NOT NULL (`{"label_pattern":"profile_attr",...}`)
- `created_at`, `updated_at` TIMESTAMP

### Endpoints PME

```
GET  /extension/url-patterns        -> UrlPatternListOut
GET  /extension/profile-summary     -> ProfileSummaryOut
POST /extension/suggest-field       -> SuggestFieldOut
GET  /extension/field-mappings      -> FieldMappingListOut (mappings publics par intermédiaire)
```

### Endpoints Admin

```
GET    /admin/url-patterns           -> liste paginée
POST   /admin/url-patterns           -> création
PATCH  /admin/url-patterns/{id}      -> update (activation/désactivation incluse)
DELETE /admin/url-patterns/{id}      -> soft delete (is_active=false)
```

### Schemas Pydantic

- `UrlPatternOut`: id, pattern, pattern_type, nature, fonds_id?, intermediaire_id?, offre_id?, offre_label?, preferred_language?
- `UrlPatternListOut`: items[], updated_at
- `ProfileSummaryOut`: account_id, raison_sociale, secteur, pays, taille, projet: { id, titre, description_courte, montant, secteur, ... } (≤ 12-15 champs, ≤ 2 KB JSON)
- `SuggestFieldIn`: field_label, field_max_length, projet_id?, offre_id?, intermediaire_id?, language='fr'
- `SuggestFieldOut`: text, length, source ('llm'|'fallback'), generated_at
- `FieldMappingOut`: intermediaire_id, mapping_json

### Audit

`record_audit(entity_type='extension', entity_id=<uuid|null>, action='extension.<op>', source_of_change='manual', actor_user_id=user.id)` — wrapper try/except.

### Extension squelette (Manifest V3)

- `manifest.json` v3 : `host_permissions` configurable, `action.default_popup`, `background.service_worker`, `content_scripts` avec `matches:["<all_urls>"]` filtrés à l'exécution.
- `popup.html` : login (email/password) + bouton refresh patterns + sélecteur langue.
- `content.js` : interroge `chrome.runtime.sendMessage` au load + sur `pushState`/`popstate` ; affiche bandeau si match.
- `background.js` : auth, fetch periodique des patterns, refresh sur 401.
- `_locales/{fr,en}/messages.json` : libellés.

### Quickstart (extension)

```
1. Charger l'extension non-empaquetée (chrome://extensions → "Load unpacked" → dossier extension/)
2. Configurer l'URL backend dans le popup (par défaut http://localhost:8000)
3. Login avec compte PME
4. Naviguer sur une URL matchant un pattern actif → bandeau apparaît.
```

## Phase 2 — Tasks

Voir [tasks.md](./tasks.md).

## Complexity Tracking

- Migration Alembic (2 nouvelles tables) — dérogation justifiée : tables petites et strictement liées au scope F33.
- Extension JS livrée non-bundlée (pas de tests unitaires JS automatisés) — couverture portée à >= 80% sur backend ; pour l'extension, tests manuels documentés (`manual-tests-33.md`).
