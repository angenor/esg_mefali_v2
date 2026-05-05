# Phase 0 — Research: F50 Documents upload + OCR viewer UI

**Date** : 2026-05-05
**Branch** : `050-documents-ocr-ui`

Toutes les NEEDS CLARIFICATION sont résolues ; ce document trace les choix techniques et les alternatives écartées.

## R1 — Empreinte de contenu pour le dédoublonnage (FR-006b, Q4)

- **Decision** : SHA-256 calculée côté **client** (`crypto.subtle.digest('SHA-256', ArrayBuffer)`) AVANT envoi pour interrogation préalable `GET /me/documents/by-fingerprint?sha256=…`, puis **recalculée côté serveur** sur le flux reçu et persistée (`document_entreprise.content_sha256`).
- **Rationale** :
  - SHA-256 = standard, pas de collision pratique pour des fichiers utilisateurs ; l'API Web Crypto est disponible dans tous les navigateurs cibles (≥ 90 % du marché PME ouest-africain en 2026).
  - Recalcul serveur empêche un client malveillant de prétendre une empreinte tronquée pour réutiliser un document d'un autre compte (RLS empêche déjà les cross-tenant, mais la défense en profondeur est meilleure).
  - L'index Postgres sur `(account_id, content_sha256, deleted_at IS NULL)` permet une réponse < 50 ms.
- **Alternatives** :
  - MD5 / SHA-1 : rejeté (collisions, signal de mauvaise hygiène).
  - Hash perceptuel (image) : prématuré, ne couvre pas PDF/Excel.
  - Empreinte basée sur (nom, taille, date) : trop de faux positifs et trop facile à contourner.

## R2 — Polling du statut OCR (FR-011, FR-012)

- **Decision** : interrogation périodique `GET /me/entreprise/documents/{id}` (champ `ocr_status` déjà fourni par F22), depuis le composable `useOcrPolling`, avec rythme `2 s` puis backoff doux `2 → 3 → 4 → 5 s` (plafonné à 5 s), arrêt et passage en « Délai dépassé » à 60 s cumulés. Annulation automatique à `unmount`.
- **Rationale** :
  - Réutilise l'API F22 existante sans casser le contrat.
  - 2 s respecte le brouillon F50 et reste faiblement bruyant.
  - Backoff léger réduit le volume de requêtes pour les extractions plus longues sans nuire à l'UX.
  - SSE/WebSockets (P8 sync bidirectionnelle) est intéressant mais introduit un canal supplémentaire (gestion connexion, RLS sur événements) — reporté post-MVP.
- **Alternatives** :
  - Long-polling : code serveur supplémentaire, gain marginal.
  - Server-Sent Events : retenu pour vague 2 si on ajoute la sync bidirectionnelle EventBus inter-onglets.

## R3 — Lazy-load du moteur PDF (FR-020, NFR-003)

- **Decision** : `pdfjs-dist` importé via `() => import('pdfjs-dist')` à l'ouverture de `DocPreviewDrawer`. Worker servi via le bundler Nuxt (`PdfjsWorker?worker`).
- **Rationale** : pdf.js pèse ~1.2 Mo gzipped ; le charger paresseusement préserve le TTFB de `/documents`.
- **Alternatives** : iframe vers le navigateur natif → contrôle UX réduit, sécurité moindre.

## R4 — Virtualisation table 200 documents (FR-007, NFR-002, SC-005)

- **Decision** : `vue-virtual-scroller` (`@tanstack/vue-virtual` non encore stable Vue 3.5 production fin 2025).
- **Rationale** : éprouvé Vue 3, faible surcharge, compatible Tailwind v4 sans recalibrage CSS.
- **Alternatives** : pagination serveur — moins agréable pour 200 lignes, ajoute des allers-retours.

## R5 — Audit pour la purge automatique (Q2, FR-024)

- **Decision** : `record_audit(..., source_of_change='system')` ; ajout de la valeur `'system'` à l'enum existant si absente (vérifier `app/audit/recorder.py`). L'événement précise `entity_type='document_entreprise'`, `action='hard_purge'`, `metadata={'soft_deleted_at': ...}`.
- **Rationale** : conserve une trace réglementaire RGPD/UEMOA même après disparition des données.
- **Alternatives** : table dédiée `purge_log` — duplique le journal d'audit existant.

