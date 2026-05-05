# Implementation Plan: F50 — Documents upload + OCR viewer UI

**Branch**: `050-documents-ocr-ui` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/050-documents-ocr-ui/spec.md`

## Summary

F50 livre l'**UI conversationnelle et applicative** des documents PME au-dessus du backend F22 (`document_entreprise` + extraction texte) et F12 (`document_projet`), en y ajoutant les capacités attendues par le spec et les 5 clarifications du 2026-05-05 :

- Page `/documents` (table virtualisée + drawer prévisualisation + fiche d'extraction validable + tags + recherche + filtres + empty state guidé), grille embed dans `/profil/projets/[id]`, et hook `ask_file_upload` pour le chat conversationnel (F41).
- Pipeline UI : drag & drop multi-fichier, queue 5 simultanés, progression XHR, dédoublonnage par empreinte SHA-256 client+serveur, MIME whitelist + cap 20 Mo client, polling `ocr_status` (≤ 2 s, plafond 60 s).
- Fiche `<ShowSummaryCard>` (F39) qui affiche les champs extraits avec confiance, autorise édition, et **valide → propage** vers `entreprise` / `projet` avec audit append-only, document marqué source.
- Many-to-many document↔projet via une nouvelle table `document_link_projet` (Q1 = M:N).
- Soft-delete avec **purge dure automatique à 30 jours** (Q2) — tâche backend planifiée.
- WCAG 2.1 AA (Q3), dédoublonnage par empreinte avec choix utilisateur (Q4), empty state illustré + CTA primaire (Q5).

L'effort est ~85 % frontend (Nuxt 4 + Pinia + Tailwind v4 + pdf.js + bottom sheet F39) et ~15 % backend (extensions F22 : champs structurés extraction, endpoint dédoublonnage, table de liens M:N, job purge 30 j).

## Technical Context

**Language/Version** : Frontend TypeScript 5.6 + Vue 3.5 (Nuxt 4) ; Backend Python 3.12 (FastAPI).
**Primary Dependencies** :
- Frontend : Nuxt 4, Pinia, Tailwind v4, gsap (bottom sheet F39), `pdfjs-dist` (chunk async), `nuxt-security`, vitest + @vue/test-utils + Playwright.
- Backend : FastAPI, SQLAlchemy 2.x (text() Core), Alembic, Pydantic v2 (`extra='forbid'`), `pypdf` (déjà F22), `hashlib.sha256` pour empreintes.
**Storage** : PostgreSQL 16 (RLS via `app.current_account_id`) + storage abstraction `app/storage/local.py` (déjà F22). Nouvelle table `document_link_projet` ; nouvelles colonnes sur `document_entreprise` (`content_sha256`, `extraction_payload JSONB`, `extraction_confidence JSONB`, `extraction_validated_at`, `extraction_validated_by`, `deleted_at`, `purge_scheduled_at`).
**Testing** :
- Backend : `pytest --cov` (markers unit/integration), `httpx` TestClient. Coverage ≥ 80 % (`fail_under`).
- Frontend : `vitest run` (unit composants + stores + composables), Playwright (E2E parcours upload + validation + suppression + empty state + WCAG).
**Target Platform** : Frontend SPA SSR Nuxt 4 (port 3001) ; Backend FastAPI (port 8010). Production : Europe / Afrique de l'Ouest uniquement.
**Project Type** : web-service (backend FastAPI) + web-app (Nuxt 4) — voir CLAUDE.md.
**Performance Goals** : Liste 200 docs scrollable < 100 ms d'interaction perçue (virtualisation) ; recherche client < 1 s ; polling OCR ≤ 2 s, plafond 60 s ; upload 18 Mo en 4G en moins de 60 s par fichier.
**Constraints** : MIME whitelist `pdf/jpg/png/xlsx/docx` ; cap UI 20 Mo (le backend F22 admet jusqu'à 25 Mo — UI plus strict pour ne pas saturer la 4G) ; bottom sheet obligatoire pour toute saisie depuis le chat (P10).
**Scale/Scope** : Jusqu'à 200 documents/PME ; cap actuel F22 = 50/entreprise → **à élever à 200** par migration et update settings (voir Constitution Check & Complexity Tracking).

### Composants UI livrés

`pages/documents/index.vue`, `components/documents/{DocumentTable,UploadZone,DocPreviewDrawer,OcrSummarySheet,DocumentTagEditor,DocumentEmptyState,DuplicateChoiceSheet,DeleteConfirmModal}.vue`, `composables/{useDocumentsStore (via Pinia store), useOcrPolling, useFileFingerprint, useDocumentPreviewLazy}.ts`, `stores/documents.ts`, `services/api/documents.ts`, `types/documents.ts`, et un point d'embed `components/documents/ProjetDocumentsGrid.vue` consommé par F43.

## Constitution Check

*GATE: doit passer avant Phase 0. Re-évalué après Phase 1.*

Reference : [.specify/memory/constitution.md](../../.specify/memory/constitution.md) v1.0.0.

| # | Principle | Gate question for this feature | Status |
|---|-----------|--------------------------------|--------|
| P1 | Sourçage anti-hallucination | F50 ne crée pas de donnée catalogue. Les valeurs propagées par validation d'extraction (raison sociale, effectifs, CA) pointent vers le `document_entreprise` (rôle de Source primaire utilisateur). Le tool `extract_from_document` (post-MVP) suivra P9. | ✅ |
| P2 | Multi-tenant RLS | `document_link_projet` porte `account_id NOT NULL` + RLS `tenant_isolation` calquée sur `document_entreprise`/`document_projet`. Cross-tenant → 404 (déjà conforme côté F22). | ✅ |
| P3 | Audit log append-only | Toutes les mutations (upload, validation extraction, correction de champ, lien/délien projet, suppression, purge auto) journalisées via `record_audit` avec `source_of_change ∈ {manual, system}` (`system` pour la purge 30 j). | ✅ |
| P4 | Versioning + snapshot | F50 ne touche pas aux référentiels/critères/formules/candidatures. N/A. | ✅ |
| P5 | Money typé | Le champ extrait « Chiffre d'affaires » est stocké côté `entreprise` selon le modèle existant (`Money = {amount, currency}`) ; F50 ne contourne pas. | ✅ |
| P6 | Pivot Indicateur unique | Aucune valeur ESG nouvelle ; F50 alimente l'`entreprise`/`projet` via les champs existants — les indicateurs continueront de référencer le document comme source. | ✅ |
| P7 | Plateforme fermée aux intermédiaires | Aucun rôle nouveau. Endpoints `/me/...` réservés `get_current_pme` ; admins via routes `admin/` séparées. | ✅ |
| P8 | Édition manuelle + sync LLM | Chaque champ de la fiche d'extraction est éditable manuellement avant validation ; après validation, action « Re-corriger » invalide la validation et émet l'événement de mutation manuelle (EventBus côté front, audit côté back). | ✅ |
| P9 | Tool-use LLM fiable | F50 n'introduit aucun nouveau tool LLM ; l'extraction structurée est consommée depuis F22 (`extraction_payload`). Si un tool `extract_from_document` est ajouté plus tard, il devra suivre P9 (eval gating, schéma strict). Hors scope MVP. | ✅ (deferred) |
| P10 | UX bottom sheet | Le bottom sheet F39 est utilisé pour l'upload depuis le chat (`ask_file_upload`), la fiche d'extraction (`<ShowSummaryCard>`) et le choix dédoublonnage. Le bouton « Répondre librement » est présent dans tous les bottom sheets initiés par le chat. | ✅ |

### Contraintes techniques (rappel)

- Stack imposée : Nuxt 4 + FastAPI + PostgreSQL/pgvector ; LLM via OpenRouter ; embeddings Voyage `voyage-3.5` (1024 dim) — non utilisé en F50 MVP.
- Dev local : backend en `.venv`, Postgres seul service Docker, frontend `pnpm dev`.
- Hébergement production : Europe ou Afrique de l'Ouest uniquement.
- Conformité : RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450 (rétention soft-delete = 30 j).
- Langue : français par défaut.

**Aucune violation constitutionnelle.** Une seule entrée justifiée dans Complexity Tracking : élévation du cap F22 de 50 → 200 documents/entreprise.

## Project Structure

### Documentation (this feature)

```text
specs/050-documents-ocr-ui/
├── plan.md              # ce fichier
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── documents_api_extensions.md
│   └── documents_ui_contracts.md
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # généré par /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── entreprise/
│   │   ├── service.py                       # extension : empreinte SHA-256, payload structuré, validation, purge
│   │   ├── schemas.py                       # extension : DocumentOut + extraction_payload, ValidateExtractionIn
│   │   └── purge_job.py                     # NOUVEAU : tâche planifiée 30 j
│   ├── api/routes/
│   │   ├── entreprise_documents.py          # extension : POST /validate, POST /link-projet, DELETE /link-projet, GET /by-fingerprint
│   │   └── projets_documents.py             # extension : GET docs d'un projet via la table de liens M:N
│   └── audit/
│       └── recorder.py                      # réutilisé tel quel (`source_of_change='system'` pour la purge)
└── alembic/versions/
    └── 0050_documents_ui_extensions.py      # NOUVELLE migration : colonnes + table document_link_projet + index

