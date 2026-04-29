# F35 — Eval LLM Continue (Golden Set + CI + Post-Processeur + Traçabilité)

**Phase** : 12 — Eval LLM Continue
**Modules brainstorm** : 10.4 (Filtrage contextuel), 10.6 (Évaluation continue eval-driven), 10.7 (Garde-fous UX post-processeur), 10.8 (Ordre priorité)
**Dépendances** : F14 (au minimum) ; idéalement F15, F16, F17, F19, F20
**Estimation** : 2 jours (peut démarrer en parallèle de F14 dès Phase 3)

## Contexte et objectif

> **Sans eval, on corrige à l'aveugle dès qu'on change de modèle (du brainstorming Module 10.6).**

Cette feature livre :
1. Un **golden set de 50–100 cas** : `(message utilisateur, contexte de page) → (tool attendu, payload attendu)`,
2. Un **runner d'eval** exécutable manuellement et en CI,
3. Des **métriques** : taux de bon tool, taux de payload valide, taux d'hallucination de schéma, distribution des fallbacks,
4. Un **post-processeur** (garde-fous UX) :
   - détecte si le LLM a répondu en texte alors qu'un `ask_qcu` aurait convenu (chips de suggestion),
   - détecte un chiffre non sourcé → bandeau d'avertissement (cohérent F03),
   - tracé tous les tool calls (entrée/sortie/durée) pour analyse a posteriori (cohérent F14 `tool_call_log`).

Cette feature est **transverse** : elle peut démarrer en parallèle de F14 dès qu'il y a un pipeline LLM minimal, et grandit avec les phases (Phase 3 → 4 → 5 …).

## User Stories

### US1 — Golden set versionné en git (P1)
**En tant que** dev,
**je veux** un dossier `tests/llm_eval/` versionné en git contenant des fichiers JSON/YAML par catégorie :
- `tools_reponse.yaml` (cas pour ask_qcu, ask_qcm, etc. — F15),
- `tools_visualisation.yaml` (F16),
- `tools_mutation.yaml` (F17),
- `skills_<name>.yaml` (cas par skill — F21).

**Format** :
```yaml
- id: "qcu-forme-juridique"
  description: "L'utilisateur ne sait pas comment formaliser le type de société"
  context:
    page: "/profil/entreprise"
    intent: "profilage"
    entity: null
  user_message: "Quelle est ma forme juridique déjà ?"
  expected:
    tool: "ask_qcu"
    payload_partial:
      options_count_min: 4
      options_contain: ["SARL", "SA"]
  tags: ["profil", "entreprise", "forme_juridique"]
```

**afin de** documenter ce qu'on attend du LLM cas par cas.

### US2 — Runner d'eval exécutable (P1)
**En tant que** dev,
**je veux** une commande `python -m backend.scripts.run_llm_eval [--filter=tag] [--output=json|markdown]` qui :
- charge le golden set,
- exécute chaque cas via le pipeline F14 (mode "eval" — pas de persistance side effect),
- compare le résultat (tool name + payload partial match) à l'attendu,
- produit un rapport.

**afin de** mesurer l'état actuel.

### US3 — Métriques calculées (P1)
**En tant que** dev,
**je veux** des métriques calculées :
- `tool_match_rate` : % de cas où le bon tool est invoqué,
- `payload_valid_rate` : % de payloads passant Pydantic,
- `payload_partial_match_rate` : % matchant les contraintes définies,
- `fallback_rate` : % retombés en texte libre,
- `retries_avg` : nombre moyen de retries Pydantic,
- distribution par tag (catégorie).

**afin de** identifier les zones de fragilité.

### US4 — CI pipeline (P1)
**En tant que** dev,
**je veux** un workflow GitHub Actions (ou équivalent) qui :
- exécute l'eval set sur chaque PR touchant le pipeline LLM, les tools, ou les skills,
- compare les métriques contre la baseline (commitée en git),
- bloque la PR si régression > seuil défini.

**afin de** prévenir les régressions automatiquement.

### US5 — Post-processeur : détection texte libre vs question fermée (P2)
**En tant que** dev,
**je veux** un module `post_processor.py` qui analyse la réponse texte LLM :
- détecte les patterns de question fermée ("préférez-vous A, B ou C ?", énumérations "1.…2.…3.…", "oui ou non ?"),
- si trouvé, propose des **chips de suggestion** côté UI (ex : 3 boutons cliquables sous la bulle),
- ou bien, demande au LLM de reformuler avec un `ask_qcu`.

**afin de** rattraper les cas où le LLM a oublié d'utiliser un tool.

### US6 — Post-processeur : détection chiffre non sourcé (P1)
**En tant que** dev,
**je veux** que si le LLM produit un chiffre / critère / formule / seuil **sans** invoquer `cite_source` (cohérent F03), un **bandeau d'avertissement** "non sourcé" s'affiche sous la bulle + log d'incident,
**afin de** rappeler la règle d'or (Module 0.1) même si la validation backend a un trou.

### US7 — Tracé des tool calls dans `tool_call_log` (P1)
**En tant que** dev,
**je veux** que **chaque tool call** soit tracé dans `tool_call_log` (déjà créé F14) avec : `tool_name, arguments, result, status, latency_ms, retries, model, prompt_tokens, completion_tokens`,
**afin de** analyse a posteriori et debug.

