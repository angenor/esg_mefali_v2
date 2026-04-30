# Feature Specification: Eval LLM Continue (Golden Set + Post-Processeur + Traçabilité)

**Feature Branch**: `035-eval-llm-postprocess`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F35 — Eval LLM Continue (Golden Set + Post-Processeur + Traçabilité). Scope MVP TRÈS focalisé : framework eval avec golden set 10-20 cas YAML/JSON minimal + post-processeur (chips sources + bandeau non sourcé) + endpoint admin trigger eval. Différé : CI eval gating, golden set 50-100, frontend, dashboard."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Golden set versionné + runner d'évaluation (Priority: P1)

L'équipe maintient un golden set de 10–20 cas représentatifs (paires `(message utilisateur, contexte) → (tool attendu, payload attendu)`) versionnés en git sous `tests/llm_eval/`. Un runner exécute le golden set contre le pipeline LLM (mode "eval", aucune écriture en base) et produit un rapport de métriques (tool match rate, payload partial match rate, fallback rate).

**Why this priority**: Sans cadre d'évaluation reproductible, toute itération sur prompt/modèle/skill se fait à l'aveugle. Ce livrable établit la baseline mesurable.

**Independent Test**: Lancer le runner via CLI sur un golden set seed (10 cas) et vérifier que le rapport JSON+Markdown contient les métriques attendues, sans qu'aucune ligne ne soit écrite en base hors `tool_call_log`.

**Acceptance Scenarios**:

1. **Given** un golden set de 10 cas YAML, **When** un dev exécute le runner, **Then** le rapport contient `tool_match_rate`, `payload_partial_match_rate`, `fallback_rate` et la liste détaillée par cas (passed/failed + raison).
2. **Given** un cas avec `expected.tool: ask_qcu` et le LLM renvoie `ask_qcm`, **When** le comparateur évalue, **Then** le cas est marqué `failed` avec raison `tool_mismatch`.
3. **Given** un cas avec `payload_partial.options_count_min: 4`, **When** le LLM renvoie 3 options, **Then** le cas est marqué `failed` avec raison `payload_partial_mismatch`.

---

### User Story 2 - Post-processeur garde-fous UX (Priority: P1)

Après que le pipeline LLM produit une réponse, un post-processeur analyse la sortie et émet deux types de signaux côté chat :
- **Chips de suggestion** lorsqu'une question fermée est détectée dans le texte libre (ex : "préférez-vous A, B ou C ?") sans tool d'interaction associé.
- **Bandeau "non sourcé"** lorsqu'un chiffre, seuil ou critère est mentionné sans qu'aucun appel `cite_source` n'ait été effectué dans le tour.

