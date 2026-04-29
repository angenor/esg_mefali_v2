# F30 — Attestation Vérifiable (PDF + signature Ed25519 + QR + page publique + révocation)

**Phase** : 8 — Scoring Crédit Vert (Module 5)
**Modules brainstorm** : 5.3 (Attestation et Certification du Score)
**Dépendances** : F23, F29
**Estimation** : 2 jours

## Contexte et objectif

> **Principe (du brainstorming Module 5.3)** : la plateforme étant **fermée aux intermédiaires**, le partage du score se fait via une **attestation vérifiable** que la PME contrôle et transmet par ses propres canaux (email, portail intermédiaire, dossier de candidature).

**Avantage compétitif majeur** : la PME garde le contrôle total ; le fund officer scanne un QR code pour vérifier l'authenticité — pas besoin de compte ; conformité RGPD/UEMOA simplifiée car pas de partage automatique.

Cette feature livre :
- **Attestation PDF** générée par la PME, contenant ses scores (solvabilité, impact, ESG par référentiel sélectionné) avec versions (F04),
- **Signature numérique Ed25519** (simple, pas besoin de PKI complexe pour MVP),
- **QR code** pointant vers une URL publique de vérification : `https://esg-mefali.com/verify/{attestation_id}`,
- **Page publique de vérification** read-only sans login,
- **Révocation** par la PME ou par un admin (en cas d'incident).

## User Stories

### US1 — Générer une attestation PDF (P1)
**En tant que** PME,
**je veux** depuis `/profil/credit-score` ou `/profil/scoring`, un bouton "Générer attestation" qui me propose de sélectionner :
- les scores à inclure (solvabilité, impact, ESG par référentiel),
- la durée de validité (3 / 6 / 12 mois — défaut 6 mois).

→ qui produit un PDF signé avec QR.

**Test indépendant** : génération → téléchargement PDF + entry dans `/profil/attestations`.

### US2 — Contenu du PDF (P1)
**En tant que** PME / fund officer destinataire,
**je veux** que le PDF contienne :
- entête : logo + nom PME + date émission + identifiant unique + validité,
- scores sélectionnés (solvabilité, impact vert, ESG par référentiel) avec versions des référentiels (F04 badge),
- récapitulatif méthodologique court (1 paragraphe par score),
- **QR code** pointant vers la page de vérification,
- **signature Ed25519 visible** (en pied de page, hex tronqué + lien vers vérification),
- annexe sources (cohérent F03 / F24).

### US3 — Signature numérique Ed25519 (P1)
**En tant que** dev,
**je veux** signer le contenu de l'attestation (hash du PDF ou du document JSON) avec une clé privée Ed25519 stockée côté backend (env var `ATTESTATION_PRIVATE_KEY`),
**afin de** garantir l'authenticité.

**Détails** :
- Génération de la paire de clés en MVP : commande CLI (`backend/scripts/generate_attestation_keys.py`).
- Clé privée gardée hors-git (env), clé publique exposée (`/verify/_pubkey`) pour vérification externe possible.
- Signature stockée en DB et inscrite dans le PDF.

### US4 — QR code vers page publique (P1)
**En tant que** fund officer recevant un PDF,
**je veux** scanner le QR pour atterrir sur une page publique read-only `/verify/{attestation_id}` qui affiche :
- statut : authentique / révoquée,
- date d'émission, date d'expiration,
- nom PME (champ déclaratif non sensible),
- scores et référentiels (sans détails sensibles),
- hash document conforme,
- bouton "Télécharger l'attestation originale" (PDF re-servi).

**Aucune authentification requise.**

**Aucune donnée sensible** au-delà de ce qui figure déjà sur l'attestation.

### US5 — Révocation par la PME (P1)
**En tant que** PME,
**je veux** depuis `/profil/attestations`, pouvoir révoquer une attestation que j'ai émise (changement majeur de profil, erreur),
**afin de** ne pas voir circuler une info périmée.

**Mécanisme** : `revoked_at`, `revoked_by`, `revoked_reason`. La page publique affiche dès lors "Attestation révoquée le YYYY-MM-DD".

### US6 — Révocation par un admin (P1)
**En tant qu'**admin (cohérent F10),
**je veux** pouvoir révoquer une attestation en cas d'incident détecté (donnée frauduleuse, fraude),
**afin de** protéger les destinataires.

**Mécanisme** : tracé en `audit_log` avec motif. La PME est notifiée.

### US7 — Historique attestations (P2)
**En tant que** PME,
**je veux** voir mes attestations (active / expirée / révoquée) avec dates + scores,
**afin de** suivi.

### US8 — Tool LLM `generate_attestation` / `revoke_attestation` (P2)
**En tant que** PME via chat,
**je veux** dire "génère mon attestation" → résultat + QR. "Révoque l'attestation X" (destructif → `ask_yes_no` cohérent F17).

### US9 — Inclusion dans le dossier de candidature (P2)
**En tant que** PME,
**je veux** que F26 (génération dossier) propose d'inclure l'attestation comme annexe,
**afin de** crédibiliser.

## Exigences fonctionnelles

- **FR-001** : Table `attestation` : `id (uuid), account_id, entreprise_id, scores_inclus_json, referentiels_versions_json, file_path (PDF), public_id (uuid public exposé sur /verify/), signature_ed25519 (hex), pubkey_fingerprint, hash_document (sha256), generated_at, generated_by, valid_until, revoked_at NULL, revoked_by NULL, revoked_reason NULL, version`.
- **FR-002** : Service `AttestationService` :
  - `generate(entreprise_id, scores_to_include, valid_for_months) -> Attestation`,
  - calcule scores via F23/F29,
  - construit document JSON canonique (ordre stable des champs),
  - hash sha256 du JSON canonique,
  - signe avec Ed25519,
  - génère PDF avec template Jinja2 + weasyprint (cohérent F24) + QR via `qrcode` lib,
  - persiste.
- **FR-003** : Endpoints :
  - `POST /me/attestations` body `{scores_to_include, valid_for_months}` → génère.
  - `GET /me/attestations` (historique).
  - `GET /me/attestations/{id}/download` (PDF).
  - `POST /me/attestations/{id}/revoke` body `{reason}`.
  - **Public** : `GET /verify/{public_id}` (page Nuxt + endpoint API JSON pour la page).
  - `GET /verify/_pubkey` (clé publique Ed25519 hex).
- **FR-004** : Page Vue publique `/verify/[public_id]` :
  - sans auth, indexable,
  - affiche statut + métadonnées,
  - bouton télécharger PDF.
- **FR-005** : Vérification de signature côté backend : `verify(document_json, signature_hex) -> bool` utilisant `cryptography` (Ed25519) ou `nacl`.
- **FR-006** : Filtre PII sur `revoked_reason` côté admin (ex : pas afficher noms personnels en clair sur la page publique — clarifier).
- **FR-007** : Tools LLM `generate_attestation(scores_to_include?)`, `revoke_attestation(id, reason)` exposés en F14/F17 avec `@destructive` pour le second.
- **FR-008** : Job cron quotidien `expire_attestations` qui passe les attestations expirées à `expired` (statut visible sur page publique).
- **FR-009** : Skill `skill_attestation` (cohérent F21) orchestrant la génération conversationnelle.

## Exigences non-fonctionnelles

- **NFR-001** : Génération attestation < 5s.
- **NFR-002** : Page publique de vérification charge en < 1s.
- **NFR-003** : Signature Ed25519 vérifiable par tout client externe disposant de la clé publique (open source standard).
- **NFR-004** : Aucune donnée sensible (PII fine, contacts, montants) sur l'attestation publique au-delà de ce qui figure déjà.
- **NFR-005** : URL `/verify/{public_id}` indexable robots.txt (ou pas — à clarifier ; recommandation : non indexable pour éviter le scraping massif, mais accessible direct).

## Entités clés

- **Attestation** (FR-001).

## Success Criteria

- **SC-001** : Génération PDF avec QR fonctionnel + signature vérifiable.
- **SC-002** : Page publique `/verify/{id}` affiche correctement (statut, scores, référentiels, dates).
- **SC-003** : Révocation propage immédiatement à la page publique.
- **SC-004** : Vérification signature externe (depuis script Python ou Node) avec clé publique → OK.
- **SC-005** : Expiration auto à la date de validity → page publique mise à jour.

## Hors-scope MVP

- PKI complexe (CA, certificats X.509) — Ed25519 simple suffit MVP.
- Multiples paires de clés (rotation) — clés uniques en MVP.
- Watermarking visible du PDF avec QR additionnel anti-photocopie.
- Notifications aux destinataires si attestation révoquée (post-MVP — comment savoir qui l'a reçue ?).
- Vérification offline (sans Internet) — possible avec clé publique embarquée mais hors-scope.
- Multi-langue de l'attestation (FR par défaut, EN post-MVP).

## Risques et points de vigilance

- **Sécurité de la clé privée** : si elle fuite, toutes les attestations passées sont compromises. Storage env var, accès très restreint. Procédure de rotation à documenter.
- **Snapshots des scores** : l'attestation gel les scores au moment de la génération (cohérent F04 versioning). Si la PME édite son profil ensuite, l'attestation reste valide jusqu'à expiration ou révocation.
- **Page publique = surface d'attaque** : rate-limit fort, no auth, mais aucun action destructive possible. Read-only strict.
- **Scraping de la page publique** : pas de catalogue de toutes les attestations (sécurité par UUID). Pas d'endpoint listing public.
- **Conformité légale** : signature numérique = valeur juridique limitée en MVP. C'est une preuve d'intégrité, pas de signature électronique réglementée (eIDAS / UEMOA). Documenter clairement.
- **Qualité du PDF** : si l'attestation est mal mise en page, elle perd en crédibilité. Investir dans le template (cohérent F24).
