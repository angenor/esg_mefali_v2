# F19 — Moteur de Skills (loader, fusion prompt, injection sources, intégration LangGraph)

**Phase** : 4 — Skills (Playbooks Métier)
**Modules brainstorm** : 11.1 (Définition), 11.3 (Stockage hybride), 11.5 (Chargement dans LangGraph)
**Dépendances** : F03, F06, F09, F14
**Estimation** : 2 jours

## Contexte et objectif

> **Problème (du brainstorming)** : un seul system prompt monolithique qui couvre tous les domaines (diagnostic ESG, scoring GCF, génération dossier BOAD, calcul carbone, attestation…) **dilue** les instructions critiques (sourçage, garde-fous) et fait dériver le LLM hors de son domaine.

Une **Skill** = bundle métier réutilisable qui combine **un prompt expert focalisé**, **un sous-ensemble de tools autorisés**, **une procédure pas-à-pas**, **des sources pré-résolues**, et **des exemples gold**. Chargée dynamiquement par le sélecteur LangGraph (F14) selon le contexte (page, intention, entité active, offre/référentiel ciblé).

F19 livre **le moteur** (loader, fusion prompt, injection sources, intégration LangGraph). F20 livrera le CRUD back-office. F21 livrera les skills MVP seedées.

## User Stories

### US1 — Schéma BDD Skill (P1)
**En tant qu'**architecte,
**je veux** une table `skill` avec tous les champs du brainstorming Module 11.3 :
- `id, name (unique), version, domain`,
- `prompt_expert TEXT`,
- `procedure TEXT`,
- `tool_whitelist TEXT[]` (multi-select sur les noms valides en code),
- `sources INT[]` (FK vers Source, F03),
- `activation_rules JSONB` (page, intent, entity),
- `golden_examples JSONB`,
- `status ENUM('draft','published')`,
- `created_by, verified_by, valid_from, valid_to, version`.

**afin de** stocker les skills proprement.

### US2 — Loader de skills selon contexte (P1)
**En tant que** dev,
**je veux** un module `skill_loader.py` qui retourne **1 à 2 skills max** selon `(page, intent, entity_active, offre_ciblee, referentiel_ciblé)`,
**afin de** ne jamais surcharger le LLM.

**Scénarios** :
1. Page `/profil/projets/[id]` + intent `analyse` → skill `skill_esg_diagnostic`.
2. Candidature ciblée GCF×BOAD + intent `mutation` (générer dossier) → skill `skill_dossier_gcf_via_boad` (priorité dossier > scoring > diagnostic).
3. Aucune skill ne matche → mode "system prompt global" sans skill.

### US3 — Fusion prompt système + skill prompt (P1)
**En tant que** dev,
**je veux** un module `skill_fusion.py` qui combine :
- system prompt global (invariants F14 : sourçage, multi-tenant, langue FR, ton…),
- prompt expert de la skill,
- sources pré-résolues injectées en bloc citations prêtes,
- contexte de page + entités,
- tools sélectionnés (filtrés par `skill.tool_whitelist`).

**afin de** envoyer au LLM un prompt cohérent et focalisé.

### US4 — Injection des sources pré-résolues (P1)
**En tant que** dev,
**je veux** que les Sources liées à une skill soient **pré-résolues** dans le contexte (titre + extrait + URL + ID),
**afin de** réduire les hallucinations et accélérer le sourçage : le LLM cite directement par ID au lieu de chercher.

### US5 — Intersection avec tool_whitelist (P1)
**En tant que** dev,
**je veux** que quand une skill est active, le sélecteur de tools (F14 US2) limite son choix à `tools_disponibles ∩ skill.tool_whitelist`,
**afin que** la skill réduit l'espace, ne l'élargit pas.

### US6 — 1 à 2 skills max par tour, priorité (P1)
**En tant que** dev,
**je veux** une règle de priorité claire si plusieurs skills sont candidates :
- skill dossier > skill scoring > skill diagnostic > skill générale,
- en cas d'égalité, prendre celle dont les sources sont les plus à jour.

**afin de** éviter la dilution.

### US7 — Une skill draft n'est jamais servie au LLM (P1)
**En tant que** garant de la qualité,
**je veux** que seules les skills `status='published'` ET dont **toutes** les sources liées sont `verified` soient chargeables,
**afin de** garantir la rigueur (cohérent F03 + F06).

