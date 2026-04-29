# Feature Specification: Catalog Sources Management (F07)

**Feature Branch**: `007-catalog-sources-management`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F07 — Gestion des Sources (CRUD, Vérification, Impact Analysis). Phase 1 — Back-office Admin & Catalogue. Dépendances : F03, F06."

## Clarifications

### Session 2026-04-29

- Q: Quand l'équipe n'a qu'un seul admin actif, comment gérer la double vérification ? → A: Bloquer strictement (`verified_by != captured_by` toujours appliqué côté serveur ; aucun bypass ni mode dégradé en MVP).
- Q: Page publique `/sources/{id}` quand la source est `pending` ? → A: 404 Not Found ; seules `verified` et `outdated` sont rendues publiquement.
- Q: Règle exacte de canonicalisation d'URL ? → A: Forcer `https://` ; host en lower-case ; retirer le préfixe `www.` ; retirer le slash final (sauf root `/`) ; retirer les paramètres de tracking (`utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`) ; conserver les fragments deep-link (`#page=`, `#:~:text=`).
- Q: Impact d'un mark-outdated sur les snapshots de candidatures ? → A: Snapshots immutables ; pas de cascade ; badge "source obsolète" seulement à l'UI ; audit log conservé.
- Q: Indexation moteurs de recherche pour la page publique en MVP ? → A: `noindex` HTTP + pas de sitemap en MVP (post-MVP) ; cohérent avec plateforme fermée.

## Overview