frontend/
├── app/
│   ├── pages/
│   │   ├── documents/index.vue              # NOUVEAU
│   │   └── (embed dans pages/profil/projets/[id].vue existant)
│   ├── components/
│   │   └── documents/
│   │       ├── DocumentTable.vue            # virtualisée
│   │       ├── UploadZone.vue               # drag & drop, file input, queue 5
│   │       ├── DocPreviewDrawer.vue         # pdf.js lazy chunk + image fallback
│   │       ├── OcrSummarySheet.vue          # bottom sheet fiche extraction (F39)
│   │       ├── DocumentTagEditor.vue        # chips inline editable
│   │       ├── DocumentEmptyState.vue       # FR-007b
│   │       ├── ProjetDocumentsGrid.vue      # grille embed projet + FR-008b
│   │       ├── DuplicateChoiceSheet.vue     # FR-006b
│   │       └── DeleteConfirmModal.vue
│   ├── composables/
│   │   ├── useOcrPolling.ts                 # polling 2 s + plafond 60 s
│   │   ├── useFileFingerprint.ts            # SHA-256 via SubtleCrypto
│   │   └── useDocumentPreviewLazy.ts        # import dyn pdfjs-dist
│   ├── stores/
│   │   └── documents.ts                     # Pinia
│   ├── services/api/
│   │   └── documents.ts
│   └── types/
│       └── documents.ts
└── tests/
    ├── unit/
    │   ├── DocumentTable.test.ts
    │   ├── UploadZone.test.ts
    │   ├── OcrSummarySheet.test.ts
    │   ├── DuplicateChoiceSheet.test.ts
    │   └── composables/{useOcrPolling,useFileFingerprint}.test.ts
    └── e2e/
        ├── documents-upload.spec.ts         # parcours US1, US2, US7
        ├── documents-preview.spec.ts        # US3
        ├── documents-projet.spec.ts         # US4
        ├── documents-search-tags.spec.ts    # US5
        └── documents-a11y.spec.ts           # SC-009 (axe-core)
