# UI Contract — Composants F50 et intégrations

## 1. Mapping `ocr_status` (backend) → libellé UI

| Backend | UI label | Couleur (token F36) | Action principale |
|---------|----------|---------------------|-------------------|
| `pending` | « En file d'attente » | `--color-neutral-500` | — |
| `processing` | « Extraction en cours… » | `--color-info-500` | (spinner) |
| `done` && `extraction_validated_at IS NULL` | « Vérifier » | `--color-warning-500` | Ouvre `OcrSummarySheet` |
| `done` && `extraction_validated_at IS NOT NULL` | « Validé » | `--color-success-500` | Re-corriger |
| `error` | « Échec » | `--color-danger-500` | Relancer extraction |
| Polling cumulé > 60 s sans terminal (UI-only) | « Délai dépassé » | `--color-warning-700` | Relancer extraction |

Les champs `extraction_payload.fields[].confidence` < 0.6 produisent un libellé UI auxiliaire « Faible confiance » sur la fiche (le statut macroscopique reste `done`).

## 2. Composant `<DocumentTable>`

```ts
defineProps<{
  items: DocumentListItem[];
  loading?: boolean;
  selectedId?: string | null;
}>();
defineEmits<{
  (e: 'select', id: string): void;
  (e: 'preview', id: string): void;
  (e: 'verify', id: string): void;
  (e: 'delete', id: string): void;
  (e: 'tag-edit', payload: { id: string; tags: string[] }): void;
}>();
```

- Virtualisation `vue-virtual-scroller` ; row height fixe.
- Colonnes : Nom, Type, Date, Statut OCR (badge), Taille, Actions.
- A11y : `<table role="grid">`, header sticky, `aria-rowindex` pour chaque ligne virtualisée, focus visible (Tailwind ring) sur ligne active.

## 3. Composant `<UploadZone>`

```ts
defineProps<{
  context: 'entreprise' | 'projet';
  projetId?: string;
}>();
defineEmits<{
  (e: 'upload-start', files: File[]): void;
  (e: 'upload-progress', payload: { fileId: string; percent: number }): void;
  (e: 'upload-success', doc: DocumentDetail): void;
  (e: 'upload-error', payload: { fileId: string; error: AppError }): void;
  (e: 'duplicate-detected', payload: { file: File; existing: DocumentDetail }): void;
}>();
```

- Drag & drop + bouton fallback (FR-A11Y-003).
- Pré-validation : MIME + 20 Mo + queue 5 simultanés.
- Empreinte SHA-256 calculée par `useFileFingerprint` AVANT XHR ; si pre-flight 200 → émet `duplicate-detected` au lieu de transfert ; le parent ouvre `<DuplicateChoiceSheet>`.

## 4. Composant `<DuplicateChoiceSheet>` (bottom sheet F39)

```ts
defineProps<{
  file: File;
  existing: DocumentDetail;
}>();
defineEmits<{
  (e: 'reuse', existingId: string): void;
  (e: 'force-new', file: File): void;
  (e: 'cancel'): void;
}>();
```

UX : titre « Document déjà connu », résumé du document existant (nom, date upload, statut), 2 boutons (« Réutiliser le document existant » primaire / « Forcer un nouvel envoi » secondaire), lien « Annuler ».

## 5. Composant `<OcrSummarySheet>` (réutilise F39 `<ShowSummaryCard>`)

```ts
defineProps<{
  document: DocumentDetail;
}>();
defineEmits<{
  (e: 'validate', payload: ValidateExtractionIn): void;
  (e: 'cancel'): void;
  (e: 'recorrect'): void;     // sur document déjà validé
  (e: 'relaunch'): void;
}>();
```

- Champs éditables 1 par 1 ; chaque champ affiche sa confiance (chip).
- Bouton « Répondre librement » (P10) : bascule en zone texte libre adressée à l'IA pour corriger autrement.
- Bouton primaire « Valider » désactivé tant qu'un champ requis est vide.

