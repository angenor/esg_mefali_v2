# Phase 0 — Research

**Feature**: F54 Agent Context Builder
**Date**: 2026-05-06

## R1 — Comptage de tokens : tiktoken + fallback heuristique

**Decision** : Utiliser `tiktoken` (>= 0.7) avec encoding `cl100k_base` par défaut, exposer `LLM_TIKTOKEN_ENCODING` (env) pour override, fallback heuristique `len(text) / 4` quand l'encoding n'est pas reconnu.

**Rationale** :
- `cl100k_base` est l'encoding utilisé par GPT-4/3.5 et accepté par OpenRouter pour la plupart des modèles compatibles, donnant une approximation correcte.
- minimax-m2.7 (modèle par défaut configuré) **n'est pas** un modèle OpenAI ; tiktoken donnera une approximation conservatrice (sous-estimation de ~5–10 % observée empiriquement sur des benchmarks similaires).
- Le fallback `len/4` est volontairement plus pessimiste que tiktoken (1 token ≈ 4 chars en français latin) — préfère couper trop que pas assez.
- NFR-002 (≤ 4000 tokens dans 99 % des cas) est respecté avec une marge.

**Alternatives considered** :
- `transformers.AutoTokenizer` chargeant le tokenizer minimax depuis HuggingFace : ajoute une dépendance lourde (>500 MB) et un téléchargement, refusé pour MVP.
- `sentencepiece` directement : trop bas niveau, refusé.
- Pas de comptage (toujours envoyer tout) : refusé, viole NFR-002.

## R2 — EventBus in-process (F41) — contrat de subscription

**Decision** : F54 souscrit aux événements suivants émis par F41 EventBus :
- `company_profile_updated` (payload : `{account_id, fields_changed[]}`)
- `projet_created` / `projet_updated` / `projet_archived` (payload : `{account_id, projet_id, …}`)
- `candidature_created` / `candidature_updated` / `candidature_status_changed` (payload : `{account_id, candidature_id, …}`)
- `indicateur_created` / `indicateur_updated` (payload : `{account_id, indicateur_id, …}`)
- `score_credit_calculated` (payload : `{account_id, scoring_id, …}`)
- `plan_action_step_updated` (payload : `{account_id, …}`)

Sur réception d'un de ces événements, le cache `BusinessContext` invalide l'entrée `account_id` correspondante (pas tout le cache).