## R6 — Mécanique de la tâche planifiée 30 j (Q2, FR-024)

- **Decision** : commande Click `python -m app.scripts.purge_documents` exécutée par cron OS (production) ; en dev, invocable manuellement via `make purge-documents`. Pas de dépendance APScheduler en MVP.
- **Rationale** : minimise la surface d'attaque et la complexité de configuration ; conforme à la philosophie "Postgres seul service Docker en dev".
- **Alternatives** : APScheduler dans le lifespan FastAPI — couple le cycle de vie process avec une tâche batch (multi-instance ⇒ courses), augmente le risque opérationnel pour peu de gain.

## R7 — Validation accessibilité WCAG 2.1 AA (Q3, SC-009)

- **Decision** : intégration `@axe-core/playwright` dans la suite E2E ; gate CI sur 0 violations « serious » ou « critical ». Pour le runtime : `aria-live="polite"` sur les badges de progression et statut OCR ; `aria-live="assertive"` sur les erreurs et l'expiration de délai ; ordre de tabulation logique vérifié manuellement et testé via Playwright `keyboard.press('Tab')` dans `documents-a11y.spec.ts`.
- **Rationale** : axe-core couvre ~57 % des cas WCAG (suffisant pour le gate automatique) ; le reste validé par scénarios E2E ciblés.
- **Alternatives** : pa11y — moins intégré au pipeline Playwright/Vitest existant.

## R8 — Élévation du cap documents/entreprise (50 → 200)

- **Decision** : modifier la constante `MAX_DOCUMENTS_PER_ENTREPRISE` (settings F22) à 200 ; vérifier que l'index `idx_document_entreprise_account_deleted` reste performant.
- **Validation** : `EXPLAIN ANALYZE` sur `SELECT * FROM document_entreprise WHERE entreprise_id = $1 AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 200` reste sous 5 ms en local sur jeu de test 1 000 lignes.
- **Rationale** : SC-005 impose 200 docs ; sans cette élévation, la fonctionnalité est non-fonctionnelle dès le 51ᵉ document.

## R9 — Many-to-many document ↔ projet (Q1, FR-008/009)

- **Decision** : table de liens `document_link_projet (document_id, projet_id, account_id, created_at, created_by)` avec contrainte unique `(document_id, projet_id)` et RLS `account_id`.
- **Rationale** :
  - Préserve `document_entreprise` (uploads niveau entreprise) et `document_projet` (uploads originellement liés à un projet) tels qu'ils existent en F22/F12.
  - La grille projet (FR-008) consomme l'union `document_projet` natif **et** liens M:N pointant vers `document_entreprise`.
  - Le délien d'un projet ne supprime jamais le document.
- **Alternatives** :
  - Champ `projet_ids UUID[]` : casse les contraintes ref + index.
  - Migrer `document_projet` vers `document_link_projet` : breaking change, hors-scope MVP.

## R10 — Bottom sheet pour saisie chat (P10, FR-030)

- **Decision** : réutiliser le moteur F39 (`useBottomSheet`) ; F50 fournit un slot `<UploadZone>` à `ask_file_upload`. Bouton « Répondre librement » présent dans la barre supérieure du bottom sheet (pattern F39 standard).
- **Rationale** : conformité stricte au principe constitutionnel P10 et au pattern UX déjà livré par F39/F41.

## Récapitulatif des décisions

| # | Sujet | Décision |
|---|-------|----------|
| R1 | Dédoublonnage | SHA-256 client + recalcul serveur, index par account |
| R2 | Polling OCR | setInterval 2 s + backoff doux jusqu'à 5 s, plafond 60 s |
| R3 | PDF preview | `pdfjs-dist` import dynamique |
| R4 | Virtualisation | `vue-virtual-scroller` |
| R5 | Audit purge | `source_of_change='system'` |
| R6 | Tâche purge 30 j | Click + cron OS, pas d'APScheduler |
| R7 | WCAG 2.1 AA | axe-core/playwright + ARIA live regions |
| R8 | Cap docs/entreprise | 50 → 200 |
| R9 | M:N document ↔ projet | Table `document_link_projet` |
| R10 | Bottom sheet upload chat | Réutilisation moteur F39 |
