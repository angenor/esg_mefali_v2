# F20 — CRUD Skills Back-Office (workflow draft→published, anti-injection, eval gating)

**Phase** : 4 — Skills (Playbooks Métier)
**Modules brainstorm** : 11.2 (Catalogue MVP), 11.3 (Stockage), 11.4 (Garde-fous)
**Dépendances** : F06, F19
**Estimation** : 1.5–2 jours

## Contexte et objectif

Permettre aux **admins ESG Mefali** de créer, éditer, publier et versionner les Skills via le back-office (Module 9 + 11.3 du brainstorming).

> **Frontière nette (du brainstorming Module 11.3)** :
> | Couche | Où | Qui édite |
> |---|---|---|
> | Moteur de skills (loader, fusion, validateur) | Code Git Python/FastAPI | Devs |
> | Catalogue des **noms de tools** | Code Git | Devs |
> | Schémas Pydantic des tools | Code Git | Devs |
> | **Contenu de skill** (prompt, procédure, sources, exemples) | **BDD** | Admins via back-office |
> | **Tool whitelist par skill** | BDD (multi-select sur la liste code) | Admins |

Aucune logique critique n'est éditable via UI — seulement le contenu métier.

## User Stories

### US1 — Liste des skills avec leur statut (P1)
**En tant qu'**admin,
**je veux** une page `/admin/skills` listant toutes les skills avec colonnes : nom, domain, version, statut, sources liées, créateur, dernière modif,
**afin de** avoir une vue d'ensemble.

### US2 — Créer/éditer une skill (P1)
**En tant qu'**admin,
**je veux** un formulaire `/admin/skills/new` ou `/admin/skills/[id]/edit` avec sections :
- Identité : `name`, `domain`, `version`,
- Prompt expert : éditeur markdown (toast-ui/editor déjà installé F01) avec compteur de tokens en live,
- Procédure : éditeur markdown,
- Tool whitelist : multi-select alimenté par le registry de tools (F14, F15, F16, F17),
- Sources : multi-select sur les sources `verified` (F07),
- Activation rules : éditeur JSON avec validation live (FR-003 F19),
- Golden examples : éditeur JSON ou liste de paires `(message, tool_attendu, payload_attendu)`.

**afin de** éditer toutes les facettes.

### US3 — Validation au save (P1)
**En tant qu'**admin,
**je veux** que le save vérifie :
- les `tool_whitelist` ne contiennent que des noms de tools réellement enregistrés en code,
- les `sources` existent et sont `verified`,
- le `prompt_expert` ne dépasse pas `SKILL_PROMPT_MAX_TOKENS` (F19),
- l'`activation_rules` parse selon le schéma JSON strict (F19),
- les `golden_examples` sont au moins au nombre de 5 (recommandation Module 11.1).

**afin de** ne pas publier une skill cassée.

### US4 — Workflow draft → published (P1)
**En tant qu'**admin,
**je veux** un bouton "Publier" qui ne fonctionne que si :
- toutes les validations US3 passent,
- toutes les sources liées sont `verified`,
- (optionnel mais fortement recommandé) l'eval gating des golden examples passe (US6).

**afin de** garantir la qualité avant exposition.

### US5 — Versioning automatique (P1)
**En tant qu'**admin,
**je veux** que toute édition d'une skill `published` crée une nouvelle version (cohérent F04),
**afin de** ne jamais casser les conversations en cours (snapshot F19 US8).

### US6 — Eval gating obligatoire avant publication (P1)
**En tant qu'**admin,
**je veux** un bouton "Run eval" qui exécute les `golden_examples` de la skill sur la version `draft` et retourne :
- taux de bon tool,
- taux de payload valide,
- distribution des fallbacks,
- diff vs version `published` précédente.

**Et** que la publication soit **bloquée** si régression > seuil défini (ex : taux de bon tool baisse de plus de 10 points).

**afin de** ne pas publier une régression.

Cette feature livre l'eval gating MVP : exécution simple des golden examples avec réponse LLM en sandbox. F35 livrera l'eval continue plus large.

### US7 — Anti-injection (P1)
**En tant que** garant de la sécurité,
**je veux** que le `prompt_expert` soit scanné automatiquement à la sauvegarde pour détecter :
- patterns d'injection ("ignore previous instructions", "tu es désormais...", "system:", "</system>", etc.),
- caractères de contrôle anormaux,
- présence de tokens secrets en dur (regex simple).

**afin de** bloquer les tentatives d'injection malicieuses ou les fuites accidentelles.

**Scénarios** :
1. Save bloqué avec liste des patterns détectés → admin doit corriger.
2. Override possible via case "Override anti-injection" + saisie de motif (logué dans audit).

