# F21 — Seed des Skills MVP (esg_diagnostic, score_gcf, dossier_gcf_via_boad + 5–6 additionnelles)

**Phase** : 4 — Skills (Playbooks Métier)
**Modules brainstorm** : 11.2 (Catalogue MVP — ~10 skills), 11.7 (Ordre de priorité)
**Dépendances** : F08, F09, F19, F20
**Estimation** : 2.5 jours (50/50 contenu métier + intégration technique)

## Contexte et objectif

Livrer **les 3 skills critiques** du brainstorming Module 11.7 :

1. `skill_esg_diagnostic` — diagnostic ESG général (Module 2)
2. `skill_score_gcf` — scoring GCF (8 critères)
3. `skill_dossier_gcf_via_boad` — génération dossier GCF×BOAD (Module 3.3)

**Plus 5-6 skills additionnelles** (Module 11.2) progressivement après MVP minimum. Cette feature livre :
- 3 skills seedées en BDD (via migration ou script `seed_skills.py`),
- 3 templates de structure pour les autres skills,
- la suite de tests d'eval associés (golden examples × 5 par skill),
- vérification que F19 + F20 + F14 fonctionnent end-to-end avec ces skills réelles.

## User Stories

### US1 — skill_esg_diagnostic seedée et fonctionnelle (P1)
**En tant qu'**équipe ESG Mefali,
**je veux** une skill activable qui fait un diagnostic ESG général d'une PME,
**afin de** alimenter le scoring multi-référentiels (F23) avec une procédure rigoureuse :
- Étape 1 : extraire de la conversation et des documents les éléments E/S/G clés.
- Étape 2 : faire une grille E/S/G (Module 2.2).
- Étape 3 : pour chaque indicateur manquant, poser une question via `ask_qcu/qcm/number/rating` (F15).
- Étape 4 : produire un résumé via `show_summary_card` (F15) + radar `show_radar_chart` (F16) + recommandation prioritaire.

**Activation** : page diagnostic ESG OU intent "évaluer ESG" OU page Profil avec scoring inactif.
**Tools whitelist** : `ask_qcu`, `ask_qcm`, `ask_number`, `ask_rating`, `ask_file_upload`, `show_summary_card`, `show_radar_chart`, `show_kpi_card`, `cite_source`, `search_source`, `recall_history`, `update_company_profile`, `update_project`.
**Sources** : référentiel ESG Mefali (F09), ADEME, IPCC pour facteurs (F09), GRI pour terminologie.

### US2 — skill_score_gcf seedée et fonctionnelle (P1)
**En tant qu'**équipe,
**je veux** une skill spécialisée GCF qui :
- connaît les **8 critères d'investissement GCF** (impact potentiel, paradigm shift potential, sustainable development, recipient country needs, country ownership, efficiency and effectiveness, etc.),
- pour chaque critère, mobilise les indicateurs sourcés correspondants (F09),
- calcule un score par critère + score global,
- pose des questions ciblées si données manquantes,
- explique chaque chiffre avec source GCF officielle.

