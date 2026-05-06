# Phase 0 — Research: F58 Agent Guardrails

**Date**: 2026-05-06 | **Branch**: `058-agent-guardrails-eval`

## Décisions de recherche

### R1 — Bibliothèque de détection de langue

- **Decision**: utiliser `langdetect` (port Python de Google language-detection).
- **Rationale**: détection FR/EN/ES/AR fiable (>95 % sur textes > 30 caractères),
  latence ~3-5 ms par appel, MIT license, pas de dépendance lourde, pip install
  simple. Couvre NFR-001 (latence guardrails < 30 ms p95).
- **Alternatives considered**:
  - `langid.py` : plus rapide (~1 ms) mais moins précis sur textes courts mêlant FR + termes techniques anglais (« API », « ESG »).
  - Heuristique custom (table de mots-clés FR/EN) : trop d'edge cases, risque de drift maintenance.
  - Appel LLM dédié : coûteux (~50 ms + tokens) et redondant.

### R2 — Implémentation circuit breaker

- **Decision**: implémentation custom in-memory (~80 LOC) basée sur le pattern
  "rolling window" (deque des N dernières erreurs avec timestamp).
- **Rationale**: contrôle total sur la sémantique semi-ouverte (exigence FR-010),
  pas de dépendance externe non maintenue. Lib `circuitbreaker` Python (PyPI) pas
  de release depuis 2022.
- **Alternatives considered**:
  - Lib `circuitbreaker` : abandon, sécurité non garantie.
  - Lib `pybreaker` : maintenue mais pas de support natif `httpx async` ; plus de
    code de glue qu'une implémentation custom équivalente.
  - Coordination Redis : reportée post-MVP (clarification Q2 — single worker MVP).

### R3 — Compilation des regex PII

- **Decision**: `re.compile()` au démarrage app via `lru_cache(maxsize=None)` ;
  patterns dans constante `pii_patterns.py` (séparé de la logique).
- **Rationale**: regex compilés une fois → latence d'évaluation ~µs ; séparation
  données/logique facilite les tests et l'ajout de patterns post-MVP. Format
  compatible avec import dynamique futur (par pays).
- **Alternatives considered**:
  - Compilation à chaque appel : latence x10, NFR-001 menacée.
  - Lib externe `presidio` (Microsoft) : très lourde (Spacy + ML), overkill MVP,
    non aligné avec MVP "règles + heuristique" du source doc.

### R4 — Hashing arguments pour loop detection

- **Decision**: `hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode())`.
- **Rationale**: déterministe quel que soit l'ordre des clés JSON ; collision
  pratique négligeable ; `default=str` gère Decimal/UUID/datetime sans erreur.
- **Alternatives considered**:
  - `hash(tuple(sorted(args.items())))` : Python `hash()` non stable cross-process
    (sécurité PYTHONHASHSEED) → faux négatifs après redémarrage.
  - `pickle.dumps()` + hash : risque de deser unsafe ; plus lent.

### R5 — Stratégie eval LLM (mock vs real)

- **Decision**: framework hybride. Mode `mock` utilise `unittest.mock.patch` sur
  `app.llm_client.complete()` avec fixtures JSONL (`tests/golden/agent_e2e_mock_responses.jsonl`)
  pré-enregistrées par cas. Mode `real` lit `LLM_API_KEY` + `LLM_BASE_URL` depuis
  env CI et appelle l'API vraie. Le runner (`scripts/eval_agent.py`) accepte `--mode`.
- **Rationale**: mock est gratuit (~30s pour 50 cas), déterministe, exécutable sur
  chaque PR (smoke test). Real est précis mais coûteux ($2-5 / 50 cas via
  OpenRouter minimax-m2.7), réservé au job nocturne et aux PR taguées
  `eval-required`. Aligné avec le risque "Coût eval continue" du source doc.
- **Alternatives considered**:
  - Tout en real : coût explose ($100+/mois si CI sur chaque PR).
  - Tout en mock : fausse détection des régressions LLM (changement de modèle, etc.).
  - VCR.py (recording HTTP) : possible mais complexité de gestion des cassettes
    pour 50 cas multi-tour ; mock direct plus simple.

### R6 — Format payload Slack webhook

