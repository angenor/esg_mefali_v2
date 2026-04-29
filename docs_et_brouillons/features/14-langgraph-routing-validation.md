# F14 — LangGraph Routing & Validation Pydantic + Retry

**Phase** : 3 — Chat & LLM Tool-Use
**Modules brainstorm** : 10.1 (Architecture en couches), 10.2 (Tools auto-descriptifs), 10.3 (System prompt arbre de décision), 10.5 (Validation + retry)
**Dépendances** : F13
**Estimation** : 3 jours

## Contexte et objectif

Le LLM laissé seul face à 30+ tools (réponse, visualisation, mutation, lecture/calcul/recherche) **dégrade rapidement** : mauvais tool, mauvais payload, hallucination de schéma. Cette feature est le **garde-fou structurel** qui rend le tool-use fiable.

Architecture livrée :

```
[Classifier d'intention LLM léger ou règles]
  → [Sélecteur de sous-ensemble de tools (5–10 max selon page + intention + entités actives)]
    → [LLM principal (minimax-m2.7) avec tools filtrés]
      → [Validateur Pydantic systématique du payload]
        → [Boucle de retry max 2 si payload invalide, fallback texte sinon]
          → [Réponse au frontend]
```

Cette feature livre **le moteur**. Les tools eux-mêmes (ask_*, show_*, mutations) viennent en F15, F16, F17. Les Skills viennent en F19. F35 livrera l'eval-driven measurement.

## User Stories

### US1 — Classifier d'intention déterministe (P1)
**En tant que** dev backend,
**je veux** un classifier qui catégorise un message utilisateur en intention parmi : `profilage`, `mutation`, `analyse`, `navigation`, `question_fermee`, `aide`, `autre`,
**afin de** sélectionner ensuite le bon sous-ensemble de tools.

**Approche MVP** :
- Première passe règles (regex/keywords pour patterns évidents : "supprime", "ajoute", "compare", "explique").
- Deuxième passe LLM léger (Haiku via OpenRouter ou minimax-m2.7 lui-même avec un prompt court) si règles ambiguës.
- Cache de la dernière intention par thread pour éviter de reclassifier à chaque tour.

### US2 — Sélecteur de sous-ensemble de tools (P1)
**En tant que** dev backend,
**je veux** un sélecteur qui retourne **5 à 10 tools maximum** par tour selon : intention (US1) + page courante (`context_json`) + entités actives + skills actives (F19),
**afin de** ne jamais surcharger le LLM.

**Scénarios** :
1. Page `Profil → Entreprise` + intention `mutation` → tools : `update_company_profile`, `ask_qcu`, `ask_select`, `show_summary_card`.
2. Page `Candidatures` + intention `analyse` → tools : `show_match_card`, `show_radar_chart`, `show_comparison_table`, `cite_source`, `search_source`.
3. Page n'importe quelle + intention `aide` → tools : `ask_qcu`, `ask_yes_no`.

### US3 — Tools auto-descriptifs (P1)
**En tant que** dev,
**je veux** que chaque tool exposé au LLM ait :
- nom verbal sans ambiguïté (`update_candidature_status`, jamais `do_thing`),
- description avec règles "use when / don't use when" explicites,
- exemples positifs et négatifs (few-shot inline),
- schéma Pydantic strict (champs requis, enums fermés, bornes, regex).

**afin que** le LLM choisisse correctement même sans vu sur les autres tools.

Cette feature livre **la convention de définition d'un tool** (classe Python avec décorateur ou Pydantic + helper) ; les tools concrets viendront en F15/F16/F17.

### US4 — System prompt avec arbre de décision (P1)
**En tant que** dev,
**je veux** un system prompt construit dynamiquement qui inclut :
- les invariants de la plateforme (sourçage, multi-tenant, langue FR, ton),
- l'arbre de décision tools (Module 10.3 du brainstorming),
- les anti-exemples ("ne fais pas X parce que Y"),
- les tools sélectionnés (US2) avec leurs descriptions,
- le contexte de page (entité courante).

**afin de** maximiser la précision de sélection.

### US5 — Validation Pydantic systématique (P1)
**En tant que** dev,
**je veux** que tout payload renvoyé par le LLM soit validé via le schéma Pydantic du tool correspondant **avant** d'être exécuté ou rendu côté front,
**afin de** rejeter immédiatement les hallucinations de schéma.

### US6 — Boucle de retry avec erreur structurée (P1)
**En tant que** dev,
**je veux** que si la validation échoue, l'erreur soit re-envoyée au LLM **structurée** ("le champ `severity` doit être un enum parmi [blocking, warning, info], tu as envoyé `critical`"), avec **max 2 retries**, puis fallback texte ("je n'arrive pas à formaliser cette action — peux-tu reformuler ?") + log d'incident.

### US7 — Logging des tool calls (P2)
**En tant que** dev,
**je veux** que chaque appel de tool (entrée, sortie, durée, succès/erreur) soit loggué dans une table `tool_call_log`,
**afin de** pouvoir analyser a posteriori et ajuster les descriptions / system prompt.

Sera consommé par F35 (Eval).

## Exigences fonctionnelles

