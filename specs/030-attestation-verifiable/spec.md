# Feature Specification: Attestation Vérifiable

**Feature Branch**: `030-attestation-verifiable`
**Created**: 2026-04-29
**Status**: Draft
**Input**: F30 — Attestation Vérifiable. Source: docs_et_brouillons/features/30-attestation-verifiable.md. PME génère une attestation PDF signée Ed25519 avec QR pointant vers une page publique de vérification. Inclut révocation par PME et admin, expiration auto. MVP scope: signature Ed25519, table attestation, génération PDF basique, page publique vérification, révocation. Defer: QR custom polish, frontend riche, intégration F23/F29 enrichie.

## Clarifications

### Session 2026-04-29

- Q: Quels scores sont acceptés à l'inclusion en MVP ? → A: uniquement `solvability` (F29) et `esg_referential_<code>` (F23). `impact` est reporté post-MVP.
- Q: Quel backend de stockage pour le PDF ? → A: filesystem local via le service `app.storage` existant, sous `attestations/<yyyy>/<mm>/<public_id>.pdf` (cohérent F22/F24).
- Q: Quel format de document JSON canonique signé ? → A: JSON UTF-8 trié lexicographiquement sans espaces (équivalent `json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False)`), pas de RFC 8785.

## Contexte

La plateforme ESG Mefali est fermée aux intermédiaires (fund officers, bailleurs). Le partage des scores
de la PME (solvabilité F29, impact/ESG F23) se fait donc par une **attestation vérifiable** que la PME
contrôle et transmet par ses propres canaux. Cette feature livre le socle MVP : génération d'une
attestation PDF signée cryptographiquement (Ed25519), accompagnée d'un QR pointant vers une page
publique en lecture seule, avec un mécanisme de révocation par la PME et par un administrateur. Le
polish frontend, le QR custom et l'intégration enrichie F23/F29 sont reportés.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Générer une attestation signée (Priority: P1)

En tant que **PME** authentifiée, je veux générer une attestation contenant mes scores actuels
(solvabilité, ESG par référentiel sélectionné, impact) avec une durée de validité (3 / 6 / 12 mois,
défaut 6 mois), afin de pouvoir la transmettre à un fund officer.

**Why this priority** : c'est le cœur de la feature. Sans génération, rien d'autre n'a de sens.

**Independent Test** : un appel API `POST /me/attestations` avec une PME valide retourne une
attestation persistée + un fichier PDF téléchargeable et une signature Ed25519 vérifiable.

**Acceptance Scenarios** :

1. **Given** une PME authentifiée disposant de scores calculés, **When** elle demande la génération
   d'une attestation valide 6 mois, **Then** le système crée un enregistrement avec `public_id`,
   `signature_ed25519`, `hash_document`, `valid_until`, et un PDF stocké.
2. **Given** une demande de génération, **When** la PME ne possède pas de scores calculés
   (F23/F29 non exécutés), **Then** le système refuse avec un message explicite et n'insère rien.
3. **Given** une attestation générée, **When** un tiers récupère le document JSON canonique et la
   clé publique, **Then** il peut vérifier la signature avec une bibliothèque Ed25519 standard.

---

### User Story 2 — Vérifier l'authenticité via une page publique (Priority: P1)

En tant que **destinataire** de l'attestation (fund officer, partenaire), je veux scanner le QR code
ou ouvrir l'URL et voir une page publique sans authentification qui affiche le statut, les scores et
les dates de validité, afin de me convaincre de l'authenticité du document.

**Why this priority** : sans vérification publique, la signature Ed25519 n'est pas exploitable par
les destinataires.

**Independent Test** : un appel `GET /verify/{public_id}` (non authentifié) retourne le statut
(active/expirée/révoquée), la date d'émission, l'expiration, le hash document, le nom de la PME et
la liste des scores. Un endpoint `GET /verify/_pubkey` expose la clé publique en hex.

**Acceptance Scenarios** :

1. **Given** une attestation active, **When** un visiteur non connecté ouvre `/verify/{public_id}`,
   **Then** il voit `status=active`, dates, scores et un lien de téléchargement du PDF original.
2. **Given** une attestation révoquée, **When** un visiteur ouvre la page publique, **Then** elle
   affiche `status=revoked` et la date de révocation (sans motif PII brut).
3. **Given** une attestation expirée, **When** la page est consultée, **Then** elle affiche
   `status=expired` et la date d'expiration.

---

### User Story 3 — Révocation par la PME (Priority: P1)

En tant que **PME** émettrice, je veux révoquer une attestation que j'ai émise (changement majeur
de profil, erreur), afin que les destinataires en cours de vérification voient un statut révoqué.

**Why this priority** : la révocation est un garde-fou indispensable pour la confiance ; sans elle,
une donnée périmée resterait valide jusqu'à expiration.

**Independent Test** : `POST /me/attestations/{id}/revoke` met `revoked_at`, `revoked_by`,
`revoked_reason` et la page publique reflète le statut immédiatement.

