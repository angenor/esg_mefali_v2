# F22 — Upload & OCR de Documents (FR/EN) + Extraction LLM

**Phase** : 5 — Conformité ESG (Module 2)
**Modules brainstorm** : 2.1 (Upload et Analyse de Documents)
**Dépendances** : F11, F12, F13, F17
**Estimation** : 2.5 jours

## Contexte et objectif

Permettre à la PME d'**uploader des documents** (statuts juridiques, rapports d'activité, factures, contrats fournisseurs, politiques internes, business plan, étude d'impact, etc.), de les passer en **OCR** si scanné, et de **laisser le LLM extraire** les informations pertinentes pour préfiller le profil entreprise (F11), créer/enrichir des projets (F12), et alimenter le scoring ESG (F23).

L'OCR doit comprendre **français ET anglais** (les documents juridiques en Afrique de l'Ouest mêlent souvent les deux).

## User Stories

### US1 — Uploader un document depuis le chat (P1)
**En tant que** PME,
**je veux** que le LLM me propose `ask_file_upload` (F15) "Pouvez-vous m'envoyer vos statuts ?" → je dépose le PDF → l'OCR + extraction LLM se déclenchent → je vois `show_summary_card` (F15) avec ce qui a été extrait.

**Test indépendant** : upload via le chat, OCR, extraction d'au moins 5 champs (raison sociale, forme juridique, capital, siège, gérant), affichage récapitulatif.

### US2 — Uploader un document depuis la page Profil (P1)
**En tant que** PME,
**je veux** un bouton "Importer depuis un document" sur la page `/profil/entreprise` ou `/profil/projets/[id]`,
**afin de** ne pas dépendre du chat.

### US3 — Types de documents supportés (P1)
- PDF (texte natif ou scanné)
- Images (JPG, PNG, HEIC)
- Word (.docx)
- Excel (.xlsx)

**Limite** : 25 MB par fichier, 50 fichiers par entité.

### US4 — OCR multi-langue (FR + EN) (P1)
**En tant que** PME francophone,
**je veux** que l'OCR comprenne aussi bien des documents en français qu'en anglais (rapports d'investisseurs internationaux, contrats avec partenaires anglophones, etc.),
**afin de** ne pas avoir à traduire avant.

**Stack proposée MVP** :
- PDF avec texte natif → extraction directe via `pypdf` ou `pdfplumber`.
- PDF scanné / image → OCR via Tesseract (langues `fra` + `eng`) en local.
- **Alternative** : Replicate Whisper n'est pas un OCR (c'est de la STT). Mais Replicate héberge des modèles d'OCR comme `microsoft/trocr` ou des wrappers Tesseract si l'équipe préfère un service distant. Le `.env` du projet a déjà `REPLICATE_API_TOKEN` — utilisable si besoin.
- Recommandation MVP : **Tesseract local (rapide, gratuit, privé)**, fallback Replicate si qualité insuffisante.

### US5 — Extraction LLM structurée (P1)
**En tant que** PME,
**je veux** que le LLM lise le texte OCR (ou le texte natif) et extraie les champs pertinents en fonction du type de document détecté :
- statuts juridiques → forme juridique, raison sociale, capital, siège, gérant, objet social,
- rapport d'activité → CA, effectifs, secteur, principales activités,
- facture / justificatif → montants, dates, fournisseurs,
- contrat → parties, durée, montants,
- politique interne → indicateurs ESG mentionnés (anti-corruption, environnement, RH).

**Mécanisme** : le LLM invoque un tool `extract_from_document(doc_id)` qui retourne un payload structuré ; l'utilisateur valide via `show_summary_card` ; les valeurs validées déclenchent les mutations (F17 `update_company_profile`, `update_project`, etc.).

### US6 — Aperçu visuel + zones surlignées (P2)
**En tant que** PME,
**je veux** voir le PDF avec les zones d'où chaque info a été extraite surlignées,
**afin de** vérifier que le LLM ne s'est pas trompé.

**Stack** : pdfjs-dist côté front + bbox stockés dans le payload extraction.

### US7 — Stockage du document + métadonnées d'extraction (P1)
**En tant que** dev,
**je veux** que chaque document uploadé soit stocké avec :
- son fichier brut (`storage_path`),
- son texte extrait (`text_content`, full-text indexé),
- son embedding (Voyage AI, pour recherche sémantique future),
- ses extractions LLM (`extractions_json` versionnées : 1 doc peut être ré-analysé plusieurs fois).

**afin de** ne pas re-OCR systématiquement et permettre les analyses futures.

### US8 — Documents d'entreprise vs documents de projet (P1)
**En tant que** dev,
**je veux** distinguer :
- documents **d'entreprise** (statuts, KBIS, rapports) → table `document_entreprise`,
- documents **de projet** (étude faisabilité, business plan vert) → table `document_projet` (déjà créée F12).

**afin de** une bonne organisation. Mais l'OCR + extraction sont communs.

## Exigences fonctionnelles