**Activation** : Offre ciblée = GCF (n'importe quel intermédiaire).
**Tools whitelist** : `ask_*`, `show_radar_chart`, `show_progress_bar`, `show_kpi_card`, `show_match_card`, `cite_source`, `search_source`, `recompute_score`.
**Sources** : politique GCF Investment Framework + Initial Investment Criteria (sourcées en F07).

### US3 — skill_dossier_gcf_via_boad seedée et fonctionnelle (P1)
**En tant qu'**équipe,
**je veux** la skill **la plus critique** : génération de dossier pour l'Offre GCF via BOAD :
- connaît le **format imposé** par BOAD pour les dossiers GCF (sections obligatoires, longueurs cibles, vocabulaire),
- connaît la **politique sectorielle BOAD** (sauvegardes ESS, exclusions, secteurs prioritaires),
- adapte le ton (institutionnel, jargon banque de développement),
- langue par défaut FR ; bascule EN sur demande (cohérent `accepted_languages` de l'Offre F08),
- évite explicitement les anti-patterns ("ne jamais promettre un impact non quantifié").

**Activation** : Candidature ciblée à Offre `fonds=GCF, intermediaire=BOAD`.
**Tools whitelist** : `ask_*`, `show_summary_card`, `show_comparison_table`, `cite_source`, `generate_dossier`, `recompute_score`.
**Sources** : BOAD politique sectorielle, BOAD safeguards ESS, GCF country programme Côte d'Ivoire (sourcées F07).

### US4 — 5–6 skills additionnelles ébauchées (P2)
**En tant qu'**équipe,
**je veux** 6 templates de skills avec leur shell (name, domain, activation_rules, tool_whitelist, prompts à compléter par les experts métier post-MVP) :
- `skill_score_boad`,
- `skill_score_ifc`,
- `skill_carbon_calc` (Module 4),
- `skill_dossier_sunref_ecobank`,
- `skill_dossier_fem_via_pnud`,
- `skill_intermediaire_boad` (navigation/dialogue autour BOAD),
- `skill_attestation` (Module 5.3),
- `skill_credit_score` (Module 5.2).

Soit **8 skills additionnelles** au total (cohérent Module 11.2 catalogue MVP). MVP : les 3 critiques sont **fonctionnelles** ; les 5-8 autres sont **en draft** avec structure prête.

### US5 — Golden examples × 5 par skill critique (P1)
**En tant que** dev eval,
**je veux** 5 golden examples par skill critique stockés dans `golden_examples` (F19/F20),
**afin de** que l'eval gating fonctionne dès la première publication.

**Format** :
```json
{
  "input_message": "Je suis une PME agro 80 employés, je veux candidater au GCF",
  "page_context": "/profil/projets/X",
  "intent": "analyse",
  "expected_tool": "show_radar_chart",
  "expected_payload_partial": {"axes": ["Impact","Paradigm","SDG","Country needs"]}
}
```

### US6 — Procédure documentée par skill (P2)
**En tant qu'**admin,
**je veux** que chaque skill ait une `procedure` markdown lisible (étapes 1-N, critères d'entrée/sortie, points de vigilance),
**afin de** pouvoir auditer ce que la skill fait sans lire le prompt complet.

## Exigences fonctionnelles

- **FR-001** : Script de seed `backend/scripts/seed_skills.py` qui :
  - vérifie que les sources requises sont présentes et `verified` (sinon arrête),
  - vérifie que les tools référencés existent dans le registry (F14),
  - insère les 3 skills critiques en `published` (sources verified) ou `draft` (sources pending),
  - insère les 5-8 skills shells en `draft`,
  - insère les golden examples associés,
  - idempotent : relancer le script ne duplique pas.
- **FR-002** : Script de seed exécutable via `python -m backend.scripts.seed_skills` une fois la stack montée (après F09 catalogue référentiels et F07 sources).
- **FR-003** : Documentation interne `docs/skills/<name>.md` pour chaque skill critique, expliquant son périmètre, ses sources, sa procédure (cohérence brainstorming Module 11.6).
- **FR-004** : Tests E2E par skill : pour chacune des 3 skills critiques, un test d'intégration `tests/test_skill_<name>.py` qui :
  - charge la skill via F19 loader,
  - simule un message utilisateur typique,
  - vérifie le tool invoqué + payload validé.
- **FR-005** : Le contenu de `prompt_expert` de chaque skill critique est revu et validé par l'équipe métier ESG Mefali (humain-in-the-loop) avant insertion.
- **FR-006** : Les sources requises pour chaque skill (~10–20 sources ESG/finance verte/référentiels) sont **listées et seedées en F07** (cohérent dépendance).
- **FR-007** : L'eval gating (F20 US6) est exécuté sur les 3 skills avant `published`. Les métriques cibles : `tool_match_rate ≥ 0.8`, `payload_valid_rate ≥ 0.9`.

## Exigences non-fonctionnelles

- **NFR-001** : Le seed se termine en < 30 secondes.
- **NFR-002** : Les 3 skills critiques fonctionnent end-to-end avec un LLM réel (minimax-m2.7) sur 80%+ des golden examples.
- **NFR-003** : Le contenu métier est rédigé en français — c'est la langue par défaut de la plateforme.

## Entités clés

- Réutilise `skill`, `skill_source` (F19/F20).

## Success Criteria

- **SC-001** : 3 skills critiques `published` après seed.
- **SC-002** : Test d'intégration : message utilisateur typique sur page `/profil/projets/X` (avec offre GCF×BOAD ciblée) → la skill `skill_dossier_gcf_via_boad` est activée par le loader F19.
- **SC-003** : Eval initial : `tool_match_rate ≥ 0.8` sur les 5 golden examples de chaque skill critique.
- **SC-004** : Le `prompt_expert` de chaque skill critique tient sous le budget tokens (`SKILL_PROMPT_MAX_TOKENS=1500`).

## Hors-scope MVP

- Skills marketplace.
- Skill drafting assisté par LLM.
- Skills avec sous-skills.
- Skills par sous-secteur (agriculture vs énergie vs transport — possible post-MVP).
- 100% des skills additionnelles publiées (MVP = 3 critiques + 5-8 shells).

## Risques et points de vigilance

- **Qualité du contenu** : un mauvais `prompt_expert` casse l'expérience même si le moteur est bon. Investir le temps métier nécessaire — ce n'est pas un travail de dev seul.
- **Dépendance aux sources F07** : le seed des skills critiques est bloquant tant que les sources ne sont pas saisies. Coordonner avec l'équipe métier qui peuple F07.
- **Drift de version** : si un référentiel évolue (ex : GCF passe de v3 à v4), la skill peut devenir obsolète. Workflow F20 : alerte admin "sources liées ont changé" → re-test eval → re-publish.
- **Charge cognitive admin** : 11+ skills à maintenir, chacune avec sources, prompts, golden examples. Prévoir documentation interne et formation.
- **Test avec LLM réel** : les golden examples doivent être réalistes (pas des cas d'école). Récolter auprès de PME pilotes.
