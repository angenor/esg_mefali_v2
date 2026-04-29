# Feature Specification: Catalogue Fonds, Intermédiaires & Offres (F08)

**Feature Branch**: `008-catalog-fonds-intermediaires-offres`
**Created**: 2026-04-29
**Status**: Draft
**Phase** : 1 — Back-office Admin & Catalogue
**Modules brainstorm** : 3.1 (Catalogue), 9.1 (Gestion du Catalogue)
**Dépendances** : F04 (audit/versioning), F06 (back-office skeleton), F07 (catalog sources management)
**Input**: Modélisation des trois entités Fonds source, Intermédiaire accrédité, Offre (= couple Fonds × Intermédiaire) avec calcul automatique des critères/documents effectifs et comparateur d'intermédiaires.

## Contexte et objectif

Cette feature livre la **différenciation cœur** de la plateforme : modéliser non pas une seule liste de "fonds", mais **trois entités distinctes** — `FondsSource`, `Intermediaire`, `Offre` — reliées par une table d'accréditation datée.

> **Vérité du terrain (brainstorming)** : la plupart des grands fonds verts ne décaissent jamais directement aux PME africaines. L'**Intermédiaire** est souvent le vrai filtre, et c'est l'**Offre** (couple Fonds × Intermédiaire) qui est l'unité commercialement accessible. Une PME peut être éligible "GCF via BOAD" et incompatible "GCF via UNDP".