- **Decision**: Slack Block Kit standard. Sévérité → couleur attachment (`good`,
  `warning`, `danger`) ; titre en `header` block ; fields markdown table.
  Implémentation httpx async avec timeout 5s + 1 retry exponentiel.
- **Rationale**: format standard, rendu propre dans Slack, compatible avec autres
  systèmes (Discord, Teams) via adapters futurs. Timeout strict pour ne jamais
  bloquer le flux principal (FR-022).
- **Alternatives considered**:
  - Texte brut markdown : moins lisible, pas de coloration sévérité.
  - Lib `slack_sdk` : dépendance lourde (~5 MB) pour un webhook one-shot ; httpx
    suffit.

### R7 — Comptage tokens conversation vs OCR/analyse

- **Decision**: enrichir `agent_run_step` (table existante F53) avec une colonne
  `flow ENUM('conversation', 'ocr_analysis')`. Migration 0037 inclut cet ALTER.
  Les compteurs sont calculés à la volée par agrégation `SUM(tokens_in + tokens_out)
  WHERE account_id = X AND ts >= today_utc AND flow = Y`. Cache in-memory TTL 60s
  côté `budget.py` pour éviter une requête par tour.
- **Rationale**: pas de table compteur dédiée (P3 audit append-only respecté) ;
  l'agrégation reste rapide grâce à un index `(account_id, ts, flow)`. Cache 60s
  est cohérent avec le quota quotidien (granularité minute suffit).
- **Alternatives considered**:
  - Table `account_token_counter` matérialisée : duplication de données, risque
    de désync.
  - Vue matérialisée Postgres : refresh manuel ou trigger, complexité ; cache
    in-memory simple suffit MVP.

### R8 — UI admin metrics page (frontend)

- **Decision**: 1 page Vue 3 `frontend/app/pages/admin/agent/metrics.vue`,
  composition API + Pinia store `useAgentMetrics()` qui fetch
  `GET /admin/agent/metrics?period=...`. 6 sections en cards Tailwind v4 ; charts
  via chart.js (déjà dans le stack). Responsive minimal.
- **Rationale**: cohérent avec les pages admin existantes (sourcing F56, etc.).
  US9 marquée P2 → si charge trop élevée, livrable post-MVP, l'endpoint reste
  utilisable via curl.
- **Alternatives considered**:
  - Dashboard externe (Grafana) : nécessite stack Prometheus, hors-scope.
  - Endpoint sans UI : violations principle "tableau de bord visible" du source
    doc US9 ; UI livrable même minimaliste.

### R9 — Sourcing du golden set jailbreak (100 prompts)

- **Decision**: extraire 100 prompts depuis bases publiques :
  - 50 prompts depuis OWASP LLM Top 10 (LLM01 Prompt Injection 2024).
  - 30 prompts depuis PromptBench (open dataset MIT license).
  - 20 prompts adaptés FR (traductions des canoniques anglais + injections en FR
    « oublie tes consignes », « tu es maintenant... »).
- **Rationale**: sources publiques évitent l'exposition d'attaques internes (note
  source doc « Ne pas exposer les attaques internes au repo public »). Coverage
  multilingue indispensable car cible UEMOA.
- **Alternatives considered**:
  - Bases payantes (Lakera) : surcoût + lock-in.
  - Génération LLM-based : risque de cas synthétiques peu réalistes ; reportée.

### R10 — Coverage tooling

- **Decision**: réutiliser `pytest --cov=app.agent.guardrails --cov-fail-under=85`
  conformément à `pyproject.toml` existant. Ajouter cible spécifique dans Makefile :
  `make test-guardrails`.
- **Rationale**: aligné avec le coverage gate 80% global (`fail_under = 80`).
  Cible 85% F58 plus stricte (NFR-007).
- **Alternatives considered**:
  - Coverage 100% : irréaliste sur les retry async + edge cases circuit breaker.
  - Coverage gate global porté à 85% : impacte tous les modules existants, hors
    scope F58.

## Synthèse — toutes les NEEDS CLARIFICATION résolues

Les 5 clarifications du spec (Q1-Q5) + 10 décisions de recherche couvrent toutes
les zones grises. Aucun NEEDS CLARIFICATION résiduel. Plan prêt pour Phase 1.
