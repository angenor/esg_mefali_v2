# Feature Specification: Collecte Données & Algorithme de Scoring Crédit Vert

**Feature Branch**: `029-credit-scoring-collecte-algo`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F29 — collecte données crédit (Mobile Money via upload statement, déclaratif via ask_*, photos via upload, données publiques déclaratives) avec consentements F05, et algorithme de scoring hybride : 3 scores (solvabilité 0-100, impact vert 0-100, combiné 0-100) calculés selon méthodologie publiée et sourcée (référentiel F09)."

## Clarifications

### Session 2026-04-29

- Q: Format CSV Mobile Money exigé MVP ? → A: Format générique normalisé (colonnes `date_iso`, `amount_xof`, `direction` ∈ {in, out}, `counterparty` optionnel). Mappers Wave/Orange/MTN/Free Money sont post-MVP.
- Q: Cap taille upload statement ? → A: max 5 MB et 10 000 transactions ; dépassement → HTTP 413.
- Q: Recalcul concurrent même entreprise ? → A: sérialisation par `pg_advisory_xact_lock(entreprise_id)` ; la dernière écriture gagne, les scores antérieurs restent en historique.
- Q: Historique des scores ? → A: table `credit_score` append-only ; `GET /me/credit-score` retourne le plus récent (`computed_at DESC`).
- Q: Source ESG/carbone manquante au moment du calcul ? → A: facteur omis avec `value=null, contribution=0` ; `coherence_warning=true` si la couverture solvabilité ou impact_vert tombe sous 50%.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Calcul d'un score crédit hybride sourcé (Priority: P1)

En tant que PME ayant complété son profil entreprise (F11), ses projets (F12), son empreinte carbone (F28) et son scoring ESG (F23), je veux déclencher le calcul de mon score crédit hybride et obtenir trois indicateurs (solvabilité, impact vert, score combiné) accompagnés de leurs facteurs détaillés et de la source méthodologique.

**Why this priority**: C'est le cœur de la feature et la condition pour permettre l'inclusion financière. Sans ce calcul, aucune des autres User Stories n'a de valeur.

**Independent Test**: Une PME démo (entreprise + projet vert + empreinte + ESG existants) appelle `POST /me/credit-score/recompute` avec consentements `declaratif` actifs et obtient un `CreditScoreResult` contenant trois scores 0-100, la liste des facteurs (nom, valeur, poids, contribution, source_id), et la version de méthodologie utilisée.

**Acceptance Scenarios**:

1. **Given** une PME ayant donné les consentements requis et disposant des données minimales (entreprise + projet + empreinte ou ESG), **When** elle appelle `POST /me/credit-score/recompute`, **Then** un `credit_score` est persisté avec `solvabilite`, `impact_vert`, `combine` chacun dans [0, 100], `methodologie_version` figé, et `facteurs` non vide.
2. **Given** une PME sans consentement `declaratif`, **When** elle appelle `POST /me/credit-score/recompute`, **Then** la réponse est 403 et aucune ligne `credit_score` n'est créée.
3. **Given** une PME ayant un score calculé, **When** elle appelle `GET /me/credit-score`, **Then** elle reçoit le score persisté avec ses facteurs et la version de méthodologie.

---

### User Story 2 — Collecte de données crédit déclaratives et statements (Priority: P1)

En tant que PME, je veux déposer des données structurées (déclaratives sur la régularité de paiement, saisonnalité, diversification) ou un statement Mobile Money (CSV) afin que ces données alimentent mon score crédit.

**Why this priority**: Sans collecte, le score n'aurait que les données déjà existantes (entreprise/projets/ESG/carbone). Les données déclaratives + Mobile Money permettent d'enrichir significativement le score solvabilité.

**Independent Test**: Une PME envoie `POST /me/credit-data` avec `kind=declaratif` et `payload_json={paiements_reguliers: true, saisonnalite: "agricole", diversification_clients: 5}`, puis upload un statement Mobile Money CSV ; les deux lignes sont persistées et associées au consentement actif.

**Acceptance Scenarios**:

1. **Given** un consentement `declaratif` actif, **When** la PME `POST /me/credit-data` avec `kind=declaratif` et un payload valide, **Then** une ligne `credit_data` est créée et liée au `consent_id`.
2. **Given** un consentement `mobile_money` actif et un fichier CSV Wave/Orange Money valide, **When** la PME upload le statement, **Then** le fichier est parsé, normalisé en transactions, et les indicateurs dérivés (volume mensuel moyen, écart-type, ratio entrées/sorties, nombre de transactions) sont stockés dans le payload.
3. **Given** un consentement non actif pour le `kind` envoyé, **When** la PME poste de la donnée, **Then** la requête est refusée avec 403.

