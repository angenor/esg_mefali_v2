# Feature Specification: F01 — Initialisation Stack & Modèle Multi-tenant

**Feature Branch**: `001-foundations-stack-init`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F01 — Initialisation Stack & Modèle Multi-tenant. Phase 0 — Fondations transversales. Mettre en place l'ossature technique (frontend Nuxt 4 + backend FastAPI), base PostgreSQL+pgvector dockerisée, migrations Alembic, configuration multi-tenant, types Money, squelette du modèle conceptuel. Infrastructure obligatoire pour 35+ features ultérieures."

## Clarifications

### Session 2026-04-29

- Q: Type d'identifiant primaire pour toutes les entités (id) ? → A: UUID v4 (`uuid` PostgreSQL natif, généré côté DB via `gen_random_uuid()` de l'extension `pgcrypto`)
- Q: Type et nullabilité de `created_by` sur les tables métier ? → A: FK nullable vers `account_user.id` (NULL autorisé pour créations système / migrations / seeds)
- Q: Stratégie de suppression sur les tables métier en F01 ? → A: Soft delete préparé — colonne `deleted_at TIMESTAMP NULL` ajoutée sur toutes les tables métier (Entreprise, Projet, Candidature, ChatMessage, AccountUser). AuditLog reste append-only sans soft delete. Hard delete possible mais non recommandé.
- Q: Devise par défaut implicite si une seed/test omet `_currency` ? → A: `XOF` (Franc CFA UEMOA) — devise par défaut documentée. Aucun défaut imposé en base : la contrainte CHECK exige les deux colonnes ensemble ou les deux NULL.
- Q: Stratégie de vérification DB dans `/health` ? → A: `SELECT 1` avec timeout 2 secondes ; succès → 200 `{status:"ok",db:"ok"}`, échec/timeout → 503 `{status:"degraded",db:"unreachable"}`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Démarrer l'environnement de développement rapidement (Priority: P1)

Un développeur rejoignant le projet clone le dépôt, copie `.env.example` en `.env`, crée son `.venv` Python, lance la base PostgreSQL via Docker, exécute les migrations Alembic, puis démarre le backend FastAPI et le frontend Nuxt en local. L'ensemble fonctionne en moins de 10 minutes sans configuration manuelle additionnelle.

**Why this priority**: Sans environnement de dev reproductible, aucune autre feature ne peut être développée. C'est la condition d'accès au reste du projet.

**Independent Test**: Sur une machine vierge (Linux, macOS ou WSL2), un développeur suivant le `README.md` arrive à un backend qui répond `/health` et un frontend qui affiche le statut backend, sans intervention humaine externe, en moins de 10 minutes mesurées.

**Acceptance Scenarios**:

1. **Given** un repo fraîchement cloné, **When** le développeur exécute la séquence documentée (copie `.env.example`, crée venv, `pip install`, `docker compose up -d`, `alembic upgrade head`, `uvicorn`, `pnpm install && pnpm dev`), **Then** le backend répond 200 sur `/health` et le frontend affiche "backend OK" sur sa page d'accueil.
2. **Given** un environnement déjà monté, **When** le développeur exécute `docker compose down -v && docker compose up -d && alembic upgrade head`, **Then** la base est recréée à l'identique sans erreur.
3. **Given** un poste avec un autre service sur le port 5432, **When** le développeur définit `POSTGRES_PORT=5433` dans `.env`, **Then** la stack démarre sans conflit.

---

### User Story 2 - Modèle de données conforme au mapping conceptuel (Priority: P1)

L'architecte technique vérifie qu'après la première migration, toutes les entités du mapping conceptuel (Account, AccountUser, Entreprise, Projet, FondsSource, Intermediaire, Accreditation, Offre, Candidature, Referentiel, Indicateur, Critere, Source, AuditLog, ChatMessage, DocumentRequis, FacteurEmission, Template) existent dans la base avec leurs colonnes structurantes et leurs clés étrangères cohérentes.

**Why this priority**: Les 35+ features futures s'appuient toutes sur ce modèle. Une omission ou incohérence ici provoque des refontes coûteuses plus tard.

**Independent Test**: Après `alembic upgrade head` sur une base vierge, l'inspection du schéma (via `\dt` psql ou requête `information_schema`) liste toutes les tables attendues avec leurs colonnes communes (`id`, `account_id` pour les tables métier, `created_at`, `updated_at`, `created_by`, `version`).