### US8 — Versioning et snapshot (P2)
**En tant que** dev,
**je veux** que les conversations en cours conservent la **version active** de la skill au tour où elles ont été démarrées (snapshot de la version `id`),
**afin que** une mise à jour d'une skill ne casse pas un dossier en cours.

## Exigences fonctionnelles

- **FR-001** : Table `skill` (US1) avec contraintes : `name UNIQUE`, `version INT NOT NULL`, FK vers `source` via table de liaison `skill_source` (n-n).
- **FR-002** : Module `skill_loader.py` :
  - `load_active_skills(context: dict) -> list[Skill]` (1 ou 2 max),
  - logique : matche `activation_rules` contre `context`, filtre par `status='published'` + sources `verified`.
- **FR-003** : `activation_rules` JSON schéma strict :
  ```json
  {
    "any_of": [
      {"page": "/profil/projets/*", "intent": ["analyse","mutation"]},
      {"entity_type": "candidature", "offre_id_match": {"fonds_code": "GCF", "intermediaire_code": "BOAD"}}
    ]
  }
  ```
  Validateur Pydantic dédié.
- **FR-004** : Module `skill_fusion.py` :
  - `build_prompt(global_invariants, skill, sources_resolved, context, tools) -> str`,
  - sections claires en markdown : `## Invariants`, `## Skill: <name>`, `## Sources de référence`, `## Procédure`, `## Tools disponibles`, `## Contexte`.
- **FR-005** : Helper `resolve_sources(source_ids: list[int]) -> list[ResolvedSource]` qui charge titre, publisher, extrait court (200 caractères) pour chaque source `verified`.
- **FR-006** : Intégration au pipeline F14 :
  - après classifier, avant sélecteur de tools, on charge les skills,
  - le sélecteur intersecte avec `skill.tool_whitelist`,
  - le system prompt est construit via `skill_fusion.build_prompt`.
- **FR-007** : Helper `snapshot_skill_version(thread_id, skill_id, version)` pour figer la version utilisée dans le thread.
- **FR-008** : Limite tokens du `prompt_expert` configurable (`SKILL_PROMPT_MAX_TOKENS=1500`). Au save (F20), le validator rejette si > limite.
- **FR-009** : Endpoint admin `GET /admin/skills/{id}` (sera détaillé en F20) — pour MVP F19, exposer un endpoint interne `/internal/skill-loader/test?context=...` pour tests.

## Exigences non-fonctionnelles

- **NFR-001** : Latence du loader (DB query + fusion) < 100ms p95.
- **NFR-002** : Le cache des skills publishées peut être invalidé par version (post-MVP : warm cache + invalidation par event).
- **NFR-003** : Une skill avec 5 sources pré-résolues ne doit pas faire dépasser le budget tokens contexte (`CONTEXT_TOKEN_BUDGET` cohérent F18).

## Entités clés

- **Skill** (FR-001).
- **SkillSource** (table de liaison n-n).
- (Pas d'entité utilisateur supplémentaire — `golden_examples` JSONB inline.)

## Success Criteria

- **SC-001** : Une skill `skill_esg_diagnostic` seedée → loader la charge sur la bonne page + intent (test).
- **SC-002** : 2 skills candidates → la priorité est respectée (test).
- **SC-003** : Une skill `draft` ou avec source `pending` n'est jamais chargée (test).
- **SC-004** : Le system prompt fusionné reste sous la limite tokens (test).
- **SC-005** : Une mutation de skill ne casse pas une conversation en cours (snapshot version).

## Hors-scope MVP

- CRUD admin → **F20**.
- Skills seedées MVP → **F21**.
- Marketplace de skills externes → backlog post-MVP.
- Composition récursive (skills avec sous-skills) — explicitement écarté en MVP.
- A/B testing automatique de versions de skills.
- Génération assistée de skill par LLM (drafting).

## Risques et points de vigilance

- **Sélection trop agressive** : si le loader n'active jamais de skill, le LLM perd le contexte expert. À l'inverse, activer une skill non pertinente fait dériver. F35 (eval) mesurera.
- **Tool whitelist incohérent** : si une skill liste un tool qui n'existe pas dans le code, alarme au save (validation FR-008). Cohérent avec F20.
- **Prompt fusion explose en tokens** : monitoring continu via le logger LLM (F10). Compaction intelligente si > limite.
- **Cohérence sources skill ↔ sources F03** : ce sont les mêmes objets. Les sources d'une skill **doivent** être référencées par les indicateurs/critères/référentiels qu'elle exploite. Au save F20, on peut warner si incohérence.
