# Feature Specification: Plan d'Action ESG Personnalisé (MVP)

**Feature Branch**: `031-plan-action-rappels-bibliotheque`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F31 — Plan d'Action, Rappels Cron & Bibliothèque de Ressources. MVP focalisé : table action_plan + action_step (US1+US2), endpoints generate/get/patch. Reporter en [DEFERRED] cron, notifications, bibliothèque, fiches intermédiaires, frontend, tool LLM."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Générer une feuille de route personnalisée (Priority: P1)

En tant que PME ayant complété son profil ESG et lancé au moins un calcul de score, je veux déclencher la génération automatique d'un plan d'action couvrant un horizon (6, 12 ou 24 mois) afin d'obtenir une roadmap concrète à partir de mes lacunes mesurées.

**Why this priority** : valeur centrale de la feature — sans plan généré, rien n'existe. La génération s'appuie strictement sur des signaux déjà calculés (score ESG F23) pour rester déterministe et sourcée.

**Independent Test** : Un compte PME avec un calcul de score F23 récent appelle l'endpoint de génération avec horizon=12 → reçoit un plan persisté contenant N étapes priorisées, chacune liée à un indicateur ESG manquant ou faiblement scoré ; un second appel produit une nouvelle version.

**Acceptance Scenarios** :

1. **Given** une PME authentifiée avec un `ScoreCalculation` F23 contenant ≥ 1 indicateur en lacune, **When** elle appelle `POST /me/action-plan/generate?horizon=12`, **Then** le système crée un `ActionPlan` (account_id, horizon=12, version=1) et au moins une `ActionStep` par lacune prioritaire, ordonnées par priorité, et renvoie l'objet complet.
2. **Given** une PME sans calcul de score F23 disponible, **When** elle appelle l'endpoint de génération, **Then** le système répond 422 avec un message clair invitant à lancer un scoring d'abord.
3. **Given** un `ActionPlan` existant, **When** la PME appelle `GET /me/action-plan`, **Then** elle reçoit son plan courant (le plus récent) avec toutes ses étapes triées par priorité puis horizon.
4. **Given** une autre PME, **When** elle appelle `GET /me/action-plan`, **Then** elle ne voit jamais le plan d'un compte voisin (RLS).

---

### User Story 2 — Suivre et mettre à jour les étapes (Priority: P1)

En tant que PME, je veux pouvoir marquer chaque étape comme `à faire`, `en cours`, `fait` ou `différé`, afin de suivre mon avancement et garder le plan vivant.

**Why this priority** : sans suivi de statut, la roadmap est statique et perd toute utilité opérationnelle.

**Independent Test** : Une PME passe une étape de `todo` à `doing`, puis à `done` via `PATCH /me/action-plan/steps/{id}` ; les transitions sont persistées, auditées, et un GET ultérieur reflète les nouveaux statuts.

**Acceptance Scenarios** :

1. **Given** une étape avec status `todo`, **When** la PME envoie `PATCH /me/action-plan/steps/{id}` avec `status=doing`, **Then** le statut est mis à jour, un audit log est écrit, et la réponse contient l'étape mise à jour.
2. **Given** une étape, **When** la PME tente de la passer à un statut inconnu (ex. `blocked`), **Then** le système renvoie 422.
3. **Given** une étape appartenant à une autre PME, **When** la PME courante tente le PATCH, **Then** le système renvoie 404 (RLS).
4. **Given** une étape, **When** la PME met à jour `responsible_user_id` (déclaratif, optionnel), **Then** la valeur est persistée et auditée.

---

### Edge Cases

- Aucun `ScoreCalculation` F23 disponible → 422 explicite.
- Score F23 présent mais sans lacune → plan généré avec ≥ 1 étape par défaut "Revue annuelle ESG" pour éviter un plan vide.
- Régénération : un nouvel appel `generate` crée une **nouvelle version** (`version = max+1`) ; les versions précédentes restent en base mais `GET` renvoie la dernière.
- Horizon hors {6, 12, 24} → 422.
- RLS strict : seul le `account_id` du token JWT peut lire/muter ses plans.
- Concurrence : deux générations simultanées d'une même PME → la seconde produit version+1 sans corruption.

