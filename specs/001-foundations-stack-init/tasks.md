---
description: "Task list for F01 — Initialisation Stack & Modèle Multi-tenant"
---

# Tasks: F01 — Initialisation Stack & Modèle Multi-tenant

**Input**: Design documents from `/specs/001-foundations-stack-init/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/health.openapi.yaml, quickstart.md

**Tests**: Inclus — la spec exige des tests automatisés (NFR-003 idempotence migrations, SC-003 health 200/503, et tests config fail-fast).

**Organization**: Tâches groupées par user story (US1–US5) pour permettre validation indépendante.

## Format: `[ID] [P?] [Story] Description`

- **[P]** : peut s'exécuter en parallèle (fichiers différents, pas de dépendance bloquante)
- **[Story]** : US1, US2, US3, US4, US5 (sinon Setup/Foundational/Polish)

## Path Conventions

- Repo racine : `/Users/mac/Documents/projets/2025/esg_mefali_v2/`
- Backend : `backend/`
- Frontend : `frontend/`
- Postgres dockerisée : `docker-compose.yml` racine

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialiser la structure de repo et les fichiers de configuration racine.

- [X] T001 Créer la structure racine du repo : dossiers `backend/`, `frontend/`, fichiers `README.md`, `.gitignore` (excluant `.env`, `.venv`, `node_modules`, `__pycache__`, `.nuxt`, `dist`, `*.pyc`)
- [X] T002 [P] Créer `.env.example` à la racine avec toutes les variables documentées (`DB_PASSWORD`, `POSTGRES_PORT`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `APP_URL`, `JWT_SECRET`, `VOYAGE_API_KEY`, `REPLICATE_API_TOKEN`) — sans valeurs réelles
- [X] T003 [P] Créer un `Makefile` racine optionnel exposant `make setup`, `make db-up`, `make db-down`, `make migrate`, `make backend`, `make frontend`, `make test`
- [X] T004 Créer `docker-compose.yml` racine avec UN SEUL service `postgres` (image `pgvector/pgvector:pg16`, volume nommé `pgdata`, healthcheck `pg_isready`, port `${POSTGRES_PORT:-5432}:5432`, credentials lus depuis env, `POSTGRES_DB=esg_mefali`, `POSTGRES_USER=esg`, `POSTGRES_PASSWORD=${DB_PASSWORD}`)

**Checkpoint Setup** : Repo cloné contient l'ossature minimale ; `docker compose up -d` lance Postgres healthy.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend bootstrap et config minimale partagée par toutes les stories.

**CRITICAL** : Aucune user story ne peut démarrer avant cette phase.

- [X] T005 Créer `backend/requirements.txt` avec versions épinglées : `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]`, `pydantic>=2`, `pydantic-settings`, `python-dotenv`, `openai`, `httpx`, `langgraph`, `langchain`, `voyageai` (ou commenté si SDK direct), plus dev : `pytest`, `pytest-asyncio`, `ruff`
- [X] T006 [P] Créer `backend/pyproject.toml` configurant `ruff` (line-length 100) et `pytest` (testpaths=["tests"], asyncio_mode="auto")
- [X] T007 Créer `backend/app/__init__.py` (vide) puis `backend/app/config.py` exposant `Settings(BaseSettings)` Pydantic v2 lisant `.env`, avec champs obligatoires (`DB_PASSWORD`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `APP_URL`, `JWT_SECRET`, `VOYAGE_API_KEY`, `REPLICATE_API_TOKEN`) et optionnels (`POSTGRES_PORT=5432`, `POSTGRES_HOST=localhost`, `POSTGRES_DB=esg_mefali`, `POSTGRES_USER=esg`). Utiliser `lru_cache` pour `get_settings()`. Fail-fast au boot.
- [X] T008 [P] Créer `backend/app/db.py` exposant `engine = create_engine(DATABASE_URL)` et `SessionLocal = sessionmaker(...)` + une dépendance FastAPI `get_db()`. URL construite à partir de Settings.
- [X] T009 Créer `backend/alembic.ini` (config standard) et `backend/alembic/env.py` lisant `DATABASE_URL` via `app.config.get_settings()` (pas de duplication d'URL)
- [X] T010 Initialiser le dossier `backend/alembic/versions/` (vide pour l'instant — la migration arrive en US2)

**Checkpoint Foundational** : `cd backend && python -c "from app.config import get_settings; print(get_settings().LLM_MODEL)"` fonctionne ; `alembic --help` répond.

---

## Phase 3: User Story 1 — Démarrer l'environnement de dev rapidement (Priority: P1) — MVP

**Goal** : Un dev clone le repo, suit le README, obtient backend `/health` 200 + frontend qui affiche le statut, en < 10 min.

**Independent Test** : Sur poste vierge, suivre `quickstart.md` et obtenir `curl localhost:8000/health` → 200 et `http://localhost:3000` affichant "backend OK".

