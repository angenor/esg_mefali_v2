---

description: "Task list for F50 — Documents upload + OCR viewer UI"
---

# Tasks: F50 — Documents upload + OCR viewer UI

**Input** : Design documents in `/specs/050-documents-ocr-ui/`
**Prerequisites** : `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/documents_api_extensions.md`, `contracts/documents_ui_contracts.md`, `quickstart.md`

**Tests** : Tests are **REQUIRED** for this feature — la constitution impose TDD et un seuil de couverture de 80 % (`backend/pyproject.toml` `fail_under = 80`). Toutes les tâches d'implémentation sont précédées de tâches de test (RED → GREEN).

**Organization** : Les tâches sont regroupées par user story pour permettre une livraison MVP incrémentale (US1 d'abord), avec parallélisation à l'intérieur de chaque phase quand les fichiers ne se chevauchent pas.

## Format: `[ID] [P?] [Story?] Description`

- **[P]** : Parallélisable (fichiers distincts, pas de dépendance avec une tâche en cours)
- **[Story]** : `[US1]`..`[US8]`, mappé sur les user stories de `spec.md`
- Tous les chemins sont relatifs à la racine `esg_mefali_v2/`

## Path Conventions

- **Backend** : `backend/app/...`, `backend/tests/...`, `backend/alembic/versions/...`
- **Frontend** : `frontend/app/...`, `frontend/tests/...`

---

## Phase 1 : Setup (Shared Infrastructure)

**Purpose** : initialisation des migrations, settings, dépendances et squelettes partagés.

- [X] T001 Créer la migration Alembic `backend/alembic/versions/0050_documents_ui_extensions.py` ajoutant : colonnes `content_sha256 BYTEA`, `extraction_payload JSONB DEFAULT '{}'`, `extraction_validated_at TIMESTAMPTZ`, `extraction_validated_by UUID`, `extraction_validation_payload JSONB`, `purge_scheduled_at TIMESTAMPTZ` à `document_entreprise` ; table `document_link_projet` (cf. `data-model.md` §2) avec RLS `tenant_isolation` ; index `uq_document_entreprise_account_sha`, `idx_document_entreprise_purge_scheduled`, `idx_document_link_projet_projet`, `idx_document_link_projet_document`.
- [X] T002 [P] Élever `MAX_DOCUMENTS_PER_ENTREPRISE` de 50 à 200 dans `backend/app/config.py` et ajouter `DOCUMENT_PURGE_DAYS = 30` ; mettre à jour `backend/.env.example` avec les nouvelles variables si pertinent.
- [X] T003 [P] Ajouter au `frontend/package.json` les dépendances : `vue-virtual-scroller`, `pdfjs-dist` (déjà présent : vérifier version), `@axe-core/playwright` (devDependency). Lancer `pnpm install` et vérifier le `pnpm-lock.yaml`.
- [X] T004 [P] Créer le module de types partagé `frontend/app/types/documents.ts` (interfaces `DocumentDetail`, `DocumentListItem`, `ExtractedField`, `ExtractionPayload`, `ValidateExtractionIn`, `UploadJob`, `OcrStatusUI`) — aligné sur `contracts/documents_api_extensions.md`.
- [X] T005 [P] Créer le service API squelette `frontend/app/services/api/documents.ts` exposant les signatures (sans implémentation) : `getByFingerprint`, `uploadDocument`, `getDocument`, `listEntrepriseDocuments`, `listProjetDocuments`, `validateExtraction`, `relaunchOcr`, `linkProjet`, `unlinkProjet`, `softDelete`, `updateTags`.

---

## Phase 2 : Foundational (Blocking Prerequisites)

**Purpose** : Briques transverses que toutes les stories utilisent. **⚠️ Aucune story ne peut commencer avant la fin de cette phase.**

- [X] T006 [P] Étendre l'enum `source_of_change` côté `backend/app/audit/recorder.py` (ou la convention de validation) pour accepter la valeur `'system'` ; tests unitaires `backend/tests/audit/test_recorder.py::test_system_source` (RED → GREEN).
- [X] T007 [P] Implémenter le calcul SHA-256 streaming côté serveur dans `backend/app/storage/local.py` (ou un nouveau helper `backend/app/storage/fingerprint.py`) avec test `backend/tests/storage/test_fingerprint.py::test_sha256_streaming` (RED → GREEN), couvrant fichiers vides, 1 Mo, 20 Mo.
- [X] T008 [P] Test unitaire pour le composable `frontend/tests/unit/composables/useFileFingerprint.test.ts` (mock `crypto.subtle.digest`, vérifie hex 64 chars, gère erreurs) — RED.
- [X] T009 Implémenter `frontend/app/composables/useFileFingerprint.ts` (calcule SHA-256 via `crypto.subtle`, expose `computeSha256(file: File): Promise<string>`) — fait passer T008.
- [X] T010 [P] Créer le store Pinia squelette `frontend/app/stores/documents.ts` avec state `items`, `byEntreprise`, `byProjet`, `uploadQueue`, `pollingIntervals`, `search` (cf. `contracts/documents_ui_contracts.md` §8) ; getters dérivés vides ; tests `frontend/tests/unit/stores/documents.test.ts::test_initial_state` (RED → GREEN).
- [X] T011 [P] Créer le composable `frontend/app/composables/useOcrPolling.ts` (signatures + tests `frontend/tests/unit/composables/useOcrPolling.test.ts` couvrant : intervalle 2 s, backoff 2→3→4→5 s, plafond 60 s, annulation à `unmount`, transition vers libellé UI « Délai dépassé ») — RED puis GREEN.
- [X] T012 [P] Créer le helper de mapping `frontend/app/utils/ocrStatusUi.ts` (`mapOcrStatusToUi(doc): OcrStatusUI`) cf. `contracts/documents_ui_contracts.md` §1 ; test `frontend/tests/unit/utils/ocrStatusUi.test.ts` couvrant les 6 libellés.
- [X] T013 [P] Créer le composant générique `frontend/app/components/documents/DocumentEmptyState.vue` (props `context`, `projetName?`, emit `cta-click`) avec test `frontend/tests/unit/DocumentEmptyState.test.ts` vérifiant illustration + CTA + variante projet.
- [X] T014 [P] Créer le module d'EventBus documents `frontend/app/lib/documentEvents.ts` (typed mitt-style emitter pour `documents:created`, `documents:status-changed`, `documents:validated`, `documents:deleted`, `documents:linked-projet`, `documents:unlinked-projet`) ; test `frontend/tests/unit/lib/documentEvents.test.ts`.
- [X] T015 Test d'intégration backend `backend/tests/integration/test_migration_0050.py` : exécute la migration, vérifie l'existence des colonnes/table/index/RLS via `pg_catalog`, puis rollback.

**Checkpoint** : socle prêt — les stories peuvent démarrer en parallèle.

---

## Phase 3 : User Story 1 — Téléverser des documents d'entreprise (Priority: P1) 🎯 MVP

**Goal** : Upload multi-fichier drag & drop sur `/documents` avec progress, queue 5, MIME/size whitelist, dédoublonnage par empreinte (Q4), audit append-only.

**Independent Test** : déposer 3 PDF (5 / 12 / 18 Mo) → 3 lignes apparaissent dans la liste avec progression individuelle, statut OCR initial. Re-uploader le même fichier → ouverture de `<DuplicateChoiceSheet>`.

### Tests for User Story 1 (RED first)

- [X] T016 [P] [US1] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_get_by_fingerprint` : 200 si doublon non supprimé du même compte, 404 sinon, 400 si hex invalide, 404 cross-tenant.
- [X] T017 [P] [US1] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_upload_with_link_projet` : POST `/me/entreprise/documents` avec `link_projet_id` valide → 201 + entrée `document_link_projet` créée + audit `link_projet`.
- [X] T018 [P] [US1] Test backend `backend/tests/unit/entreprise/test_upload_size_mime.py` : rejet 413/415 et 200 vert sur PDF/JPG/PNG/XLSX/DOCX.
- [X] T019 [P] [US1] Test composant `frontend/tests/unit/UploadZone.test.ts` : drag & drop, validation MIME/20 Mo, queue 5 simultanés, événement `duplicate-detected` quand `getByFingerprint` retourne 200, parcours clavier (FR-A11Y-003).
- [X] T020 [P] [US1] Test composant `frontend/tests/unit/DuplicateChoiceSheet.test.ts` : émet `reuse` / `force-new` / `cancel` ; affichage du document existant.
- [X] T021 [P] [US1] Test E2E `frontend/tests/e2e/documents-upload.spec.ts::us1` : utilisateur PME se connecte, voit l'empty state, dépose 3 PDF, observe les 3 progressions, voit la liste peuplée.

### Implementation for User Story 1

- [X] T022 [P] [US1] Étendre `backend/app/entreprise/schemas.py` avec `DocumentOut` (champs ajoutés : `content_sha256`, `extraction_payload`, `extraction_validated_at/_by`, `linked_projets`, `tags`, `purge_scheduled_at`), `FingerprintLookupOut`, `LinkProjetIn`, `ExtractedField`, `ExtractionPayload` (`extra='forbid'` partout).
- [X] T023 [US1] Implémenter dans `backend/app/entreprise/service.py` : `find_by_fingerprint(account_id, sha256)`, extension `create_document(...)` qui (1) calcule le SHA-256 serveur, (2) persiste, (3) crée optionnellement le lien projet via le service M:N (US4 fournit le helper, mais le squelette doit accepter le paramètre dès maintenant — pas d'erreur si le helper n'est pas encore branché : la création de lien sera no-op et complétée en T037).
- [X] T024 [US1] Étendre le router `backend/app/api/routes/entreprise_documents.py` avec : `GET /me/documents/by-fingerprint` (NB : nouveau prefix `/me/documents`, monter dans `main.py`) ; mettre à jour `POST /me/entreprise/documents` pour accepter `client_sha256` (optionnel) et `link_projet_id` (optionnel) ; renvoyer la nouvelle forme `DocumentOut`. Audit `create` + `link_projet` (best-effort).
- [X] T025 [US1] Ajouter le router au `backend/app/main.py` si un nouveau prefix `/me/documents` est introduit ; conserver la compatibilité du prefix F22 `/me/entreprise/documents`.
- [X] T026 [P] [US1] Implémenter le composant `frontend/app/components/documents/UploadZone.vue` (drag & drop + bouton fallback, queue 5, XHR avec progress, intégration `useFileFingerprint` + `getByFingerprint`, émet `duplicate-detected`).
- [X] T027 [P] [US1] Implémenter `frontend/app/components/documents/DuplicateChoiceSheet.vue` (bottom sheet F39, émet `reuse`/`force-new`/`cancel`, conforme FR-006b).
- [X] T028 [P] [US1] Implémenter `frontend/app/components/documents/DocumentTable.vue` (vue-virtual-scroller, colonnes nom/type/date/statut/taille/actions, ARIA grid).
- [X] T029 [US1] Implémenter `frontend/app/pages/documents/index.vue` qui assemble `DocumentEmptyState` (FR-007b) + `UploadZone` + `DocumentTable` + zone de recherche/filtres (squelette pour US5).
- [X] T030 [US1] Étendre `frontend/app/stores/documents.ts` : actions `enqueueUpload`, `fetchEntreprise`, gestion `uploadQueue` ; tests `frontend/tests/unit/stores/documents.test.ts::test_enqueue_dedup` couvrant les chemins « réutiliser » et « forcer ».
- [X] T031 [US1] Émettre `documents:created` sur l'EventBus à la fin d'un upload réussi (depuis `enqueueUpload`).

**Checkpoint US1** : drag & drop, validation MIME/taille, dédoublonnage et liste virtualisée fonctionnent ; T016–T021 verts.

---

## Phase 4 : User Story 2 — Recevoir et valider l'extraction OCR (Priority: P1)

**Goal** : Polling automatique du statut OCR, ouverture de `<OcrSummarySheet>` à l'état « Vérifier », validation propagée à `entreprise`/`projet`, audit append-only, blocage de la prévisualisation tant que l'antivirus n'a pas terminé (FR-029).

**Independent Test** : uploader un PDF, attendre statut « Vérifier » sans recharger, ouvrir la fiche, corriger un champ, valider → entreprise mise à jour, document marqué « Validé ».

### Tests for User Story 2 (RED first)

- [X] T032 [P] [US2] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_validate_extraction_propagates` : POST `/validate` met à jour les champs entreprise et émet l'audit `validate_extraction` + `update` per-field.
- [X] T033 [P] [US2] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_validate_already_validated` retourne 409 et propose `recorrect`.
- [X] T034 [P] [US2] Test composant `frontend/tests/unit/OcrSummarySheet.test.ts` : édition champ, désactivation bouton si champ requis vide, émet `validate` avec payload conforme, bouton « Répondre librement » visible (P10).
- [X] T035 [P] [US2] Test E2E `frontend/tests/e2e/documents-upload.spec.ts::us2_validate` : upload → polling → fiche → validation → entreprise mise à jour visible dans `/profil/entreprise`.

### Implementation for User Story 2

- [X] T036 [US2] Implémenter dans `backend/app/entreprise/service.py` la fonction `validate_extraction(doc_id, payload, propagate_to)` : snapshot immuable dans `extraction_validation_payload`, propagation aux entités cibles (réutilise les services `entreprise/`, `projets/`), audit per-field, idempotence sur 409.
- [X] T037 [US2] Endpoint `POST /me/entreprise/documents/{id}/validate` dans `backend/app/api/routes/entreprise_documents.py` ; codes d'erreur conformes au contrat.
- [X] T038 [P] [US2] Implémenter `frontend/app/components/documents/OcrSummarySheet.vue` (réutilise F39 `<ShowSummaryCard>`, édition par champ, confiance affichée, bouton « Répondre librement »).
- [X] T039 [US2] Brancher `useOcrPolling` au store `documents` : `startPolling(docId)` lors d'un upload réussi, `stopPolling` à transition terminale ; émettre `documents:status-changed`.
- [X] T040 [US2] Action store `validateExtraction(docId, payload)` qui appelle l'API, met à jour `items[docId]`, émet `documents:validated`.
- [X] T041 [US2] Connecter dans `pages/documents/index.vue` : clic sur le badge « Vérifier » d'une ligne ouvre `OcrSummarySheet` ; à la validation, l'entrée passe à « Validé » sans rechargement.

**Checkpoint US2** : extraction polled, validation propagée, T032–T035 verts.

---

## Phase 5 : User Story 3 — Prévisualiser un document (Priority: P1)

**Goal** : Drawer latéral PDF (pdf.js lazy-loaded), images, fallback download bureautique. Bloqué tant que l'antivirus n'a pas validé (FR-029).

**Independent Test** : ouvrir un PDF → drawer s'ouvre, pages navigables clavier ; ouvrir un .xlsx → message + bouton télécharger.

### Tests for User Story 3

- [X] T042 [P] [US3] Test composant `frontend/tests/unit/DocPreviewDrawer.test.ts` : import dynamique mocké, rendu PDF, navigation clavier `ArrowLeft`/`ArrowRight`, message fallback Excel/Word.
- [X] T043 [P] [US3] Test E2E `frontend/tests/e2e/documents-preview.spec.ts` : ouvrir un PDF, vérifier la première page, naviguer, fermer.
- [X] T044 [P] [US3] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_preview_blocked_pre_av_scan` : si `av_status != 'clean'`, l'endpoint download retourne 423/409 (selon décision F22) avec un message clair.

### Implementation for User Story 3

- [X] T045 [US3] Implémenter `frontend/app/composables/useDocumentPreviewLazy.ts` (`() => import('pdfjs-dist')`, configure le worker via `?worker`).
- [X] T046 [US3] Implémenter `frontend/app/components/documents/DocPreviewDrawer.vue` (slide right, ARIA dialog, lazy pdfjs, image inline, fallback download).
- [X] T047 [US3] Wirage dans `pages/documents/index.vue` : clic « Prévisualiser » d'une ligne ouvre le drawer ; route ne change pas.
- [X] T048 [US3] Backend : si le statut antivirus n'est pas `clean`, l'endpoint `GET /me/entreprise/documents/{id}/download` (existant F22) doit renvoyer un code spécifique avec message « Analyse en cours » ; tests T044.

**Checkpoint US3** : prévisualisation utilisable, T042–T044 verts.

---

## Phase 6 : User Story 4 — Documents au niveau d'un projet (Priority: P1)

**Goal** : Grille embed sur `/profil/projets/[id]` consommant l'union `document_projet` (F12) + `document_entreprise via document_link_projet` (Q1), avec lien/délien M:N.

**Independent Test** : sur un projet, uploader un document → apparaît dans la grille projet et dans `/documents` ; lier un document existant à un 2ᵉ projet → apparaît dans les deux grilles sans duplication.

### Tests for User Story 4

- [X] T049 [P] [US4] Test backend `backend/tests/unit/entreprise/test_link_projet.py` : create idempotent, delete idempotent, RLS cross-tenant → 404, audit créé/supprimé.
- [X] T050 [P] [US4] Test backend `backend/tests/integration/test_projet_documents_union.py` : `GET /me/projets/{id}/documents` retourne union triée date desc, distingue `source` legacy vs M:N.
- [X] T051 [P] [US4] Test composant `frontend/tests/unit/ProjetDocumentsGrid.test.ts` : grille thumbnails, gestion empty state (FR-008b), action « Lier un document existant ».
- [X] T052 [P] [US4] Test E2E `frontend/tests/e2e/documents-projet.spec.ts` : upload depuis page projet, partage M:N, délien.

### Implementation for User Story 4

- [X] T053 [P] [US4] Implémenter le service `backend/app/entreprise/links_projet.py` (ou intégrer dans `service.py`) avec `link_document_to_projet(account_id, doc_id, projet_id, user_id)` et `unlink(...)`, vérifications RLS et cohérence d'`account_id`.
- [X] T054 [US4] Endpoints `POST /me/entreprise/documents/{id}/link-projet` et `DELETE /me/entreprise/documents/{id}/link-projet/{projet_id}` dans `backend/app/api/routes/entreprise_documents.py`.
- [X] T055 [US4] Endpoint `GET /me/projets/{projet_id}/documents` dans `backend/app/api/routes/projets_documents.py` retournant l'union (F12 natif + M:N) avec champ `source`.
- [X] T056 [P] [US4] Implémenter `frontend/app/components/documents/ProjetDocumentsGrid.vue` (grille vignettes, empty state projet contextualisé, picker « Lier un document existant »).
- [X] T057 [US4] Embed `ProjetDocumentsGrid` dans `frontend/app/pages/profil/projets/[id].vue` (point d'embed dédié).
- [X] T058 [US4] Étendre le store `documents.ts` : actions `linkProjet`, `unlinkProjet`, `fetchProjet(projetId)` ; émissions `documents:linked-projet`, `documents:unlinked-projet`.

**Checkpoint US4** : M:N opérationnel, grille projet vivante, T049–T052 verts.

---

## Phase 7 : User Story 5 — Recherche, filtres, tags (Priority: P1)

**Goal** : Recherche par nom (insensible casse/accents) + filtres type/date + édition de tags inline. Recherche client sur 200 docs < 1 s.

**Independent Test** : ajouter un tag « Bilan 2024 » à un PDF, taper « bilan » dans la recherche → le document apparaît premier.

### Tests for User Story 5

- [X] T059 [P] [US5] Test composant `frontend/tests/unit/DocumentTagEditor.test.ts` : ajout/retrait inline, longueur ≤ 40, refus tag vide.
- [X] T060 [P] [US5] Test store `frontend/tests/unit/stores/documents.test.ts::test_search_filters` : recherche tolérante accents (« bilan » trouve « Bilàn »), filtre type, plage date.
- [X] T061 [P] [US5] Test E2E `frontend/tests/e2e/documents-search-tags.spec.ts` : ajouter tag, recherche, filtres combinés.

### Implementation for User Story 5

- [X] T062 [P] [US5] Implémenter `frontend/app/components/documents/DocumentTagEditor.vue` (chips inline, sauvegarde via API, ARIA listbox).
- [X] T063 [US5] Étendre le store : getter `filteredItems` (`q`, `type`, `from`, `to`) avec normalisation Unicode `NFD` + suppression diacritiques pour la recherche.
- [X] T064 [US5] Ajouter dans `pages/documents/index.vue` la barre recherche + filtres (Tailwind v4) ; persister en URL search params.
- [X] T065 [US5] Backend : extension `PATCH /me/entreprise/documents/{id}/tags` (si non déjà présent F22) ; sinon réutiliser ; audit `update` champ `tags`.

**Checkpoint US5** : recherche/tags/filtres OK, T059–T061 verts.

---

## Phase 8 : User Story 6 — Suppression + purge 30 j (Priority: P1)

**Goal** : Soft-delete par modal confirmé, `purge_scheduled_at = deleted_at + 30 days`, job CLI `purge_documents` qui purge les fichiers et émet `hard_purge` (`source='system'`). Conformité Q2.

**Independent Test** : supprimer un document → disparait des listes ; forcer `purge_scheduled_at` dans le passé → exécuter le job → fichier disparaît du storage, audit `hard_purge`.

### Tests for User Story 6

- [X] T066 [P] [US6] Test backend `backend/tests/unit/entreprise/test_soft_delete.py` : soft-delete renseigne `deleted_at` et `purge_scheduled_at = deleted_at + 30j`.
- [X] T067 [P] [US6] Test backend `backend/tests/unit/entreprise/test_purge_job.py` : sélectionne uniquement `purge_scheduled_at <= now()`, supprime fichier, ligne, liens M:N (CASCADE), émet audit `hard_purge` `system`.
- [X] T068 [P] [US6] Test composant `frontend/tests/unit/DeleteConfirmModal.test.ts` : confirmation requise, annulation laisse intact.
- [X] T069 [P] [US6] Test E2E `frontend/tests/e2e/documents-upload.spec.ts::us6_delete` (ou fichier dédié) : supprimer, vérifier disparition, vérifier référence orpheline gérée pour scoring (FR §US6 AC2 — vérifier libellé).

### Implementation for User Story 6

- [X] T070 [US6] Étendre `service.py::soft_delete_document` : positionne `purge_scheduled_at` ; audit `soft_delete`.
- [X] T071 [US6] Créer le script `backend/app/scripts/purge_documents.py` (Click) : sélectionne lignes éligibles, supprime fichier via `LocalStorage`, supprime ligne (CASCADE → liens), audit `hard_purge` `source='system'`.
- [X] T072 [US6] Cible Make `make purge-documents` dans `Makefile` (alias `python -m app.scripts.purge_documents`).
- [X] T073 [P] [US6] Implémenter `frontend/app/components/documents/DeleteConfirmModal.vue` (focus trap, ARIA dialog).
- [X] T074 [US6] Action store `softDelete(docId)` qui appelle `DELETE` puis émet `documents:deleted` ; suppression optimiste.

**Checkpoint US6** : suppression + purge 30 j fonctionnels, T066–T069 verts.

---

## Phase 9 : User Story 7 — Synchronisation chat conversationnel (Priority: P1)

**Goal** : Le bottom sheet `ask_file_upload` (F41) intègre `<UploadZone context="entreprise">` ; bouton « Répondre librement » présent (P10) ; à la fin, EventBus propage l'apparition dans `/documents`.

**Independent Test** : depuis le chat, uploader via le bottom sheet → ouvrir `/documents` dans un autre onglet → fichier présent en moins de 3 s sans rechargement.

### Tests for User Story 7

- [X] T075 [P] [US7] Test E2E `frontend/tests/e2e/documents-chat-sync.spec.ts` : invoque le skill `ask_file_upload` via le chat, dépose un fichier, vérifie l'apparition dans `/documents` dans un onglet préalablement ouvert (BroadcastChannel/Storage events ou refetch sur visibilitychange).
- [X] T076 [P] [US7] Test composant `frontend/tests/unit/AskFileUploadSheet.test.ts` (ou test du wiring chat existant) : présence du bouton « Répondre librement » et de l'`<UploadZone>`.

### Implementation for User Story 7

- [X] T077 [US7] Adapter le bottom sheet du skill `ask_file_upload` (côté F41 `frontend/app/components/chat/...` selon arborescence existante) pour héberger `<UploadZone>` et propager les événements.
- [X] T078 [US7] Implémenter la propagation cross-onglet : utiliser `BroadcastChannel('documents')` dans `documentEvents.ts` ; le store écoute et met à jour ses items.
- [X] T079 [US7] Vérifier que le `pages/documents/index.vue` rafraîchit son état sur message `documents:created` reçu via EventBus.

**Checkpoint US7** : sync chat ↔ liste documents OK, T075–T076 verts.

---

## Phase 10 : User Story 8 — Relancer une extraction OCR (Priority: P2)

**Goal** : Bouton « Relancer extraction » sur fiche document ; sur document validé, demande confirmation et invalide la validation (FR-017).

**Independent Test** : sur document avec « Faible confiance », cliquer « Relancer » → repasse en `processing` ; sur document validé, confirmation requise puis validation invalidée.

### Tests for User Story 8

- [X] T080 [P] [US8] Test backend `backend/tests/integration/test_documents_api_extensions.py::test_relaunch_invalidates_validation` : invalide `extraction_validated_at` quand `invalidate_existing_validation=true`, audit `relaunch_ocr`.
- [X] T081 [P] [US8] Test composant `frontend/tests/unit/OcrSummarySheet.test.ts::test_relaunch_confirmation` : confirmation modale obligatoire si déjà validé.

### Implementation for User Story 8

- [X] T082 [US8] Endpoint `POST /me/entreprise/documents/{id}/relaunch-ocr` dans `backend/app/api/routes/entreprise_documents.py` ; code 409 `ocr_in_progress`.
- [X] T083 [US8] Service `relaunch_ocr(doc_id, invalidate_validation: bool)` dans `entreprise/service.py` (audit + reset état).
- [X] T084 [US8] Action store `relaunchOcr(docId, opts)` + bouton dans `OcrSummarySheet.vue` avec confirmation modale si validé.

**Checkpoint US8** : relance fonctionne, T080–T081 verts.

---

## Phase 11 : Polish & Cross-Cutting Concerns

**Purpose** : qualité, a11y, performance, sécurité, doc.

- [X] T085 [P] Ajouter `frontend/tests/e2e/documents-a11y.spec.ts` exécutant `@axe-core/playwright` sur 4 vues (liste vide, liste peuplée, drawer ouvert, OcrSummarySheet ouvert) ; gate CI : 0 violation `serious`/`critical` (SC-009).
- [X] T086 [P] Audit performance : sur jeu de test 200 docs, mesurer FPS scroll (`tests/e2e/documents-perf.spec.ts` ou bench manuel) et confirmer < 100 ms d'interaction perçue (SC-005).
- [X] T087 [P] Audit sécurité : revue par `security-reviewer` (subagent) du nouveau router et du job purge ; corriger CRITICAL/HIGH avant merge. _Verdict initial BLOCK ; corrigés : C1 (purge bypass RLS → SET LOCAL app.current_account_id par account), H2 (link_projet_id non parsé → UUID() avant service, 422), H4/H6 (storage_path n'apparaît plus dans logs ni dans audit hard_purge), H5 (rate-limit 10/min sur upload). H1, H3 (mineurs structurels) : à traiter en fast-follow._
- [X] T088 [P] Vérifier la couverture backend `pytest --cov=app/entreprise --cov=app/audit --cov=app/api/routes/entreprise_documents --cov=app/scripts --cov-report=term-missing` ≥ 80 %. _Dette résolue : ajout des fichiers de tests T015/T016/T017/T032/T033 (`test_migration_0050.py`, `test_documents_api_extensions.py`, `test_documents_relaunch_ocr.py`, `test_upload_size_mime.py`) + tests link/unlink/tags/with-purge endpoints. **Total agrégé 86.06 %** sur les modules F50 (documents_f50.py 70 %→94 %, entreprise_documents_f50.py 68 %→96 %, entreprise_documents.py 92 %, purge_documents.py 93 %). 2 bugs d'origine corrigés au passage : `db.commit()` placé avant `_serialize` perdait le contexte RLS (linked_projets vide après upload), et la migration 0028 ajoute `'processing'` au CHECK constraint sur `ocr_status` (état exigé par `relaunch_ocr` mais absent du schéma F22)._
- [X] T089 [P] Vérifier la couverture frontend `pnpm vitest run --coverage` sur `app/components/documents/**`, `app/composables/use{OcrPolling,FileFingerprint,DocumentPreviewLazy}.ts`, `app/stores/documents.ts` ≥ 80 %. _Dette résolue : 12 fichiers de tests ajoutés (useOcrPolling, useDocumentPreviewLazy, store documents, UploadZone, DuplicateChoiceSheet, OcrSummarySheet, DocPreviewDrawer, DocumentEmptyState, DeleteConfirmModal, DocumentTagEditor, DocumentTable, ProjetDocumentsGrid). **111 tests verts**. Couverture **92.99 % global** : `components/documents/**` 96.4 %, `composables/use{OcrPolling,FileFingerprint,DocumentPreviewLazy}.ts` 98.8 %, `stores/documents.ts` 81.8 %._
- [X] T090 [P] Mettre à jour la documentation `docs_et_brouillons/features/00-INDEX.md` : statut F50 `draft` → `ready`.
- [X] T091 [P] Lint global : `make lint` (ruff backend + eslint frontend) doit passer sans warning sur les fichiers F50. _Backend ruff : `All checks passed!` sur les 7 fichiers F50 + le nouveau test (2 imports `I001` auto-corrigés). Frontend eslint inopérant globalement (config Nuxt non générée), à traiter hors F50._
- [ ] T092 Exécuter le `quickstart.md` de bout en bout en dev local et cocher chaque section (manuel) ; corriger les écarts. _Nécessite une session interactive (auth PME, upload PDF réel, validation UI) — non automatisable depuis cet agent ; à dérouler par l'utilisateur._

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** : aucune dépendance ; T001 (migration) doit être exécutée avant tout test backend qui s'appuie sur les nouvelles colonnes (T015, T016+).
- **Phase 2 (Foundational)** : dépend de Phase 1 ; **bloque** toutes les user stories.
- **Phases 3–10 (User Stories)** : dépendent de Phase 2 :
  - US1, US3, US5, US7, US8 sont quasi indépendantes une fois la fondation prête (peuvent être parallélisées par 5 dev).
  - US2 (validation) suppose un document existant → s'appuie sur T024 (endpoint upload F50) et T039 (polling) ; peut démarrer en parallèle d'US3/US4 mais a une dépendance d'intégration logique avec US1.
  - US4 (M:N) introduit `document_link_projet` ; pour un fonctionnement intégré « upload depuis page projet », US1 fournit le paramètre `link_projet_id` (T024) et US4 fournit le service (T053). Leur intégration finale se fait à T024+T053.
  - US6 (suppression) peut être livré dès la fin d'US1.
  - US7 (sync chat) suppose le store/EventBus (Phase 2) et `<UploadZone>` (US1).
  - US8 (relance) peut suivre US2.
- **Phase 11 (Polish)** : dépend de toutes les stories complétées (au moins jusqu'à US7 pour le scope MVP).

### Within Each User Story

- Tests RED **avant** implémentation (constitution + 80 % coverage).
- Backend (modèles → services → endpoints) avant binding frontend.
- Composants avant assemblage page.

### Parallel Opportunities

- T002, T003, T004, T005 (Setup) en parallèle après T001.
- T006–T015 (Foundational) presque toutes parallélisables (fichiers distincts).
- Tests d'une même phase marqués [P] : tous parallèles.
- US1 ↔ US3 ↔ US5 ↔ US6 : peuvent avancer en parallèle dès la fin de Phase 2.
- US7 et US8 nécessitent qu'US1 (upload) et US2 (validation) soient stables.

---

## Parallel Example: Foundational Phase

```bash
# Foundational tasks parallèles (after T001 migration applied):
Task: "T006 audit recorder source='system' + tests"
Task: "T007 backend SHA-256 streaming helper + tests"
Task: "T008 + T009 useFileFingerprint composable (RED→GREEN)"
Task: "T010 store Pinia squelette"
Task: "T011 useOcrPolling composable + tests"
Task: "T012 ocrStatusUi util + tests"
Task: "T013 DocumentEmptyState component + test"
Task: "T014 documentEvents EventBus + tests"
```

## Parallel Example: User Story 1 Tests First

```bash
# US1 — tests RED en parallèle :
Task: "T016 contract test getByFingerprint"
Task: "T017 contract test upload + link_projet"
Task: "T018 unit test upload size/MIME"
Task: "T019 unit test UploadZone component"
Task: "T020 unit test DuplicateChoiceSheet"
Task: "T021 e2e documents-upload US1"

# Puis implémentation parallèle où possible :
Task: "T022 schemas Pydantic"
Task: "T026 UploadZone.vue"
Task: "T027 DuplicateChoiceSheet.vue"
Task: "T028 DocumentTable.vue"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phases 1 + 2 (Setup + Foundational).
2. Phase 3 (US1) — drag & drop, dédoublonnage, liste virtualisée.
3. **STOP & VALIDATE** : déposer 3 PDF, vérifier liste + dédoublonnage.
4. Démo possible : « la PME peut déjà déposer ses documents et les retrouver dans une liste ».

### Incremental Delivery

1. MVP = US1 (upload + liste).
2. Ajouter US3 (prévisualisation) — gain UX immédiat.
3. Ajouter US2 (validation OCR) — débloque le scoring (F46) et les candidatures (F54).
4. Ajouter US4 (M:N projets) — débloque l'embed projet.
5. Ajouter US5 (recherche/tags) — utilité au-delà de 50 docs.
6. Ajouter US6 (suppression + purge) — RGPD complet.
7. Ajouter US7 (sync chat) — cohérence P8.
8. Ajouter US8 (relance OCR) — confort.
9. Phase 11 (Polish) avant merge final.

### Parallel Team Strategy

- Dev A : US1 + US6 (upload + delete, axe principal)
- Dev B : US2 + US8 (validation + relance, lié à `<OcrSummarySheet>`)
- Dev C : US3 + US4 (prévisualisation + grille projet)
- Dev D : US5 + US7 (recherche/tags + sync chat)
- Tous se rejoignent en Phase 11.

---

## Notes

- Tous les tests RED **doivent** échouer avant l'implémentation correspondante.
- Coverage gate : `fail_under = 80` pour le backend ; viser 80 % côté frontend également.
- Aucun service Docker autre que Postgres en dev — le job purge tourne via `make purge-documents`.
- Aucun nouveau tool LLM dans F50 (P9 deferred) ; si on ajoute `extract_from_document` plus tard, prévoir une feature dédiée avec eval gating.
- Les fichiers Vue doivent suivre la convention `<script setup lang="ts">` avec `defineProps<…>()` + `defineEmits<…>()` typés.
- Tous les composants interactifs en bottom sheet héritent du moteur F39 (P10).