### US8 — Dashboard admin des métriques eval (P2)
**En tant qu'**admin,
**je veux** une page `/admin/llm-eval` affichant :
- métriques agrégées sur la dernière semaine,
- top 10 des cas qui régressent,
- distribution des fallbacks,
- distribution des erreurs Pydantic.

**afin de** piloter l'amélioration continue.

### US9 — Édition des golden examples depuis l'UI (P3)
**En tant qu'**admin,
**je veux** ajouter/éditer un golden example via le back-office (cohérent F20),
**afin de** capturer un cas réel observé en prod.

**Mécanisme** : sync bidirectionnelle entre `golden_examples` table (par skill F19) et fichiers `tests/llm_eval/` git (export quotidien ou à la demande).

## Exigences fonctionnelles

- **FR-001** : Dossier `tests/llm_eval/` avec sous-dossiers par catégorie + YAML par cas.
- **FR-002** : Module `eval_runner.py` :
  - `run_eval(filter_tags?, parallel=N) -> EvalReport`,
  - mode "eval" du pipeline F14 (pas de persistance, pas de side-effects côté DB).
- **FR-003** : Comparateur `compare_payload(expected_partial, actual) -> bool` qui supporte :
  - `options_count_min/max`,
  - `options_contain`,
  - exact match sur certains champs,
  - regex sur champs texte.
- **FR-004** : Output `EvalReport` en JSON et Markdown (lisible pour PR).
- **FR-005** : GitHub Action `.github/workflows/llm-eval.yml` qui exécute le runner sur les PR touchant `backend/llm/`, `backend/tools/`, `backend/skills/`, `tests/llm_eval/`.
- **FR-006** : Baseline metrics committed en `tests/llm_eval/baseline.json`. Régression détectée si delta > X% (configurable).
- **FR-007** : Post-processeur (US5, US6) hook dans le pipeline F14 entre validation et envoi front. Émet :
  - `chips_suggestion` event SSE si pattern détecté,
  - `unsourced_warning` event SSE si chiffre non sourcé.
- **FR-008** : Composant Vue `<ChipsSuggestion :options>` qui rend les chips cliquables sous la bulle (ne casse pas la règle UX F15 — c'est une suggestion auxiliaire, pas un widget de saisie).
- **FR-009** : Composant Vue `<UnsourcedWarning>` rendu sous la bulle quand un chiffre non sourcé est détecté.
- **FR-010** : Page admin `/admin/llm-eval` consommant `tool_call_log` agrégé.
- **FR-011** : Démarrage avec **30 cas critiques** (Module 10.8 priorité 3 : ask_*, show_kpi_card, mutations Profil) ; étendre à 100 progressivement.

## Exigences non-fonctionnelles

- **NFR-001** : Eval set de 100 cas s'exécute en < 10 min (parallèle si possible — mais OpenRouter rate limits à respecter).
- **NFR-002** : Coût d'un run d'eval < 1 USD avec minimax-m2.7 (à mesurer).
- **NFR-003** : Le post-processeur ajoute < 100ms de latence par message.
- **NFR-004** : Les patterns de détection (texte libre, chiffre non sourcé) sont configurables sans déploiement (table ou fichier YAML lu au runtime).

## Entités clés

- Pas de nouvelle table — `tool_call_log` (F14) suffit.
- Fichiers eval set en git.

## Success Criteria

- **SC-001** : Eval set de 30 cas sur F15 (tools réponse) → `tool_match_rate ≥ 0.85`.
- **SC-002** : CI bloque une PR qui fait passer `tool_match_rate` de 0.85 à 0.70.
- **SC-003** : Post-processeur détecte une question fermée non outillée et propose des chips.
- **SC-004** : 100% des chiffres affichés sans source génèrent un warning visible.
- **SC-005** : Dashboard admin affiche métriques en < 2s.

## Hors-scope MVP

- Tests A/B en production sur sous-ensembles d'utilisateurs (post-MVP).
- Apprentissage en ligne sur les corrections utilisateurs (post-MVP).
- Eval set étendu (>200 cas, multi-modèles).
- Comparaison de modèles (minimax-m2.7 vs Claude vs GPT-4o) — possible mais hors-MVP.
- Synthetic data generation (créer des golden examples par LLM) — post-MVP.

## Risques et points de vigilance

- **Eval set représentatif** : 30 cas inventés en interne ≠ usage réel. Compléter avec des cas observés en production (capture des sessions PME pilotes).
- **Coût des runs** : 100 cas × 5 PR/jour = 500 calls/jour OpenRouter. Acceptable mais à monitorer.
- **Non-déterminisme du LLM** : même prompt peut donner 2 résultats différents. Recommandation : `temperature=0` en eval, eval N=3 pour stabilité, prendre le mode.
- **Patterns de post-processeur trop laxistes / trop stricts** : itérer en analysant les faux positifs/négatifs sur les sessions réelles.
- **Synchro `golden_examples` BDD ↔ git** : éviter les diff bruyants. Format YAML stable, ordre des clés fixe.
- **Module 10.8 priorité MVP** : démarrer avec **3 niveaux d'eval** progressivement :
  1. Tools critiques (ask_*, show_kpi_card) — semaine 1.
  2. Mutations Profil — semaine 2.
  3. Skills (esg_diagnostic, score_gcf, dossier) — semaine 3+.