### Tests for User Story 1

- [X] T011 [P] [US1] Test contract `/health` 200 dans `backend/tests/test_health.py` : `client.get("/health")` retourne 200 + body `{"status":"ok","db":"ok"}` (DB up)
- [X] T012 [P] [US1] Test contract `/health` 503 dans `backend/tests/test_health.py` : monkeypatch DB session pour raise OperationalError → response 503 + body `{"status":"degraded","db":"unreachable"}`
- [X] T013 [P] [US1] Test fail-fast config dans `backend/tests/test_config.py` : pop `DB_PASSWORD` de l'env → `get_settings()` lève `ValidationError`

### Implementation for User Story 1

- [X] T014 [US1] Implémenter `backend/app/main.py` : `app = FastAPI(title="ESG Mefali API")`, route `GET /health` qui exécute `SELECT 1` via SQLAlchemy session avec `statement_timeout` 2 s, retourne 200/503 selon résultat. CORS middleware autorise `http://localhost:3000`.
- [X] T015 [P] [US1] Créer `backend/app/llm_client.py` : factory `get_llm_client()` retournant `openai.OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)`. Aucun appel réel. Docstring documentant l'usage F14+.
- [X] T016 [P] [US1] Créer `backend/app/embeddings_client.py` : fonction `embed(texts: list[str]) -> list[list[float]]`. Implémentation appelle `httpx.post("https://api.voyageai.com/v1/embeddings", headers=Bearer settings.VOYAGE_API_KEY, json={"input": texts, "model": "voyage-3.5"})`. Lève `RuntimeError("VOYAGE_API_KEY missing")` si clé absente. Aucun appel exécuté en F01 (fonction présente, testable mais non câblée).
- [X] T017 [P] [US1] Initialiser le projet Nuxt 4 dans `frontend/` : `pnpm dlx nuxi@latest init .` puis ajouter dépendances : `pinia @pinia/nuxt tailwindcss @tailwindcss/vite chart.js mermaid leaflet gsap driver.js @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/vue-fontawesome @toast-ui/editor @langchain/langgraph`. Générer `pnpm-lock.yaml`.
- [X] T018 [US1] Configurer `frontend/nuxt.config.ts` : enregistrer `@pinia/nuxt`, ajouter le plugin Vite `@tailwindcss/vite`, définir `runtimeConfig.public.apiBase = process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000'`
- [X] T019 [P] [US1] Créer `frontend/assets/css/main.css` avec `@import "tailwindcss";` et l'importer dans `nuxt.config.ts` via `css: ["~/assets/css/main.css"]`
- [X] T020 [P] [US1] Créer `frontend/composables/useHealth.ts` : exporte `useHealth()` qui fait `useFetch(\`\${useRuntimeConfig().public.apiBase}/health\`, { lazy: true })`
- [X] T021 [US1] Implémenter `frontend/pages/index.vue` : appelle `useHealth()`, affiche "Backend OK" si `status==='ok'`, "Backend indisponible" sinon, en français. Tailwind pour mise en forme minimale.
- [X] T022 [US1] Écrire `README.md` racine couvrant : pré-requis, setup en 5 commandes, structure des dossiers, déploiement Europe/Afrique de l'Ouest uniquement, lien vers `specs/001-foundations-stack-init/quickstart.md`
- [X] T023 [US1] Vérifier manuellement (ou via script) que la séquence du `quickstart.md` complète sous 10 min sur poste vierge — documenter dans le README une checklist "Premier démarrage"

**Checkpoint US1** : Backend répond `/health`, frontend affiche le statut, dev arrive en < 10 min via README. **MVP livrable.**

---

## Phase 4: User Story 2 — Modèle de données conforme au mapping conceptuel (Priority: P1)

**Goal** : Migration initiale Alembic crée les 18 tables avec colonnes communes et FK cohérentes.

**Independent Test** : Sur DB vierge, `alembic upgrade head` puis inspection schéma : 18 tables présentes avec colonnes communes (id UUID, version, created_at, etc.).

### Tests for User Story 2