## Requirements *(mandatory)*

### Functional Requirements (MVP)

- **FR-001** : Le système MUST exposer `POST /me/action-plan/generate?horizon={6|12|24}` qui produit un `ActionPlan` daté, versionné, lié au compte courant, à partir des lacunes ESG du dernier `ScoreCalculation` F23.
- **FR-002** : Chaque `ActionStep` MUST porter : titre court, description, catégorie (`esg|carbone|credit|candidature`), priorité (`haute|moyenne|basse`), horizon (date cible), statut (`todo|doing|done|postponed`), `responsible_user_id` optionnel, `indicateur_id` optionnel (lien lacune F23), `source_id` optionnel (F03).
- **FR-003** : Le système MUST exposer `GET /me/action-plan` qui renvoie le plan le plus récent (étapes triées par priorité décroissante puis date cible croissante).
- **FR-004** : Le système MUST exposer `PATCH /me/action-plan/steps/{id}` autorisant la modification de `status` et `responsible_user_id`. Les autres champs sont immuables côté PME en MVP.
- **FR-005** : Toute mutation MUST être journalisée via le mécanisme d'audit append-only (F04).
- **FR-006** : Les tables `action_plan` et `action_step` MUST porter une politique RLS qui restreint lecture/écriture au `account_id` propriétaire.
- **FR-007** : La génération MUST être déterministe pour un même `ScoreCalculation` source : chaque lacune (indicateur sous seuil F23) produit exactement une `ActionStep` priorisée selon la sévérité.
- **FR-008** : Le système MUST produire ≥ 1 étape par défaut même sans lacune détectée.
- **FR-009** : La régénération MUST créer une nouvelle version sans détruire les versions précédentes.

### Hors-scope MVP (explicitement [DEFERRED])

- **[DEFERRED] FR-010** : Cron `notify_offer_deadlines`, `notify_inactive_candidatures`, `monthly_progress_digest` (US3).
- **[DEFERRED] FR-011** : Table `notification` + envoi email transactionnel.
- **[DEFERRED] FR-012** : Bibliothèque `ressource` + CRUD admin + fiches intermédiaires.
- **[DEFERRED] FR-013** : Frontend Vue `/profil/plan-action` et `/ressources`.
- **[DEFERRED] FR-014** : Tool LLM `generate_action_plan` (US8).
- **[DEFERRED] FR-015** : Recommandation contextuelle de ressources (US7).

### Key Entities

- **ActionPlan** : feuille de route versionnée pour un compte PME. Attributs : `id`, `account_id`, `horizon_months ∈ {6,12,24}`, `generated_at`, `version`, `score_calculation_id` (lien F23).
- **ActionStep** : étape d'un plan. Attributs : `id`, `plan_id`, `title`, `description`, `category`, `priority`, `horizon_at`, `status`, `responsible_user_id` (optionnel), `indicateur_id` (optionnel, F23), `source_id` (optionnel, F03).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : 100 % des PME avec un score F23 récent peuvent générer un plan en moins de 2 secondes (P95).
- **SC-002** : Pour une PME ayant ≥ 5 indicateurs en lacune F23, le plan généré contient ≥ 5 étapes priorisées.
- **SC-003** : Aucune fuite cross-tenant lors des tests RLS (100 % des accès non autorisés renvoient 404).
- **SC-004** : 100 % des transitions de statut d'étape sont auditées.
- **SC-005** : Couverture de tests automatisés ≥ 80 % sur les modules introduits par cette feature.

## Assumptions

- F02 (auth + JWT/account_id) et F04 (audit) sont déjà en place et stables.
- F23 (`ScoreCalculation`) expose les indicateurs en lacune via accès SQLAlchemy direct ou service réutilisable.
- L'horizon est imposé en MVP : {6, 12, 24} mois (pas d'horizon libre).
- La régénération est autorisée à volonté (pas de quota MVP).
- Aucune intégration LLM, cron, email ou frontend n'est livrée — uniquement backend HTTP/SQL + algo déterministe.
- Le sourcing F03 sur les étapes est optionnel en MVP : la colonne existe, l'enrichissement canonique reste post-MVP.