**Acceptance Scenarios**:

1. **Given** une base vierge, **When** `alembic upgrade head` est exécuté, **Then** les 18 tables listées dans Key Entities existent et leurs FK sont cohérentes.
2. **Given** la migration appliquée, **When** on inspecte chaque table métier, **Then** chacune porte `id`, `account_id NOT NULL` (sauf Account et tables de référence pures), `created_at`, `updated_at`, `created_by`, `version INT DEFAULT 1`.
3. **Given** la migration appliquée, **When** `alembic downgrade base` puis `alembic upgrade head`, **Then** aucune erreur n'est levée et le schéma final est identique.

---

### User Story 3 - Isolation multi-tenant préparée (Priority: P1)

Toute table métier contient une colonne `account_id` indexée et non-nullable, prête à recevoir l'activation des politiques Row-Level Security (RLS) en F02. Les tables transversales (référentiels publics, sources, facteurs d'émission) sont explicitement marquées comme partagées (sans `account_id`).

**Why this priority**: Le multi-tenant est un invariant non négociable. Ajouter `account_id` après-coup sur des tables peuplées est risqué et coûteux.

**Independent Test**: Une requête SQL liste toutes les tables et confirme que celles considérées "métier" (Entreprise, Projet, Candidature, ChatMessage, AuditLog, AccountUser) portent `account_id NOT NULL` et que la colonne est indexée. Les tables partagées (Source, Referentiel, Indicateur, FondsSource, Intermediaire, FacteurEmission, Template, Offre, Accreditation, DocumentRequis, Critere) sont documentées comme telles dans le code.

**Acceptance Scenarios**:

1. **Given** la migration initiale appliquée, **When** on inspecte les colonnes de Entreprise, Projet, Candidature, ChatMessage, AuditLog, AccountUser, **Then** chacune porte `account_id` non-nullable avec un index.
2. **Given** la migration initiale appliquée, **When** on tente d'insérer une ligne dans Entreprise sans `account_id`, **Then** la base rejette l'insertion.

---

### User Story 4 - Valeurs financières typées Money (Priority: P2)

Tous les champs représentant un montant monétaire dans le modèle utilisent un pattern Money cohérent : un couple (`*_amount NUMERIC(18,2)`, `*_currency CHAR(3)`) avec une contrainte CHECK garantissant que les deux sont fournis ensemble ou tous deux nuls. Le peg FCFA-EUR fixe (655,957) est documenté pour usage par les features ultérieures (F27 simulateur, F29 scoring crédit).

**Why this priority**: Stocker un montant sans devise est un défaut de conception fréquent qui se paie cher en multi-devises (XOF, EUR, USD). Adopter le pattern dès F01 évite la dette.

**Independent Test**: Inspection du schéma : toutes les colonnes représentant un montant (ex. `taille_ca_amount`/`taille_ca_currency` sur Entreprise, `montant_recherche_amount`/`montant_recherche_currency` sur Projet, `plafond_amount`/`plafond_currency` sur FondsSource, etc.) suivent le pattern, et une contrainte CHECK existe.

**Acceptance Scenarios**:

1. **Given** la migration appliquée, **When** on insère une ligne avec `taille_ca_amount` mais sans `taille_ca_currency`, **Then** la base rejette l'insertion.
2. **Given** la migration appliquée, **When** on insère une ligne avec les deux à NULL, **Then** l'insertion réussit.

---

### User Story 5 - pgvector activé pour la mémoire LLM future (Priority: P2)

L'extension `pgvector` est installée dans la base et la table `chat_message` contient une colonne `embedding vector(1024)` (dimension alignée avec le modèle d'embeddings `voyage-3.5` de Voyage AI, retenu pour le multilingue français). Un module backend `embeddings_client.py` est en place, lit `VOYAGE_API_KEY` et expose une fonction `embed(texts) -> list[list[float]]`. Aucun appel réel à Voyage AI n'est effectué en F01 — l'objectif est uniquement la disponibilité de l'infrastructure.

**Why this priority**: Ajouter pgvector et migrer les colonnes embedding à chaud quand la Phase 3 (RAG) arrivera est risqué. Le préparer maintenant ne coûte rien.

**Independent Test**: `SELECT * FROM pg_extension WHERE extname='vector'` retourne une ligne. La table `chat_message` possède la colonne `embedding vector(1024)`. Le module `embeddings_client.py` est importable sans erreur et lève une exception claire si `VOYAGE_API_KEY` est absent au moment d'un appel.