## 6. Composant `<DocPreviewDrawer>`

- Slide right, `role="dialog" aria-modal="true"`.
- PDF : import dynamique `pdfjs-dist`, contrôles précédent/suivant clavier (`ArrowLeft`/`ArrowRight`), zoom `+/-`.
- Image : `<img>` avec `alt` = nom du document.
- Excel/Word : message + bouton « Télécharger ».

## 7. Composant `<DocumentEmptyState>` (FR-007b/FR-008b)

```ts
defineProps<{
  context: 'entreprise' | 'projet';
  projetName?: string;
}>();
defineEmits<{
  (e: 'cta-click'): void;
}>();
```

UI : illustration SVG sobre + titre + corps + CTA primaire `<UiButton variant="primary">`. Sur grille projet, le titre cite explicitement le nom du projet.

## 8. Pinia store `useDocumentsStore`

State :

```ts
interface DocumentsState {
  items: Record<string, DocumentDetail>;
  byEntreprise: string[];          // ids triés date desc
  byProjet: Record<string, string[]>; // projetId → docIds
  uploadQueue: UploadJob[];
  pollingIntervals: Record<string, number>; // docId → intervalId
  search: { q: string; type: string | null; from: string | null; to: string | null };
}
```

Actions principales :

- `fetchEntreprise()`, `fetchProjet(projetId)`.
- `enqueueUpload(file, opts)` (calcule empreinte, pré-flight, gère choix dédoublonnage).
- `validateExtraction(docId, payload)` — appelle `POST /validate`.
- `linkProjet(docId, projetId)` / `unlinkProjet(docId, projetId)`.
- `softDelete(docId)`.
- `relaunchOcr(docId, { invalidateValidation })`.
- `startPolling(docId)` / `stopPolling(docId)`.

Getters dérivés : filtrage client (`q`, `type`, `from`, `to`) ; comptes par statut.

## 9. EventBus inter-features (P8 sync)

| Event | Émis par | Consommé par |
|-------|----------|--------------|
| `documents:created` | `useDocumentsStore.enqueueUpload` (sur 201) | `pages/documents`, grille projet F43, chat F41 |
| `documents:status-changed` | `useOcrPolling` (transition d'état) | toute vue ouverte |
| `documents:validated` | `validateExtraction` (sur 200) | `useEntrepriseStore`, `useProjetStore`, panneaux scoring F46 |
| `documents:deleted` | `softDelete` | toute vue ouverte |
| `documents:linked-projet` / `documents:unlinked-projet` | link/unlink | grille projet F43 |

## 10. Intégration chat F41 (FR-026, FR-030)

- Skill `ask_file_upload` (F41) ouvre un bottom sheet hébergeant `<UploadZone context="entreprise" />` (ou `context="projet"` si la conversation est ancrée à un projet).
- Au succès, le store F50 émet `documents:created` ; F41 reçoit l'ID et insère un message confirmant l'ajout (texte bulle, jamais inline interactif — P10).
- Bouton « Répondre librement » présent dans la barre supérieure du bottom sheet.

## 11. Conformité accessibilité (FR-A11Y-001/002/003, SC-009)

- Tous les badges OCR : `aria-label` explicite (« Statut OCR : …»).
- Barres de progression : `<progress>` natif + `aria-valuenow/valuemin/valuemax`, conteneur `role="status" aria-live="polite"`.
- Erreurs et expirations de délai : `role="alert" aria-live="assertive"`.
- Drag & drop : zone porte `role="button"` + `tabindex="0"`, ouvre dialogue `<input type="file">` au `Enter`/`Space`.
- E2E : `tests/e2e/documents-a11y.spec.ts` exécute axe-core sur les 4 vues principales (liste vide, liste peuplée, drawer ouvert, bottom sheet validation) et échoue le CI sur toute violation `serious`/`critical`.