La feature doit honorer les invariants Module 0 :
1. **Sourcing obligatoire** : tout chiffre/seuil/critère pointe vers Source `verified` (F03 canonicalisée par F07).
2. **RLS multi-tenant** : Fonds/Intermédiaires/Offres sont GLOBAUX (pas d'`account_id`, comme Source).
3. **Audit append-only** (F04) sur toutes les opérations.
4. **Versioning** draft→published avec If-Match (F04).
5. **Money typé** peg FCFA-EUR 655.957 pour montants Fonds/Offres/plafonds Accréditation.
6. **UI bottom sheet** pour les formulaires admin.
7. **Plateforme fermée** PME+Admin.

## Clarifications

### Session 2026-04-29

- Q: Quel schéma JSONB pour les critères (Fonds, Intermédiaire, Offre) ? → A: Schéma typé minimal `{key: str, operator: ENUM('eq','min','max','in','not_in','contains'), value: any, unit?: str, source_id: uuid}`. Liste de tels objets dans `criteres_json`. Validation Pydantic au CRUD. Free-form refusé pour garantir la déterminisme du calcul effective et la traçabilité source par critère.
- Q: Sémantique exacte de l'intersection des critères pour `/effective` ? → A: Règles typées par `operator` :
  - `min` (seuils minimaux, ex. `min_project_size`) → `max` des deux valeurs (règle la plus restrictive).
  - `max` (seuils maximaux, ex. `max_amount`) → `min` des deux valeurs.
  - `in`/`not_in` (listes éligibilité, ex. `pays`) → intersection ensembliste ; intersection vide ⇒ `effective_warning`.
  - `eq` (égalité requise, ex. `currency`) → conflit si différent ⇒ `effective_warning`.
  - `contains` (sous-set ex. `instruments`) → intersection.
  Documents → toujours UNION (key `document_id`). Frais Money → somme. Délais jours → somme. Algorithme déterministe testé sur les 5 cas d'école (SC-002).
- Q: Quand est déclenché `needs_refresh` sur les Offres ? → A: Hook synchrone applicatif dans la transaction de save (PUT/PATCH) d'un Fonds ou Intermédiaire `published` v_n. Le hook scanne les Offres dérivées, recalcule l'intersection critères + union documents, compare au snapshot précédent, et set `needs_refresh=true` si diff. Pas de queue async ni de cron au MVP.
- Q: Comment détecter automatiquement qu'une Offre devient `outdated` (toutes accréditations expirées) ? → A: Lazy check au moment de la lecture (`GET /admin/offres/{id}`, `GET /admin/offres`, `GET /catalog/offres`) : la couche service vérifie `is_active(now)` sur les Accreditations associées au couple. Si aucune n'est active, set `status=outdated` (transactionnel) + audit_log. Endpoint admin manuel `POST /admin/offres/recheck-status` pour bulk refresh. Pas de cron au MVP.
- Q: Surface lecture PME du catalogue ? → A: Endpoint séparé `GET /catalog/offres` (et `GET /catalog/offres/{id}`, `GET /catalog/fonds`, `GET /catalog/intermediaires`) sous `/catalog/*`, authentification PME requise (plateforme fermée), RLS lecture-seule, exclut `draft/archived/outdated`. L'admin garde `/admin/*`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CRUD Fonds source (Priority: P1)

L'admin crée, édite et publie une fiche `FondsSource` représentant un bailleur (GCF, FEM, AFD, BAD, BOAD, BIDC, IFC, etc.) avec son identité, sa thématique, ses instruments financiers, ses plafonds Money, son éligibilité géographique, sa taxonomie/référentiel propre, et son `submission_mode`.

**Why this priority** : sans modélisation des Fonds source, aucune des autres entités n'est utile. C'est la fondation du catalogue et la donnée la plus visible côté PME (via F25 Matching).

**Independent Test** : un admin authentifié POST `/admin/fonds/` avec un payload complet (GCF), reçoit `201` avec `status=draft, version=1`. Après ajout d'au moins une `Source` `verified` liée (politique du fonds, taxonomie), un PUT `/publish` (avec `If-Match`) bascule le fonds en `published`. Une lecture publique PME GET `/admin/fonds/{id}` (filtrée `status=published`) renvoie la fiche.

**Acceptance Scenarios** :
1. **Given** un admin authentifié et au moins 1 Source `verified` correspondant à la politique du fonds, **When** il POST `/admin/fonds/` avec name="GCF", organisation="Green Climate Fund", type="multilateral", thematique=["climat"], plafond_money={amount:250_000_000, currency:"USD"}, **Then** la réponse est `201` avec `status=draft, version=1` et l'événement est journalisé en `audit_log`.
2. **Given** un Fonds en `draft` sans Source `verified` rattachée, **When** l'admin tente PUT `/admin/fonds/{id}/publish`, **Then** la réponse est `409 publish_gate_failed` (référence F06 publish gate).
3. **Given** un Fonds en `published` v1, **When** un admin l'édite via PUT avec `If-Match: <etag-v1>`, **Then** une nouvelle version `published v2` est créée et `audit_log` enregistre le diff. Une concurrence (If-Match désynchronisé) renvoie `412`.

---

### User Story 2 - CRUD Intermédiaire accrédité (Priority: P1)

L'admin crée, édite et publie une fiche `Intermediaire` (BOAD, NSIA, Ecobank, PNUD, Atmosfair, agence nationale climat, etc.) avec son identité, son type d'accréditation (DAE/NIE/RIE/MIE/banque_locale/dev_carbone/agence_nationale/agence_implem), pays d'opération, contact, frais, délais, portail, track-record manuel.

**Why this priority** : les intermédiaires sont le vrai filtre pour les PME. Aucune Offre ne peut exister sans Intermédiaire publié.

**Independent Test** : POST `/admin/intermediaires/` avec un payload BOAD, statut `draft`. Après ajout d'au moins 1 Source `verified` (page d'accréditation officielle), publication possible et lecture confirmée.

**Acceptance Scenarios** :
1. **Given** un admin, **When** il POST `/admin/intermediaires/` avec name="BOAD", type="NIE", pays=["BJ","BF","CI","ML","NE","SN","TG","GW"], frais_json={origination_pct:1.5}, **Then** réponse `201, status=draft`.
2. **Given** un Intermédiaire `published`, **When** un autre admin tente une suppression, **Then** la réponse est `409` (entité référencée par accréditations/offres) — soft delete uniquement.

---

### User Story 3 - Accréditations datées et plafonnées (Priority: P1)

L'admin enregistre une `Accreditation` reliant un Intermédiaire à un Fonds sur une période (`valid_from`, optionnel `valid_to`), avec un plafond `Money` typé, une `source_id` pointant vers la preuve officielle, et des notes.

**Why this priority** : sans accréditation active, aucune Offre n'est créable. La table d'accréditation est le pivot temporel du catalogue.

**Independent Test** : POST `/admin/accreditations/` `{intermediaire_id:BOAD, fonds_id:GCF, valid_from:'2018-03-01', plafond_money:{amount:500_000_000, currency:'USD'}, source_id:<gcf-board-doc>}`. Endpoint `GET /admin/accreditations/{id}/is_active?at=now` renvoie `true`. Quand `valid_to` est passé, helper renvoie `false` et les Offres rattachées sont marquées `outdated` (job/lazy check).