- [X] T024 [P] [US2] Test idempotence dans `backend/tests/test_migration_idempotency.py` : `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` réussit sans erreur (utilise pytest-postgresql ou DB de test dédiée)
- [X] T025 [P] [US2] Test de présence des tables dans `backend/tests/test_schema.py` : après upgrade, requête `information_schema.tables` confirme les 18 tables attendues
- [X] T026 [P] [US2] Test de présence des colonnes communes dans `backend/tests/test_schema.py` : pour chaque table métier, vérifier présence de `id`, `account_id` (sauf account), `created_at`, `updated_at`, `version`, `deleted_at` (où applicable)

### Implementation for User Story 2

- [X] T027 [US2] Créer la migration `backend/alembic/versions/0001_initial_schema.py` qui exécute en début de `upgrade()` : `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")` puis `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`. `downgrade()` ne supprime PAS les extensions (partagées).
- [X] T028 [US2] Dans la même migration `0001`, créer les tables CATALOGUE (sans `account_id`) dans cet ordre pour respecter les FK : `source`, `account` (avant `account_user`), puis `referentiel`, `indicateur`, `intermediaire`, `fonds_source`, `accreditation`, `offre`, `critere`, `document_requis`, `facteur_emission`, `template`. Pour chaque table : colonnes typées selon `data-model.md`, contraintes Money CHECK où applicable, FK conformes.
- [X] T029 [US2] Dans la même migration `0001`, créer les tables MÉTIER (avec `account_id NOT NULL` indexé) dans l'ordre : `account_user`, `entreprise`, `projet`, `candidature`, `chat_message` (avec `embedding vector(1024)`), `audit_log`. Toutes portent les colonnes communes (`id UUID DEFAULT gen_random_uuid()`, `created_at`, `updated_at`, `created_by` FK nullable, `version`, `deleted_at` sauf audit_log).
- [X] T030 [US2] Ajouter dans la même migration les contraintes CHECK Money sur : `entreprise.taille_ca_*`, `projet.montant_recherche_*`, `fonds_source.plafond_*`, `fonds_source.plancher_*`, `accreditation.plafond_*`. Format : `CHECK ((amount IS NULL AND currency IS NULL) OR (amount IS NOT NULL AND currency IS NOT NULL AND char_length(currency)=3))`.
- [X] T031 [US2] Ajouter dans la même migration les CHECK exclusifs : `critere` (exactement un de offre_id/referentiel_id non-NULL), `document_requis` (au moins un de fonds_id/intermediaire_id), et le CHECK `audit_log.source_of_change IN ('manual','llm','import','admin')`
- [X] T032 [US2] Ajouter dans la même migration les INDEX BTREE sur `account_id` pour les 6 tables métier, plus index sur `audit_log.timestamp`, `audit_log.entity_type`, `audit_log.entity_id`, et UNIQUE INDEX sur `account_user.email`
- [X] T033 [US2] Implémenter `downgrade()` de la migration 0001 : `op.drop_table()` dans l'ordre INVERSE des créations pour respecter les FK
- [X] T034 [US2] Documenter en commentaire de tête de la migration 0001 : peg FCFA-EUR fixe `655,957`, devise par défaut `XOF` pour seeds, et la liste des contraintes qui seront enforced en F02 (RLS), F03 (source_id NOT NULL), F04 (audit triggers + role enum)

**Checkpoint US2** : `alembic upgrade head` crée les 18 tables avec colonnes communes, FK et CHECK ; idempotence vérifiée par T024.

---

## Phase 5: User Story 3 — Isolation multi-tenant préparée (Priority: P1)

**Goal** : Toute table métier porte `account_id NOT NULL` indexée, prête pour activation RLS en F02.

**Independent Test** : Inspection schéma confirme `account_id` non-nullable + index sur les 6 tables métier ; tentative d'INSERT sans `account_id` rejetée par la base.

### Tests for User Story 3

- [X] T035 [P] [US3] Test dans `backend/tests/test_schema.py` : pour chaque table de la liste {entreprise, projet, candidature, chat_message, audit_log, account_user}, requête `information_schema.columns` confirme `account_id` est NOT NULL
- [X] T036 [P] [US3] Test dans `backend/tests/test_schema.py` : pour chaque table métier, requête `pg_indexes` confirme la présence d'un index sur `account_id`
- [X] T037 [P] [US3] Test négatif dans `backend/tests/test_schema.py` : un INSERT brut sur `entreprise` sans `account_id` lève `IntegrityError`
- [X] T038 [P] [US3] Test exclusion dans `backend/tests/test_schema.py` : pour chaque table partagée {source, referentiel, indicateur, fonds_source, intermediaire, accreditation, offre, critere, document_requis, facteur_emission, template}, vérifier qu'AUCUNE colonne `account_id` n'existe

### Implementation for User Story 3