- **FR-001** : Module backend `langgraph_orchestrator.py` exposant une fonction `respond(user_message, context, thread_history) -> ChatResponse` qui implémente le pipeline complet (classifier → sélecteur → LLM → validateur → retry → réponse).
- **FR-002** : Décorateur `@tool` avec metadata : `name, description, use_when, dont_use_when, examples, schema (Pydantic class), handler (callable async)`. Registry global `TOOL_REGISTRY: dict[str, ToolDef]`.
- **FR-003** : Module `intent_classifier.py` : `classify(message: str, context: dict) -> Intent` (avec règles + LLM léger en fallback). Cache LRU par thread.
- **FR-004** : Module `tool_selector.py` : `select_tools(intent, context, active_skills) -> list[ToolDef]` avec règles déclaratives (config JSON ou Python dict). Limite hard 10 tools.
- **FR-005** : Module `system_prompt_builder.py` : `build(context, tools, skills) -> str` qui concatène les briques (invariants + arbre décision + anti-exemples + tools + contexte).
- **FR-006** : Module `payload_validator.py` : `validate(tool_name, payload) -> ValidatedPayload | ValidationError`. Erreur structurée avec champ, valeur reçue, valeur attendue.
- **FR-007** : Stratégie retry : si `ValidationError`, re-call LLM avec un message d'erreur formaté ; max 2 tries ; sinon fallback texte (configurable).
- **FR-008** : Table `tool_call_log` : `id, account_id, user_id, thread_id, tool_name, arguments_json, result_json, status ENUM('ok','validation_error','handler_error','timeout'), latency_ms, retries INT, model, prompt_tokens, completion_tokens, created_at`. Cohérent F10 `LlmUsageLog` (peut fusionner ou rester distinct ; recommandation : 2 tables, JOIN possible).
- **FR-009** : Le pipeline est **streamable** : émettre des events SSE au fur et à mesure (`thinking`, `tool_call_started`, `tool_call_completed`, `text_delta`, `message_done`) — cohérent F13 streaming.
- **FR-010** : Hook d'extension pour Skills (F19) : le sélecteur de tools peut être restreint par `skill.tool_whitelist`. F14 prévoit l'API ; F19 livre le moteur Skills.

## Exigences non-fonctionnelles

- **NFR-001** : Latence ajoutée par le pipeline (classifier + sélecteur + validateur + retry) < 1 seconde p95 (hors temps LLM principal).
- **NFR-002** : Le system prompt total (invariants + tools descriptions + skills + contexte) doit tenir en < 4 000 tokens. Au-delà, alarme et tronquer prudemment.
- **NFR-003** : Le retry n'incrémente pas l'usage tokens du quota PME — c'est un coût plateforme. Logger séparément.
- **NFR-004** : Le pipeline doit être resilient : si le classifier LLM échoue, fallback sur règles ; si le sélecteur retourne 0 tools, exposer un set par défaut minimal.

## Entités clés

- **ToolCallLog** (FR-008).
- Aucune table métier nouvelle — surtout du code.

## Success Criteria

- **SC-001** : 5 tools fictifs déclarés avec le décorateur `@tool` → classifier + sélecteur fonctionnent sur 10 cas tests.
- **SC-002** : Validation Pydantic rejette correctement 5 payloads malformés avec erreur structurée lisible.
- **SC-003** : Retry avec erreur structurée → LLM corrige sur 80%+ des cas (mesuré sur eval set F35 quand dispo).
- **SC-004** : Streaming SSE : un message "complexe" (tool call + texte de suite) arrive au front en plusieurs events lisibles.
- **SC-005** : Logs `tool_call_log` enregistrés à 100% (vérifié par test d'intégration).

## Hors-scope MVP (post-MVP)

- Routage multi-modèle (Haiku pour classifier, GPT-4o ou Claude pour analyse complexe). MVP : un seul modèle (minimax-m2.7) configuré via `LLM_MODEL`.
- Cache sémantique des réponses tools (post-MVP).
- Apprentissage en ligne sur les corrections utilisateurs.
- Plus de 10 tools concurrents par tour (volontairement limité en MVP).

## Risques et points de vigilance

- **Sélecteur trop strict** : si le sélecteur ne propose pas le bon tool, le LLM va répondre en texte alors qu'un tool aurait convenu. F35 (post-processeur) compensera, mais le sélecteur doit être bon. Démarrer permissif (8-10 tools par défaut) puis raffiner avec eval.
- **Validation Pydantic trop laxiste** : un schéma sans `extra='forbid'` laisse passer des champs hallucinés. Verrouiller : `model_config = ConfigDict(extra='forbid')` partout.
- **System prompt drift** : ajouter un tool sans mettre à jour l'arbre de décision = drift. Centraliser dans un module `system_prompt_builder.py` qui reconstruit dynamiquement à partir du registry.
- **Coût retry** : 2 retries × prompt énorme = coût explosif. Limiter le contexte renvoyé en retry au strict nécessaire (tool name, schéma, erreur, ignorer l'historique long).
- **Détection d'intention ambiguë** : "modifier mon projet" peut être profilage OU mutation. Quand ambigu, on demande au LLM de poser une question (ask_qcu) — c'est le cas d'usage de F15.