backend/tests/
├── unit/entreprise/
│   ├── test_fingerprint.py
│   ├── test_validate_extraction.py
│   ├── test_link_projet.py
│   └── test_purge_job.py
└── integration/
    └── test_documents_api_extensions.py
```

**Structure Decision** : web-service (backend) + web-app (frontend) conforme à CLAUDE.md. Aucune nouvelle racine. F50 étend les domaines existants `entreprise/`, `api/routes/`, et le dossier frontend `components/documents/` (n'existait pas — création).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Cap documents/entreprise élevé de 50 → 200 (settings backend + revue migration F22) | SC-005 nécessite un corpus de 200 docs ; le cap actuel F22 (50) est issu d'un MVP storage-only et ne couvre plus l'usage attendu d'F50 (multi-projet, chat-driven uploads). | Garder 50 imposerait à la PME de supprimer manuellement avant chaque nouvel upload, cassant SC-005, le partage M:N entre projets et la friction zero promise par le bottom sheet chat. Aucune alternative architecturale — seul le seuil change. |
| Table `document_link_projet` (M:N) en plus de `document_entreprise.entreprise_id` et `document_projet` | Q1 a tranché M:N : un même document partagé entre N projets sans duplication du fichier. La table `document_projet` existante reste pour les uploads originellement liés à un projet ; la nouvelle table de liens étend le partage à **tout** `document_entreprise` ET `document_projet` (référence polymorphe légère, voir data-model). | Ajouter un champ `projet_ids UUID[]` sur `document_entreprise` casse RLS multi-tenant et empêche les index efficaces. Forcer la duplication de fichier viole la promesse Q1 et fausse l'audit. |

## Phase 0 — Research (résolu dans `research.md`)

Voir [research.md](./research.md) pour les décisions techniques détaillées :

1. Empreinte de contenu — choix `SHA-256` via Web Crypto API client + Python `hashlib.sha256` serveur, recalculée serveur (jamais faire confiance à l'empreinte client seule pour la sécurité).
2. Polling OCR — choix interrogation périodique `setInterval` sur `GET /me/entreprise/documents/{id}` (réutilise F22) avec backoff doux 2 s → 4 s → 5 s, plafond 60 s, alternative SSE/WebSocket reportée post-MVP.
3. Lazy-load `pdfjs-dist` — import dynamique `() => import('pdfjs-dist')` à l'ouverture du drawer.
4. Virtualisation — choix `<TanStack Virtual>` (alignement écosystème) ou `vue3-virtual-scroller`. Décision retenue : `vue-virtual-scroller` (déjà éprouvé Vue 3, pas de surcoût Tailwind v4).
5. Empreinte d'audit pour purge 30 j — `source_of_change='system'`, ajout d'une convention dans `app/audit/recorder.py`.
6. Tâche planifiée — choix `APScheduler` interne FastAPI lifespan vs. cron externe. Décision MVP : commande Click `app/scripts/purge_documents.py` invocable via cron OS (Compose/host), évite d'introduire une nouvelle dépendance scheduler.
7. WCAG 2.1 AA — `axe-core` Playwright pour SC-009 ; pattern ARIA `role="alert"` (assertif) pour erreurs OCR, `role="status"` (poli) pour progrès.
8. Cap 50 → 200 — confirmation que la table actuelle indexée sur `(entreprise_id, deleted_at)` reste linéaire avec le nouveau seuil ; pas de risque de saturation pour la liste.

## Phase 1 — Design & Contracts (résolu)

- **`data-model.md`** — schéma des nouvelles colonnes `document_entreprise`, table `document_link_projet`, transitions d'état OCR & validation, RLS, index, soft-delete & purge.
- **`contracts/documents_api_extensions.md`** — extensions HTTP au-dessus de F22 : `POST /me/documents/{id}/validate`, `POST /me/documents/{id}/link-projet`, `DELETE /me/documents/{id}/link-projet/{projet_id}`, `GET /me/documents/by-fingerprint?sha256=…`, et clarification de la forme `extraction_payload`.
- **`contracts/documents_ui_contracts.md`** — contrats UI internes (props/events des composants F50, modèle Pinia, evenements EventBus avec le chat F41 et le projet F43).
- **`quickstart.md`** — comment lancer F50 en dev (migration, settings, premier upload, validation, partage M:N, purge manuelle 30 j).

CLAUDE.md mis à jour pour pointer vers `specs/050-documents-ocr-ui/plan.md` (entre marqueurs SPECKIT).
