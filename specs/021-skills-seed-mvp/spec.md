# Feature Specification: Seed des Skills MVP (F21)

**Feature Branch**: `021-skills-seed-mvp`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F21 — Seed des Skills MVP. Livrer 3 skills critiques (skill_esg_diagnostic, skill_score_gcf, skill_dossier_gcf_via_boad) en published + 5-8 shells skills additionnelles en draft + golden_examples (5 par skill critique) + script seed idempotent backend/scripts/seed_skills.py qui réutilise SkillRepository F20.

## Clarifications

### Session 2026-04-29

- Q: Format de stockage des fixtures de skills (YAML vs JSON) ? → A: YAML (lisible métier, commentaires, multi-ligne).
- Q: Comportement si une source requise n'existe pas en BDD ? → A: skill basculée en `draft` + warning log, ne bloque pas le run (non-blocking).
- Q: Stratégie de versioning lors d'un update idempotent ? → A: bump `version` uniquement si `content_hash(prompt_expert + activation_rules + tool_whitelist)` change.
- Q: Vérification de la tool whitelist — runtime ou liste statique ? → A: registry runtime F14 (import direct), source de vérité unique.
- Q: Comportement si un tool de la whitelist est introuvable ? → A: skip la skill avec erreur loguée + exit code non-zéro à la fin si ≥ 1 skill skippée.

## User Scenarios & Testing

### User Story 1 — Seed des 3 skills critiques (Priority: P1)

L'équipe ESG Mefali exécute le script de seed pour insérer en base les 3 skills critiques (`skill_esg_diagnostic`, `skill_score_gcf`, `skill_dossier_gcf_via_boad`) avec leur prompt expert, leurs règles d'activation, leur tool whitelist et leurs sources liées. Si toutes les sources sont `verified`, les skills passent en `published`; sinon elles restent en `draft` avec un message clair.

**Why this priority**: sans ces 3 skills le moteur F19 n'a rien à activer en production — c'est le livrable qui rend la chaîne F19+F20 utile pour les pilotes.

**Independent Test**: lancer le script sur une base avec sources verifiées → vérifier via SkillRepository que les 3 skills existent en `published` avec le tool whitelist attendu et les sources liées; relancer le script → aucun doublon.

**Acceptance Scenarios**:

1. **Given** une base avec les sources requises seedées en F07 et toutes `verified`, **When** l'admin lance le script de seed, **Then** les 3 skills critiques apparaissent en statut `published`, chacune avec ≥ 2 sources liées et une tool whitelist non vide.
2. **Given** une base où 1 source d'une skill est encore `pending`, **When** l'admin lance le script, **Then** la skill concernée est insérée en `draft` avec un message indiquant la source manquante; les autres skills critiques peuvent être `published`.
3. **Given** une base où les 3 skills critiques existent déjà, **When** l'admin relance le script, **Then** aucune duplication n'est créée et les champs sont mis à jour idempotemment (upsert by `name`).

---

### User Story 2 — Golden examples seedés pour eval gating (Priority: P1)

Pour chaque skill critique, 5 golden examples (input_message, page_context, intent, expected_tool, expected_payload_partial) sont insérés en base, permettant à F20 d'exécuter l'eval avant publication.

**Why this priority**: sans golden examples l'eval gating F20 ne peut pas s'exécuter, donc la skill ne peut pas être publiée correctement.

**Independent Test**: après seed, lister les golden_examples par skill_id → vérifier exactement 5 par skill critique avec `expected_tool` valide.

**Acceptance Scenarios**:

1. **Given** les 3 skills critiques seedées, **When** on requête les golden examples, **Then** chaque skill a 5 exemples avec un `expected_tool` listé dans la whitelist de la skill.
2. **Given** le seed déjà exécuté, **When** on relance le script, **Then** les golden examples ne sont pas dupliqués.

---

### User Story 3 — Shells de skills additionnelles en draft (Priority: P2)

Le script insère 6 à 8 skills shells (`skill_score_boad`, `skill_score_ifc`, `skill_carbon_calc`, `skill_dossier_sunref_ecobank`, `skill_dossier_fem_via_pnud`, `skill_intermediaire_boad`, `skill_attestation`, `skill_credit_score`) en `draft` avec structure prête (nom, domaine, règles d'activation, tool whitelist, prompt expert placeholder à compléter).

**Why this priority**: ces shells permettent au back-office F20 de présenter à l'admin la liste des skills à compléter, donnant une roadmap visible sans bloquer le MVP critique.

**Independent Test**: après seed, lister les skills via SkillRepository → vérifier qu'au moins 6 skills additionnelles sont en `draft` avec un nom unique.

**Acceptance Scenarios**:

1. **Given** une base vierge, **When** le script s'exécute, **Then** ≥ 6 skills shells sont en `draft` avec un placeholder dans `prompt_expert`.
2. **Given** le seed déjà exécuté, **When** on relance le script, **Then** les shells ne sont pas dupliqués; un passage manuel d'une shell en `published` n'est pas écrasé (le script ne rétrograde jamais une skill `published` vers `draft`).

---

### User Story 4 — Procédure d'audit documentée par skill critique (Priority: P3)

Chaque skill critique dispose d'une procédure markdown lisible (étapes, critères d'entrée/sortie, points de vigilance) accessible via le champ `procedure`.

**Why this priority**: utile pour audits internes et formation admin, mais non bloquant pour le MVP fonctionnel.

**Independent Test**: pour chaque skill critique, vérifier la présence d'une description procédurale lisible (≥ 200 caractères, étapes numérotées).

**Acceptance Scenarios**:

1. **Given** une skill critique seedée, **When** un admin consulte sa fiche, **Then** il voit une procédure expliquant les étapes du raisonnement de la skill.

---

### Edge Cases