**Acceptance Scenarios**:

1. **Given** la migration appliquée, **When** on requête `pg_extension`, **Then** l'extension `vector` est listée.
2. **Given** la migration appliquée, **When** on inspecte `chat_message`, **Then** une colonne `embedding` de type `vector(1024)` existe.

---

### Edge Cases

- Conflit de port Postgres sur le poste du développeur → géré par `POSTGRES_PORT` paramétrable dans `.env`.
- Variables d'environnement obligatoires manquantes au démarrage du backend → le backend doit lever une erreur claire au boot indiquant la variable manquante (fail-fast), pas un crash silencieux à la première requête.
- Migration appliquée deux fois → Alembic doit la marquer idempotente et ne rien faire la seconde fois.
- Postgres temporairement injoignable quand `/health` est appelé → réponse 503 explicite avec `{status:"degraded", db:"unreachable"}` au lieu d'un timeout.
- Tentative d'`alembic downgrade base` puis `upgrade head` → doit reproduire exactement le même schéma sans erreur (NFR-003).
- Frontend démarré sans backend → la page d'accueil doit afficher un état "backend indisponible" plutôt qu'écran blanc.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le repo MUST contenir une racine avec `backend/` (FastAPI), `frontend/` (Nuxt 4), un `docker-compose.yml` racine, un `README.md` racine, et un `.gitignore` excluant `.env`, `.venv`, `node_modules`, et autres artefacts locaux.
- **FR-002**: Le `docker-compose.yml` racine MUST contenir un seul et unique service `postgres` basé sur l'image `pgvector/pgvector:pg16`, avec un volume nommé persistant, un healthcheck, exposant le port 5432 (paramétrable via `POSTGRES_PORT`), et lisant ses credentials depuis l'environnement.
- **FR-003**: Le backend FastAPI MUST démarrer via `uvicorn` exécuté dans le `.venv` local de `backend/` et MUST exposer un endpoint `GET /health` qui exécute `SELECT 1` sur la base avec un timeout de 2 secondes et retourne 200 `{status:"ok", db:"ok"}` si la requête réussit, ou 503 `{status:"degraded", db:"unreachable"}` si la requête échoue ou expire.
- **FR-004**: Alembic MUST être configuré dans `backend/` avec une migration initiale unique qui crée toutes les entités listées dans Key Entities. Chaque table MUST utiliser un identifiant `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` (extension `pgcrypto` activée par la migration). Chaque table métier MUST porter en plus : `account_id UUID NOT NULL` (FK Account), `created_at TIMESTAMP NOT NULL DEFAULT now()`, `updated_at TIMESTAMP NOT NULL DEFAULT now()`, `created_by UUID NULL` (FK `account_user.id`, NULL autorisé pour créations système), `version INT NOT NULL DEFAULT 1`, `deleted_at TIMESTAMP NULL` (soft delete préparé).
- **FR-005**: Tout champ représentant un montant monétaire MUST suivre le pattern Money : un couple `_amount NUMERIC(18,2)` + `_currency CHAR(3)` avec une contrainte CHECK garantissant la cohérence (les deux fournis ou les deux NULL).
- **FR-006**: L'extension PostgreSQL `pgvector` MUST être activée par la migration initiale, et la table `chat_message` MUST contenir une colonne `embedding vector(1024)` (dimension alignée avec `voyage-3.5` de Voyage AI). Un module backend `embeddings_client.py` MUST être présent, lire `VOYAGE_API_KEY` depuis l'environnement, et exposer une fonction `embed(texts: list[str]) -> list[list[float]]` (sans appel réel exigé en F01).
- **FR-007**: Le frontend Nuxt 4 MUST démarrer via `pnpm dev` et MUST proposer une page d'accueil minimale qui appelle `GET /health` du backend et affiche le statut retourné.
- **FR-008**: Le `README.md` racine MUST documenter les pré-requis (Python 3.11+, Node 20+, Docker, pnpm), les commandes de setup, les commandes de dev, et la structure des dossiers.
- **FR-009**: Le frontend MUST avoir installées et configurées les libs suivantes : Pinia (plugin enregistré), TailwindCSS v4 (chargé), chart.js, mermaid, Leaflet, gsap, driver.js, fontawesome, toast-ui/editor.
- **FR-010**: Le backend MUST inclure dans `requirements.txt` les paquets `langgraph` et `langchain` (utilitaire) avec versions épinglées.
- **FR-011**: Un client LLM centralisé `llm_client.py` MUST être présent côté backend, MUST utiliser le SDK `openai` Python (compatible OpenRouter), et MUST lire `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` depuis l'environnement (sans appel réel exigé en F01).
- **FR-012**: Un fichier `.env.example` versionné à la racine MUST lister toutes les variables d'environnement requises : `DB_PASSWORD`, `POSTGRES_PORT`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `APP_URL`, `JWT_SECRET`, `VOYAGE_API_KEY`, `REPLICATE_API_TOKEN`. Le fichier `.env` réel MUST être gitignored.
- **FR-013**: Au démarrage du backend, la présence des variables d'environnement critiques (au minimum `DB_PASSWORD`) MUST être vérifiée et l'absence MUST provoquer une erreur explicite (fail-fast).
- **FR-014**: Les tables métier (Entreprise, Projet, Candidature, ChatMessage, AuditLog, AccountUser) MUST porter une colonne `account_id NOT NULL` indexée. Les tables partagées (Source, Referentiel, Indicateur, FondsSource, Intermediaire, FacteurEmission, Template, Offre, Accreditation, DocumentRequis, Critere) NE doivent PAS porter `account_id`.
- **FR-015**: Toutes les tables métier (Entreprise, Projet, Candidature, ChatMessage, AccountUser) MUST porter une colonne `deleted_at TIMESTAMP NULL` (soft delete préparé pour F04). La table AuditLog MUST rester strictement append-only et NE PAS porter `deleted_at`.
- **FR-016**: La devise par défaut documentée pour les seeds, tests et exemples MUST être `XOF` (Franc CFA UEMOA). Aucun défaut n'est imposé en base — la contrainte CHECK Money exige les deux colonnes ensemble ou les deux NULL.