**Acceptance Scenarios** :

1. **Given** une attestation active de la PME, **When** elle appelle l'endpoint de révocation avec
   un motif, **Then** l'enregistrement est mis à jour et un événement audit append-only est inscrit.
2. **Given** une attestation déjà révoquée, **When** la PME tente de la révoquer à nouveau,
   **Then** le système répond une erreur idempotente (409) sans modifier l'enregistrement.
3. **Given** une attestation appartenant à une autre PME, **When** la PME tente de la révoquer,
   **Then** le système renvoie 404 (RLS appliquée).

---

### User Story 4 — Révocation par un admin (Priority: P1)

En tant qu'**admin** de la plateforme, je veux pouvoir révoquer une attestation en cas d'incident
(fraude, donnée frauduleuse) avec motif, afin de protéger les destinataires. Cette action est
journalisée dans l'audit log.

**Why this priority** : F10 (support admin) référence déjà ces hooks (`revoked_at/by/reason`).

**Independent Test** : `POST /admin/attestations/{id}/revoke` met à jour l'attestation et inscrit
deux événements audit (`source_of_change='admin'`).

**Acceptance Scenarios** :

1. **Given** une attestation active d'une PME, **When** un admin révoque avec motif,
   **Then** l'enregistrement passe en révoqué et l'audit log porte `actor_role=admin`.
2. **Given** un utilisateur non admin, **When** il appelle l'endpoint admin de révocation,
   **Then** le système renvoie 403.

---

### User Story 5 — Historique des attestations (Priority: P2)

En tant que **PME**, je veux lister mes attestations passées et présentes (active, expirée,
révoquée) avec leurs dates et scores, afin de garder une trace.

**Independent Test** : `GET /me/attestations` retourne la liste paginée des attestations de la PME.

**Acceptance Scenarios** :

1. **Given** une PME ayant émis 3 attestations dont 1 expirée et 1 révoquée, **When** elle appelle
   l'endpoint, **Then** la réponse contient les 3 entrées avec leur statut calculé.

---

### User Story 6 — Expiration automatique (Priority: P2)

En tant que **système**, je dois marquer comme expirées les attestations dont `valid_until` est
dépassé, afin que la page publique reflète le bon statut sans intervention manuelle.

**Independent Test** : un job exécutable manuellement (`expire_attestations`) traite les attestations
en retard et la page publique passe en `expired`.

**Acceptance Scenarios** :

1. **Given** une attestation dont `valid_until` est passé d'un jour, **When** le job s'exécute,
   **Then** la page publique affiche `expired` (statut calculé à la lecture, le job sert
   principalement aux notifications futures).

---

### Edge Cases

- Une PME tente de générer une attestation alors qu'aucun score n'est calculé : refus 422.
- Une attestation est demandée pour téléchargement après révocation : le PDF original reste
  téléchargeable mais la page publique signale clairement la révocation.
- Le `public_id` fourni est inconnu : 404 sans fuite d'information.
- La clé privée n'est pas configurée au démarrage : refus 503 au moment de la génération avec
  message explicite côté logs serveur, et message générique côté API.
- Un `revoked_reason` contient des PII : la page publique n'expose pas ce motif brut, seulement la
  date de révocation. Le motif reste visible côté admin et audit log.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** : Le système MUST persister chaque attestation avec, au minimum :
  identifiant interne (UUID), `account_id`, `entreprise_id`, snapshot JSON canonique des scores
  inclus avec versions des référentiels, chemin du PDF généré, `public_id` (UUID public exposé sur
  `/verify/`), signature Ed25519 (hex), empreinte de la clé publique utilisée, hash sha256 du
  document JSON canonique, dates `generated_at`, `generated_by`, `valid_until`, et trois colonnes
  nullables `revoked_at`, `revoked_by`, `revoked_reason`, plus un compteur de version (cohérence F04).
- **FR-002** : Le système MUST exposer `POST /me/attestations` (PME authentifiée) qui prend les
  scores à inclure (en MVP : `solvability` et/ou `esg_referential_<code>` ; `impact` reporté
  post-MVP) et la durée de validité (3 / 6 / 12 mois, défaut 6) et retourne l'attestation créée
  avec `public_id`, signature et URL de téléchargement.
- **FR-003** : Le système MUST exposer `GET /me/attestations` paginé pour l'historique d'une PME et
  `GET /me/attestations/{id}/download` pour récupérer le PDF original.
- **FR-004** : Le système MUST exposer `POST /me/attestations/{id}/revoke` (PME) et
  `POST /admin/attestations/{id}/revoke` (admin) avec motif obligatoire ; chaque révocation
  produit deux entrées dans `audit_log` (cohérent F04) avec `source_of_change` adéquat.
- **FR-005** : Le système MUST exposer `GET /verify/{public_id}` non authentifié qui retourne
  un payload JSON minimal (statut, dates, nom PME déclaratif, scores avec versions de référentiels,
  hash document, lien PDF) et `GET /verify/_pubkey` qui retourne la clé publique Ed25519 hex.
