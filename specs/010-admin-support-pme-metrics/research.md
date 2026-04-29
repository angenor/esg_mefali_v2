# Phase 0 — Research

## R1. Email transactionnel provider

**Decision**: **Resend** (https://resend.com), abstrait derrière une interface `EmailSender` Python.

**Rationale**:
- API HTTP simple (`POST /emails`), SDK Python officiel mais utilisable via `httpx` minimal.
- Free tier 3 000 emails/mois suffisant en MVP, conforme RGPD (DC EU disponible).
- Templates HTML simples ; webhooks pour bounces / complaints.
- L'interface `EmailSender(send(to, subject, html, kind))` permet de basculer vers Postmark/SES sans toucher au métier.

**Alternatives considérées**:
- Postmark — sérieux mais hors free tier rapidement.
- Mailgun — mature mais incidents récents de réputation.
- Amazon SES — cher en setup (validation DKIM, sandbox), surdimensionné MVP.
- SMTP générique — trop fragile pour transactionnel critique.

## R2. Cache d'agrégats dashboard

**Decision**: `cachetools.TTLCache(maxsize=64, ttl=60)` in-process Python, encapsulé dans un service `DashboardCache` ; invalidation explicite (`cache.clear()` ou clé spécifique) sur événements critiques (révocation d'attestation).

**Rationale**:
- Pas de Redis en MVP (KISS).
- 64 entrées suffisent (5 blocs × granularités).
- Thread-safe avec lock asyncio si besoin (FastAPI mono-process en dev, gunicorn workers en prod ⇒ acceptation : chaque worker a son cache, coût d'un flush répété est trivial).

**Alternatives considérées**:
- Redis — overkill pour 5 endpoints lus.
- `lru_cache` simple — pas de TTL natif.
- Postgres materialized view — rafraîchissement coûteux et lent.

## R3. Retry email

**Decision**: `BackgroundTasks` FastAPI + helper `enqueue_email_with_retry()` qui replanifie via `asyncio.sleep` jusqu'à 3 tentatives avec backoff exponentiel : 1 min, 5 min, 15 min (plafond 21 min). Statut consigné dans `email_delivery_log` à chaque tentative.

**Rationale**:
- Pas de Celery/RQ en MVP.
- Couvre les pannes réseau temporaires courantes (< 20 min).
- Au-delà, statut `failed` visible pour intervention manuelle ; admin peut relancer.

**Alternatives considérées**:
- Celery + Redis broker — surcoût opérationnel non justifié.
- Pas de retry — perte d'un email = bug critique.

## R4. Filtre PII pour motif public

**Decision**: Fonction utilitaire `mask_pii(text)` en backend, basée sur des regex (email, téléphone international, IBAN, CIN, NIF). Appliquée uniquement à la sortie publique (`/verify/{id}`), pas à la donnée stockée.

**Rationale**:
- Couvre 95 % des fuites accidentelles avec coût zéro.
- Conserve la donnée originale pour audit/traçabilité.

**Alternatives considérées**:
- Microsoft Presidio — dépendance lourde, faux positifs sur prénoms.
- LLM-based redaction — coût et latence inacceptables pour rendu public.

## R5. Logger d'usage LLM

**Decision**: Point d'extension dans `app/llm_client.py` (wrapper existant ou à créer minimalement). À chaque appel LLM, après réception de la réponse, insertion synchrone d'une ligne `llm_usage_log` (pas de batch) à partir de l'objet `usage` du provider (OpenRouter renvoie `usage.prompt_tokens` et `usage.completion_tokens`).

**Rationale**:
- Pas de re-tokenisation locale (coût CPU + risque divergence).
- Insertion synchrone OK : volume estimé 5 000 lignes/jour (négligeable).
- Compatible F35 (Eval) qui réutilisera la table.

**Alternatives considérées**:
- Compteur local + flush périodique — perte en cas de crash.
- Re-tokenisation `tiktoken` — divergence garantie avec billing provider.

## R6. Granularité d'audit `admin_view`

**Decision**: Enum strict côté DB et backend : `dashboard | projets | candidatures | scores | attestations | llm | audit`. Une ligne d'audit par GET de section. Pas de dédoublonnage : la transparence prime sur le volume.

**Rationale**:
- 7 sections couvrent l'UI sans exploser la table d'audit.
- Volume estimé : 50 admins × 10 PME/jour × 7 sections = 3 500 lignes/jour, soutenable.

## R7. Pagination & recherche admin

**Decision**: Recherche `ILIKE` sur `email` et `raison_sociale` avec index trigram (pg_trgm) ; pagination keyset (`created_at, id`). Page size 50.

**Rationale**:
- 10k comptes au maximum en cible Phase 1, ILIKE + pg_trgm < 100ms.
- Keyset > offset pour stabilité.

## R8. Versioning `LlmPricing`

**Decision**: Lignes immutables avec `valid_from` (timestamp) et `valid_to` nullable (open-ended si actuel). Calcul de coût : SELECT la ligne dont `valid_from <= log.created_at < COALESCE(valid_to, +inf)`. Aucun UPDATE rétroactif.

**Rationale**:
- Garantit reproductibilité des coûts historiques.
- Aligné avec le principe de versioning Module 0.

## Récap

Toutes les NEEDS CLARIFICATION sont résolues. Aucun blocage pour Phase 1.
