# F23 — Scoring ESG Multi-Référentiels (Mefali + UEMOA/GCF/IFC/GRI/ODD + Intermédiaires)

**Phase** : 5 — Conformité ESG (Module 2)
**Modules brainstorm** : 2.2 (Grille E/S/G), 2.3 (Scoring multi-référentiels)
**Dépendances** : F09, F21, F22
**Estimation** : 3 jours

## Contexte et objectif

> **Principe (du brainstorming)** : un score ESG n'a de sens que par rapport à un référentiel. Hybride : un score synthétique "ESG Mefali" en vitrine pour la lisibilité + scores détaillés par référentiel (fonds source ET intermédiaires), calculés depuis le **même catalogue d'indicateurs** (Module 0.7 mapping).

Cette feature est l'un des **points différenciants majeurs** de la plateforme :
- une seule réponse PME alimente plusieurs scores,
- chaque score est sourcé bout-en-bout (cliquable vers source officielle),
- l'activation contextuelle calcule **deux scores quand un projet cible une Offre** (fonds + intermédiaire) — le `min` des deux étant l'éligibilité réelle,
- benchmarking sectoriel + évolution dans le temps + explicabilité.

## User Stories

### US1 — Score ESG Mefali (vitrine principale) (P1)
**En tant que** PME,
**je veux** voir un score global sur 100 + scores E/S/G par pilier sur ma page dashboard / profil,
**afin de** avoir une vue synthétique compréhensible.

**Test indépendant** : entreprise + projet renseignés → calcul du score Mefali via le référentiel "ESG Mefali" (F09) → affichage `show_kpi_card` (F16) global + `show_radar_chart` E/S/G.

### US2 — Scores par référentiel externe (P1)
**En tant que** PME,
**je veux** voir en parallèle des scores selon : taxonomie UEMOA, GCF (8 critères), IFC PS (8 standards), GRI, ODD ONU, et les référentiels intermédiaires (BOAD, BAD, SUNREF, etc.),
**afin de** comprendre où je suis éligible et où non.

**Liste évolutive** : nouveaux référentiels ajoutables sans code (configuration F09 + sources F07).

### US3 — Activation contextuelle des deux scores (fonds + intermédiaire) (P1)
**En tant que** PME ciblant une Offre (ex : GCF via BOAD),
**je veux** voir **deux scores côte-à-côte** :
- score selon référentiel **fonds** (GCF),
- score selon référentiel **intermédiaire** (politique BOAD),

avec identification du **goulot d'étranglement** (lequel est le plus bas).

**afin de** savoir où concentrer mes efforts.

**Mécanisme** : c'est le `min` des deux qui détermine l'éligibilité réelle.