### Non-Functional Requirements

- **NFR-001**: Aucun secret (clé API, mot de passe, token) NE DOIT apparaître en dur dans le code ou dans un fichier versionné. Tout passe par `.env` (gitignored) et `.env.example` (versionné, sans valeurs réelles).
- **NFR-002**: Le repo MUST pouvoir être cloné et monté sans modification sur Linux, macOS et WSL2.
- **NFR-003**: Les migrations Alembic MUST être idempotentes : la séquence `upgrade head` → `downgrade base` → `upgrade head` MUST passer sans erreur et produire le même schéma.
- **NFR-004**: Le port Postgres exposé par Docker MUST être paramétrable via la variable `POSTGRES_PORT`.
- **NFR-005**: La migration initiale MUST s'appliquer en moins de 30 secondes sur une instance Postgres dockerisée locale standard.

### Key Entities *(include if feature involves data)*

- **Account** : racine multi-tenant. Attributs : id, name, created_at. (Pas d'`account_id` — c'est lui-même la racine.)
- **AccountUser** : utilisateur rattaché à un compte. Attributs : id, account_id, email, password_hash, role. (F02 enrichira.)
- **Entreprise** : profil entreprise PME, 1 par account. Attributs : id, account_id, name, secteur, taille_ca (Money), taille_effectifs, localisation, gouvernance, pratiques_actuelles_json, version.
- **Projet** : projet de financement / impact. Attributs : id, account_id, entreprise_id, nom, description, type_impact, maturite, montant_recherche (Money), structure_financement, indicateurs_impact_json, localisation, statut, version.
- **FondsSource** : fonds d'impact disponible. Attributs : id, name, organisation, type, thematique, instruments, plafond (Money), plancher (Money), eligibilite_geo, submission_mode, version, status.
- **Intermediaire** : intermédiaire financier. Attributs : id, name, type, pays, contact, frais_json, delais_json, version, status.
- **Accreditation** : lien accréditation entre intermédiaire et fonds. Attributs : intermediaire_id, fonds_id, date_debut, date_fin, plafond (Money), source_id.
- **Offre** : offre concrète de financement. Attributs : id, fonds_id, intermediaire_id, accepted_languages, version, status.
- **Candidature** : dossier de candidature soumis. Attributs : id, account_id, projet_id, offre_id, statut, snapshot_json, soumission_at, version.
- **Referentiel** : référentiel ESG (ex. ODD, taxonomie UE). Attributs : id, name, version, valid_from, valid_to, status.
- **Indicateur** : indicateur ESG. Attributs : id, name, definition, unite, status.
- **Critere** : critère d'éligibilité ou de scoring. Attributs : id, offre_id ou referentiel_id, expression_json, indicateur_ids, source_id.
- **Source** : source documentaire vérifiable. Attributs : id, url, title, publisher, version, date_publi, page, section, captured_at, captured_by, verified_by, verification_status. (F03 enrichira.)
- **AuditLog** : journal append-only. Attributs : id, user_id, account_id, timestamp, entity_type, entity_id, field, old_value, new_value, source_of_change. (F04 enrichira.)
- **ChatMessage** : message de chat avec mémoire vectorielle. Attributs : id, account_id, user_id, role, content, payload_json, embedding (vector 1024), created_at.
- **DocumentRequis** : document attendu pour une offre/intermédiaire. Attributs : id, fonds_id ou intermediaire_id, name, source_id.
- **FacteurEmission** : facteur d'émission carbone. Attributs : id, name, valeur, unite, pays, source_id, version.
- **Template** : template de dossier de candidature. Attributs : id, offre_id, name, structure_json, source_id.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Un développeur sans contexte préalable monte la stack en moins de 10 minutes en suivant uniquement le `README.md`.
- **SC-002** : `alembic upgrade head` applique la migration initiale en moins de 30 secondes sur Postgres dockerisée locale.
- **SC-003** : `GET /health` répond 200 avec `{status:"ok", db:"ok"}` quand Postgres tourne, et 503 avec un statut dégradé quand Postgres est arrêté.
- **SC-004** : `pnpm dev` lance le frontend sans erreur et la page d'accueil affiche le statut backend en moins de 3 secondes après chargement.
- **SC-005** : La séquence `docker compose down -v && docker compose up -d && alembic upgrade head` reproduit un environnement identique à 100 % (mêmes tables, mêmes colonnes, mêmes contraintes).
- **SC-006** : Aucun secret en dur n'est détecté par un scan basique du repo (grep des patterns clés) sur les fichiers versionnés.
- **SC-007** : 100 % des tables métier listées dans US3 portent `account_id NOT NULL` indexée après la migration initiale.
- **SC-008** : 100 % des champs montants identifiés suivent le pattern Money (`_amount` + `_currency` + CHECK).