---

### User Story 3 — Méthodologie publique versionnée (Priority: P1)

En tant que PME, bailleur ou tiers, je veux consulter la méthodologie de scoring (formule, facteurs, pondérations, sources scientifiques) sans authentification, dans la version utilisée par mon score, afin d'auditer et comprendre le calcul.

**Why this priority**: La transparence est l'avantage compétitif (vs boîte noire ML). Sans page publique versionnée, la promesse "sourcé et explicable" n'est pas tenable.

**Independent Test**: `GET /methodologie/credit-scoring` retourne la version active publiée (Markdown rendu côté client) et `GET /methodologie/credit-scoring?version=1` retourne la version 1 même si v2 est active.

**Acceptance Scenarios**:

1. **Given** une méthodologie publiée v1, **When** un visiteur (sans login) consulte la page publique, **Then** il voit le contenu Markdown, la liste des facteurs, leurs poids, leurs sources cliquables et le numéro de version.
2. **Given** une méthodologie v2 publiée par admin et un score historique calculé contre v1, **When** la PME consulte ce score, **Then** la méthodologie v1 reste consultable et `methodologie_version=1` est affiché.

---

### User Story 4 — Facteurs explicables (Priority: P2)

En tant que PME, je veux consulter, pour chaque facteur de mon score, sa définition, sa valeur calculée pour mon entreprise, son poids, sa contribution numérique et sa source.

**Why this priority**: Indispensable à terme pour l'expérience utilisateur, mais le calcul (US1) et la collecte (US2) sont prioritaires. La donnée structurée est livrée via API en MVP ; le frontend détaillé est différé.

**Independent Test**: La réponse `GET /me/credit-score` contient pour chaque facteur les champs `name`, `definition`, `value`, `weight`, `contribution`, `source_id`.

**Acceptance Scenarios**:

1. **Given** un score calculé, **When** la PME consulte la liste des facteurs, **Then** chaque facteur expose nom, valeur, poids, contribution et source.

---

### Edge Cases

