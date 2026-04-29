# Phase 0 — Research: Source & Sourçage Anti-Hallucination

**Feature**: 003-source-anti-hallucination
**Date**: 2026-04-29

Aucune entrée NEEDS CLARIFICATION ne subsiste après `/speckit-clarify`. Cette
note de recherche consigne les choix techniques validés et les alternatives
écartées.

## R1 — Recherche hybride full-text + vectorielle PostgreSQL

- **Decision** : index GIN sur `to_tsvector('french', title || ' ' || publisher || ' ' || coalesce(notes,''))` + index IVFFlat (`lists=100`) sur `embedding vector(1024)` ; le service `search_source` exécute deux requêtes parallèles puis combine les scores via une formule `0.5 * rank_text + 0.5 * (1 - cos_distance)` paginée.
- **Rationale** : tsvector PostgreSQL est mature et supporte le français nativement ; pgvector IVFFlat est l'index recommandé pour 1k-10k vecteurs avec 1024 dim ; la fusion linéaire reste le baseline le plus simple à expliquer / tuner ; budget < 200ms p95 atteignable d'après les benchmarks pgvector publiés.
- **Alternatives écartées** :
  - HNSW : meilleure recall mais coût mémoire et build plus élevés ; surdimensionné pour 5000 vecteurs.
  - Reciprocal Rank Fusion : plus robuste mais ajoute une dépendance/calibration ; pourra être adopté en F35 si nécessaire.
  - ts_rank_cd seul (pas de vectoriel) : recall insuffisant pour requêtes en langage naturel du LLM.

## R2 — Cache de décisions du middleware

- **Decision** : `cachetools.TTLCache(maxsize=10000, ttl=300)` (5 minutes) ; clé = `sha256(message_text + sorted(cited_source_ids) + max(source_status_versions))`. Invalidation immédiate via un compteur `source_status_version` incrémenté à chaque transition de statut Source : la clé inclut la valeur courante du compteur, rendant le cache obsolète automatiquement.
- **Rationale** : conforme à la clarification (TTL court + bust sur changement de statut), zéro dépendance externe (pas de Redis), bornage mémoire dur, perte de cache acceptable.
- **Alternatives écartées** :
  - Redis distribué : surdimensionné en MVP single-instance ; ajoutera un service à provisionner.
  - Cache infini avec invalidation pub/sub : complexité disproportionnée.

## R3 — Tool-calls structurés OpenRouter (function-calling)

- **Decision** : la réponse du LLM est analysée comme un `chat.completions` OpenAI-compatible ; les `tool_calls` JSON natifs sont la seule source de citations acceptée par le middleware (FR-008 b). Aucun parsing de balises libres.
- **Rationale** : OpenRouter expose une API OpenAI-compatible avec function-calling pour `minimax-m2.7` ; le format JSON est non-ambigu et déjà validé par le SDK ; conforme P9 (Pydantic strict côté tool handler).
- **Alternatives écartées** :
  - Balises en clair `[cite_source: id=42]` : sujet à hallucination de format ; rejeté par P9.
  - JSON Schema "structured outputs" sans tool-call : moins idiomatique et empêche d'exposer search_source au modèle dans le même tour.

## R4 — Vues SQL `v_<entity>_verified`

- **Decision** : pour chaque table catalogue, une vue `v_<entity>_verified AS SELECT t.* FROM <entity> t JOIN source s ON s.id = t.source_id WHERE s.verification_status = 'verified'`. Le LLM, l'UI PME et les rapports lisent uniquement ces vues. Les admins lisent les tables brutes (RBAC F02).
- **Rationale** : centralise la règle "verified-only" en SQL (single source of truth), exploite l'optimiseur Postgres, simplifie les tests d'intégration, n'exige pas de changement de code applicatif quand on ajoute une nouvelle entité catalogue.
- **Alternatives écartées** :
  - Filtre applicatif côté Python : duplication par chaque service consommateur, risque d'oubli.
  - Materialized view : surcoût d'invalidation, inutile vu le volume.

## R5 — Workflow double-validation

- **Decision** : contrainte CHECK + trigger BEFORE UPDATE sur `source` qui rejette toute transition `pending → verified` lorsque `NEW.verified_by = OLD.captured_by`. Le service applicatif vérifie en amont pour produire une erreur lisible.
- **Rationale** : la contrainte DB est non-contournable (P1), même par un cron admin ; le trigger ajoute le message structuré.
- **Alternatives écartées** :
  - Contrôle applicatif seul : contournable par accès direct DB.

## R6 — Heuristiques de détection chiffre ESG

- **Decision** : regex initiale couvrant `[\d]+([.,]\d+)?\s*(tCO2e|tCO2|tco2e|FCFA|XOF|EUR|€|USD|\$|%|kWh|MWh|GWh|tep|GJ|MJ|ha)` (case-insensitive) + dictionnaire de mots-clés (`seuil`, `critère`, `critere`, `formule`, `taux d'intérêt`, `émission`, `intensité carbone`). Toute correspondance déclenche l'exigence d'au moins un `cite_source` valide.
- **Rationale** : démarrer strict (faux positifs > faux négatifs) ; jeu d'évals 20 cas (extensible F35) garantit le tuning ; latence négligeable (< 5ms par message).
- **Alternatives écartées** :
  - LLM secondaire de classification : coût + latence + boucle dépendance.
  - NER spaCy : surdimensionné en MVP.

## R7 — Voyage AI — calcul d'embedding à la vérification

- **Decision** : `embedding_service.compute(text=title + ' ' + publisher + ' ' + notes)` appelle `voyage-3.5` (1024 dim, `input_type='document'`). La transition `pending → verified` est atomique (BEGIN; UPDATE + INSERT vector; COMMIT) et échoue avec message structuré si le service répond > 5s ou en erreur.
- **Rationale** : F01 a déjà posé le client Voyage ; coût < 1 cent par source ; voyage-3.5 est le modèle FR-friendly imposé.
- **Alternatives écartées** :
  - Recompute asynchrone post-commit : risque de fenêtre où la source est `verified` sans embedding utilisable par `search_source`.

## R8 — Endpoint admin agrégé `unsourced-claims`

- **Decision** : `GET /admin/unsourced-claims?days=30&limit=50` exécute `SELECT lower(claim_text) AS claim, count(*) AS freq, max(created_at) AS last_seen FROM unsourced_claim_log WHERE created_at > now() - interval '30 days' GROUP BY lower(claim_text) ORDER BY freq DESC LIMIT 50` ; RLS filtre automatiquement par `account_id`.
- **Rationale** : agrégation simple Postgres, RLS héritée, pagination par `limit`.
- **Alternatives écartées** :
  - Index dédié : non requis pour le volume cible.