**Why this priority**: Garde-fou contre les régressions UX et contre les hallucinations non sourcées (règle d'or F03). Cohérent avec Module 0.1 du brainstorm.

**Independent Test**: Soumettre une réponse synthétique contenant "1. Option A 2. Option B 3. Option C" et vérifier que le post-processeur émet un signal `chips_suggestion`. Soumettre "le seuil est de 50 000 FCFA" sans cite_source et vérifier `unsourced_warning`.

**Acceptance Scenarios**:

1. **Given** une réponse texte contenant un pattern d'énumération de choix, **When** le post-processeur s'exécute, **Then** un signal `chips_suggestion` avec les options extraites est attaché au message.
2. **Given** une réponse contenant un chiffre/seuil sans `cite_source`, **When** le post-processeur s'exécute, **Then** un signal `unsourced_warning` est émis et un incident est loggé (audit log).
3. **Given** une réponse avec `cite_source` valide, **When** le post-processeur s'exécute, **Then** aucun signal `unsourced_warning` n'est émis.

---

### User Story 3 - Endpoint admin pour déclencher une eval (Priority: P1)

Un admin authentifié déclenche un run d'évaluation via un endpoint API en filtrant éventuellement par tag. La réponse contient le rapport synthétique (métriques globales + résumé par cas).

**Why this priority**: Sans interface (frontend différé), l'endpoint est l'unique surface MVP pour exécuter une eval à la demande.

**Independent Test**: Authentifier en admin, appeler `POST /api/admin/llm-eval/run` et obtenir un rapport JSON < 30s pour 10 cas.

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il appelle l'endpoint sans filtre, **Then** le runner exécute tous les cas du golden set et renvoie un rapport.
2. **Given** un utilisateur PME, **When** il appelle l'endpoint, **Then** la requête est rejetée (403).
3. **Given** un filtre `tags=["forme_juridique"]`, **When** l'endpoint est appelé, **Then** seuls les cas correspondants sont exécutés.

---

### Edge Cases

- Golden set vide → runner renvoie un rapport vide avec métriques nulles, pas d'erreur.
- LLM indisponible (timeout) → cas marqué `failed` avec raison `llm_timeout`, le run continue.
- Payload pas valide Pydantic → cas marqué `failed` avec raison `payload_invalid`.
- Post-processeur sur réponse vide → aucun signal émis.
- Chiffre cité dans une citation explicite avec `cite_source` valide → pas de bandeau non sourcé.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST stocker un golden set sous `tests/llm_eval/` versionné en git, format YAML, avec 10–20 cas seed.
- **FR-002** : Chaque cas MUST contenir : `id`, `description`, `context` (page, intent, entity), `user_message`, `expected.tool`, `expected.payload_partial`, `tags`.
- **FR-003** : Le système MUST fournir une commande CLI `python -m backend.scripts.run_llm_eval [--filter=tag] [--output=json|markdown]`.
- **FR-004** : Le runner MUST exécuter chaque cas en mode "eval" (pas d'écriture DB hors `tool_call_log` minimal) et produire un rapport contenant : `tool_match_rate`, `payload_partial_match_rate`, `fallback_rate`, détails par cas.
- **FR-005** : Le système MUST fournir un comparateur `compare_payload(expected_partial, actual)` supportant : `options_count_min`, `options_count_max`, `options_contain`, `equals`, `regex`.
- **FR-006** : Le système MUST fournir un post-processeur appelé après validation et avant émission front qui détecte les patterns d'énumération (signal `chips_suggestion`) et chiffres/seuils sans `cite_source` (signal `unsourced_warning`).
- **FR-007** : Les patterns de détection MUST être configurables via un fichier YAML lu au démarrage.
- **FR-008** : Le système MUST exposer un endpoint `POST /api/admin/llm-eval/run` accessible uniquement aux admins.
- **FR-009** : Le système MUST tracer chaque tool call dans `tool_call_log` avec : `tool_name`, `arguments`, `result`, `status`, `latency_ms`, `model`.
- **FR-010** : Les incidents `unsourced_warning` MUST être journalisés dans l'audit log avec `event_type="llm_unsourced"`.
- **FR-011** : Le post-processeur MUST se désactiver silencieusement si la réponse n'est pas du texte libre.

### Key Entities

- **GoldenCase** : un cas d'évaluation (fichier YAML) — `id`, `description`, `context`, `user_message`, `expected`, `tags`. Stocké en git, pas en base.
- **EvalReport** : sortie du runner — métriques agrégées + détails par cas. Pas persisté en base au MVP.
- **PostProcessSignal** : signal attaché à un message du chat — `type` (`chips_suggestion`|`unsourced_warning`), `payload`, `message_id`.
- **ToolCallLog** (existant F14) : utilisé tel quel pour tracer chaque appel tool.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Un dev exécute le golden set seed (10 cas) en moins de 60 secondes en local et obtient un rapport lisible.
- **SC-002** : Le post-processeur détecte 100 % des chiffres/seuils mentionnés sans source dans un échantillon de 5 réponses synthétiques de test.
- **SC-003** : L'endpoint admin renvoie un rapport en moins de 30 secondes pour 10 cas.
- **SC-004** : Couverture de tests ≥ 80 % sur les modules `eval_runner`, `post_processor`, `compare_payload`.
- **SC-005** : Une PME (rôle non admin) ne peut pas appeler l'endpoint d'évaluation (403).

## Assumptions

- Le pipeline LLM minimal F14 (langgraph-routing-validation) est mergé et expose un mode "eval" non persistant.
- La table `tool_call_log` existe (créée par F14).
- L'audit log centralisé est disponible (Module 0).
- Les signaux post-processeur sont attachés à la réponse côté backend ; le rendu frontend est différé.
- Le golden set MVP cible 10–20 cas critiques ; extension à 50–100 différée.
- Le gating CI sur eval est différé hors MVP.
- Les modèles LLM utilisés respectent `temperature=0` en eval.

## Hors-scope MVP (Differred)

- Workflow GitHub Actions de gating eval sur PR.
- Golden set étendu (50–100 cas) et golden set par skill.
- Composants frontend `<ChipsSuggestion>`, `<UnsourcedWarning>`.
- Page admin `/admin/llm-eval` et dashboard métriques.
- Édition de golden examples depuis l'UI (sync git ↔ DB).
- Comparaison multi-modèles, A/B testing en prod, synthetic data generation.