- Sources requises absentes en base : le script remonte la liste des sources manquantes et bascule la skill concernée en `draft` plutôt que `published`.
- Tool référencé absent du registry F14 : le script avorte la skill concernée avec message d'erreur explicite et continue les autres.
- Skill du même nom déjà `published` éditée manuellement : le script ne réécrit pas le `prompt_expert` modifié manuellement (option `--force` requise pour overrider).
- Re-exécution partielle après crash : le script peut reprendre sans corrompre l'état (transactionnel par skill).
- Échec d'insertion d'un golden example : la skill reste insérée mais le seed remonte un warning et un code de sortie non-zéro.

## Requirements

### Functional Requirements

- **FR-001**: Le système DOIT fournir un script Python `backend/scripts/seed_skills.py` exécutable via `python -m backend.scripts.seed_skills` qui peuple les skills MVP.
- **FR-002**: Le script DOIT être idempotent : ré-exécution ne crée pas de doublons (clef d'unicité = `skill.name`).
- **FR-003**: Le script DOIT insérer 3 skills critiques (`skill_esg_diagnostic`, `skill_score_gcf`, `skill_dossier_gcf_via_boad`) avec prompt_expert, activation_rules, tool_whitelist, sources liées, procedure.
- **FR-004**: Le script DOIT vérifier avant insertion que chaque source référencée existe et est `verified`; si toutes verified → `published`, sinon → `draft`.
- **FR-005**: Le script DOIT vérifier (via import runtime du tool registry F14) que tous les tools listés dans la whitelist sont enregistrés; si un tool est introuvable, la skill concernée est SKIPPÉE (non insérée), une erreur est loguée, et le script termine avec un exit code non-zéro.
- **FR-006**: Le script DOIT insérer ≥ 6 skills shells additionnelles en `draft` avec structure minimale (name, domain, activation_rules, tool_whitelist, prompt_expert placeholder).
- **FR-007**: Le script DOIT insérer 5 golden examples par skill critique (15 au total) avec `input_message`, `page_context`, `intent`, `expected_tool`, `expected_payload_partial`.
- **FR-008**: Le script DOIT s'exécuter en moins de 30 secondes sur la base de dev locale.
- **FR-009**: Le script NE DOIT JAMAIS rétrograder une skill `published` vers `draft` lors d'une ré-exécution; modification d'un champ `prompt_expert` modifié manuellement nécessite l'option explicite `--force`.
- **FR-010**: Le script DOIT logger un résumé final : nombre de skills créées, mises à jour, skippées, en draft, en published, golden examples créés.
- **FR-011**: Le contenu seedé DOIT être en français (langue par défaut de la plateforme).
- **FR-012**: Les fixtures (contenu des skills + golden examples) DOIVENT être stockées au **format YAML** sous `backend/scripts/seeds/skills/` pour faciliter la revue métier sans relire le code Python (commentaires + blocs multi-ligne supportés).
- **FR-013**: Lors d'une ré-exécution, le script DOIT bumper le champ `version` d'une skill UNIQUEMENT si le hash de contenu (`content_hash` calculé sur `prompt_expert` + `activation_rules` + `tool_whitelist`) a changé; sinon `version` est préservée.
- **FR-014**: Si une source requise par une skill n'existe pas en BDD ou n'est pas `verified`, le script DOIT basculer la skill concernée en `draft` (au lieu de `published`), logger un warning listant les sources manquantes, et continuer le run sans échec global.

### Key Entities

- **Skill** (réutilise F19/F20) : `name` (unique), `domain`, `version`, `status` (draft|published), `activation_rules`, `tool_whitelist`, `prompt_expert`, `procedure`, `language_default`.
- **SkillSource** (réutilise F19/F20) : lien skill ↔ source.
- **GoldenExample** (réutilise F19/F20) : `skill_id`, `input_message`, `page_context`, `intent`, `expected_tool`, `expected_payload_partial`.
- **Source** (réutilise F07) : pré-existant, requis `verified` pour passage `published`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Après exécution du script sur une base de dev avec sources verifiées, les 3 skills critiques sont en statut `published` avec ≥ 2 sources liées chacune.
- **SC-002**: Le script s'exécute en moins de 30 secondes (mesuré sur poste dev).
- **SC-003**: Re-exécution du script sur une base déjà seedée ne crée aucun doublon (count stable ±0).
- **SC-004**: 100% des golden examples seedés ont un `expected_tool` présent dans la `tool_whitelist` de leur skill associée.
- **SC-005**: Pour chaque skill critique, l'eval gating F20 peut s'exécuter sur les 5 golden examples sans erreur structurelle.
- **SC-006**: Le `prompt_expert` de chaque skill critique tient sous le budget tokens (≤ 1500 tokens).
- **SC-007**: Couverture de tests ≥ 80 % sur le code F21 ajouté (script de seed et helpers).

## Assumptions

- Les sources requises (politique GCF, BOAD safeguards, référentiel ESG Mefali, ADEME, IPCC, GRI) sont seedées par F07 ou disponibles via fixtures dédiées dans le projet pour le dev local; à défaut, les skills concernées restent en `draft` avec message clair.
- Les tools référencés (`ask_*`, `show_*`, `cite_source`, `recompute_score`, `generate_dossier`, `update_*`) sont enregistrés dans le registry F14/F15/F16/F17.
- Le contenu métier des `prompt_expert` est rédigé par l'équipe ESG Mefali et stocké en YAML versionné; le script se contente de l'insérer en BDD.
- L'environnement d'exécution dispose de la variable `DATABASE_URL` et accès aux migrations F19/F20 appliquées.
- L'eval gating réel avec LLM live (`tool_match_rate ≥ 0.8`) est exécuté manuellement post-seed (validé hors script CI), conformément au scope MVP.