- **FR-001** : Table `document_entreprise` (parallèle à `document_projet` de F12) : `id, account_id, entreprise_id, name, original_filename, mime_type, size_bytes, type_document ENUM('statuts','rapport_activite','facture','contrat','politique','autre'), storage_path, text_content TEXT NULL, embedding vector(1024) NULL, ocr_status ENUM('pending','done','failed'), ocr_error NULL, extractions_json JSONB NULL, uploaded_by, uploaded_at`.
- **FR-002** : Endpoints :
  - `POST /me/entreprise/documents` (multipart upload),
  - `GET /me/entreprise/documents`, `GET /me/entreprise/documents/{id}/download`,
  - `POST /me/entreprise/documents/{id}/reprocess` (re-OCR + re-extraction).
  - Endpoints équivalents pour projets sur `/me/projets/{id}/documents` (déjà F12).
- **FR-003** : Service backend `OcrService` :
  - Détecte si PDF a du texte natif → extraction directe,
  - Sinon, OCR Tesseract (`pytesseract`) avec langues `fra+eng`,
  - Pour Word : extraction via `python-docx`. Pour Excel : `openpyxl`.
  - Synchrone en MVP (acceptable < 30s par doc moyen). Post-MVP : Celery.
- **FR-004** : Service `ExtractionService` qui :
  - utilise le LLM (avec skill `skill_esg_diagnostic` ou skill ad-hoc d'extraction),
  - prompt orienté JSON structuré (forme juridique, CA, effectifs, etc.),
  - validation Pydantic (F14) du payload extrait,
  - retourne un `ExtractionResult` avec confidence par champ.
- **FR-005** : Tool LLM `extract_from_document(doc_id) -> ExtractionResult` exposé en F14 registry pour les flows d'upload depuis le chat.
- **FR-006** : Workflow utilisateur :
  1. Upload → `ocr_status='pending'`.
  2. OCR + extraction synchrones → `ocr_status='done'` + `extractions_json` rempli.
  3. UI affiche `show_summary_card` avec les champs extraits + boutons Valider / Corriger.
  4. Au Valider, mutations F17 appliquent les changements.
- **FR-007** : Embedding du `text_content` calculé via Voyage AI à la fin de l'OCR — utilisable pour recherche full-text + sémantique côté admin (post-MVP).
- **FR-008** : Affichage du document : pdfjs-dist en lecture seule, zoom, recherche dans le texte. Surlignage bbox (US6) en optionnel post-MVP.

## Exigences non-fonctionnelles

- **NFR-001** : OCR d'un PDF de 10 pages < 20s sur une machine standard (Tesseract).
- **NFR-002** : Taille des fichiers : 25 MB max upload (limite Nuxt + FastAPI à configurer).
- **NFR-003** : OCR multilingue testé sur au moins 5 documents réels (statuts juridiques CI / SN / BJ ; rapports d'investisseurs en EN).
- **NFR-004** : Le `text_content` extrait n'est jamais affiché brut côté UI (fuite de mise en page) — toujours via le payload structuré ou le PDF original.
- **NFR-005** : Pas de stockage en cache des extractions LLM en clair côté front — tout passe par l'API.

## Entités clés

- **DocumentEntreprise** (FR-001).
- Réutilise **DocumentProjet** (F12).

## Success Criteria

- **SC-001** : Upload statuts juridiques CI → 5+ champs extraits avec ≥ 80% de précision.
- **SC-002** : Upload rapport d'activité PDF natif → CA + effectifs extraits.
- **SC-003** : Upload contrat en anglais → OCR + extraction valides.
- **SC-004** : Validation utilisateur de l'extraction → mutations F17 appliquent les changements + audit log.
- **SC-005** : Re-process d'un document → nouvelle extraction stockée, l'ancienne archivée.

## Hors-scope MVP

- Détection automatique du type de document (en MVP, l'utilisateur sélectionne le type).
- Surlignage bbox cliquable (post-MVP).
- Documents en arabe / autres langues africaines (post-MVP, Tesseract supporte mais l'extraction LLM est moins fiable).
- OCR de tableaux structurés Excel-like dans des images (post-MVP).
- Versioning fin des documents (post-MVP).
- Audio (transcription via Replicate Whisper) → post-MVP, mais le `REPLICATE_API_TOKEN` est en place pour quand on l'activera.

## Risques et points de vigilance

- **OCR qualité variable** : statuts juridiques scannés en photo téléphone = bruit. Le pré-traitement (deskew, denoise) avec OpenCV améliore. Documenter pour l'utilisateur.
- **Hallucination LLM lors de l'extraction** : le LLM peut inventer une forme juridique. Imposer `confidence` par champ + UI qui flag les confidence < 70% en orange. L'utilisateur valide explicitement.
- **PDF complexe (multi-colonnes, headers/footers)** : `pdfplumber` mieux que `pypdf`. Tester.
- **Coût LLM** : extraction = 1-2 appels par document. Avec 100 PME × 10 docs/mois = 1000–2000 appels = OK budget.
- **Réutilisation Replicate Whisper** : le projet a la clé en .env. Audio (note vocale d'une PME pour décrire son projet) = beau cas d'usage post-MVP. Pas en MVP.
- **Privacy** : les statuts juridiques contiennent des infos personnelles (numéro CNI du gérant). Ne pas envoyer plus que nécessaire au LLM. Recommandation : strip des données personnelles avant prompt.
