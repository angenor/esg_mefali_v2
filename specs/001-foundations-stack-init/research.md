# Phase 0 — Research : F01 Foundations Stack Init

**Date** : 2026-04-29
**Statut** : Complete — toutes les NEEDS CLARIFICATION résolues en clarify ou par défauts éprouvés.

## R1 — Image Docker Postgres + pgvector

- **Decision** : `pgvector/pgvector:pg16`
- **Rationale** : image officielle pgvector basée sur Postgres 16, utilisée en production par de nombreux projets (Supabase, ChromaDB hosted). Inclut pgvector ≥ 0.7 (HNSW + IVFFlat). Compatible `gen_random_uuid()` via `pgcrypto`.
- **Alternatives évaluées** : `ankane/pgvector` (deprecated, redirige vers pgvector officiel) ; `supabase/postgres` (trop d'extensions inutiles, ~1 GB).

## R2 — Génération d'UUID en base

- **Decision** : Extension `pgcrypto` activée par migration ; PK `UUID DEFAULT gen_random_uuid()`.
- **Rationale** : `gen_random_uuid()` est dans `pgcrypto` sur Postgres 16 (devient natif en Postgres 17). Plus simple que `uuid-ossp` (moins de variantes). UUID v4 random, pas de fuite d'info.
- **Alternatives évaluées** : `uuid-ossp` (extension legacy) ; UUID côté Python (Python-generated UUID4, mais moins safe si bug applicatif crée des doublons).

## R3 — Pattern Money en SQL

- **Decision** : Pattern « deux colonnes + CHECK » : `<champ>_amount NUMERIC(18,2)` + `<champ>_currency CHAR(3)` + contrainte `CHECK ((amount IS NULL AND currency IS NULL) OR (amount IS NOT NULL AND currency IS NOT NULL AND length(currency)=3))`.
- **Rationale** : Pleinement compatible SQLAlchemy/ORM standards (un `composite()` SQLAlchemy mappe les deux colonnes vers un value-object Python `Money`). Évite les types composites Postgres natifs, mal supportés par les drivers et migrations. Constrainte CHECK garantit la cohérence en base, indépendamment du code applicatif.
- **Alternatives évaluées** : Type composite Postgres `CREATE TYPE money_t AS (amount numeric(18,2), currency char(3))` (rejeté : friction Alembic + SQLAlchemy) ; type natif `MONEY` Postgres (rejeté : mono-devise, pas adapté).
- **Devise par défaut documentée pour seeds/exemples** : `XOF` (FCFA UEMOA). Aucun défaut imposé en base.

## R4 — Dimension de vecteur pgvector

- **Decision** : `vector(1024)` sur `chat_message.embedding`.
- **Rationale** : Aligné sur le modèle d'embeddings retenu : Voyage AI `voyage-3.5` (multilingue, performant français, 1024 dimensions). Fixé par la constitution.
- **Alternatives évaluées** : 1536 (text-embedding-3-small OpenAI, hébergé US — exclu RGPD/UEMOA) ; 768 (modèles open-source français type CamemBERT — moins performants).

## R5 — Client LLM centralisé

- **Decision** : Module `app/llm_client.py` utilisant le SDK `openai` Python (compatible OpenRouter via `base_url`). Lit `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` depuis l'environnement. Aucun appel réel exécuté en F01 — fonction de fabrique `get_llm_client()` retourne un client `openai.OpenAI(api_key=..., base_url=...)`.
- **Rationale** : Le SDK officiel `openai` est compatible OpenRouter (qui expose une API OpenAI-like) et avec la plupart des fournisseurs alternatifs (Anthropic via proxy OpenAI-compat, Mistral, Llama hébergé). Changer de provider = 3 vars d'env, pas de code.
- **Alternatives évaluées** : `httpx` brut (rejeté : duplication d'effort sur retries, streaming, tool-calling) ; SDK Anthropic direct (rejeté : moins flexible, lock-in).

## R6 — Client embeddings Voyage AI

- **Decision** : Module `app/embeddings_client.py` exposant `embed(texts: list[str]) -> list[list[float]]`. Utilise le SDK `voyageai` Python officiel ou `httpx` direct vers `https://api.voyageai.com/v1/embeddings` avec `model="voyage-3.5"`. Lit `VOYAGE_API_KEY`. Aucun appel réel en F01 — la fonction lève `RuntimeError` claire si la clé est absente.
- **Rationale** : Voyage AI est hébergé hors USA (Canada), conforme RGPD/UEMOA. `voyage-3.5` est multilingue avec excellents scores en français.
- **Alternatives évaluées** : OpenAI text-embedding-3 (rejeté : USA + dimension non alignée) ; modèles auto-hébergés (rejeté : opex MVP).

## R7 — Health check FastAPI

- **Decision** : `GET /health` exécute `SELECT 1` via une session SQLAlchemy avec `statement_timeout` à 2 secondes. Réponse 200 `{status:"ok", db:"ok"}` si OK ; 503 `{status:"degraded", db:"unreachable"}` si exception/timeout.
- **Rationale** : Liveness standard, peu coûteux, ne charge pas le pool. Le timeout évite que `/health` lui-même devienne un point de blocage.
- **Alternatives évaluées** : Vérification du pool entier (rejeté : trop coûteux en charge) ; ping TCP simple sur 5432 (rejeté : ne détecte pas Postgres planté process up).

## R8 — Configuration et fail-fast

- **Decision** : `app/config.py` utilise `pydantic-settings` (`BaseSettings`) qui lit `.env` automatiquement. Le constructeur `Settings()` est appelé au démarrage de FastAPI (dépendance `lru_cache`). `DB_PASSWORD` est marqué obligatoire (pas de défaut). L'absence de `DB_PASSWORD` lève `ValidationError` au boot, bloquant le démarrage avec un message clair.
- **Rationale** : Pydantic v2 + pydantic-settings est le standard FastAPI. Fail-fast au boot évite des bugs en runtime.
- **Alternatives évaluées** : `os.getenv()` manuel (rejeté : pas de validation typée) ; dynaconf (rejeté : sur-dimensionné pour MVP).

## R9 — Frontend Nuxt 4 + TailwindCSS v4

- **Decision** : Nuxt 4 (composition API) + TailwindCSS v4 via `@tailwindcss/vite` (pipeline Vite natif v4) + `@nuxtjs/tailwindcss` n'est PAS utilisé (incompatible v4). Pinia via `@pinia/nuxt`. Page `pages/index.vue` appelle `useFetch('/health')` proxifié vers `http://localhost:8000/health`.
- **Rationale** : Tailwind v4 abandonne PostCSS au profit du plugin Vite officiel. Nuxt 4 supporte cela via `vite.plugins`.
- **Alternatives évaluées** : Tailwind v3 (rejeté : la stack imposée demande v4) ; Module Nuxt Tailwind community (rejeté : v4 non encore wrappé).

## R10 — Idempotence des migrations Alembic

- **Decision** : Migration unique `0001_initial_schema.py` avec `op.create_table()` pour chaque entité, `op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")` et `vector` en début de fonction `upgrade()`. La fonction `downgrade()` exécute `op.drop_table()` dans l'ordre inverse + `DROP EXTENSION` conditionnel.
- **Rationale** : `IF NOT EXISTS` rend les `CREATE EXTENSION` idempotents. `op.drop_table()` Alembic est strict mais OK car downgrade part toujours de l'état post-upgrade. Test `test_migration_idempotency.py` exécute upgrade/downgrade/upgrade en boucle.
- **Alternatives évaluées** : Plusieurs petites migrations (rejeté : sur-découpage, F01 a une seule étape conceptuelle).

## R11 — Gestion des dépendances Python

- **Decision** : `requirements.txt` versionné, `pip install -r requirements.txt` dans le `.venv`. Pas de `poetry`/`uv lock` versionné pour le MVP.
- **Rationale** : Plus simple à comprendre pour un dev qui rejoint, compatible avec tout. `uv` peut être utilisé localement par préférence (lit `requirements.txt`).
- **Alternatives évaluées** : `poetry` (rejeté : complexité, lock-in) ; `uv` avec `pyproject.toml` lock (envisageable post-MVP).

## R12 — Hébergement & souveraineté

- **Decision** : Production Europe ou Afrique de l'Ouest uniquement. Documenté dans `README.md` section "Déploiement".
- **Rationale** : Constitution v1.0.0 + RGPD + UEMOA 20/2010 + loi ivoirienne 2013-450. Fournisseurs candidats : OVH, Scaleway (FR), Africa Data Centres (ZA/SN), AWS Cape Town (ZA).
- **Alternatives évaluées** : USA (interdit constitutionnellement).