- Recalcul demandé alors qu'aucun consentement n'est actif → 403 explicite, score précédent conservé.
- Aucune donnée minimale (pas d'entreprise complète) → 422 avec message clair.
- Statement Mobile Money mal formé (encodage, colonnes manquantes) → 400 avec champs en erreur.
- Statement Mobile Money > 5 MB ou > 10 000 transactions → HTTP 413.
- Recalcul concurrent pour la même entreprise → sérialisation via `pg_advisory_xact_lock(entreprise_id)` ; la dernière écriture gagne, l'ancien score reste en historique.
- Méthodologie v2 publiée pendant un calcul en cours → le calcul utilise la version active au démarrage (snapshot).
- Score combiné > 80 sans aucune donnée Mobile Money ni ESG → flag `coherence_warning=true` (signal anti-fraude, pas blocage).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La plateforme MUST stocker les données crédit dans une table `credit_data` (id, account_id, entreprise_id, kind, payload_json, consent_id, uploaded_at, valid_until nullable) avec RLS multi-tenant.
- **FR-002**: La plateforme MUST exposer `POST /me/credit-data` qui valide le consentement actif correspondant au `kind` (F05) avant insertion, et journalise l'opération via l'audit append-only (F04).
- **FR-003**: La plateforme MUST exposer `POST /me/credit-data/mobile-money` qui accepte un fichier CSV au format générique normalisé (colonnes obligatoires `date_iso`, `amount_xof`, `direction` ∈ {in, out}, `counterparty` optionnel), de taille ≤ 5 MB et ≤ 10 000 transactions (dépassement → HTTP 413), et l'enregistre comme `credit_data(kind=mobile_money)` avec son payload normalisé (transactions + indicateurs dérivés volume_mensuel_moyen, ecart_type, ratio_entrees_sorties, nb_transactions). Mappers Wave / Orange Money / MTN / Free Money sont `[DEFERRED]` post-MVP.
- **FR-004**: Le service `CreditScoringService` MUST calculer trois scores (solvabilite 0-100, impact_vert 0-100, combine 0-100) à partir des sources disponibles : Mobile Money (US2), déclaratif, profil entreprise (F11), projets (F12), empreinte carbone (F28), score ESG (F23). Si une source est absente, le facteur correspondant est conservé avec `value=null, contribution=0` plutôt que de bloquer le calcul.
- **FR-005**: Chaque facteur calculé MUST exposer `name`, `definition`, `value`, `weight`, `contribution`, `source_id` (référant à un référentiel F09 nommé `credit_scoring_methodology`).
- **FR-006**: La plateforme MUST exposer `GET /me/credit-score` (dernier score persisté ordonné par `computed_at DESC`, 404 si aucun) et `POST /me/credit-score/recompute` (force recalcul ; sérialisation via `pg_advisory_xact_lock(entreprise_id)` ; persiste un nouveau résultat append-only sans écraser l'historique).
- **FR-007**: La plateforme MUST exposer `GET /methodologie/credit-scoring` (page publique, sans auth) qui retourne la méthodologie active (Markdown + facteurs + poids + sources). Paramètre optionnel `?version=N`.
- **FR-008**: Le calcul MUST être bloqué (403) si le consentement requis pour la donnée concernée n'est pas actif. Mapping consentements F05 existants : `kind=mobile_money` → `ConsentKind.MOBILE_MONEY`, `kind=photos` → `ConsentKind.EXPLOITATION_PHOTOS`. Les consentements `declaratif` et `publique` ne sont pas gatés (données saisies/déclarées explicitement par la PME via les endpoints F11/F12 ou la collecte). Aucune contrainte de consentement supplémentaire n'est exigée pour produire le score à partir des données déjà saisies.
- **FR-009**: Tout changement de pondération MUST créer une nouvelle version de méthodologie (F04). Les scores existants MUST rester calculables et consultables contre leur version d'origine.
- **FR-010**: Toutes les opérations (collecte, calcul, recalcul, consultation publique) MUST être journalisées (F04, source_of_change adapté).
- **FR-011**: La plateforme MUST tagger `coherence_warning=true` lorsque (a) un score combiné > 80 est calculé sans donnée Mobile Money ni score ESG, OU (b) la couverture des facteurs alimentant solvabilité ou impact_vert tombe sous 50% (facteurs omis avec `value=null, contribution=0`).
- **FR-012**: Le combiné MUST être calculé `combine = round(α * solvabilite + β * impact_vert)` avec α et β publiés dans le référentiel méthodologie (somme = 1, valeurs par défaut α=0.6 / β=0.4).

### Key Entities

- **CreditData** : représente un lot de données crédit déposé par une PME ; attributs clés : compte, entreprise, type (mobile_money/declaratif/photos/publique), payload JSON, consentement associé, dates.
- **CreditScore** : représente un score calculé pour une entreprise à un instant donné, append-only (chaque recalcul ajoute une ligne) ; attributs clés : compte, entreprise, solvabilite, impact_vert, combine, facteurs (json détaillé incluant facteurs omis avec `value=null`), version méthodologie, coherence_warning, computed_at.
- **CreditScoringMethodology** : référentiel F09 spécifique versionné contenant les facteurs, leurs poids, leurs sources et la formule combinée (α/β). Stocké comme `Referentiel(kind='credit_scoring_methodology')` avec versioning F04.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME démo (entreprise + projet vert + empreinte carbone + ESG) obtient ses trois scores en moins d'une seconde après recalcul.
- **SC-002**: 100% des facteurs publiés sur la page méthodologie ont une `source_id` valide (cohérence F03).
- **SC-003**: Toute tentative de calcul sans consentement `declaratif` actif retourne une erreur 403 et n'écrit aucune donnée (vérifié via test E2E ou intégration).
- **SC-004**: Une méthodologie v2 peut être publiée sans casser les scores calculés contre v1 (les scores v1 restent lisibles, leur version est correctement affichée).
- **SC-005**: Un statement Mobile Money de 100 transactions est parsé en moins d'une seconde et alimente correctement les indicateurs dérivés (volume_mensuel_moyen, ratio).

## Assumptions

- Les consentements F05 (`declaratif`, `mobile_money`, `photos`, `publique`) existent et sont gérables par la PME via les endpoints F05 ; cette feature ne crée que la dépendance.
- Les référentiels F09 supportent un `kind=credit_scoring_methodology` versionnable (FR-009), avec stockage du Markdown public et des pondérations.
- Le scoring ESG (F23) et l'empreinte carbone (F28) exposent des accès lecture stables (services Python internes ou table) consommables par `CreditScoringService`.
- La page publique `/methodologie/credit-scoring` est servie via un endpoint backend `GET /methodologie/credit-scoring` (le rendu HTML/Markdown côté frontend est différé hors du scope MVP).
- Le MVP livre exclusivement le backend : pas de page Vue, pas d'intégration Mobile Money live, pas d'analyse multimodale des photos, pas de scraping social ; les fonctionnalités frontend et les intégrations live sont marquées `[DEFERRED]`.
- L'algorithme MVP repose sur des règles pondérées sourcées (pas de modèle ML supervisé).
- Le skill `skill_credit_score` (F21) est étendu uniquement pour orchestrer la collecte côté LLM dans une itération ultérieure ; la définition du skill côté backend (registration) est dans le scope, l'orchestration LLM avancée est hors scope.