**Acceptance Scenarios** :
1. **Given** une accréditation `valid_from=2018-03-01, valid_to=null`, **When** GET `/is_active?at=2026-04-29`, **Then** `true`.
2. **Given** une accréditation expirée (`valid_to=2025-12-31`) reliée à 2 Offres `published`, **When** le job/lazy check tourne après échéance, **Then** les 2 Offres passent en `outdated` et un événement `audit_log` est écrit.
3. **Given** absence d'accréditation active entre Fonds X et Intermédiaire Y, **When** un admin tente POST `/admin/offres/` avec ce couple, **Then** réponse `409 no_active_accreditation`.

---

### User Story 4 - CRUD Offre (Fonds × Intermédiaire) avec calcul "effective" (Priority: P1)

L'admin crée une `Offre` en sélectionnant un Fonds publié et un Intermédiaire publié parmi ceux ayant une accréditation active entre eux. La fiche Offre stocke uniquement les champs **spécifiques** (nom commercial, accepted_languages, deadline override, criteres_offre_specifiques, frais_specifiques, delais_specifiques). Le **calcul effectif** est exposé en lecture seule via `GET /admin/offres/{id}/effective`.

**Why this priority** : c'est l'unité qu'une PME peut réellement viser. C'est aussi la donnée que F23 (Scoring), F25 (Matching) et F26 (Génération de dossier) consomment.

**Independent Test** : POST `/admin/offres/` `{fonds_id:GCF, intermediaire_id:BOAD, name:"GCF via BOAD", accepted_languages:["fr","en"]}`. GET `/effective` renvoie un arbre à 2 niveaux `{fonds_layer:{...}, intermediaire_layer:{...}, criteres_effectifs:[...intersection...], documents_effectifs:[...union...], frais_effectifs:Money, delais_effectifs:int_jours, accepted_languages:["fr","en"]}` testé déterministe sur 5 cas d'école.

**Acceptance Scenarios** :
1. **Given** GCF avec critère `min_project_size=10M USD` et BOAD avec critère `min_project_size=2M USD`, **When** l'admin crée Offre "GCF via BOAD" et GET `/effective`, **Then** `criteres_effectifs.min_project_size = max(10M, 2M) = 10M USD` (intersection = règle la plus restrictive) ET `documents_effectifs` = union des deux listes.
2. **Given** une Offre `published`, **When** le Fonds est ré-édité (v2) avec nouveaux critères, **Then** l'Offre reçoit un badge `needs_refresh=true` et l'admin peut cliquer "Actualiser" pour publier une nouvelle version d'Offre alignée.
3. **Given** une Offre dérivée d'un Fonds `submission_mode=call_for_proposals` avec deadline=2026-09-30, **When** l'Offre n'a pas de `deadline` override, **Then** `effective.deadline = 2026-09-30` (héritée).
4. **Given** une Offre avec `accepted_languages=["fr"]`, **When** F26 demande génération en EN, **Then** F26 reçoit la liste et peut refuser/avertir (consommation downstream).

---

### User Story 5 - Comparateur intermédiaires d'un même fonds (Priority: P2)

L'admin (et plus tard la PME via F25) consulte une vue tabulaire alignée affichant tous les Intermédiaires accrédités actifs pour un Fonds donné, avec leurs critères/frais/délais/track-record côte à côte.

**Why this priority** : valeur métier forte mais dérivée des données P1. Page de lecture pure, pas de mutation.

**Independent Test** : GET `/admin/fonds/{gcf_id}/intermediaires` renvoie `[BOAD, UNDP, PNUE]` filtré sur accréditations actives. Page admin `/admin/fonds/[id]/comparator` charge ces 3 intermédiaires et leurs Offres dérivées dans un tableau aligné.

**Acceptance Scenarios** :
1. **Given** GCF avec 3 accréditations actives (BOAD, UNDP, PNUE), **When** GET `/admin/fonds/{gcf_id}/intermediaires`, **Then** liste de 3 entrées avec les Offres dérivées et leurs `effective` calculés.
2. **Given** une 4e accréditation expirée, **When** même endpoint, **Then** elle n'apparaît pas (filtré actif).

