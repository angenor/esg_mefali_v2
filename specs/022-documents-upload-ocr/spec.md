# Feature Specification: Documents Upload & OCR

**Feature Branch**: `022-documents-upload-ocr`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "F22 — Upload & OCR de Documents (FR/EN) + Extraction LLM. MVP P1 backend: endpoint upload entreprise documents (multipart, 25MB max, types PDF/images/Word/Excel), table document_entreprise (parallèle à document_projet F12), OcrService basique (PDF text natif), audit log, RLS account_id. Réutiliser storage abstraction F12. DEFERRED: tesseract OCR images, replicate, extraction LLM structurée, embedding Voyage AI, surlignage bbox, audio Whisper."

## Clarifications

### Session 2026-04-29

- Q: Liste exacte des mime types autorisés à l'upload ? → A: `application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- Q: Backend de stockage en MVP ? → A: Réutiliser sans modification l'abstraction de stockage F12 (filesystem local en dev, object store via interface commune en prod).
- Q: Traitement OCR/extraction synchrone ou asynchrone ? → A: Synchrone, time-boxé à 30 secondes ; au-delà le statut bascule à `failed` avec message d'erreur.
- Q: Politique de suppression des documents ? → A: Soft-delete (colonne `deleted_at` mise à `now()`) + suppression best-effort du fichier physique, par cohérence avec F12 et pour traçabilité d'audit ; les documents soft-deletés sont exclus de tous les endpoints utilisateurs.
- Q: Pagination sur le listing ? → A: Pas de pagination en MVP (cap dur 50 docs par entreprise rend l'utilité marginale) ; tous les documents sont retournés.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Uploader un document d'entreprise (Priority: P1)

En tant que PME connectée, je peux uploader un document lié à mon entreprise (statuts juridiques, KBIS, rapport d'activité, etc.) via un endpoint API afin que ce document soit stocké de manière sécurisée et associé à mon compte.

**Why this priority**: Sans cette capacité, aucune des fonctionnalités d'analyse documentaire (extraction LLM, scoring ESG, génération de dossiers) ne peut fonctionner. C'est la base qui débloque le reste du module 2.

**Independent Test**: Authentifier une PME, envoyer un PDF de moins de 25 MB en multipart vers l'endpoint d'upload entreprise, recevoir un identifiant de document, puis interroger l'endpoint de listing et vérifier que le document apparaît avec ses métadonnées.

**Acceptance Scenarios**:

1. **Given** une PME authentifiée avec son entreprise déjà créée, **When** elle uploade un PDF valide de 2 MB de type "statuts", **Then** le système enregistre le document, retourne 201 avec l'identifiant, et le document apparaît dans la liste des documents de l'entreprise.
2. **Given** une PME authentifiée, **When** elle uploade un fichier de plus de 25 MB, **Then** le système refuse avec une erreur 413 et un message clair.
3. **Given** une PME authentifiée, **When** elle uploade un fichier de type non supporté (ex: .exe), **Then** le système refuse avec une erreur 415 et la liste des types autorisés.
4. **Given** une PME A propriétaire d'un document, **When** une PME B authentifiée tente d'accéder au document de A via son identifiant, **Then** le système répond 404 (isolation par compte).

---

### User Story 2 - Lister, télécharger et supprimer ses documents (Priority: P1)

En tant que PME, je peux lister les documents que j'ai uploadés pour mon entreprise, télécharger leur contenu original, et les supprimer si je me suis trompée.

**Why this priority**: Sans listing/download, l'upload est aveugle. Sans suppression, l'utilisateur n'a pas le contrôle minimal RGPD attendu.

**Independent Test**: Après avoir uploadé deux documents, lister, télécharger l'un d'eux (vérifier le contenu binaire), supprimer l'autre, lister à nouveau et vérifier qu'il ne reste plus qu'un seul document.

**Acceptance Scenarios**:

1. **Given** une PME ayant trois documents, **When** elle appelle GET sur l'endpoint de listing, **Then** elle reçoit les trois documents avec nom, type, taille, date d'upload et statut OCR.
2. **Given** un document existant, **When** la PME demande son téléchargement, **Then** elle reçoit le fichier binaire d'origine avec le bon mime type.
3. **Given** un document existant, **When** la PME le supprime, **Then** le document disparaît de la liste, le fichier sous-jacent est effacé du stockage, et un événement d'audit est enregistré.

---

### User Story 3 - Extraction de texte basique sur PDF natifs (Priority: P1)

En tant que PME, lorsque j'uploade un PDF qui contient du texte natif (non scanné), je veux que le système en extraie automatiquement le contenu textuel afin que ce texte soit disponible pour les fonctionnalités ultérieures (extraction LLM, recherche, scoring).

**Why this priority**: La majorité des documents administratifs récents en Afrique de l'Ouest sont des PDF natifs (générés par Word, par les greffes, par les banques). Couvrir ce cas couvre 60-70 % du volume sans dépendance OCR lourde.

**Independent Test**: Uploader un PDF natif connu, attendre la fin du traitement synchrone, interroger l'endpoint de détail du document et vérifier que le champ de texte extrait contient au moins les phrases attendues du PDF source.

**Acceptance Scenarios**:

1. **Given** un PDF natif de 3 pages, **When** la PME l'uploade, **Then** à la fin de l'upload le document a un statut "done" et son texte extrait est non vide et contient les mots clés présents dans le PDF.
2. **Given** un PDF scanné (image only) ou une image JPG, **When** la PME l'uploade, **Then** le document est accepté et stocké, le statut OCR est marqué "deferred" (extraction d'image non disponible en MVP) avec un message explicatif, sans erreur bloquante.
3. **Given** un fichier Word ou Excel uploadé en MVP, **When** le traitement se déclenche, **Then** le document est stocké, le statut OCR est marqué "deferred" avec un message explicatif, le fichier reste téléchargeable.

---

### Edge Cases

- Upload interrompu en cours (réseau coupé) : le document partiel ne doit pas apparaître dans le listing, ni occuper d'espace.
- Fichier au mime type valide mais corrompu (PDF illisible) : statut OCR passe à "failed" avec un message d'erreur lisible, le document reste consultable et téléchargeable.
- Plus de 50 documents déjà associés à l'entreprise : nouvel upload refusé avec un message clair.
- Nom de fichier contenant des caractères dangereux (path traversal, slashes) : nom assaini avant stockage, le nom d'origine reste affiché à l'utilisateur.
- Suppression simultanée d'un document par deux requêtes : la seconde retourne 404 sans erreur 500.
- Compte sans entreprise associée tente d'uploader : refus 400 avec message clair.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT permettre à une PME authentifiée d'uploader un document associé à son entreprise via un appel multipart, avec un type de document choisi parmi une liste fermée (statuts, rapport_activite, facture, contrat, politique, autre).
- **FR-002**: Le système DOIT refuser tout upload supérieur à 25 mégaoctets avec une erreur explicite.
- **FR-003**: Le système DOIT refuser tout upload dont le mime type n'appartient pas à l'ensemble autorisé : `application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (.docx), `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (.xlsx).
- **FR-004**: Le système DOIT limiter à 50 le nombre de documents simultanément associés à une même entreprise.
- **FR-005**: Le système DOIT stocker chaque document avec ses métadonnées : nom d'origine, mime type, taille, type de document, identifiant de l'entreprise, identifiant du compte, identifiant de l'utilisateur uploadeur, horodatage, chemin de stockage, statut de traitement OCR.
- **FR-006**: Le système DOIT garantir l'isolation des documents par compte : aucun appel ne doit révéler l'existence ou le contenu d'un document appartenant à un autre compte.
- **FR-007**: Le système DOIT proposer un endpoint de listing qui ne renvoie que les documents du compte appelant pour l'entreprise visée.
- **FR-008**: Le système DOIT proposer un endpoint de téléchargement qui retourne le fichier original avec son mime type d'origine, uniquement si le document appartient au compte appelant.
- **FR-009**: Le système DOIT proposer un endpoint de suppression qui efface l'enregistrement et le fichier sous-jacent, uniquement si le document appartient au compte appelant.
- **FR-010**: Le système DOIT, à l'upload d'un PDF, tenter une extraction de texte natif et stocker le texte obtenu si elle réussit ; en cas d'échec ou de PDF sans texte natif, le statut OCR DOIT être marqué "deferred" ou "failed" sans bloquer l'upload.
- **FR-011**: Pour les types non couverts par l'extraction MVP (images, Word, Excel), le système DOIT marquer le statut OCR "deferred" et conserver le document utilisable pour téléchargement.
- **FR-012**: Le système DOIT enregistrer dans le journal d'audit chaque création, téléchargement et suppression de document avec acteur, action, ressource, horodatage.
- **FR-013**: Les noms de fichiers fournis par l'utilisateur DOIVENT être assainis avant d'être utilisés comme chemin de stockage, sans altérer le nom affiché à l'utilisateur.
- **FR-014**: Le système DOIT exposer le statut de traitement (pending, done, deferred, failed) et le message d'erreur éventuel sur l'endpoint de détail du document.
- **FR-015**: Le traitement OCR/extraction de texte DOIT être exécuté de manière synchrone à l'upload, time-boxé à 30 secondes ; au-delà de ce délai le statut DOIT passer à `failed` avec un message explicite.
- **FR-016**: La suppression d'un document DOIT être un soft-delete (`deleted_at = now()`) avec suppression best-effort du fichier physique, par cohérence avec F12 ; les documents soft-deletés DOIVENT être exclus de tous les endpoints utilisateurs.
- **FR-017**: L'endpoint de listing DOIT retourner l'ensemble des documents de l'entreprise du compte appelant sans pagination en MVP, le cap de 50 documents par entreprise rendant la pagination superflue.

### Key Entities *(include if feature involves data)*

- **DocumentEntreprise**: représente un document uploadé par une PME et lié à son entreprise. Attributs principaux : identifiant, identifiant du compte propriétaire, identifiant de l'entreprise, nom affiché, nom de fichier d'origine, mime type, taille, type métier (statuts/rapport/facture/...), chemin de stockage, texte extrait éventuel, statut de traitement OCR, message d'erreur éventuel, identifiant de l'utilisateur uploadeur, horodatage de création.
- **AuditEvent** (réutilisé): événement de journal correspondant à chaque action (create/download/delete) sur un DocumentEntreprise.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une PME peut uploader un document de 5 MB et voir l'identifiant retourné en moins de 5 secondes en conditions de réseau standard.
- **SC-002**: 100 % des tentatives d'accès croisé entre comptes (compte B accédant à un document du compte A) retournent un refus, vérifié automatiquement par les tests d'intégration.
- **SC-003**: Pour un PDF natif de moins de 10 pages, le texte extrait couvre au moins 95 % du contenu lisible du document, mesuré sur un échantillon de tests.
- **SC-004**: 100 % des actions de création, téléchargement et suppression de documents apparaissent dans le journal d'audit avec acteur identifié.
- **SC-005**: Toute requête d'upload dépassant la limite de taille ou de type est rejetée en moins de 200 ms sans persister de fichier partiel.

## Assumptions

- L'authentification, le découpage par compte et le journal d'audit sont déjà en place (modules antérieurs F02 et F04) et seront réutilisés tels quels.
- La couche d'abstraction de stockage (filesystem local en dev, à brancher sur un object store en prod) est déjà fournie par F12 et sera réutilisée sans modification.
- La table `document_projet` créée par F12 reste inchangée ; F22 ajoute une table parallèle `document_entreprise`.
- Les documents projet ne sont pas re-traités dans cette feature : F22 ne modifie pas les endpoints `/me/projets/{id}/documents` de F12.
- Le traitement OCR/extraction est synchrone en MVP (pas de file d'attente), acceptable car limité à l'extraction texte natif PDF (rapide).
- L'OCR d'images, l'extraction structurée par LLM, l'embedding sémantique, l'aperçu PDF avec surlignage et la transcription audio sont explicitement reportés à des features ultérieures et restent hors scope ici.
- L'utilisateur sélectionne explicitement le type de document à l'upload (pas de détection automatique en MVP).
- L'interface frontale n'est pas livrée par F22 ; seuls les endpoints backend et leurs tests sont produits, conformément au mode sériel orchestrateur.