### US4 — Détail du score : indicateurs couverts/manquants + sources (P1)
**En tant que** PME,
**je veux** cliquer sur un score pour voir :
- les **indicateurs couverts** (avec valeur PME, poids, contribution au score, source de l'indicateur),
- les **indicateurs manquants** (à renseigner pour améliorer le score, et lien vers l'écran approprié),
- l'**écart au seuil d'éligibilité** (si applicable),

avec **chaque chiffre cliquable vers sa source officielle** (cohérent F03).

### US5 — Benchmarking sectoriel (P2)
**En tant que** PME,
**je veux** voir comment je me situe par rapport à d'autres PME du même secteur (anonymisées) pour chaque référentiel,
**afin de** me situer.

**Mécanisme MVP** : moyennes sectorielles calculées sur l'ensemble des PME du compte (anonymisées). Pas de benchmark public en MVP.

### US6 — Évolution dans le temps (P2)
**En tant que** PME,
**je veux** un `show_line_chart` (F16) avec mon score par référentiel sélectionné sur les 12 derniers mois,
**afin de** suivre ma progression.

**Mécanisme** : chaque calcul de score est persisté avec timestamp + version référentiel utilisé (cohérent F04 versioning).

### US7 — Recalcul à la demande + à la modification de données (P1)
**En tant que** PME,
**je veux** que le score soit recalculé :
- à chaque modification du profil entreprise / projet (debounced 5s),
- sur demande explicite via le tool `recompute_score` (F17),
- au changement de version de référentiel.

**afin de** voir l'impact de mes changements.

### US8 — Score Mefali = projection pédagogique des indicateurs (P1)
**En tant que** dev,
**je veux** que la grille E/S/G du Module 2.2 soit **une projection** pédagogique du catalogue d'indicateurs principaux par pilier — pas une donnée séparée,
**afin de** respecter le mapping unique (Module 0.7).

## Exigences fonctionnelles

- **FR-001** : Service backend `ScoringService` :
  - `compute_score(entity_id, referentiel_code, version?, at?) -> ScoreResult`,
  - parcourt les indicateurs liés au référentiel,
  - pour chaque indicateur, lit la valeur depuis `entreprise` / `projet` / réponses LLM (selon mapping),
  - applique la formule du référentiel (`weighted_sum` MVP, `custom` post-MVP),
  - retourne `{score_global, scores_by_pillar?, indicateurs_couverts:[{id,value,weight,contribution,source_id}], indicateurs_manquants:[{id,reason}], seuil_eligibilite, ecart, sources_used:[]}`.
- **FR-002** : Table `score_calculation` : `id, account_id, entity_type, entity_id, referentiel_id, referentiel_version, score_global, scores_by_pillar JSONB, details_json JSONB, computed_at, snapshot_id NULL`. Index `(entity_id, referentiel_id, computed_at DESC)`.
- **FR-003** : Endpoints REST :
  - `GET /me/scoring/{entity_type}/{entity_id}` → tous les scores actifs pour cette entité,
  - `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}` → détail d'un score,
  - `POST /me/scoring/{entity_type}/{entity_id}/recompute?referentiel=` → force recalcul.
- **FR-004** : Endpoint `GET /me/scoring/offre/{offre_id}` → calcule **deux scores** (fonds + intermédiaire) pour le projet ciblé, retourne `{fonds_score, intermediaire_score, min, bottleneck:'fonds'|'intermediaire'}`.
- **FR-005** : Page Vue `/profil/scoring` listant tous les référentiels avec score, statut (éligible / proche / loin du seuil), badge versioning (F04 US7).
- **FR-006** : Page détail `/profil/scoring/[referentiel_code]` :
  - Score global + radar par pilier,
  - Tableau indicateurs (couverts / manquants),
  - Bouton "Recalculer",
  - Annexe sources cliquable (F03).
- **FR-007** : Recalcul auto au save profil/projet : déclenché par hook (F11/F12) avec debounce 5s + queue.
- **FR-008** : Endpoint `GET /me/scoring/{ref}/benchmark` → retourne `{my_score, sector_avg, sector_p25, sector_p75, sector_count}` (avec anonymisation et `sector_count >= 5` minimum sinon retourne null).
- **FR-009** : Endpoint `GET /me/scoring/{entity}/{ref}/history?from=&to=` → série temporelle pour `show_line_chart`.
- **FR-010** : La grille E/S/G de l'UI est **calculée dynamiquement** depuis les indicateurs du référentiel ESG Mefali groupés par `pillar` (cohérent F09 indicateur.pillar). Pas de table dédiée.

## Exigences non-fonctionnelles

- **NFR-001** : Calcul d'un score < 200ms p95 pour un référentiel à 30 indicateurs.
- **NFR-002** : 100% des chiffres affichés dans la page scoring ont une source cliquable (audité par tests).
- **NFR-003** : Le calcul est **déterministe** : mêmes inputs → même score (testable, snapshot-friendly cohérent F04).
- **NFR-004** : RLS strict (F02) : impossible de calculer un score sur une entité d'un autre compte.

## Entités clés

- **ScoreCalculation** (FR-002).
- Réutilise **Referentiel**, **Indicateur**, **Critere** (F09).
- Réutilise **Entreprise**, **Projet** (F11/F12) comme sources de valeurs.

## Success Criteria

- **SC-001** : Score Mefali calculé pour une PME complète sur 30 indicateurs en < 200ms.
- **SC-002** : 5 référentiels externes calculés en parallèle (UEMOA, GCF, IFC, BOAD, GRI).
- **SC-003** : Activation contextuelle : Offre GCF×BOAD → 2 scores affichés avec bottleneck identifié.
- **SC-004** : 100% des indicateurs/scores ont leur source cliquable.
- **SC-005** : Recalcul automatique 5s après modification profil → UI mise à jour.

## Hors-scope MVP

- Formules de référentiel `custom` (eval JSON safe) — MVP : `weighted_sum` uniquement.
- Benchmarking public (cross-PME hors compte, anonymisé).
- A/B testing de versions de référentiel.
- Score prédictif ("si tu fais X, ton score passera de A à B"). Le plan d'action F31 le couvre partiellement.
- Score temps réel pendant la saisie (debounce suffit).

## Risques et points de vigilance

- **Mapping Indicateur ↔ Champ entreprise/projet** : c'est l'endroit le plus critique. Chaque indicateur doit avoir une "source de valeur" déclarée (champ `entreprise.taille_effectifs`, ou réponse LLM stockée, ou calcul dérivé). Définir un schéma de mapping clair en F09 (peut-être un champ `indicateur.value_source_path` JSON).
- **Indicateurs manquants** : la majorité des PME n'auront pas toutes les valeurs au début. Le score doit être calculable avec coverage partielle (typiquement, ne compter que les indicateurs renseignés et normaliser, ou afficher "score provisoire avec X indicateurs sur Y").
- **Cohérence entre score Mefali et scores externes** : éviter les doublons d'indicateurs entre référentiels. Le mapping unique (F09) garantit déjà cela.
- **Performance** : 20 référentiels × 30 indicateurs × 1 PME = 600 lookups. Cache simple par PME + invalidation au save.
- **Dépendance forte aux données catalogue F07/F09** : sans 5+ référentiels seedés et 100+ indicateurs, F23 reste théorique. Coordonner avec l'équipe métier.