- **FR-006** : Le système MUST signer un document JSON canonique (clés triées lexicographiquement,
  séparateurs `,` et `:` sans espaces, encodage UTF-8 sans `ensure_ascii`) avec une clé privée
  Ed25519 chargée depuis une variable d'environnement `ATTESTATION_PRIVATE_KEY` et MUST refuser de
  générer si la clé est absente.
- **FR-007** : Le système MUST générer un PDF basique contenant : entête (nom PME, date émission,
  identifiant unique, validité), bloc scores avec versions des référentiels, QR code pointant vers
  l'URL publique `/verify/{public_id}`, et signature Ed25519 visible (hex tronqué) en pied de page.
  Le PDF est persisté via le service `app.storage` existant sous
  `attestations/<yyyy>/<mm>/<public_id>.pdf`.
- **FR-008** : Le système MUST appliquer la RLS existante sur les endpoints PME (`/me/...`) — une
  PME ne voit que ses attestations — et MUST exiger le rôle admin sur l'endpoint admin.
- **FR-009** : Le système MUST permettre la vérification externe : un script Python ou Node
  utilisant la clé publique exposée par `/verify/_pubkey` doit pouvoir vérifier la signature du
  document JSON canonique sans dépendance interne (Ed25519 standard ouvert).
- **FR-010** : Le système MUST calculer le statut (`active`/`expired`/`revoked`) à la lecture, en
  comparant `valid_until` à `now()` et en regardant `revoked_at`. Un job optionnel
  `expire_attestations` peut journaliser les passages d'état pour les notifications futures (post-MVP).
- **FR-011** : Le système MUST inscrire dans `audit_log` les événements `attestation.generated`,
  `attestation.revoked` (PME et admin) en cohérence avec F04 (append-only, snapshot before/after).
- **FR-012** : Le système MUST limiter l'accès à `/verify/{public_id}` par un rate-limit (au moins
  60 req/min/IP) afin de prévenir le scraping/brute-force d'UUID.

### Key Entities

- **Attestation** : représente une attestation signée émise par une PME pour un ensemble de scores
  à un instant donné. Contient l'empreinte signée du document et le PDF généré. Reliée à un compte
  (account) et une entreprise. Statut dérivé (active/expirée/révoquée).
- **Clé publique de signature** : ressource statique exposée publiquement, permettant la
  vérification externe de toute signature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Une PME peut générer une attestation et obtenir le PDF téléchargeable en moins de
  5 secondes (P95 sur 100 générations).
- **SC-002** : Un destinataire ouvrant la page publique voit le statut correct (active/expirée/
  révoquée) en moins d'une seconde après chargement initial.
- **SC-003** : Un script externe disposant de la clé publique vérifie 100 % des signatures
  produites (test reproductible).
- **SC-004** : 100 % des révocations se reflètent sur la page publique au plus tard à la requête
  suivante (pas de cache > 5 s).
- **SC-005** : Couverture de tests ≥ 80 % sur les modules signature et vérification.

## Assumptions

- Les scores F23 (ESG multi-référentiels) et F29 (credit scoring) sont déjà calculables pour la
  PME ; cette feature lit ces scores via les services existants. L'intégration enrichie est reportée.
- La signature Ed25519 vaut comme **preuve d'intégrité technique**, pas comme signature
  électronique réglementée (eIDAS/UEMOA). Cela est documenté dans le PDF.
- La clé privée Ed25519 est stockée dans une variable d'environnement (pas de KMS en MVP). Une
  procédure de rotation sera documentée mais non automatisée.
- La page publique est non indexable (robots.txt `Disallow`), accessible uniquement par UUID
  partagé hors-bande.
- Un seul couple de clés actif en MVP. Le `pubkey_fingerprint` est stocké pour préparer la rotation
  future, mais une seule clé est servie par `/verify/_pubkey`.
- Le PDF MVP utilise un template simple (texte + QR) ; le polish typographique est reporté.
- Pas de notification automatique aux destinataires lors d'une révocation (post-MVP).
- Le frontend Nuxt riche (page `/verify/[public_id]` polish, page PME `/profil/attestations`) est
  reporté ; le MVP livre les endpoints API et un rendu HTML serveur minimal pour `/verify`.
- Tools LLM (`generate_attestation`, `revoke_attestation`) reportés post-MVP.
- Le scope F26 (intégration au dossier de candidature) et F32 (dashboard PME) ne sont pas touchés.

## Out of Scope (MVP)

- PKI complexe (CA, certificats X.509) — Ed25519 simple suffit.
- Rotation automatisée des clés.
- Watermarking PDF anti-photocopie.
- Notifications aux destinataires.
- Vérification offline (sans Internet).
- Multi-langue (FR uniquement, EN reporté).
- Tools LLM d'attestation.
- Frontend Nuxt riche.
