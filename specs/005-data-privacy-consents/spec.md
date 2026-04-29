# Feature Specification: F05 — Conformité Données Personnelles, Consentements & Devises

**Feature Branch**: `005-data-privacy-consents`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F05 — Modules 0.3 (conformité données personnelles RGPD/UEMOA/CI 2013-450) + 0.6 (devises et taux de change). Dépendances : F02, F04. Plateforme fermée PME+Admin (sauf page politique de confidentialité publique).

## Clarifications

### Session 2026-04-29

- Q: Format de l'export utilisateur (FR-002) ? → A: Archive ZIP contenant un fichier JSON par catégorie d'entité, un `manifest.json` (taille, nombre d'éléments, hash SHA-256 par fichier) et un dossier `files/` pour les pièces jointes binaires (documents uploadés).
- Q: Format de l'identifiant pseudonyme utilisé pour le RTBF dans l'audit (FR-015) ? → A: `anon_<HMAC-SHA256(account_id, server_pepper) tronqué 16 caractères hexadécimaux>`. Déterministe, irréversible sans le pepper côté serveur, longueur fixe.
- Q: Mécanisme de jobs programmés pour `purge_pending_deletions`, `refresh_fx_rates` et alertes (FR-004, FR-011, FR-019) ? → A: Ordonnanceur applicatif APScheduler embarqué dans le service backend, avec table `scheduled_job_run` pour idempotence (clé : nom du job + date) et observabilité. Cette feature livre le mécanisme ; F31 le réutilisera ou l'étendra.
- Q: Mécanisme de versioning et de ré-acceptation de la politique de confidentialité (FR-008) ? → A: Entité `privacy_policy_version` versionnée via le helper `publish_new_version` de F04, portant un drapeau `is_major`. Une table `consent_acceptance (account_id, policy_version_id, accepted_at)` enregistre l'acceptation. Au login, si la dernière version `is_major=true` n'a pas été acceptée, l'utilisateur est redirigé vers un écran de ré-acceptation présenté en bottom sheet bloquante.
- Q: Stratégie de suppression effective des données pour respecter NFR-004 et SC-002 ? → A: Stratégie hybride explicite — pour les entités tenant-scoped (projets, candidatures, scores, attestations, documents, consentements, demandes de suppression), `ON DELETE CASCADE` depuis `account` ; pour les entrées de `audit_log` (append-only, F04), seule la colonne identifiant utilisateur est mise à jour vers le pseudonyme conformément à FR-015 (le trigger immutable de F04 doit autoriser explicitement cette colonne) ; pour les FK vers le catalogue partagé (sources, référentiels), aucune action. Un script de vérification post-purge énumère toutes les tables tenant-scoped.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Page « Mes données » avec export et suppression différée (Priority: P1)

Une PME authentifiée accède à `/me/donnees` pour visualiser un résumé de toutes ses données stockées (entreprise, projets, candidatures, scores, attestations, documents, conversations, audit), exporter l'ensemble en JSON (archive ZIP) et déclencher une demande de suppression différée de 30 jours, annulable pendant le délai.

**Why this priority**: Obligation légale (RGPD art. 15, 17, 20 ; loi ivoirienne 2013-450 ; règlement UEMOA 20/2010). Sans cette page, la plateforme ne peut accueillir une PME dans la légalité.

**Independent Test**: Un utilisateur PME se connecte, ouvre `/me/donnees`, voit le résumé agrégé par type d'entité (nombre + dernière modification), télécharge l'export JSON et obtient une archive valide contenant toutes ses entités (sans secret type empreinte de mot de passe ; références anonymisées vers les comptes tiers). Une demande de suppression peut être créée puis annulée dans la fenêtre de 30 jours.

**Acceptance Scenarios**:
1. **Given** une PME avec des projets et candidatures, **When** elle visite `/me/donnees`, **Then** elle voit pour chaque catégorie (entreprise, projets, candidatures, scores, attestations, documents, conversations, audit) le nombre d'éléments et la date de dernière modification.
2. **Given** la même PME, **When** elle clique « Exporter », **Then** le système produit en moins de 30 secondes une archive JSON téléchargeable contenant toutes ses entités, sans empreinte de mot de passe, et où les clés étrangères vers le catalogue partagé (sources, référentiels) sont représentées par leur identifiant et URL et non dupliquées.
3. **Given** la même PME, **When** elle demande la suppression, **Then** son compte passe en statut « suppression demandée » avec une date d'effet à J+30 et un bouton d'annulation reste visible jusqu'à cette date.
4. **Given** une suppression demandée non annulée, **When** J+30 est atteint, **Then** un job programmé supprime définitivement toutes les lignes liées à ce compte, supprime les fichiers physiques associés, révoque les attestations actives, invalide les jetons de rafraîchissement et un script de vérification confirme zéro ligne résiduelle.

---

### User Story 2 — Consentements granulaires par usage (Priority: P1)

Une PME accède à `/me/consentements` pour activer ou retirer indépendamment chaque consentement non essentiel : analyse des flux Mobile Money, traitement de photos d'exploitation, génération automatique d'attestation publique, conservation d'historique de conversation au-delà de 90 jours, communication marketing. Lorsqu'une fonctionnalité requiert un consentement absent, l'action est bloquée et un message d'invitation à activer le consentement est affiché.

**Why this priority**: Base légale du traitement. Sans consentement granulaire, plusieurs modules métiers (F28, F29, F30) ne peuvent traiter aucune donnée et la conformité RGPD est cassée.

**Independent Test**: Un utilisateur visite `/me/consentements`, voit la liste des consentements et leur état, désactive « Mobile Money », tente une action métier qui dépend de ce consentement et constate un blocage avec message clair l'invitant à le réactiver. La réactivation rétablit l'accès.

**Acceptance Scenarios**:
1. **Given** une PME nouvellement inscrite, **When** elle ouvre `/me/consentements`, **Then** seuls les consentements essentiels (contractuels) sont marqués actifs, tous les autres sont inactifs.
2. **Given** un consentement « Mobile Money » inactif, **When** la PME tente une action protégée par ce consentement, **Then** la requête est refusée avec un message structuré indiquant le type de consentement manquant et l'interface affiche une invitation à l'activer.
3. **Given** un consentement actif, **When** la PME le retire, **Then** l'horodatage de retrait est enregistré, les traitements en cours sont stoppés et les données collectées au titre de ce consentement sont marquées pour purge dans les 30 jours.
4. **Given** chaque toggle ou retrait, **When** l'événement survient, **Then** une entrée est ajoutée au journal d'audit avec le type de consentement et l'origine de la modification.

---

### User Story 3 — Politique de confidentialité publique versionnée (Priority: P1)

Tout visiteur (sans authentification) peut consulter `/politique-confidentialite` qui détaille les finalités de traitement, bases légales, catégories de données, destinataires, durées de conservation, droits de la personne concernée et l'email de contact. La page est versionnée : une refonte majeure invalide les consentements requérant ré-acceptation lors de la prochaine connexion.

**Why this priority**: Obligation d'information (RGPD art. 13-14). C'est la seule page publique de la plateforme fermée et elle conditionne la collecte de tout consentement.

**Independent Test**: Un visiteur non authentifié accède à `/politique-confidentialite` et voit le contenu rendu. La page est listée comme indexable dans `robots.txt`. Lorsqu'une nouvelle version majeure est publiée, les PME existantes voient une demande de ré-acceptation à leur prochaine connexion.

**Acceptance Scenarios**:
1. **Given** un visiteur non authentifié, **When** il ouvre `/politique-confidentialite`, **Then** la page s'affiche correctement avec finalités, bases légales, catégories de données, destinataires, durées de conservation, droits, contact `privacy@esg-mefali.com` et numéro de version visible.
2. **Given** une PME ayant accepté la version N, **When** une version N+1 marquée « majeure » est publiée, **Then** au prochain login la PME voit un écran de ré-acceptation listant les changements et ne peut continuer qu'après acceptation.
3. **Given** la page publiée, **When** un robot d'indexation consulte `robots.txt`, **Then** `/politique-confidentialite` est listée comme indexable.

---

### User Story 4 — Type Money typé de bout en bout (Priority: P1)

Tout montant manipulé dans la plateforme (offres, simulateurs, scoring) porte explicitement sa devise via un type structuré `{montant, devise}` avec devise contrainte à une liste fermée (XOF, EUR, USD, GHS, NGN, MAD, GBP). Le frontend dispose d'un composant d'affichage et d'un composable de manipulation cohérents.

**Why this priority**: Évite les bugs de devise muette, permet l'audit financier, prérequis indispensable des fonctionnalités d'offres (F08), simulateur (F27) et scoring (F23).

**Independent Test**: Un développeur peut créer un objet montant avec 1000 et la devise XOF, le sérialiser en JSON `{"amount":"1000","currency":"XOF"}`, le passer au composant d'affichage front qui rend « 1 000 FCFA », et tenter de créer un montant avec une devise hors liste — l'opération échoue avec une erreur de validation claire.

**Acceptance Scenarios**:
1. **Given** un service backend, **When** il sérialise un montant, **Then** la sortie JSON contient explicitement `amount` (chaîne décimale) et `currency` (code ISO de la liste fermée).
2. **Given** un payload entrant avec une devise non supportée, **When** le service le valide, **Then** la validation échoue avec un message d'erreur clair listant les devises acceptées.
3. **Given** un montant `{1000, XOF}`, **When** le composant d'affichage le rend, **Then** l'utilisateur voit « 1 000 FCFA » avec un format conforme à la locale.

---

### User Story 5 — Taux de change avec snapshot quotidien et fallback (Priority: P1)

Le système maintient une table de taux de change (`fx_rate`) alimentée quotidiennement par un fournisseur externe gratuit pour les devises non pegguées (USD, GHS, NGN, MAD, GBP). Le peg fixe FCFA-EUR (655,957) est codé en constante avec une source de référence liée. En cas d'échec d'appel externe, le service continue avec la dernière valeur connue et un incident est consigné.

**Why this priority**: Permet de convertir les montants entre devise PME (FCFA) et devises des fonds (EUR, USD), prérequis du matching et du simulateur.

**Independent Test**: Un appel à la conversion `1000 XOF → EUR` retourne environ 1,524 EUR (peg appliqué). Un appel `1000 XOF → USD` retourne une valeur cohérente avec le snapshot du jour. Si l'API externe est indisponible, le service répond avec la dernière valeur connue et un événement d'incident est journalisé.

**Acceptance Scenarios**:
1. **Given** une demande de conversion XOF → EUR, **When** le service est appelé, **Then** il applique le peg fixe 655,957 (sourcé) et retourne le résultat en moins de 200 ms.
2. **Given** un cron quotidien `refresh_fx_rates`, **When** il s'exécute, **Then** une nouvelle ligne par couple de devises non-pegguées est insérée dans `fx_rate` avec horodatage de capture et l'opération est idempotente sur le même jour.
3. **Given** une indisponibilité de l'API externe, **When** le job s'exécute, **Then** aucune ligne n'est insérée, un incident est consigné et le service de conversion utilise le dernier taux connu sans erreur.
4. **Given** N jours consécutifs sans rafraîchissement réussi (seuil par défaut 7), **When** le seuil est atteint, **Then** une alerte administrateur est déclenchée.

---

### User Story 6 — Affichage parallèle PME / fonds (Priority: P2)

Une PME consultant une offre voit le montant à la fois dans la devise du fonds (EUR ou USD) et dans sa devise locale (FCFA), pour comprendre le pouvoir d'achat réel.

**Why this priority**: Améliore l'expérience mais n'est pas bloquant pour la conformité ni le MVP fonctionnel.

**Independent Test**: Une PME ouvre une offre libellée 10 000 EUR ; le composant d'affichage rend « 10 000 EUR (≈ 6 559 570 FCFA) ».

**Acceptance Scenarios**:
1. **Given** une offre en EUR consultée par une PME, **When** la page s'affiche, **Then** le montant principal est en EUR et la conversion en XOF est rendue à côté avec une étiquette claire.
2. **Given** un montant en USD, **When** la conversion est demandée, **Then** elle utilise le taux du dernier snapshot disponible et l'horodatage de référence est consultable.

---

### User Story 7 — Audit log des consentements et suppressions avec pseudonymisation RTBF (Priority: P2)

Chaque toggle de consentement et chaque demande/annulation de suppression est journalisé dans le journal d'audit append-only (F04) avec l'origine et le type de consentement. Lors de la purge effective d'un compte (J+30), l'identifiant utilisateur dans le journal est remplacé par un identifiant pseudonymisé déterministe afin de préserver l'intégrité append-only tout en respectant le droit à l'oubli.

**Why this priority**: Preuve de consentement à un instant T (obligation RGPD art. 7) et résolution du conflit RTBF vs append-only.

**Independent Test**: Toggler un consentement crée une entrée d'audit avec le bon type. Demander puis annuler une suppression crée deux entrées distinctes. Après purge effective, les anciennes entrées d'audit du compte ont leur identifiant utilisateur remplacé par une chaîne pseudonymisée stable.

**Acceptance Scenarios**:
1. **Given** une PME activant le consentement Mobile Money, **When** l'événement est traité, **Then** une entrée d'audit est créée avec le type de consentement, l'horodatage et l'origine `manual`.
2. **Given** une demande de suppression, **When** elle est créée puis annulée, **Then** deux entrées d'audit distinctes existent, la seconde référençant la première.
3. **Given** la purge effective au J+30, **When** le job s'exécute, **Then** toutes les entrées d'audit historiques portant l'identifiant du compte voient cet identifiant remplacé par un identifiant pseudonyme déterministe et aucune autre colonne n'est modifiée.

---

### Edge Cases

- L'API externe de change est indisponible plusieurs jours consécutifs : le service utilise la dernière valeur connue, journalise un incident à chaque tentative et déclenche une alerte au seuil configuré.
- Un utilisateur tente d'exporter ses données alors qu'une demande de suppression est en cours : l'export reste autorisé jusqu'à J+30.
- Un utilisateur annule une demande de suppression à J+29 : la suppression est annulée, le statut redevient actif et une entrée d'audit le constate.
- Une refonte majeure de la politique de confidentialité est publiée pendant qu'une PME est connectée : à la prochaine requête, la PME est redirigée vers l'écran de ré-acceptation.
- Une devise hors liste fermée arrive dans un payload : la requête est rejetée avec une erreur de validation explicite avant tout traitement.
- Le peg FCFA-EUR doit être modifié exceptionnellement : la constante doit pouvoir être versionnée comme un référentiel via le mécanisme de versioning F04 (validité temporelle du peg dans `fx_rate`).
- Une PME demande la suppression alors qu'elle a des candidatures actives transmises à un intermédiaire : la suppression efface ses données côté plateforme mais le dossier déjà transmis hors plateforme reste hors scope.
- Une attestation publique vérifiable existe au moment de la suppression : elle est révoquée explicitement avant purge.
- Un consentement est retiré alors qu'un traitement asynchrone est en cours : le traitement est interrompu et les artefacts intermédiaires sont marqués pour purge.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT exposer un endpoint authentifié restituant un résumé agrégé des données du compte courant par catégorie (entreprise, projets, candidatures, scores, attestations, documents, conversations, audit) avec nombre d'éléments et date de dernière modification.
- **FR-002**: Le système DOIT permettre à une PME authentifiée d'exporter toutes ses données dans une archive ZIP contenant : un fichier JSON par catégorie d'entité, un `manifest.json` (date de génération, nombre d'éléments et hash SHA-256 par fichier) et un dossier `files/` regroupant les pièces jointes binaires (documents uploadés). L'archive ne contient aucune empreinte de mot de passe ; les clés étrangères vers le catalogue partagé (sources, référentiels) sont représentées par leur identifiant et leur URL canonique sans duplication du contenu partagé.
- **FR-003**: Le système DOIT permettre à une PME de demander la suppression de son compte avec un statut « suppression demandée » et une date d'effet à J+30, ainsi que d'annuler cette demande tant que la date d'effet n'est pas atteinte.
- **FR-004**: Le système DOIT exécuter un job programmé quotidien qui purge effectivement les comptes dont la date d'effet de suppression est atteinte et qui n'ont pas annulé leur demande. Les jobs programmés s'exécutent via un ordonnanceur applicatif (APScheduler) embarqué dans le service backend, avec une table `scheduled_job_run` (clé unique : nom du job + date d'exécution) garantissant l'idempotence et la traçabilité.
- **FR-005**: Le système DOIT persister les consentements en tant qu'entité dédiée portant compte, type de consentement (liste fermée), état d'octroi, horodatage d'octroi, horodatage de retrait nullable et origine de la modification, isolés par compte via le mécanisme multi-tenant.
- **FR-006**: Le système DOIT exposer une page et des endpoints permettant de consulter et basculer chaque consentement individuellement.
- **FR-007**: Le système DOIT bloquer toute action métier dépendant d'un consentement absent avec une réponse structurée indiquant le type de consentement requis, exploitable par l'interface pour afficher une invitation à l'activer.
- **FR-008**: Le système DOIT publier une page de politique de confidentialité accessible sans authentification, versionnée via le mécanisme `publish_new_version` de F04. Chaque version porte un drapeau `is_major`. Une entité `consent_acceptance` enregistre l'acceptation d'une version par un compte. Lors d'une refonte majeure, à la prochaine requête authentifiée d'une PME n'ayant pas accepté la dernière version majeure, le système la redirige vers un écran de ré-acceptation présenté en bottom sheet bloquante.
- **FR-009**: Le système DOIT manipuler tout montant via un type structuré associant montant décimal et devise issue d'une liste fermée, avec validation du couple à l'entrée et sérialisation explicite.
- **FR-010**: Le système DOIT fournir un service de change permettant d'obtenir un taux et de convertir un montant entre deux devises supportées, en appliquant le peg fixe FCFA-EUR sourcé pour ce couple et le dernier taux connu pour les autres.
- **FR-011**: Le système DOIT exécuter un job programmé quotidien et idempotent (via APScheduler + table `scheduled_job_run`) qui rafraîchit la table des taux pour les devises non-pegguées via un fournisseur externe gratuit, en consignant un incident en cas d'échec et en n'écrasant pas la dernière valeur connue.
- **FR-012**: Le système DOIT fournir au frontend un composant d'affichage de montant et un composable de manipulation, cohérents avec le type structuré, supportant l'affichage simple et l'affichage parallèle dans une devise cible.
- **FR-013**: Le système DOIT lire la clé d'API du fournisseur de change et la devise d'affichage par défaut depuis l'environnement.
- **FR-014**: Le système DOIT journaliser dans l'audit append-only chaque toggle de consentement et chaque demande ou annulation de suppression avec l'origine `manual` et le type de consentement le cas échéant.
- **FR-015**: Lors de la purge effective d'un compte, le système DOIT remplacer l'identifiant utilisateur dans toutes les entrées d'audit historiques par un identifiant pseudonyme de la forme `anon_<HMAC-SHA256(account_id, server_pepper) tronqué 16 caractères hexadécimaux>` (déterministe par compte, irréversible sans le pepper côté serveur), sans modifier d'autres colonnes. Le trigger immutable de F04 doit autoriser explicitement la mise à jour de cette unique colonne dans ce contexte de purge.
- **FR-016**: Le système DOIT, lors de la purge, supprimer toutes les lignes des entités tenant-scoped via `ON DELETE CASCADE` depuis `account` (projets, candidatures, scores, attestations, documents, consentements, demandes de suppression, acceptations de politique), supprimer les fichiers physiques associés au compte, révoquer les attestations actives et invalider les jetons de rafraîchissement. Les FK vers le catalogue partagé (sources, référentiels) ne sont pas touchées. Pour `audit_log` (append-only), seul l'identifiant utilisateur est mis à jour conformément à FR-015.
- **FR-017**: Le système DOIT fournir un script de vérification post-purge confirmant qu'aucune ligne ne reste en base avec l'identifiant du compte purgé.
- **FR-018**: Les interfaces de toggle de consentement et de confirmation de suppression DOIVENT utiliser un panneau coulissant depuis le bas (bottom sheet) conformément à l'invariant UI Module 0.
- **FR-019**: Le système DOIT déclencher une alerte administrateur lorsque le rafraîchissement des taux échoue pendant un nombre de jours consécutifs supérieur ou égal à un seuil configurable (par défaut 7).
- **FR-020**: La page de politique de confidentialité DOIT être listée comme indexable dans `robots.txt`.

### Non-Functional Requirements

- **NFR-001**: Tout le trafic en production DOIT utiliser TLS 1.3 avec HSTS activé.
- **NFR-002**: Le chiffrement au repos DOIT s'appuyer sur le chiffrement natif du fournisseur PostgreSQL managé et être documenté dans le README opérationnel.
- **NFR-003**: L'export complet d'un compte de taille typique DOIT s'achever en moins de 30 secondes.
- **NFR-004**: La conversion de montant DOIT répondre en moins de 200 ms en lecture cache.
- **NFR-005**: Aucun secret applicatif ni empreinte de mot de passe NE DOIT apparaître dans l'export utilisateur.
- **NFR-006**: La table des taux DOIT pouvoir être interrogée par toute PME en lecture seule via le mécanisme multi-tenant existant ; les écritures sont réservées au job de rafraîchissement administratif.

### Key Entities

- **Consent** : associe un compte à un type de consentement (liste fermée : `mobile_money`, `exploitation_photos`, `public_attestation`, `long_history`, `marketing`), porte état d'octroi, horodatages d'octroi et de retrait, et origine de la modification.
- **DeletionRequest** : représente une demande de suppression différée d'un compte avec date d'effet à J+30 et état (demandée, annulée, exécutée). Peut être matérialisée comme attribut du compte ou comme entité dédiée selon implémentation.
- **FxRate** : capture le taux entre deux devises à un instant donné avec horodatage de capture ; supporte une période de validité optionnelle pour le peg pour anticiper sa version.
- **PrivacyPolicyVersion** : version publiée de la politique avec numéro, date, drapeau `is_major`, contenu Markdown rendu, créée via `publish_new_version` (F04).
- **ConsentAcceptance** : associe un compte à une `PrivacyPolicyVersion` acceptée avec horodatage. Détermine la nécessité d'un écran de ré-acceptation au login.
- **ScheduledJobRun** : enregistre l'exécution d'un job programmé (nom, date, statut, message d'incident éventuel, identifiant unique nom+date) pour assurer idempotence et observabilité.
- **Money** : type structuré associant montant décimal et devise issue d'une liste fermée. Pas une entité persistée mais un type partagé backend/frontend.
- **AuditEntry (extension)** : ajoute la capacité de référencer un type de consentement pour les événements de consentement, dans le respect de l'append-only et avec pseudonymisation à la purge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME peut télécharger l'export complet de ses données en moins de 30 secondes pour un compte de taille typique (≤ 50 Mo en JSON).
- **SC-002**: Trente jours après une demande de suppression non annulée, un script de vérification confirme zéro ligne restante référant au compte purgé.
- **SC-003**: Lorsqu'un consentement requis est absent, l'action protégée est refusée dans 100 % des cas avec un message structuré exploitable par l'interface, et l'interface propose un parcours d'activation.
- **SC-004**: La conversion `1000 XOF → EUR` retourne environ 1,524 EUR (écart < 0,01 EUR vis-à-vis du peg sourcé) ; la conversion `1000 XOF → USD` retourne une valeur cohérente avec le dernier snapshot quotidien à ±0,5 %.
- **SC-005**: La page de politique de confidentialité est accessible sans authentification et indexable selon `robots.txt`.
- **SC-006**: 100 % des toggles de consentement et des demandes/annulations de suppression apparaissent dans le journal d'audit avec le type et l'origine corrects.
- **SC-007**: En cas d'indisponibilité de l'API externe de change pendant 24 h, le service de conversion répond toujours avec succès en utilisant la dernière valeur connue, sans erreur visible côté utilisateur.

## Assumptions

- L'authentification, la séparation des rôles PME/Admin et l'isolation multi-tenant fournis par F02 sont disponibles et utilisables sans modification.
- Le journal d'audit append-only et le mécanisme de versioning de F04 sont disponibles, avec les helpers `record_audit` et `publish_new_version`.
- Le mécanisme de sourcing obligatoire de F03 est disponible pour lier la constante du peg à une référence officielle (BCEAO ou décret).
- Le mécanisme de jobs programmés (cron Postgres ou ordonnanceur applicatif) requis par les jobs `purge_pending_deletions`, `refresh_fx_rates` et l'alerte administrateur est disponible ou sera fourni dans le cadre de cette feature si F31 n'est pas encore livré.
- L'alias mail `privacy@esg-mefali.com` est configuré côté ops, hors scope code.
- Le fournisseur externe choisi est exchangerate-api.com en tier gratuit ; le seuil d'alerte par défaut pour absence de rafraîchissement consécutif est de 7 jours.
- La liste fermée des devises supportées au MVP est `XOF, EUR, USD, GHS, NGN, MAD, GBP`.
- La liste fermée des types de consentement non essentiels au MVP est `mobile_money, exploitation_photos, public_attestation, long_history, marketing`. Les consentements essentiels (contractuels, exécution du service) sont implicites et toujours actifs.
- La page de politique de confidentialité au MVP est un draft validé en interne ; la validation juridique formelle est un prérequis ops avant mise en production et hors scope code.
- L'invariant UI bottom sheet du Module 0 s'applique à toutes les confirmations sensibles introduites par cette feature.

## Out of Scope (MVP)

- Nomination formelle d'un DPO et registre des traitements complet.
- Purge granulaire fine par catégorie de données ou par âge.
- Standard Contractual Clauses pour transfert hors UE.
- Bandeau cookies (la plateforme ne dépose pas de cookies tiers en MVP).
- API publique d'export pour intégrations tierces.
- Devise d'affichage préférée enregistrée par utilisateur.
- Multi-currency display avancé au-delà de l'affichage parallèle PME ↔ fonds.

## Dependencies

- **F01** : tables et types fondationnels, type `Money` ébauché, `vector(1024)`, healthcheck.
- **F02** : authentification PME/Admin, RLS multi-tenant, middleware `app.current_account_id`.
- **F03** : sources et middleware de validation LLM (utilisé pour lier la source du peg).
- **F04** : audit log append-only (`record_audit`), versioning (`publish_new_version`, `If-Match`), trigger snapshot immutable.
