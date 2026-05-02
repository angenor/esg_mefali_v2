# F50 — Documents upload + OCR viewer UI (UI de F22)

**Phase** : E — Documents, rapports, attestations
**Modules brainstorm** : 2.2 documents + OCR
**Dépendances** : F36, F37, F38, F39, F40, F22 backend (storage + OCR pipeline)
**Estimation** : 2.5 jours

## Contexte et objectif

Page **`/documents`** + composants embed dans `/profil/projets/[id]` (F43) et chat (F41 `ask_file_upload`). PME upload PDF/images/Excel, reçoit retour OCR/extraction structurée (`<ShowSummaryCard>` F39) qu'elle valide ou corrige. Source critique pour scoring (F46) et candidatures (F54).

## User Stories

- **US1 Liste documents entreprise (P1)** — table : nom, type, date upload, statut OCR, taille, preview.
- **US2 Liste documents projet (P1)** — section dans `/profil/projets/[id]` : grid thumbnails, nom + tags.
- **US3 Drag & drop upload (P1)** — `<UiFileUpload>` F37 plein-page, multi-fichier, MIME whitelist (`.pdf, .jpg, .png, .xlsx, .docx`), max 20 MB par fichier.
- **US4 Progress upload (P1)** — barre par fichier, retry, queue 5 max simultanés.
- **US5 OCR feedback (P1)** — polling `GET /me/documents/{id}/ocr`, "Extraction en cours…" → "Vérifier" → `<ShowSummaryCard>` F39.
- **US6 Validation extraction (P1)** — preview champs (Raison sociale, Effectifs, CA) + actions Valider/Corriger/Annuler. Valider → mute entités liées.
- **US7 Preview document (P1)** — drawer right : `pdf.js`, `<img>`, fallback download Excel/Word.
- **US8 Tags / catégorisation (P1)** — chips "Bilan 2024", "Photo terrain", édition inline.
- **US9 Suppression (P1)** — confirm modal → `DELETE /me/documents/{id}` soft.
- **US10 Recherche / filtres (P2)** — search nom + filtres type + plage date.
- **US11 OCR re-run (P2)** — "Relancer extraction" si résultat médiocre.
- **US12 Sync chat (P1)** — chat `ask_file_upload` (F39) → pousse fichier, refresh liste.

## Exigences fonctionnelles

- **FR-001** : `pages/documents/index.vue` + `components/documents/{DocumentTable,UploadZone,DocPreviewDrawer,OcrSummarySheet,DocumentTagEditor}.vue`.
- **FR-002** : Pinia `useDocumentsStore`.
- **FR-003** : Upload XHR + progress events.
- **FR-004** : OCR polling 2 s, max 60 s timeout, fallback notif.
- **FR-005** : `<ShowSummaryCard>` F39 utilise payload F22.
- **FR-006** : Sanitize noms fichiers (XSS, path traversal).
- **FR-007** : MIME whitelist client ET serveur.

## Exigences non-fonctionnelles

- **NFR-001** : Upload 20 MB sur 4G < 60 s avec progress.
- **NFR-002** : Liste 200 docs → virtualisation table.
- **NFR-003** : Preview PDF lazy-load (pdf.js async chunk).

## Success Criteria

- **SC-001** : Upload 3 PDFs simultanés OK.
- **SC-002** : OCR feedback < 30 s sur petit PDF, validation mute entreprise.
- **SC-003** : Preview PDF drawer fonctionne.
- **SC-004** : Suppression soft → doc disparaît.

## Hors-scope MVP

- Annotation collaborative PDF → post-MVP.
- Comparaison versions → post-MVP.
- OCR multilingue avancé (arabe, langues locales) → post-MVP.
- Signature électronique → post-MVP.

## Risques et points de vigilance

- Gros fichiers : timeout réseau, retry segmenté (post-MVP).
- OCR latence : informer, ne pas bloquer session.
- MIME spoofing : valider serveur jamais client.
- Scan virus : backend (clamav ou service tiers).
- RLS strict : pas de leak entre tenants.
