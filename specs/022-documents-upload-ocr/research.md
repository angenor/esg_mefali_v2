# Research — F22 Documents Upload & OCR

## R-1 — Lib d'extraction PDF natif

**Decision**: `pypdf` (>= 4.0).
**Rationale**: lib pure-Python, pas de dépendance native (pas de `poppler`/`tesseract`), suffisante pour extraire le texte d'un PDF natif (`PdfReader.pages[i].extract_text()`).
**Alternatives**: `pdfplumber` (lourd, post-MVP) ; `pymupdf` (AGPL, écarté).

## R-2 — Politique de suppression

**Decision**: soft-delete via colonne `deleted_at TIMESTAMP NULL`, en miroir de `document_projet` (F12).
**Rationale**: cohérence avec F12, traçabilité audit, simplicité, RGPD respecté car le fichier physique est effacé du stockage à la suppression.
**Alternatives**: hard-delete strict (incohérent avec F12, écarté).

## R-3 — Timeout synchrone du traitement OCR

**Decision**: `concurrent.futures.ThreadPoolExecutor` (1 worker) + `future.result(timeout=30)`. En cas de `TimeoutError`, statut OCR = `failed` avec message `ocr_timeout`.
**Rationale**: pypdf est synchrone bloquant ; ThreadPoolExecutor isole et impose un timeout dur sans dépendance externe.
**Alternatives**: Celery (post-MVP).

## R-4 — Mime sniffing

**Decision**: trust de `UploadFile.content_type` + validation contre la whitelist FR-003.
**Rationale**: en MVP le fichier est stocké hors web root et servi avec son mime déclaré ; SVG non autorisé donc pas de risque XSS.
**Alternatives**: `python-magic` (libmagic, post-MVP).

## R-5 — Limite de taille — enforcement

**Decision**: double check : (a) `Content-Length` si fourni, (b) `len(data) > 25 MB` après lecture → `ValidationError(code='size_too_large')` → HTTP 413.
**Rationale**: defense-in-depth. SC-005 demande rejet < 200 ms.

## R-6 — Réutilisation `Storage` F12

**Decision**: `app.storage.local.LocalStorage` via `Depends(get_storage)` avec sous-chemin `entreprise/{account_id}/{entreprise_id}/{doc_id}.{ext}`.
**Rationale**: zéro modif de F12 ; isolation account dans le path.

## R-7 — Statut OCR — valeurs et transitions

**Decision**: enum colonne `ocr_status` ∈ {`pending`, `done`, `deferred`, `failed`} + colonnes `ocr_error TEXT NULL` et `text_content TEXT NULL`.
- `pending` → juste après INSERT, avant traitement.
- `done` → extraction PDF natif réussie, `text_content` non vide.
- `deferred` → type non couvert en MVP (image, .docx, .xlsx) ou PDF sans texte natif.
- `failed` → erreur d'IO, timeout, PDF corrompu.
**Rationale**: distingue "non encore disponible" de "erreur" ; prêt pour reprocess post-MVP.

## R-8 — Index et contraintes Postgres

**Decision**: index sur `(entreprise_id)` et `(account_id)`, CHECK sur `type` (statuts/rapport_activite/facture/contrat/politique/autre), CHECK sur `size_bytes BETWEEN 1 AND 26214400`, CHECK sur `ocr_status`, CHECK sur `source_of_change`.
**Rationale**: défense en profondeur DB ; aligné F12.

## R-9 — Récupération de l'`entreprise_id` du PME courant

**Decision**: lookup `SELECT id FROM entreprise WHERE account_id = :aid AND deleted_at IS NULL LIMIT 1` (pattern déjà utilisé dans `app/entreprise/service.py:98`). Si pas d'entreprise → HTTP 400 `entreprise_required`.
**Rationale**: en MVP une PME = une entreprise (cf. F11). Pas besoin de URL `/me/entreprise/{id}/documents`.