F07 livre l'expérience admin complète pour saisir, vérifier et maintenir la base de Sources qui alimente le sourçage anti-hallucination défini en F03. C'est la première feature opérationnelle de la plateforme : sans Sources publiées et vérifiées, aucun objet du catalogue (critères, formules, facteurs d'émission, indicateurs, référentiels, skills) ne peut passer en `published` ni être utilisé par le LLM. L'équipe ESG Mefali doit pouvoir saisir et faire valider 50–100 sources de référence (taxonomie UEMOA, critères GCF, IFC PS, politiques BOAD, ADEME Base Carbone, etc.) en peu de temps, et mesurer l'impact métier de toute évolution d'une source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Saisir une nouvelle Source (Priority: P1)

Un admin remplit un formulaire de création de Source contenant `url`, `title`, `publisher`, `version`, `date_publi`, `page`, `section`, `notes`. Au save, le système normalise l'URL (protocole, slash final, paramètres de tracking retirés), tente un appel HEAD HTTP non bloquant et détecte les doublons (même URL canonique + même page). La source est enregistrée en `verification_status='pending'` avec `captured_by` = utilisateur courant.

**Why this priority**: Sans capacité de saisir des sources, aucune autre fonctionnalité de la plateforme ne peut produire d'objet `published`. Pré-requis absolu de toute la chaîne anti-hallucination.

**Independent Test**: Un admin connecté soumet un payload valide (`url`, `title`, `publisher`) au formulaire/endpoint de création. La source apparaît dans la liste des sources `pending` avec `captured_by` correctement renseigné, l'URL est normalisée, et un audit log est inscrit.

**Acceptance Scenarios**:

1. **Given** un admin authentifié, **When** il soumet une nouvelle source avec une URL valide et un titre, **Then** la source est créée en `pending`, `captured_by` est défini, et l'URL stockée est canonicalisée.
2. **Given** une URL qui retourne 404 au HEAD HTTP, **When** l'admin soumet, **Then** la source est créée quand même mais le formulaire affiche un warning "URL non joignable au moment du save".
3. **Given** une source existante avec la même URL canonique et la même page, **When** l'admin tente d'en créer une seconde, **Then** le système propose de réutiliser l'existante (UI : "Une source identique existe — réutiliser ?").
4. **Given** une URL avec paramètres `utm_*`, slash final, ou variation `www.`/non-`www.`, **When** sauvegardée, **Then** la version stockée est canonicalisée selon une règle déterministe et reproductible.

---

### User Story 2 — Workflow de double vérification (Priority: P1)

Une source ne passe en `verified` que lorsqu'un admin différent du créateur l'a relue et validée. Le créateur ne peut pas valider sa propre source ; cette règle est appliquée côté serveur.

**Why this priority**: Garantit une double lecture sur tout chiffre officiel exposé par la plateforme. Pilier qualité du sourçage et exigence de gouvernance.

**Independent Test**: Admin A crée une source ; le bouton "Valider" est désactivé pour A. Admin B ouvre la même source, clique "Valider" → statut `verified`, `verified_by=B`, audit log. Une tentative API directe par A pour valider sa propre source retourne une erreur 403/422.

**Acceptance Scenarios**:

1. **Given** une source `pending` créée par A, **When** A appelle l'endpoint de vérification, **Then** le serveur refuse (`verified_by != captured_by` violé).
2. **Given** une source `pending` créée par A, **When** B appelle l'endpoint de vérification, **Then** la source passe `verified`, `verified_by=B`, un audit log est inscrit.
3. **Given** une source `pending` non référencée par aucun objet, **When** un admin la supprime, **Then** la suppression réussit (soft-delete-if-orphan).
4. **Given** une source `verified` référencée par des objets `published`, **When** un admin tente de la supprimer, **Then** la suppression est refusée mais l'admin peut la marquer `outdated`.
5. **Given** un déploiement avec un seul admin actif, **When** cet admin tente de valider sa propre source, **Then** la requête est refusée par le serveur (aucun bypass, aucun mode dégradé) ; l'opération nécessite l'ajout d'un second compte admin actif.

---

### User Story 3 — Liste filtrable et recherche (Priority: P1)

Un admin parcourt la liste paginée des sources avec filtres (statut multi-select, publisher autocomplete, date range de capture, "capté par moi") et recherche full-text sur titre + publisher + notes.

**Why this priority**: Saisir 50–100 sources la première semaine implique de retrouver vite une source existante (éviter les doublons) et d'identifier les `pending` à valider. UX critique pour la productivité de l'équipe.

**Independent Test**: Avec un dataset de N sources mixtes, l'admin filtre par statut `pending` + recherche un mot du titre → la liste retourne uniquement les sources correspondantes en moins d'une seconde.

**Acceptance Scenarios**:

1. **Given** 5000 sources en base, **When** l'admin charge la page liste, **Then** la première page (25/50/100) s'affiche en moins d'une seconde.
2. **Given** un terme tapé dans la barre de recherche, **When** la recherche s'exécute, **Then** elle couvre `title || publisher || notes` avec un classement de pertinence.
3. **Given** un filtre statut `pending`, **When** appliqué, **Then** seules les sources non encore vérifiées sont listées.
4. **Given** un tri demandé par colonne (`title`, `publisher`, `date_capture`, `verification_status`), **When** appliqué, **Then** la liste se réordonne sans recharger toute l'application.

---

### User Story 4 — Impact analysis avant modification ou marquage outdated (Priority: P1)

Avant de modifier les champs critiques d'une source ou de la marquer `outdated`, l'admin consulte un endpoint qui liste tous les objets dépendants (Indicateurs, Critères, Formules, Facteurs d'émission, Documents, Référentiels, Skills, Candidatures) avec compteurs agrégés et expansion lazy.

**Why this priority**: Toute évolution d'une source impacte potentiellement des dizaines voire centaines d'objets `published` et de candidatures en cours. Sans visibilité d'impact, le risque d'incident métier est inacceptable.

**Independent Test**: Une source GCF référencée par 8 critères, 1 référentiel, 2 skills et 12 candidatures retourne ces compteurs en moins de 500ms via l'endpoint impact, et l'expansion d'une catégorie liste les objets concernés.

**Acceptance Scenarios**:

1. **Given** une source référencée par >1000 objets cumulés, **When** l'endpoint impact est appelé, **Then** il répond en moins de 500ms (compteurs agrégés) et l'expansion d'une catégorie est paginée.
2. **Given** une source `verified`, **When** un admin la marque `outdated`, **Then** les objets `published` qui la référencent reçoivent un badge "source obsolète" sans que leur statut publication change automatiquement.
3. **Given** une source jamais référencée, **When** l'endpoint impact est appelé, **Then** tous les compteurs sont à zéro et l'UI propose la suppression.
4. **Given** une source `verified`, **When** un admin modifie un champ critique (`url`, `version`, `publisher`), **Then** une nouvelle version de la source est créée via le mécanisme de versioning (F04).
5. **Given** une source `verified`, **When** un admin modifie un champ accessoire (`notes`), **Then** aucune nouvelle version n'est créée mais un audit log enregistre la modification.

---

### User Story 5 — Page publique de lecture d'une Source (Priority: P2)

Une page publique sans authentification rend les informations d'une source : URL deep-linkée (avec `#page=` quand disponible), titre, publisher, version, date capture, statut. Cible : PME, auditeurs, lecteurs externes qui cliquent sur le picto Source du composant `<SourceCite>` (F03).

**Why this priority**: Renforce la confiance et la traçabilité externe des chiffres exposés par la plateforme. Pas bloquante pour la chaîne admin mais indispensable à l'audit.

**Independent Test**: Un visiteur non authentifié charge `/sources/{id}` et voit une page sobre listant tous les champs publics + un lien "Voir le document officiel".

**Acceptance Scenarios**:

1. **Given** une source `verified`, **When** un visiteur non authentifié charge la page publique, **Then** la page s'affiche avec tous les champs publics et un lien externe vers l'URL canonique.
2. **Given** une source `pending`, **When** un visiteur non authentifié tente d'y accéder, **Then** la page retourne un 404 Not Found (seules les sources `verified` et `outdated` sont publiques).
3. **Given** une source `outdated`, **When** la page publique est rendue, **Then** un badge visible signale le statut obsolète.

---

### User Story 6 — Sources non sourçables détectées par le LLM (Priority: P3)

Une page admin agrège les `flag_unsourced` produits par F03 (claims que le LLM n'a pas pu sourcer), groupés par claim avec compteur d'occurrences, et propose un raccourci "Créer une nouvelle source à partir de ce claim".

**Why this priority**: Outil de pilotage qualité pour prioriser les sources à ajouter ; non bloquant pour la première vague de saisie.

**Independent Test**: La page `/admin/unsourced-claims` liste les top claims non sourcés sur la dernière période avec leur compteur et un lien direct vers le formulaire de création de source pré-rempli.

**Acceptance Scenarios**:

1. **Given** des `flag_unsourced` enregistrés par F03, **When** l'admin charge la page, **Then** les claims sont groupés et triés par fréquence décroissante.
2. **Given** un claim listé, **When** l'admin clique "Créer une source à partir de ce claim", **Then** le formulaire de création s'ouvre avec un contexte pré-rempli.

### Edge Cases

- Une source dont l'URL devient inaccessible après publication (404 au HEAD ultérieur) : le statut reste inchangé, mais la liste admin peut signaler les anomalies (post-MVP).
- Tentative de validation par un compte ayant à la fois créé et "co-créé" la source : la règle serveur stricte est `verified_by != captured_by`.
- Source identique avec deux pages différentes (page=12 vs page=27) : considérées comme deux sources distinctes (clé de doublon = URL canonique + page).
- URL sans schéma (manque `https://`) : la canonicalisation injecte `https://` par défaut.
- URL excessivement longue ou contenant des fragments encodés (`#:~:text=...`) : conserver les fragments significatifs (deep-linking F03), retirer uniquement les paramètres de tracking listés.
- Suppression simultanée d'un objet référençant une source `pending` : la source devient supprimable seulement quand toutes les références sont effectivement retirées.
- Modification de plusieurs champs critiques en une même opération : une seule nouvelle version est créée (atomicité transactionnelle).
- Recherche full-text avec accents (français) : la recherche doit être tolérante aux accents.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST exposer un CRUD admin complet sur les sources avec opérations : list (paginée, filtrable, triable), create, read, update, mark-outdated, soft-delete-if-orphan.
- **FR-002**: Le système MUST refuser côté serveur toute validation de source par le créateur lui-même (`verified_by != captured_by`).
- **FR-003**: Le système MUST proposer une opération mark-outdated qui fait passer la source en `outdated`, inscrit un audit log, et déclenche un badge "source obsolète" sur tous les objets dépendants ; aucun statut de publication n'est modifié et les snapshots de candidatures restent immutables (pas de cascade, pas de recompute).
- **FR-004**: Le système MUST exposer un endpoint d'impact analysis retournant les objets dépendants par catégorie (indicateurs, critères, formules, facteurs d'émission, documents requis, référentiels, skills, candidatures) avec compteurs agrégés.
- **FR-005**: Le système MUST fournir une recherche full-text sur `title`, `publisher`, et `notes`, avec tolérance aux accents et classement par pertinence.
- **FR-006**: Le système MUST permettre les filtres liste : statut multi-select, publisher autocomplete, date range de capture, "capté par moi".
- **FR-007**: Le système MUST tenter un appel HEAD HTTP (timeout court) au save d'une source et afficher un warning non bloquant en cas de réponse non 2xx.
- **FR-008**: Le système MUST détecter les doublons par URL canonique (+ page) au save et proposer la réutilisation de l'existante.
- **FR-009**: Le système MUST exposer une page publique read-only `/sources/{id}` accessible sans authentification pour les sources `verified` ou `outdated` (404 pour `pending`), listant les champs publics et un lien vers le document officiel ; la page renvoie un header `X-Robots-Tag: noindex` et aucun sitemap n'est exposé en MVP.
- **FR-010**: Le système MUST exposer une page admin agrégeant les claims non sourcés (`flag_unsourced` de F03) groupés par claim avec compteur et raccourci de création.
- **FR-011**: Le système MUST canonicaliser les URLs au save selon la règle déterministe suivante : (a) schéma forcé en `https://`, (b) host en lower-case, (c) retrait du préfixe `www.`, (d) retrait du slash final sauf pour la racine `/`, (e) retrait des paramètres de tracking `utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`, (f) conservation des fragments deep-link (`#page=`, `#:~:text=`).
- **FR-012**: Le système MUST inscrire un audit log F04 sur chaque opération de mutation (create, update, verify, mark-outdated, delete).
- **FR-013**: Le système MUST appliquer le mécanisme de versioning F04 lorsque les champs critiques (`url`, `version`, `publisher`) d'une source `verified` sont modifiés ; les champs accessoires (`notes`) ne déclenchent pas de nouvelle version.
- **FR-014**: Le système MUST refuser la suppression d'une source référencée par au moins un objet ; la mise en `outdated` reste possible.
- **FR-015**: Le système MUST appliquer le RLS F02 sur tous les endpoints admin et restreindre l'accès aux rôles autorisés ; la page publique reste sans authentification mais ne renvoie que les champs publics.

### Key Entities

- **Source** (table `source`, posée en F03, étendue ici par usage) : entité représentant un document officiel avec URL canonique, titre, publisher, version, date de publication, page, section, notes, statut de vérification (`pending` | `verified` | `outdated`), `captured_by`, `verified_by`, horodatages, version (F04).
- **Dépendances catalogue** : Indicateurs, Critères, Formules, Facteurs d'émission, Documents requis, Référentiels, Skills, Candidatures — tous référencent une ou plusieurs Sources via FK ; ces relations alimentent l'impact analysis.
- **flag_unsourced** (F03) : enregistrements produits quand le LLM ne peut sourcer un claim ; agrégés par claim pour US6.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: L'équipe ESG Mefali peut saisir 50 sources en une journée de travail (mesure : durée moyenne de saisie d'une source < 6 minutes incluant la double validation).
- **SC-002**: 100% des sources en statut `verified` ont `verified_by != captured_by` (vérifié par requête de cohérence sur tous les enregistrements).
- **SC-003**: Pour 5 sources test à fort impact, l'endpoint d'impact analysis retourne en moins de 500ms et l'admin obtient une réponse cohérente avec la base.
- **SC-004**: La page publique `/sources/{id}` est accessible sans login pour 100% des sources `verified` et `outdated`.
- **SC-005**: La liste des sources se charge en moins d'une seconde pour 5000 sources (page courante de 25/50/100 lignes).
- **SC-006**: Aucun bypass serveur de la double validation détecté lors d'un test de pénétration ciblé (l'API refuse toute tentative de valider sa propre source).
- **SC-007**: Pour les sources `verified` modifiées sur champs critiques, 100% génèrent une nouvelle version selon F04 ; les modifications de `notes` n'en génèrent jamais.

## Assumptions

- La table `source` et ses FK depuis les objets dépendants existent déjà (livrées par F03) ; F07 ne crée aucune nouvelle table.
- Le mécanisme d'audit append-only et le versioning par publication sont disponibles (F04) et utilisés ici sans modification.
- L'authentification, les rôles admin et le RLS sont opérationnels (F02) ; F07 réutilise les rôles existants sans en créer.
- Le squelette back-office (registry, etag, crud_router, publish gate, search, stats) livré par F06 est utilisé comme socle ; F07 ajoute des opérations dédiées (verify, mark-outdated, impact).
- La règle de canonicalisation d'URL est déterministe et stockée comme un utilitaire partagé pour cohérence avec d'éventuels imports futurs.
- L'équipe MVP doit disposer d'au moins deux comptes admin actifs distincts ; aucun mode dégradé ni bypass n'est prévu (décision Clarify Q1).
- L'import en masse CSV, l'archivage Wayback, le hash de contenu et la revalidation périodique sont post-MVP.
- La plateforme reste fermée (US5 page publique exposée mais hors workflow d'inscription ; non indexable activement en MVP, sitemap post-MVP).
