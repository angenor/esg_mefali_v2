# F12 — Profil → Projets (CRUD, duplication, statuts, documents projet)

**Phase** : 2 — Profil PME
**Modules brainstorm** : 1.3 (Profilage des Projets Verts) — partie UI/édition
**Dépendances** : F02, F04, F11
**Estimation** : 2 jours

## Contexte et objectif

L'entité **Projet** est l'**objet réel de la candidature au financement**. 0..N par entreprise. Un même projet peut faire l'objet de plusieurs candidatures à des Offres différentes (multi-fonds en parallèle, GCF via BOAD vs GCF via UNDP, etc.). Le matching projet ↔ offre sera traité en F25.

Cette feature livre la **vue Profil → Projets** : liste, création, édition, duplication, suppression, gestion du statut, et upload des documents projet (étude de faisabilité, business plan vert, étude d'impact, lettres de soutien).

## User Stories

### US1 — Lister mes projets verts (P1)
**En tant que** PME,
**je veux** une page `/profil/projets` listant tous mes projets avec colonnes : nom, type d'impact, montant recherché, maturité, statut, dernière modif,
**afin de** avoir une vue d'ensemble.

**Test indépendant** : un compte sans projet voit un état vide avec CTA "Créer mon premier projet vert" ; un compte avec projets voit la liste.

### US2 — Créer un projet (P1)
**En tant que** PME,
**je veux** un bouton "Créer un projet" qui ouvre un formulaire avec sections :
- Identité (nom, description, objectif environnemental),
- Type d'impact (mitigation carbone, adaptation, biodiversité, économie circulaire, eau, énergies renouvelables, agriculture durable, etc. — multi-select),
- Maturité (idéation / pré-faisabilité / pilote / scale / réplication),
- Aspects financiers (montant recherché Money typé, durée, structure : subvention / prêt concessionnel / equity / blending),
- Indicateurs d'impact attendus (tCO2e évitées, emplois verts créés, bénéficiaires, hectares restaurés…),
- Localisation projet (peut différer du siège entreprise),
- Statut initial : brouillon.

**afin de** formaliser un projet finançable.

### US3 — Éditer un projet (P1)
**En tant que** PME,
**je veux** modifier n'importe quel champ d'un projet (provenance + audit log + sync LLM bidirectionnelle, comme F11),
**afin de** affiner mon projet au fil de l'eau.

### US4 — Dupliquer un projet (P2)
**En tant que** PME,
**je veux** un bouton "Dupliquer" qui copie un projet existant (avec suffixe "(copie)" sur le nom et statut "brouillon"),
**afin de** créer rapidement une variante (ex : projet pilote vs projet scale).

### US5 — Supprimer un projet (P2)
**En tant que** PME,
**je veux** supprimer un projet en `brouillon` librement, et un projet avec candidatures avec confirmation explicite ("Ce projet a 2 candidatures en cours — supprimer le projet supprimera aussi les candidatures liées"),
**afin de** garder ma liste propre.

**Garde-fou** : un projet `financé` ou `en exécution` ne peut pas être supprimé sans intervention admin (post-MVP) — en MVP on autorise mais avec double confirmation.

### US6 — Gérer le statut d'un projet (P1)
**En tant que** PME,
**je veux** changer le statut de mon projet : `brouillon` → `en recherche de financement` → `financé` → `en exécution` → `clôturé`,
**afin de** suivre l'avancement.

**Scénarios** :
1. Statuts définis : `brouillon`, `en_recherche_financement`, `finance`, `en_execution`, `cloture`.
2. Transitions libres (pas de workflow strict en MVP), mais auditées.
3. Lorsqu'un projet passe `en_recherche_financement`, il devient candidat au matching de F25.

### US7 — Uploader des documents projet (P1)
**En tant que** PME,
**je veux** attacher des documents au projet : étude de faisabilité, business plan vert, étude d'impact environnemental, lettres de soutien, photos,
**afin de** les avoir disponibles pour les candidatures (F26).

**Test indépendant** : drag & drop ou button d'upload, types acceptés (PDF, Word, Excel, images), taille max 25 MB par fichier, max 50 docs par projet. Stockage local en MVP (chemin fichier en DB), avec préparation MinIO post-MVP.

### US8 — Comportements proactifs du LLM en lien avec les projets (P3)
**En tant que** PME,
**je veux** que le LLM (via F13/F17) puisse :
- détecter dans la description de mon entreprise (F11) des projets verts potentiels et me proposer de les créer,
- reformuler une activité existante en projet finançable (objectifs SMART),
- découper un grand projet en sous-projets adaptés à différentes Offres.

Cette feature livre les **endpoints CRUD** et l'**UI** ; les comportements proactifs viennent de F17/F21 (skill esg_diagnostic).

## Exigences fonctionnelles

- **FR-001** : Table `projet` (déjà créée en F01) enrichie : `id, account_id, entreprise_id (FK), nom, description, objectif_environnemental, types_impact[] (enum/multi), maturite ENUM, montant_recherche_money, duree_mois INT NULL, structure_financement[] (enum), indicateurs_impact_json, localisation_projet_pays_iso2, localisation_projet_ville, statut ENUM, version, created_at, updated_at`.
- **FR-002** : Endpoints REST :
  - `GET /me/projets`, `GET /me/projets/{id}`,
  - `POST /me/projets` (create), `PUT /me/projets/{id}`, `PATCH /me/projets/{id}`,
  - `POST /me/projets/{id}/duplicate`, `DELETE /me/projets/{id}`,
  - `POST /me/projets/{id}/transition?to=...` (changement de statut explicite).
- **FR-003** : Audit log + version optimiste (cohérent F11).
- **FR-004** : Table `document_projet` : `id, projet_id, name, original_filename, mime_type, size_bytes, type ENUM('faisabilite','business_plan','etude_impact','lettre_soutien','photo','autre'), storage_path, uploaded_by, uploaded_at, source_of_change`.
- **FR-005** : Endpoints documents :
  - `POST /me/projets/{id}/documents` (multipart upload),
  - `GET /me/projets/{id}/documents`,
  - `GET /me/projets/{id}/documents/{doc_id}/download`,
  - `DELETE /me/projets/{id}/documents/{doc_id}`.
- **FR-006** : Stockage : `backend/storage/projets/{account_id}/{projet_id}/{doc_id}.{ext}` (gitignored, monté en volume Postgres ? non — directement sur le filesystem du backend). Préparer une couche d'abstraction `Storage` qui pourra basculer sur MinIO/S3 plus tard.
- **FR-007** : Page Vue `/profil/projets` (liste) + `/profil/projets/[id]` (édition) :
  - Liste avec filtres (statut, type d'impact),
  - Édition similaire à F11 (sections, badges de provenance, sync LLM),
  - Section documents (upload, liste, preview pour PDF/images, download, delete).
- **FR-008** : Endpoint `POST /me/projets/{id}/duplicate` → copie tous les champs (sauf id, statut→brouillon, candidatures→non copiées, documents→copiés ou non selon décision ; recommandation : ne pas copier les documents pour éviter des Go de stockage).
- **FR-009** : Synchro temps réel avec LLM (cohérent F11 FR-006).

## Exigences non-fonctionnelles

- **NFR-001** : Upload d'un PDF de 10 MB se termine en < 5s sur connexion FTTH locale.
- **NFR-002** : La liste de projets pagine au-delà de 25 lignes (mais peu probable qu'une PME ait > 50 projets).
- **NFR-003** : Les documents uploadés font l'objet d'un scan antivirus minimal (`clamav` en post-MVP — en MVP, vérification du mime_type et taille suffit).
- **NFR-004** : Les indicateurs d'impact (`indicateurs_impact_json`) sont validés par un schéma JSON strict (enum pour les types, numérique pour les valeurs, unités cohérentes).

## Entités clés

- **Projet** (FR-001) — enrichi.
- **DocumentProjet** (FR-004).

## Success Criteria

- **SC-001** : Une PME crée 3 projets, en duplique un, en supprime un en < 10 min via l'UI.
- **SC-002** : Upload de 5 documents par projet OK, dont au moins 1 PDF, 1 Word, 1 image.
- **SC-003** : Sync LLM bidirectionnelle vérifiée par test d'intégration (édition manuelle → contexte LLM ; mutation LLM → UI temps réel).
- **SC-004** : Suppression d'un projet avec candidatures supprime aussi les candidatures (cascade) et journalise.
- **SC-005** : Le `duplicate` produit un projet identique sauf ID/statut, sans documents copiés.

## Hors-scope MVP

- OCR/extraction LLM des documents projet → F22 (cette feature ne fait qu'**uploader/stocker** ; l'extraction est F22).
- Versioning fin de chaque document (post-MVP).
- Liens entre projets (parent/child, sous-projets) → modèle plat en MVP, on le fera dans F25 si besoin.
- Workflow d'approbation interne (post-MVP).
- Migration vers MinIO/S3 (post-MVP).
- Multilingue de la description (FR uniquement en MVP).

## Risques et points de vigilance

- **Stockage local** : si volume PME augmente, le backend devient lourd. Anticiper la migration MinIO (couche d'abstraction `Storage`).
- **Cascade suppression** : projet → candidatures → snapshot — bien tester que les snapshots des candidatures supprimées sont conservés (peut-être ne pas supprimer les candidatures, juste les marquer `archived`). À clarifier.
- **`indicateurs_impact_json`** : tentation de faire de l'éditeur JSON brut. Préférer un mini éditeur typé (1 ligne = 1 indicateur avec dropdown unité). Sera enrichi par F17/F22.
- **Maturité** : valeurs alignées sur les standards GCF (concept note → feasibility → pilot → scale up → replication). À sourcer (F03/F09).
- **Limite documents** : 50 docs × 25 MB = 1.25 GB par projet ; 50 projets = 62 GB par PME. Pour MVP hackathon OK, mais alerte si plusieurs PME démo.
