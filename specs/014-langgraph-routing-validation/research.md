# F14 — Phase 0 Research

Décisions consolidées (synchrones avec [plan.md](./plan.md) sections R-1 à R-6).

## R-1 — Orchestrateur Python maison vs LangGraph

- **Decision** : orchestrateur Python pur, pas de dépendance `langgraph`.
- **Rationale** : pipeline linéaire, sans graphe d'états, ~500 LOC. LangGraph apporte des fonctionnalités inutiles en MVP.
- **Alternatives** : LangGraph, Temporal, Prefect — toutes rejetées.

## R-2 — Cache d'intention par fil

- **Decision** : `cachetools.TTLCache(maxsize=1024, ttl=600)`, clé `(account_id, thread_id)`.
- **Rationale** : FR-013 — pas de Redis MVP. Thread-safe.
- **Alternatives** : `functools.lru_cache` (pas de TTL), Redis (out of scope).

## R-3 — Politique de retry

- **Decision** : `max_retries = 2`, prompt minimal (tool name + schéma + erreur + dernier message user).
- **Rationale** : économie de tokens (NFR-003).
- **Alternatives** : retry illimité (rejeté), pas de retry (rejeté).

## R-4 — Sérialisation par thread_id

- **Decision** : registre global `dict[(account_id, thread_id), asyncio.Lock]` + GC waiters=0.
- **Rationale** : FR-016 ; évite races sur cache et contexte.
- **Alternatives** : Postgres advisory locks (over-engineering), aucun (bugs).

## R-5 — Format SSE des nouveaux events

- **Decision** : 3 events ajoutés (`thinking`, `tool_call_started`, `tool_call_completed`). Voir [contracts/sse-events-f14.md](./contracts/sse-events-f14.md).
- **Rationale** : compatible F13.

## R-6 — Règles du classifier d'intention

- **Decision** : 6 mappings regex/keyword + bascule LLM si confiance < seuil.
- **Rationale** : déterministe, testable.
- **Alternatives** : tout en LLM (coût/latence), embeddings (overkill).

## Dépendances ajoutées

- `cachetools` (à expliciter dans `pyproject.toml` si absent).
