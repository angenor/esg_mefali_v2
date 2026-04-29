# F29 — Collecte Données & Algorithme de Scoring Crédit Vert

**Phase** : 8 — Scoring Crédit Vert (Module 5)
**Modules brainstorm** : 5.1 (Collecte de Données Non-Conventionnelles), 5.2 (Algorithme de Scoring Hybride)
**Dépendances** : F05 (consentements), F11, F12, F21
**Estimation** : 2.5 jours

## Contexte et objectif

L'**inclusion financière** est un cœur de l'ambition du projet : permettre aux PME africaines d'accéder au crédit même sans historique bancaire formel, via des données non-conventionnelles (Mobile Money, déclaratif enrichi, photos, données publiques).

Cette feature livre :
- **Collecte** des données non-conventionnelles avec consentements granulaires (cohérent F05),
- **Algorithme de scoring hybride** avec 3 scores : solvabilité, impact vert, score combiné,
- **Méthodologie publiée et sourcée** (cohérent F03) — la PME et tout tiers peut consulter la formule, les pondérations et leur justification,
- **Explication transparente** : chaque facteur est cliquable → contribution au score + source.

> **Important** : Tous les usages nécessitent un consentement explicite (F05).

## User Stories

### US1 — Intégration Mobile Money (P1)
**En tant que** PME (avec consentement explicite),
**je veux** importer mes flux Mobile Money (Wave, Orange Money, MTN, Free Money, etc.) — au moins via export CSV ou statement uploadé en MVP — pour analyse,
**afin de** prouver la régularité et le volume de mes transactions.

**Test indépendant** : upload statement Wave/Orange Money → parsing → indicateurs extraits (volume mensuel moyen, écart-type, nombre de transactions, ratio entrées/sorties).

**MVP simple** : pas d'API live. Upload de statement + parsing + acceptation utilisateur.

### US2 — Données déclaratives enrichies (P1)
**En tant que** PME,
**je veux** que le LLM me pose via `ask_*` (F15) des questions structurées sur mes pratiques :
- Régularité des paiements fournisseurs/employés,
- Saisonnalité,
- Clients récurrents,
- Diversification.

**afin de** alimenter le scoring sans exiger de comptabilité formelle.

### US3 — Photos d'exploitation (P2)
**En tant que** PME (avec consentement),
**je veux** uploader des photos de mon site, équipement, stocks via `ask_file_upload` (F15),
**afin de** matérialiser mon activité.

**Mécanisme MVP** : upload + stockage F22. Analyse visuelle par LLM multimodal (post-MVP). En MVP : juste preuve d'activité, pas d'analyse fine.

### US4 — Données publiques (P3)
**En tant que** dev,
**je veux** la possibilité de récupérer (avec consentement) :
- présence sur réseaux sociaux (Facebook business, LinkedIn),
- avis Google Business,
- participation à des programmes verts (registres publics).

**afin de** enrichir le scoring.

**MVP** : déclaratif uniquement (la PME indique son URL Facebook, on stocke le lien — pas de scraping en MVP). Post-MVP : scraping consenti.

### US5 — Score de solvabilité (0-100) (P1)
**En tant que** PME,
**je veux** voir mon score de solvabilité calculé selon une méthodologie publiée :
- volume Mobile Money (régularité, croissance),
- diversification clients,
- ancienneté,
- ratio liquidité estimé,
- pratiques de paiement déclarées,

**afin de** savoir où je me situe pour les bailleurs.

### US6 — Score d'impact vert (0-100) (P1)
**En tant que** PME,
**je veux** voir mon score d'impact vert qui combine :
- empreinte carbone (F28),
- score ESG (F23),
- type de projet vert (F12),
- alignement ODD,

**afin de** valoriser ma contribution.

### US7 — Score combiné pondéré (P1)
**En tant que** PME,
**je veux** voir le score combiné = α·solvabilité + β·impact vert (pondérations sourcées et publiées),
**afin de** voir comment être verte = meilleur accès au crédit (cercle vertueux).

### US8 — Explication transparente (P1)
**En tant que** PME,
**je veux** cliquer sur un facteur du score et voir :
- son nom et définition,
- sa valeur calculée pour mon entreprise,
- son poids dans le score,
- sa contribution numérique,
- sa source (méthodologie cliquable cohérent F03).

**afin de** comprendre.

### US9 — Méthodologie publique (P1)
**En tant que** PME ou tiers,
**je veux** une page publique `/methodologie/credit-scoring` qui détaille :
- formule de calcul,
- liste des facteurs,
- sources scientifiques (méthodologies bailleurs : BAD inclusion financière, IFC SME Banking, GIIN IRIS+),
- pondérations,
- mises à jour (versioning F04).