- [X] T039 [US3] Vérifier via revue manuelle du fichier `backend/alembic/versions/0001_initial_schema.py` (issu de US2) que les contraintes `account_id NOT NULL` + index sont bien présentes sur les 6 tables métier (corriger sinon)
- [X] T040 [US3] Ajouter dans le commentaire de tête de la migration 0001 une note : "RLS sera activée en F02 ; en F01 le schéma est seulement préparé. Les politiques RLS attendues utilisent `current_setting('app.current_account_id')::uuid`."

**Checkpoint US3** : Tests T035–T038 passent ; le schéma est prêt pour l'activation RLS de F02.

---

## Phase 6: User Story 4 — Valeurs financières typées Money (Priority: P2)

**Goal** : Tous les champs montants suivent le pattern `_amount` + `_currency` + CHECK ; insertion incohérente rejetée.

**Independent Test** : INSERT avec amount sans currency → rejet ; INSERT avec les deux NULL → succès ; INSERT avec les deux fournis (XOF/EUR/USD) → succès.

### Tests for User Story 4

- [X] T041 [P] [US4] Test rejet `taille_ca_amount` sans currency dans `backend/tests/test_money_constraints.py`
- [X] T042 [P] [US4] Test acceptation deux NULL dans `backend/tests/test_money_constraints.py` (entreprise + projet + fonds_source)
- [X] T043 [P] [US4] Test acceptation valeurs valides (XOF/EUR/USD) dans `backend/tests/test_money_constraints.py` pour `montant_recherche_*`, `plafond_*`, `plancher_*`

### Implementation for User Story 4

- [X] T044 [US4] Vérifier dans la migration 0001 (issue US2) la présence des CHECK Money sur toutes les colonnes monétaires identifiées (`entreprise.taille_ca_*`, `projet.montant_recherche_*`, `fonds_source.plafond_*`, `fonds_source.plancher_*`, `accreditation.plafond_*`)
- [X] T045 [US4] Documenter dans `backend/app/db.py` (commentaire) le pattern Money + le peg FCFA-EUR fixe (`FX_PEG_XOF_EUR = Decimal("655.957")`) + la devise par défaut documentée pour seeds (`XOF`). Pas d'usage en F01, juste documentation pour F27/F29.

**Checkpoint US4** : Tests Money passent ; pattern documenté.

---

## Phase 7: User Story 5 — pgvector activé pour mémoire LLM future (Priority: P2)

**Goal** : Extension `vector` activée, colonne `chat_message.embedding vector(1024)`, module `embeddings_client.py` importable.

**Independent Test** : `SELECT * FROM pg_extension WHERE extname='vector'` retourne 1 ligne ; `chat_message.embedding` typé `vector(1024)` ; `embeddings_client.embed(["x"])` lève RuntimeError clair sans VOYAGE_API_KEY.

### Tests for User Story 5

- [X] T046 [P] [US5] Test dans `backend/tests/test_pgvector.py` : `SELECT * FROM pg_extension WHERE extname='vector'` retourne au moins 1 ligne
- [X] T047 [P] [US5] Test dans `backend/tests/test_pgvector.py` : requête `information_schema.columns` sur `chat_message.embedding` retourne `udt_name='vector'` et la dimension est 1024 (via `pg_typeof` ou `format_type`)
- [X] T048 [P] [US5] Test dans `backend/tests/test_embeddings_client.py` : monkeypatch pour pop `VOYAGE_API_KEY` → `embed(["test"])` lève `RuntimeError` mentionnant `VOYAGE_API_KEY`

### Implementation for User Story 5

- [X] T049 [US5] Vérifier dans la migration 0001 que `CREATE EXTENSION IF NOT EXISTS vector` est exécuté avant `chat_message`, et que `chat_message.embedding` est bien `vector(1024)` (corriger sinon)
- [X] T050 [US5] Affiner `backend/app/embeddings_client.py` (issu de US1 T016) : ajouter docstring complet avec exemples, type hints stricts, bonne gestion erreurs HTTP

**Checkpoint US5** : Tests pgvector + embeddings_client passent ; infrastructure prête pour F18 (RAG).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Nettoyage final et validation complète.