## Assumptions

- Les développeurs disposent de Python 3.11+, Node 20+, Docker (avec compose), et pnpm installés en local.
- Le gestionnaire de paquets Python retenu est `pip` (avec `requirements.txt`). `uv` peut être utilisé localement si l'équipe préfère, mais le `requirements.txt` reste la référence versionnée.
- La dimension d'embedding vector(1024) est fixée par le choix de `voyage-3.5` (Voyage AI), modèle multilingue retenu pour le français. Une migration future est possible si un autre modèle est adopté.
- Le pattern Money retenu est "deux colonnes + CHECK" plutôt qu'un type composite Postgres natif, pour rester pleinement compatible avec SQLAlchemy/ORM standards.
- Les tables Source, Referentiel, Indicateur, FondsSource, Intermediaire, FacteurEmission, Template, Offre, Accreditation, DocumentRequis, Critere sont considérées comme partagées entre tous les comptes (catalogue commun) et ne portent donc pas `account_id`. Cette décision pourra être révisée si une feature future exige un catalogue privé par compte.
- Le peg FCFA-EUR fixe (655,957) est documenté en commentaire dans le code mais n'est pas consommé en F01 — il sera utilisé par F27 (simulateur) et F29 (scoring crédit).
- Le rôle `role` sur AccountUser admet uniquement les valeurs `pme` et `admin` (plateforme fermée — invariant Module 0). F02 l'enforcera via contrainte ; F01 prévoit la colonne sans contrainte CHECK stricte.
- L'audit log et les politiques RLS sont préparés structurellement (colonnes présentes, table créée) mais ne sont pas activés fonctionnellement en F01 — F02 et F04 les activeront.
- Les sources verrouillées NOT NULL et la vérification systématique des sources sont hors-scope F01 (F03).

## Out of Scope (explicit)

- Auth, login, register → **F02**
- Activation de Row-Level Security et politiques de sécurité → **F02**
- Verrouillage NOT NULL des `source_id` et tooling LLM `cite_source` → **F03**
- Audit log fonctionnel (triggers, append-only enforcement) → **F04**
- Page Mes données / consentements RGPD → **F05**
- Backend dockerisé, Redis, Celery, MinIO → post-MVP
- Pages métier frontend (uniquement ossature et libs UI installées en F01)