---

### User Story 6 - Submission mode (rolling vs call_for_proposals) (Priority: P2)

L'admin distingue à la création d'un Fonds entre `rolling` (guichet ouvert, pas de deadline globale) et `call_for_proposals` (appels datés avec deadline héritée par les Offres).

**Why this priority** : alimente les alertes/timeline (F25, F31). Pas critique pour les premiers tests catalogue.

**Independent Test** : POST `/admin/fonds/` GCF avec `submission_mode=rolling` ⇒ pas de deadline. POST `/admin/fonds/` "AFD Adapt'Action 2026" avec `submission_mode=call_for_proposals, deadline=2026-09-30` ⇒ Offres dérivées héritent.

**Acceptance Scenarios** :
1. **Given** Fonds `rolling`, **When** Offre dérivée sans deadline override, **Then** `effective.deadline=null`.
2. **Given** Fonds `call_for_proposals` deadline=2026-09-30, **When** Offre sans override, **Then** `effective.deadline=2026-09-30`. Avec override 2026-08-31, `effective.deadline=2026-08-31`.

---

### Edge Cases

- **Accréditation chevauchante** : deux accréditations actives pour le même couple (Intermediaire, Fonds) sur des périodes qui se chevauchent → autorisé (avenants), la plus récente `valid_from` prime pour le `plafond_money`.
- **Suppression d'un Fonds référencé** : refusée tant qu'il existe une accréditation ou une Offre la référençant. Soft delete uniquement.
- **Fonds dépublié (republier en draft)** : ses Offres `published` passent automatiquement en `outdated` et apparaissent en bandeau d'alerte.
- **Multilingue accepted_languages vide** : la validation rejette ; default `["fr"]` injecté côté serveur si non fourni.
- **Plafond Money en devises différentes** : la conversion FCFA-EUR utilise le peg fixe 655.957 ; les autres devises (USD, GBP) sont stockées telles quelles avec leur code ISO et la conversion d'affichage est déférée à F32 (dashboard PME) hors scope ici.
- **Concurrence d'édition** : sans `If-Match` valide, retour `412 Precondition Failed`.
- **Conflit de critère contradictoire** : si Fonds exige `pays=["CI"]` et Intermédiaire exige `pays=["SN"]`, intersection vide → l'Offre est créable mais marquée `effective_warning="incompatible_countries"` et exclue du Matching F25.
- **Source `verified` obligatoire** : tentative de publish sans aucune source verified → `409 publish_gate_failed`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST exposer une entité `FondsSource` portant `id, name, organisation, type ENUM('multilateral','bilateral','regional','national','prive'), thematique[], instruments[], plafond_money, plancher_money, eligibilite_geo[], submission_mode ENUM('rolling','call_for_proposals'), referentiel_id (FK F09 nullable en MVP), site_url, contact_json, version, status, source_ids[], created_at, updated_at, etag`.
- **FR-002** : Le système MUST exposer une entité `Intermediaire` portant `id, name, type ENUM('DAE','NIE','RIE','MIE','banque_locale','dev_carbone','agence_nationale','agence_implem'), pays[], zone_op, contact_json, frais_json, delais_json, portail_url, track_record_json, version, status, source_ids[], created_at, updated_at, etag`.
- **FR-003** : Le système MUST exposer une entité `Accreditation` portant `id, intermediaire_id, fonds_id, valid_from, valid_to NULL, plafond_money, source_id, notes, created_at, updated_at`. Index `(intermediaire_id, fonds_id, valid_from)`. Helper `is_active(at?)`. Versioning F04 appliqué.
- **FR-004** : Le système MUST exposer une entité `Offre` portant `id, fonds_id, intermediaire_id, name, accepted_languages TEXT[] DEFAULT ['fr'], deadline TIMESTAMPTZ NULL, criteres_offre_specifiques JSONB, frais_specifiques JSONB, delais_specifiques JSONB, version, status, source_ids[], needs_refresh BOOLEAN DEFAULT false, created_at, updated_at, etag`. Contrainte applicative : il existe une Accreditation active sur la période de l'Offre (vérifiée à la création/publication).
- **FR-005** : Le système MUST exposer `GET /admin/offres/{id}/effective` qui calcule en arbre à 2 niveaux et retourne `{fonds_layer:{criteres, documents, frais, delais, referentiel, deadline}, intermediaire_layer:{criteres, documents, frais, delais, referentiel}, criteres_effectifs (intersection par règles typées par operator : min→max, max→min, in/not_in/contains→intersection ensembliste, eq→égalité requise sinon effective_warning), documents_effectifs (UNION par document_id), frais_effectifs:Money (somme), delais_effectifs:int_jours (somme), referentiel_effectif:{fonds, intermediaire}, accepted_languages, deadline, effective_warning?}`. Le calcul MUST être déterministe et testé sur les 5 cas d'école (SC-002).
- **FR-006** : Le système MUST exposer `GET /admin/fonds/{id}/intermediaires` retournant la liste des Intermédiaires accrédités actifs (avec leurs Offres dérivées et `effective`).
- **FR-007** : Le système MUST exposer `GET /admin/intermediaires/{id}/fonds` (réciproque).
- **FR-008** : Le système MUST exposer une page admin `/admin/fonds/[id]/comparator` rendant un tableau comparatif aligné de toutes les Offres dérivées (critères, frais, délais, track-record) avec UI bottom sheet pour le détail.
- **FR-009** : Le système MUST exposer `GET /admin/offres?fonds=&intermediaire=&pays=&secteur=&status=&q=` paginé (page/limit standard back-office). Endpoint accessible aussi en lecture côté PME (sans `status=draft`). Cet endpoint MUST être consommable par F25.
- **FR-010** : Le système MUST déclencher un hook de cohérence **synchrone applicatif dans la transaction de save** d'un Fonds ou Intermédiaire `published` (PUT/PATCH/publish) : scanner les Offres dérivées, recalculer intersection critères + union documents, et marquer `needs_refresh=true` si diff par rapport au snapshot précédent. Pas de queue async ni de cron au MVP. L'admin peut cliquer "Actualiser" pour publier une nouvelle version d'Offre alignée.
- **FR-011** : Le système MUST appliquer le publish gate F06 : un Fonds, un Intermédiaire ou une Offre ne peut passer en `published` que s'il existe au moins 1 Source `verified` rattachée (`source_ids[]` non vide ET au moins une `verified`).
- **FR-012** : Le système MUST tracer chaque opération CRUD (create, update, publish, soft-delete) en `audit_log` (F04) avec diff JSON.
- **FR-013** : Le système MUST appliquer le contrôle de concurrence par `ETag/If-Match` (F04/F06) sur tous les endpoints `PUT/DELETE`.
- **FR-014** : Le système MUST refuser la création d'une Offre si aucune Accreditation active n'existe entre le couple Fonds × Intermédiaire ; réponse `409 no_active_accreditation`.
- **FR-015** : Le système MUST faire passer une Offre en `outdated` via **lazy check** à chaque lecture (`GET /admin/offres/{id}`, `GET /admin/offres`, `GET /catalog/offres`) lorsque plus aucune Accreditation active n'existe sur le couple ; transition transactionnelle, événement audité. Endpoint admin manuel `POST /admin/offres/recheck-status` pour bulk refresh. Pas de cron au MVP.
- **FR-016** : Le système MUST stocker tout montant via le type `Money` (peg FCFA-EUR 655.957) pour `plafond_money`, `plancher_money` du Fonds, `plafond_money` de l'Accreditation, et `frais_effectifs` calculés.
- **FR-017** : Le système MUST appliquer une politique RLS GLOBALE (pas d'`account_id`) sur les tables `fonds_source`, `intermediaire`, `accreditation`, `offre` ; lecture autorisée à tout utilisateur authentifié pour `status=published`, écriture réservée au rôle admin.
- **FR-018** : Le système MUST garantir l'unicité opérationnelle `(fonds_id, intermediaire_id, name)` pour `Offre` afin d'éviter les doublons commerciaux.
- **FR-019** : Le système MUST permettre le soft-delete (status=archived) plutôt que la suppression dure, et refuser le soft-delete si l'entité est référencée par une entité dépendante non-archivée.
- **FR-020** : Le système MUST exposer côté PME un préfixe d'API distinct `/catalog/*` avec : `GET /catalog/offres` (paginé + filtres), `GET /catalog/offres/{id}` (détail + `effective` inclus), `GET /catalog/fonds`, `GET /catalog/fonds/{id}`, `GET /catalog/intermediaires`, `GET /catalog/intermediaires/{id}`. Tous excluent `draft/archived/outdated`. Authentification PME (rôle `pme`) requise — pas d'accès anonyme (plateforme fermée). RLS lecture-seule.

### Key Entities

- **FondsSource** : représente un bailleur/source de financement (GCF, FEM, AFD, BOAD, IFC). Attributs clés : type (multilatéral/bilatéral/régional/national/privé), thématique, instruments financiers, plafonds Money, éligibilité géo, mode de soumission, référentiel ESG propre, sources verified rattachées.
- **Intermediaire** : représente un acteur qui décaisse réellement (banque, agence, ONG accréditée). Attributs clés : type d'accréditation (DAE/NIE/RIE/MIE/banque/agence), pays d'opération, frais, délais, track-record manuel.
- **Accreditation** : relation datée et plafonnée entre un Intermediaire et un FondsSource avec source officielle. Pivot temporel obligatoire pour qu'une Offre existe.
- **Offre** : couple (FondsSource × Intermediaire) commercialement accessible. Stocke uniquement les spécificités. Les critères/documents/frais/délais effectifs sont calculés en lecture (`/effective`) en combinant les deux entités sources.
- **CritereEffectif / DocumentEffectif** : valeurs calculées en vue, pas de tables dédiées. Exposées via `/effective` en arbre à 2 niveaux (`fonds_layer`, `intermediaire_layer`) plus la fusion (intersection critères, union documents).
- **Source** (réutilisée de F03/F07) : pièce justificative `verified` requise par le publish gate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Un admin saisit Fonds + Intermédiaire + Accréditation + Offre en moins de 30 minutes au total.
- **SC-002** : Le calcul `/admin/offres/{id}/effective` retourne le bon résultat (intersection critères, union documents, frais sommés, délais sommés, deadline héritée) sur 5 cas d'école : GCF×BOAD, GCF×UNDP, FEM×PNUD, SUNREF×Ecobank, FNE-CI×banque locale (suite de tests).
- **SC-003** : Le comparateur affiche correctement 3 Offres dérivées d'un même Fonds avec leurs colonnes alignées en ≤ 2 secondes côté admin.
- **SC-004** : Une Offre dont toutes les accréditations associées sont expirées passe en `outdated` automatiquement (cron ou lazy) en moins de 24 h après expiration.
- **SC-005** : Aucune entité ne peut être publiée sans au moins 1 Source `verified` rattachée (publish gate ; 100 % des tentatives sans source verified retournent 409).
- **SC-006** : 100 % des opérations CRUD sont reflétées dans `audit_log` avec diff JSON.
- **SC-007** : L'architecture supporte la cible MVP (100 fonds, 200 intermédiaires, 500 offres) sans dégradation perceptible et est dimensionnable à 10× sans refonte.

## Assumptions

- F01 (foundations stack), F04 (audit & versioning), F06 (back-office skeleton avec publish gate, ETag, registry, crud_router, search trigram), F07 (sources management) sont mergées et opérationnelles.
- Le module Money typé (peg FCFA-EUR 655.957) est exposé par F01.
- Le `referentiel_id` du Fonds est nullable en MVP : F09 (Référentiels & Indicateurs) sera livré ensuite ; ce champ est ajouté en colonne nullable et la vraie FK sera activée par F09.
- La lecture publique côté PME (`GET /catalog/offres`) se fait dans la même base, filtrée par RLS, sans cache/CDN dédié au MVP.
- L'`accepted_languages` par défaut est `['fr']` ; le support EN est obligatoire à la saisie pour bailleurs anglophones (GCF/IFC).
- Les conversions de devises au-delà du peg FCFA-EUR (USD, GBP, etc.) ne sont pas converties automatiquement ; elles sont stockées avec leur code ISO et l'affichage multi-devise est déféré à F32.
- La détection des changements `needs_refresh` se fait à la sauvegarde (hook synchrone simple) ; la propagation/actualisation reste manuelle (clic admin), pas auto-merge.
- La cible MVP de 100/200/500 entités est respectée ; au-delà, prévoir pagination renforcée et indexation supplémentaire.
- Pas d'import CSV en masse en MVP (saisie manuelle par admin), pas de marketplace public d'offres, pas de notifications matching automatiques (F25), pas de calcul automatique de track-record (saisie manuelle).