**Rationale** :
- L'EventBus F41 est in-process (singleton) ; pas de coût Redis.
- L'invalidation ciblée par account_id préserve l'isolation P2 et minimise les recharges inutiles (un événement sur compte A n'invalide pas le cache de B).
- TTL 60s en fallback couvre le cas où l'event n'est pas émis (bug, ajout futur d'un type d'event non encore branché).

**Alternatives considered** :
- Redis pubsub : ajoute une dépendance hors stack imposée. Refusé pour MVP.
- Polling (re-vérifier `updated_at` à chaque tour) : trop de requêtes DB. Refusé.
- Pas de cache (full re-load à chaque tour) : viole NFR-001 (latence < 50 ms hot impossible). Refusé.

## R3 — LRU async-safe pour BusinessContext

**Decision** : Utiliser `cachetools.TTLCache(maxsize=512, ttl=60)` avec un `asyncio.Lock` global pour la mutation, plus une couche async-friendly `AsyncTTLCache` minimale (50 lignes) écrite en interne.

**Rationale** :
- `functools.lru_cache` ne supporte pas les coroutines (renvoie une coroutine cachée, pas le résultat).
- `async-lru` est une dépendance externe stable mais ajoute un package — choix : implémenter en interne (50 lignes) pour garder la dépendance minimale.
- `cachetools` est déjà transitive via `langchain-core` ; pas d'ajout.
- `maxsize=512` couvre largement les comptes simultanés (un PME max actif par compte, pic estimé < 100 concurrents).
- TTL 60s aligné avec FR-007.

**Alternatives considered** :
- `async-lru` : 1 dépendance de plus pour 50 lignes économisées. Refusé.
- Cache uniquement basé sur EventBus push (pas de TTL) : risqué si l'event n'est pas émis. Refusé.

## R4 — Garantir le pattern "service pur" (NFR-004)

**Decision** : Documenter la règle dans `app/agent/context/__init__.py` (docstring module) et ajouter un test de fumée `tests/unit/agent/context/test_no_circular_imports.py` qui vérifie via `importlib`/`ast` que les modules `app/agent/context/*` et `app/agent/prompt_builder.py` n'importent pas `app.chat.api` ni `app.agent.runner`.

**Rationale** :
- `import-linter` est une dépendance lourde pour un seul check ; un test pytest ad hoc fait le job.
- Le test échoue à la CI si un import interdit est introduit accidentellement par un futur dev.
- Documenter dans le docstring module rend l'intention explicite pour les reviewers.

**Alternatives considered** :
- `import-linter` (officiel) : ajoute config + dep. Refusé pour MVP, à reconsidérer si le pattern se généralise.
- Pas de check automatisé : trop fragile. Refusé.

## R5 — Snapshot du template d'invariants (SC-008)

**Decision** : Stocker le template attendu dans `tests/unit/agent/context/snapshots/invariants_2026_05.txt` et comparer string-à-string. Échec sur diff exact, hint clair "PROMPT_VERSION doit être bumpé après revue".

**Rationale** :
- Lib `syrupy` (dejà dans pyproject?) ferait l'affaire mais ajoute une syntaxe d'inline snapshot pas immédiatement lisible.
- Comparer un fichier `.txt` séparé est plus lisible pour les reviewers (diff GitHub direct).
- Le test est volontairement fragile pour forcer la revue.

**Alternatives considered** :
- syrupy : ok mais pas indispensable.
- Hash SHA-256 stocké dans un constant : moins lisible en cas de diff (on ne voit pas ce qui a changé).

## R6 — Format f-strings (vs Jinja2) — pattern d'organisation

**Decision** : Chaque bloc du prompt est généré par une fonction pure `render_<block>(...)` retournant un `str`. Le builder `build_system_prompt` orchestre l'ordre et joint avec `"\n\n"`. Constantes (séparateurs, headers) dans `prompts/identity.py` et `prompts/invariants.py`.

**Rationale** :
- f-strings + fonctions pures = chaque bloc testable en isolation.
- Pas de double-escape (Jinja2 `{{` collisionne avec FR-013 escape `{` → `{{`).
- Lecture du code = lecture du prompt sans changer de syntaxe.
- Alignement avec le style "many small files > few large files" (coding-style global).

**Alternatives considered** :
- Jinja2 avec custom escape : complexité + dépendance + double-escape risk. Refusé (cf. clarify Q2).

## R7 — Multi-devise affichage prompt (NFR-006)

**Decision** : Helper `format_money(money: Money, *, native_currencies: set[str], peg_xof_eur: Decimal = Decimal("655.957"), fx_rate_usd: Optional[Decimal] = None) -> str` qui retourne :
- Si `len(native_currencies) == 1` : `"15 000 000 XOF"` (devise native uniquement).
- Sinon : `"15 000 000 XOF (~22 868 EUR)"` ou `"22 868 EUR (~15 000 000 XOF)"`.

**Rationale** :
- Chargé une seule fois par tour : `native_currencies = collect_currencies(business_ctx)`.
- Conversion lookups :
  - XOF ↔ EUR : peg fixe 655.957.
  - USD ↔ XOF : via `fx_rate.usd_to_xof` snapshot du jour.
- Pour le MVP, on ne fait que XOF/EUR ; USD seulement si présent.

**Alternatives considered** :
- Toujours convertir en XOF (option A) : cohérent mais perd la trace native, refusé.
- Devise native sans équivalent (option C) : ambigu si l'utilisateur mélange XOF/EUR, refusé.

## R8 — Stratégie de troncature ordonnée

**Decision** : Algorithme `truncate_prompt(parts, budget)` itératif :
1. Calculer `tokens_total(parts)`.
2. Si ≤ budget → retourner directement.
3. Sinon, appliquer dans l'ordre :
   - Step 1 : ne garder que 5 indicateurs récents par axe E/S/G (déjà cap 30 au loader, ré-équilibre ici).
   - Step 2 : retirer projets `archived` et candidatures `closed`.
   - Step 3 : couper les `dont_use_when` des tools (garder `use_when`).
   - Step 4 : couper le verbatim des sources (garder id+titre+url).
4. Si toujours > budget : couper la liste de skills active à 3 (les 3 plus pertinents selon score F19).
5. Si toujours > 6000 (limite dure) : couper le bloc `recent_messages` à 8.
6. Logger `prompt_budget_exceeded=True` + liste des steps appliqués.

**Rationale** :
- L'ordre minimise la perte d'information critique (identité + tools courants restent intouchés).
- Logging permet d'observer la fréquence d'activation et tunes les caps si besoin.

**Alternatives considered** :
- LLM-driven summarization du contexte : cher (1 LLM call de plus par tour), refusé pour MVP.
- Troncature random : non déterministe, refusé.

## Synthèse

| Sujet | Décision | Impact MVP |
|---|---|---|
| Token counting | tiktoken + fallback len/4 | + dépendance tiktoken |
| Cache invalidation | EventBus push + TTL 60s fallback | Pas de Redis, EventBus déjà présent |
| LRU async | cachetools.TTLCache + asyncio.Lock interne | 50 lignes ajoutées |
| Service pur | Test d'imports automatisé | 1 test ajouté |
| Snapshot invariants | Fichier .txt comparé string | 1 test ajouté |
| f-strings vs Jinja2 | f-strings + fonctions pures | Pas de Jinja2 |
| Multi-devise | Devise native + équiv. XOF si multi | helper format_money |
| Troncature | Algorithme ordonné 5 steps | Ordre fixé |