**afin de** auditabilité.

## Exigences fonctionnelles

- **FR-001** : Table `credit_data` : `id, account_id, entreprise_id, kind ENUM('mobile_money','declaratif','photos','publique'), payload_json, consent_id (FK F05), uploaded_at, valid_until NULL`.
- **FR-002** : Service `MobileMoneyParser` : reconnaît formats Wave, Orange Money, MTN, Free Money (CSV/PDF). Statement → liste transactions normalisée. Calcul des indicateurs dérivés (volume, fréquence, etc.).
- **FR-003** : Service `CreditScoringService` :
  - `compute(entreprise_id) -> CreditScoreResult`,
  - `{solvabilite:int(0-100), impact_vert:int(0-100), combine:int(0-100), facteurs:[{name, value, weight, contribution, source_id}], methodologie_version}`,
  - utilise un référentiel "credit_scoring_methodology" stocké en F09 (sourcé) avec ses facteurs et pondérations.
- **FR-004** : Endpoints :
  - `POST /me/credit-data` (upload Mobile Money statement, déclaratif),
  - `GET /me/credit-score` → score actuel + détail facteurs.
  - `POST /me/credit-score/recompute` → force recalcul.
- **FR-005** : Page Vue `/profil/credit-score` : cartes 3 scores + graphes contributions + listing facteurs avec sources.
- **FR-006** : Page Vue publique `/methodologie/credit-scoring` (sans login) — Markdown rendu, versionné.
- **FR-007** : Skill `skill_credit_score` (cohérent F21) qui orchestre la collecte : pose les questions (`ask_*`), demande l'upload Mobile Money, valide les consentements (F05), explique les résultats.
- **FR-008** : Décorateur `@requires_consent(kind)` (F05) appliqué à chaque endpoint et à chaque tool LLM qui touche à ces données.
- **FR-009** : Versioning de la méthodologie (F04) : changer les pondérations crée une v2 ; les scores existants restent calculables contre v1.
- **FR-010** : Recalcul automatique du score à la modification des données sources (entreprise, projets, empreinte carbone, ESG).

## Exigences non-fonctionnelles

- **NFR-001** : Parsing d'un statement Wave de 100 transactions < 1s.
- **NFR-002** : Calcul du score < 200ms.
- **NFR-003** : Tous les facteurs et pondérations sont sourcés (cohérent F03).
- **NFR-004** : Aucune donnée Mobile Money brute n'est exposée hors compte. Dashboard agrégé uniquement.
- **NFR-005** : Conformité F05 stricte : pas de calcul sans consentement explicite.

## Entités clés

- **CreditData** (FR-001).
- **CreditScoreResult** (objet de transport).
- Méthodologie comme `Referentiel` spécifique en F09.

## Success Criteria

- **SC-001** : Upload Wave statement (CSV) → parsing OK → score calculé.
- **SC-002** : Score combiné cohérent (test PME démo : agro 80 employés + projet panneaux solaires → score > 60).
- **SC-003** : Page méthodologie publique accessible et lisible.
- **SC-004** : Tentative de calcul sans consentement Mobile Money → 403 + invitation à activer.
- **SC-005** : Versioning méthodologie : changer pondération → v2, ancienne consultable.

## Hors-scope MVP

- API live Mobile Money (intégrations directes Wave/Orange/MTN — post-MVP, complexe).
- Analyse photos par LLM multimodal (post-MVP).
- Scraping social media / Google Business (post-MVP).
- Modèle ML supervisé (en MVP : règles + pondérations sourcées, pas de ML).
- Score prédictif de défaut (post-MVP).

## Risques et points de vigilance

- **Confidentialité Mobile Money** : données sensibles. Storage chiffré, accès très restreint, purge agressive selon consentement F05.
- **Méthodologie auditable** : l'avantage compétitif est la **transparence**. Pas de boîte noire ML. Quitte à être moins précis, on est explicable.
- **Biais culturels** : adapter les indicateurs au contexte (saisonnalité agricole = OK, pas une faiblesse). À encoder dans les pondérations sourcées.
- **Taux d'usurpation** : la PME peut "fabriquer" des données déclaratives pour gonfler son score. Avoir une logique de cohérence (si score > 80 sans Mobile Money, c'est suspect).
- **Conformité** : un score de crédit a des implications réglementaires dans certains pays. À vérifier avec un juriste avant prod (pas un blocant code mais à signaler).