### US8 — Audit log (P1)
**En tant que** compliance,
**je veux** chaque édition de skill journalisée dans `audit_log` (F04) avec `source_of_change='admin'`, contenu avant/après,
**afin de** tracer.

### US9 — Visualisation des golden examples (P2)
**En tant qu'**admin,
**je veux** voir les golden examples sous forme de tableau (input → tool attendu → payload attendu) avec status de la dernière exécution (vert/rouge),
**afin de** identifier les cas qui régressent.

## Exigences fonctionnelles

- **FR-001** : Endpoints REST :
  - `GET /admin/skills/` (liste paginée, filtres status / domain),
  - `POST /admin/skills/` (create),
  - `GET /admin/skills/{id}`,
  - `PUT /admin/skills/{id}` (update — crée nouvelle version si published),
  - `POST /admin/skills/{id}/publish`,
  - `POST /admin/skills/{id}/run-eval` (exécute golden examples → retourne métriques),
  - `GET /admin/skills/{id}/versions`.
- **FR-002** : Page Vue `/admin/skills` (liste) + `/admin/skills/[id]/edit` (formulaire) avec sections US2.
- **FR-003** : Compteur de tokens en live sur le `prompt_expert` (calcul approximatif `n_chars/4` ou `tiktoken` côté serveur via endpoint `POST /admin/skills/_estimate-tokens`).
- **FR-004** : Validation FR-003 exécutée au save **et** au publish (double check).
- **FR-005** : Validateur anti-injection : module `anti_injection.py` avec liste de patterns regex configurable. Exposé dans une fonction `scan(text) -> list[Issue]`.
- **FR-006** : Eval runner : module `skill_evaluator.py` qui :
  - pour chaque golden example, construit le contexte de test,
  - invoque le pipeline F14 avec la skill draft chargée,
  - compare tool_called + payload contre attendu,
  - retourne `{tool_match_rate, payload_valid_rate, fallback_rate}`.
- **FR-007** : Seuils de gating configurables (`SKILL_EVAL_GATING_TOOL_MATCH_MIN=0.8`, `SKILL_EVAL_GATING_PAYLOAD_VALID_MIN=0.9`). Publication bloquée sinon.
- **FR-008** : Pas de mutations LLM sur les skills (cohérent F17 US10) — réservé back-office strictement.
- **FR-009** : Limite stricte du `prompt_expert` (≤ `SKILL_PROMPT_MAX_TOKENS`). UI affiche barre de progression rouge si > 80%, bloque > 100%.

## Exigences non-fonctionnelles

- **NFR-001** : Le formulaire d'édition d'une skill (10 KB de prompt + 20 sources + 30 golden examples) charge et persiste en < 2s.
- **NFR-002** : L'eval runner sur 30 golden examples se termine en < 60s (parallélisable post-MVP, séquentiel MVP).
- **NFR-003** : L'audit log de skills tracke les diffs structurés (par section : prompt_expert, procedure, tool_whitelist, sources, etc.) — pas seulement un blob.
- **NFR-004** : Hot reload : après publication, le loader F19 récupère la nouvelle version au prochain tour LLM (pas de cache TTL > 1 min).

## Entités clés

- Réutilise `skill` et `skill_source` de F19.
- Audit log enrichi (cohérent F04).

## Success Criteria

- **SC-001** : Un admin crée une skill, l'édite, l'évalue avec 5 golden examples, et la publie en < 30 min.
- **SC-002** : Tentative de publication d'une skill avec source `pending` → rejet avec message clair.
- **SC-003** : Pattern d'injection détecté → save bloqué.
- **SC-004** : Eval gating bloque publication si régression > seuil.
- **SC-005** : Versioning crée une v2 quand on édite une skill v1 published, l'ancienne reste accessible.

## Hors-scope MVP

- Eval continu / planifié (post-MVP F35 livrera le set étendu).
- Comparaison visuelle de versions (post-MVP).
- Suggestions LLM pour améliorer une skill (post-MVP).
- Marketplace skills.
- Copie de skill (skill A → variante B).

## Risques et points de vigilance

- **Patterns anti-injection trop laxistes / trop stricts** : démarrer simple (regex de mots-clés évidents) et raffiner avec retours admin.
- **Eval runner coûteux** : 30 examples × LLM call = 30 appels API. Sur OpenRouter, 30 appels avec minimax-m2.7 = quelques cents par run. Acceptable mais surveiller.
- **Édition collaborative** : 2 admins éditant la même skill = conflit version optimiste (cohérent F11/F12 If-Match).
- **Format golden examples** : à standardiser. Recommandation : `[{input_message, page_context, intent, expected_tool, expected_payload}]`. Cohérent avec format eval set F35.
- **Boucle de feedback** : un admin qui modifie une skill et la publie sans eval (override) doit générer un warning visible.
