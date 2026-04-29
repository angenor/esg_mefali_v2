# F01 — Initialisation Stack & Modèle Multi-tenant

**Phase** : 0 — Fondations transversales
**Modules brainstorm** : Architecture Technique, 0.7 (Mapping ESG)
**Dépendances** : aucune (point de départ)
**Estimation** : 2–3 jours

## Contexte et objectif

Mettre en place l'ossature technique sur laquelle toutes les autres features vont s'appuyer : structure du repo (frontend Nuxt 4 + backend FastAPI), base PostgreSQL+pgvector dockerisée, migrations, configuration multi-tenant, types Money, et le squelette du modèle conceptuel (Entreprise, Projet, Candidature, Offre, Indicateur, Référentiel, Source).

Cette feature ne livre pas encore de valeur métier directe à un utilisateur final, mais elle est **l'infrastructure obligatoire** sans laquelle aucune autre feature ne peut démarrer. Elle doit être suffisamment robuste pour porter 35+ features ultérieures sans refonte.

## Conventions d'environnement (impératives)

- **Backend FastAPI** : exécuté en local dans un `.venv` Python (à la racine du dossier `backend/`). Géré par `pip` (ou `uv` si l'équipe préfère, mais cohérence à choisir une fois). Pas de Dockerfile pour le backend en MVP.
- **PostgreSQL + pgvector** : **seul service dockerisé**. Un seul fichier `docker-compose.yml` à la racine du repo, exposant uniquement Postgres (port 5432, image `pgvector/pgvector:pg16`, volume nommé persistant).
- **Frontend Nuxt 4** : exécuté en local via `pnpm dev`. Pas de container.
- **Configuration** :
  - `.env` racine (gitignored) + `.env.example` versionné — partagé par backend, docker-compose et front Nuxt si pertinent.
  - Variables effectivement présentes (cf. `.env` actuel du dépôt) :
    - `DB_PASSWORD` (Postgres dockerisée)
    - `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` — OpenRouter par défaut, mais interchangeable (Anthropic, OpenAI, Mistral, Llama)
    - `APP_URL` (requis par OpenRouter pour identification de l'app)
    - `JWT_SECRET`
    - `VOYAGE_API_KEY` — embeddings Voyage AI
    - `REPLICATE_API_TOKEN` — Replicate (Whisper STT, consommé en F22)
  - Le client LLM est centralisé côté backend (un seul module `llm_client.py`) qui lit `LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL`. Le SDK utilisé est l'`openai` Python officiel (compatible OpenRouter). Changer de provider = changer 3 variables d'env, pas de code.
- **Migrations** : Alembic, exécuté depuis le `.venv` backend, ciblant la Postgres dockerisée.

## User Stories (input pour /speckit.specify)

### US1 — Démarrer l'environnement de dev en moins de 5 minutes (P1)
**En tant que** développeur rejoignant le projet,
**je veux** cloner le repo, créer mon `.venv`, lancer `docker compose up -d` pour Postgres, exécuter les migrations et lancer front+back,
**afin de** pouvoir contribuer immédiatement sans configuration manuelle complexe.

**Test indépendant** : un README/Makefile à la racine documente les 5 commandes (clone, .env copy, venv create + install, docker compose up, alembic upgrade, dev servers). Un nouveau dev y arrive en < 10 minutes.

### US2 — Le modèle de données respecte le mapping conceptuel du brainstorming (P1)
**En tant qu'**architecte,
**je veux** que les tables principales (Entreprise, Projet, Candidature, Offre, Fonds, Intermédiaire, Référentiel, Indicateur, Critère, Source, AuditLog, AccountUser) existent dès la première migration,
**afin de** garantir que toutes les features futures s'inscriront dans un modèle cohérent.

### US3 — Toute table métier porte `account_id` (P1)
**En tant que** garant de l'isolation multi-tenant,
**je veux** que chaque table métier porte une colonne `account_id NOT NULL` indexée,
**afin de** permettre l'activation de Row-Level Security en F02.

### US4 — Les valeurs financières sont typées Money (P2)
**En tant que** dev backend,
**je veux** un type composite `Money = {amount NUMERIC(18,2), currency CHAR(3)}` réutilisable,
**afin de** ne jamais stocker un montant sans devise et préparer le simulateur (F27) et le scoring crédit (F29).

### US5 — pgvector activé pour la mémoire LLM future (P2)
**En tant que** dev backend,
**je veux** que l'extension `pgvector` soit installée et qu'une migration crée la colonne `embedding vector(1536)` (ou dimension à confirmer) sur la table `chat_message`,
**afin de** ne pas avoir à migrer à chaud quand la Phase 3 (RAG) arrivera.

## Exigences fonctionnelles

- **FR-001** : Le repo contient `backend/` (FastAPI), `frontend/` (Nuxt 4), `docker-compose.yml` racine, `README.md` racine, `.gitignore` excluant `.env`, `.venv`, `node_modules`, etc.
- **FR-002** : `docker-compose.yml` ne contient **qu'un seul service** : `postgres` (image `pgvector/pgvector:pg16`, volume persistant, healthcheck, port 5432, credentials lus depuis env).
- **FR-003** : Le backend FastAPI démarre via `uvicorn` dans le `.venv`, expose un endpoint `/health` qui vérifie la connexion DB et renvoie `{status: "ok"}`.
- **FR-004** : Alembic est configuré avec une migration initiale qui crée toutes les entités principales du modèle conceptuel (a minima les colonnes `id`, `account_id`, `created_at`, `updated_at`, `created_by`, `version` quand pertinent, plus les FK structurantes).
- **FR-005** : Type composite `Money` (ou pattern équivalent : deux colonnes `_amount` + `_currency` avec contrainte CHECK) appliqué sur tous les champs montants.
- **FR-006** : Extension `pgvector` activée ; au moins une colonne `embedding vector(1024)` créée sur la table `chat_message`. **Dimension 1024** alignée avec `voyage-3.5` de Voyage AI (modèle d'embeddings multilingue retenu pour le français). Un wrapper backend `embeddings_client.py` lit `VOYAGE_API_KEY` et expose `embed(texts: list[str]) -> list[list[float]]`. Pas d'appel réel en F01 — juste le client + table prêts.
- **FR-007** : Frontend Nuxt 4 démarre en `pnpm dev`, propose une page d'accueil minimale qui appelle `/health` du backend pour confirmer que la stack répond.
- **FR-008** : Le `README.md` racine documente : pré-requis (Python 3.12+, Node 20+, Docker, pnpm), commandes de setup, commandes de dev, structure des dossiers.
- **FR-009** : Pinia, TailwindCSS v4, chart.js, mermaid, Leaflet, gsap, fontawesome, toast-ui/editor sont installés et configurés (TailwindCSS chargé, Pinia plugin enregistré). Pas de page de démo nécessaire — juste la dispo.
- **FR-010** : LangGraph (et LangChain comme utilitaire) est dans `requirements.txt` côté backend, version épinglée.
- **FR-011** : Configuration `httpx` ou client OpenRouter centralisé côté backend, lit la clé depuis `OPENROUTER_API_KEY` env var (sans appel réel pour MVP cette feature).

## Exigences non-fonctionnelles

- **NFR-001** : Aucun secret en dur dans le code ou dans les fichiers versionnés. Tout passe par `.env` et son `.env.example`.
- **NFR-002** : Le repo doit pouvoir être cloné sur Linux, macOS et WSL2 sans modification.
- **NFR-003** : Les migrations Alembic sont **idempotentes** et passent en `upgrade head` puis `downgrade base` puis `upgrade head` sans erreur.
- **NFR-004** : Le port Postgres exposé par Docker est paramétrable (`POSTGRES_PORT` env var) pour éviter les conflits de port chez les devs.

## Entités clés (modèle conceptuel — squelette)

- **Account** (id, name, created_at) — racine multi-tenant.
- **AccountUser** (id, account_id, email, password_hash, role) — F02 enrichira.
- **Entreprise** (id, account_id, name, secteur, taille_ca_money, taille_effectifs, localisation, gouvernance, pratiques_actuelles_json, version, …) — 1 par account.
- **Projet** (id, account_id, entreprise_id, nom, description, type_impact, maturite, montant_recherche_money, structure_financement, indicateurs_impact_json, localisation, statut, version, …).
- **FondsSource** (id, name, organisation, type, thematique, instruments, plafond_money, plancher_money, eligibilite_geo, submission_mode, version, status_draft_published, …).
- **Intermediaire** (id, name, type, pays, contact, frais_json, delais_json, version, status, …).
- **Accreditation** (intermediaire_id, fonds_id, date_debut, date_fin, plafond_money, source_id).
- **Offre** (id, fonds_id, intermediaire_id, accepted_languages, version, status, …).
- **Candidature** (id, account_id, projet_id, offre_id, statut, snapshot_json, soumission_at, version).
- **Referentiel** (id, name, version, valid_from, valid_to, status, …).
- **Indicateur** (id, name, definition, unite, status, …).
- **Critere** (id, offre_id ou referentiel_id, expression_json, indicateur_ids, source_id, …).
- **Source** (id, url, title, publisher, version, date_publi, page, section, captured_at, captured_by, verified_by, verification_status, …) — F03 enrichira.
- **AuditLog** (id, user_id, account_id, timestamp, entity_type, entity_id, field, old_value, new_value, source_of_change) — F04 enrichira.
- **ChatMessage** (id, account_id, user_id, role, content, payload_json, embedding vector(...), created_at).
- **DocumentRequis** (id, fonds_id ou intermediaire_id, name, source_id, ...).
- **FacteurEmission** (id, name, valeur, unite, pays, source_id, version).
- **Template** (id, offre_id, name, structure_json, source_id, ...).

> Toutes les colonnes structurantes ne sont pas listées ici — la spec détaillée par feature complétera. L'enjeu de F01 est que **les tables existent et que les FK soient cohérentes**.

## Success Criteria

- **SC-001** : Un dev sans contexte préalable monte la stack en < 10 min en suivant le README.
- **SC-002** : `alembic upgrade head` applique 1 migration initiale en < 30 secondes sur Postgres dockerisée.
- **SC-003** : `GET /health` répond 200 avec `{status:"ok",db:"ok"}` quand Postgres tourne, 503 sinon.
- **SC-004** : `pnpm dev` lance le front sans erreur et la page d'accueil affiche le statut backend.
- **SC-005** : `docker compose down -v && docker compose up -d && alembic upgrade head` reproduit un environnement vierge identique.

## Hors-scope explicite

- Auth, login, register → **F02**
- RLS et politiques de sécurité → **F02**
- Sources verrouillées NOT NULL et tools LLM cite_source → **F03**
- Audit log fonctionnel → **F04**
- Page Mes données / consentements → **F05**
- Backend dockerisé, Redis, Celery, MinIO → post-MVP

## Risques et points de vigilance

- **Type Money** : si Postgres ne supporte pas bien les types composites côté ORM (SQLAlchemy), choisir le pattern "deux colonnes + CHECK contrainte" plutôt qu'un type composite natif. À trancher en `/speckit.clarify`.
- **Dimension du vecteur pgvector** : 1536 (text-embedding-3-small OpenAI) ou 1024 (modèle local) ? À confirmer en clarify, mais ne pas bloquer cette feature : créer la colonne avec une dimension par défaut migrable plus tard.
- **Versionning** : ne pas activer `valid_from`/`valid_to` sur toutes les tables maintenant — F04 le fera. Mais prévoir la colonne `version INT DEFAULT 1` partout pour ne pas avoir à migrer.
- **Côté frontend**, ne pas créer de pages métier en F01 — juste l'ossature et les libs UI installées.