- [X] T051 [P] Lancer `ruff check backend/` et corriger toutes les issues
- [X] T052 [P] Lancer `pytest backend/tests/` et vérifier 100% de passage
- [X] T053 [P] Vérifier que `grep -r "API_KEY\|PASSWORD\|SECRET" backend/ frontend/ | grep -v ".env" | grep -v "tests/" | grep -v "node_modules"` ne retourne aucun secret hardcodé (SC-006)
- [X] T054 Exécuter le scénario complet de `specs/001-foundations-stack-init/quickstart.md` sur DB vierge (down -v / up -d / migrate / curl health) et chronométrer : valider SC-001 (<10 min), SC-002 (<30s migration), SC-005 (reset reproductible)
- [X] T055 [P] Compléter `README.md` racine avec section "Tests" et "Dépannage"
- [X] T056 [P] Mettre à jour `specs/001-foundations-stack-init/checklists/requirements.md` : cocher tous les items, ajouter note "F01 livré et validé"
- [X] T057 Smoke test E2E manuel : ouvrir `http://localhost:3000`, vérifier que le statut backend s'affiche en < 3 s (SC-004)

**Checkpoint final** : Tous les SC validés, tous les FR/NFR couverts, F01 prêt à servir de socle pour F02–F35.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** : pas de dépendance — démarre immédiatement
- **Foundational (Phase 2)** : dépend de Setup — bloque toutes les user stories
- **US1 (Phase 3)** : dépend de Foundational — peut démarrer en premier (MVP)
- **US2 (Phase 4)** : dépend de Foundational — indépendante de US1, mais nécessaire pour US3/US4/US5 car US2 crée la migration partagée
- **US3 (Phase 5)** : dépend de US2 (migration créée)
- **US4 (Phase 6)** : dépend de US2 (CHECK Money posés dans la même migration)
- **US5 (Phase 7)** : dépend de US2 (extension vector + colonne embedding posées dans la même migration) ET de US1 (T016 a posé `embeddings_client.py`)
- **Polish (Phase 8)** : dépend de toutes les autres

### User Story Dependencies (résumé)

- US1 : démarre dès la fin de Phase 2.
- US2 : démarre dès la fin de Phase 2 (peut être parallèle à US1 si 2 devs).
- US3, US4, US5 : démarrent dès la fin de US2.

### Within Each User Story

- Tests (T011, T012, T013, T024, T025, T026, T035–T038, T041–T043, T046–T048) écrits AVANT implémentation et doivent ÉCHOUER initialement.
- Implémentation suit dans l'ordre indiqué.

### Parallel Opportunities

- T002, T003 (Setup) parallèles entre eux.
- T006, T008 (Foundational) parallèles à T007 mais T009/T010 séquentiels après T007.
- US1 vs US2 : exécutables en parallèle par 2 devs après Phase 2.
- T015, T016, T017, T019, T020 (US1) parallèles entre eux.
- Tous les tests `[P]` au sein d'une même US peuvent tourner en parallèle.

---

## Parallel Example: User Story 1

```bash
# Tests US1 en parallèle :
Task: "Test /health 200 dans backend/tests/test_health.py"
Task: "Test /health 503 dans backend/tests/test_health.py"
Task: "Test fail-fast config dans backend/tests/test_config.py"

# Implémentation US1 en parallèle (après main.py) :
Task: "llm_client.py dans backend/app/"
Task: "embeddings_client.py dans backend/app/"
Task: "Init Nuxt frontend/"
Task: "main.css TailwindCSS"
Task: "useHealth composable"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Phase 1 Setup
2. Phase 2 Foundational
3. Phase 3 US1 (backend `/health` + frontend page)
4. Phase 4 US2 (migration initiale)
5. **STOP & VALIDATE** : `quickstart.md` complet en < 10 min — MVP livrable.

### Incremental Delivery

1. Setup + Foundational → Foundation prête.
2. US1 + US2 → MVP démarrage stack reproductible.
3. US3 → Multi-tenant prêt pour F02.
4. US4 → Money typé prêt pour F27/F29.
5. US5 → pgvector prêt pour F18.
6. Polish → F01 prêt comme socle pour F02–F35.

### Parallel Team Strategy

Avec 2 devs :
- Dev A : US1 (backend health + frontend bootstrap)
- Dev B : US2 (migration initiale + tests schéma)
- Puis Dev A reprend US3+US4 ; Dev B reprend US5 ; Polish ensemble.

---

## Notes

- [P] = fichiers différents, exécutable en parallèle.
- Chaque user story est livrable indépendamment et apporte une valeur testable.
- Tous les tests doivent ÉCHOUER avant l'implémentation correspondante (TDD).
- Aucune feature applicative n'est livrée en F01 — l'objectif est l'infrastructure.
- Hébergement production : Europe ou Afrique de l'Ouest UNIQUEMENT (constitution v1.0.0).
- F02 prendra le relais pour activer RLS, créer les rôles `pme`/`admin`, l'auth JWT, le login.
