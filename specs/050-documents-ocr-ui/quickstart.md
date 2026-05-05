# Quickstart — F50 Documents upload + OCR viewer UI

## 1. Pré-requis

```bash
make db-up                 # Postgres pgvector
make migrate               # alembic upgrade head (inclut 0050_documents_ui_extensions)
make backend               # uvicorn app.main:app --reload --port 8010
make frontend              # nuxt dev (port 3001)
```

`/health` doit répondre `{"status":"ok","db":"ok"}`. Le frontend attend `NUXT_PUBLIC_API_BASE=http://localhost:8010`.

## 2. Settings backend

`backend/app/config.py` :

- `MAX_DOCUMENTS_PER_ENTREPRISE = 200` (élevé depuis 50 — voir Complexity Tracking).
- `MAX_DOCUMENT_SIZE_MB = 25` (backend) ; UI plafonne à 20 Mo (sur la 4G).
- `DOCUMENT_PURGE_DAYS = 30` (Q2).

## 3. Premier upload via UI

1. Authentifier la PME (compte test `pme@example.com`).
2. Aller sur `http://localhost:3001/documents` → `<DocumentEmptyState>` s'affiche avec CTA « Téléverser mon premier document ».
3. Cliquer le CTA → `<UploadZone>` ouvert. Glisser un PDF < 20 Mo.
4. Le composable `useFileFingerprint` calcule l'empreinte SHA-256 → pre-flight `GET /me/documents/by-fingerprint?sha256=…`.
5. Sur 404 (cas premier upload) → XHR `POST /me/entreprise/documents` avec progress.
6. Sur 201 → entrée dans la table, statut « Extraction en cours… ».
7. `useOcrPolling` démarre, ping `GET /me/entreprise/documents/{id}` toutes les 2 s.
8. Statut → « Vérifier ». Cliquer ouvre `<OcrSummarySheet>` (bottom sheet F39).
9. Éditer l'effectif erroné, valider → `POST /me/entreprise/documents/{id}/validate`.
10. La fiche entreprise est mise à jour ; le document affiche « Validé ».

## 4. Test du dédoublonnage (Q4)

1. Re-glisser le **même** PDF.
2. Pre-flight retourne 200 → `<DuplicateChoiceSheet>` s'ouvre.
3. Choisir « Réutiliser le document existant » → aucun XHR upload, le rattachement projet de la session courante (s'il y en avait) est ajouté au document existant.
4. Vérifier l'audit : `audit_log` ne porte pas de nouvel événement `create` mais éventuellement un `link_projet`.

## 5. Test du partage M:N (Q1)

1. Sur `/profil/projets/{projet_id}`, cliquer « Lier un document existant » → ouvrir le picker → choisir un document.
2. `POST /me/entreprise/documents/{id}/link-projet` → 201.
3. Le document apparaît à la fois dans `/documents` (liste globale) **et** dans la grille projet, sans duplication.
4. Lier le même document à un second projet → idem ; le document apparaît dans 2 grilles.
5. Délier un projet → `DELETE …/link-projet/{projet_id}` → le document disparaît de cette grille uniquement.

## 6. Test de la suppression et de la purge 30 j (Q2)

1. Supprimer un document → modal de confirmation → `DELETE /me/entreprise/documents/{id}` → 204.
2. Vérifier en base : `deleted_at IS NOT NULL`, `purge_scheduled_at = deleted_at + 30 days`, document disparu des listes UI.
3. Pour simuler la purge en dev :

   ```bash
   cd backend && source .venv/bin/activate
   # forcer la purge_scheduled_at dans le passé sur un document de test :
   psql "$DATABASE_URL" -c "UPDATE document_entreprise SET purge_scheduled_at = now() - interval '1 minute' WHERE id = '<uuid>';"
   python -m app.scripts.purge_documents
   ```

4. Le fichier disparaît du storage ; l'événement `hard_purge` (source `system`) est journalisé.

## 7. Test accessibilité (Q3, SC-009)

```bash
cd frontend
pnpm test:e2e tests/e2e/documents-a11y.spec.ts
```

La suite échoue sur toute violation WCAG 2.1 AA `serious`/`critical` détectée par axe-core.

## 8. Test conversationnel (FR-026)

1. Ouvrir le chat sur `/dashboard`.
2. Demander à l'IA : « Je veux ajouter mon bilan ».
3. L'IA déclenche `ask_file_upload` → bottom sheet F39 hébergeant `<UploadZone context="entreprise">`.
4. Uploader le fichier ; le bottom sheet se ferme.
5. Ouvrir `/documents` dans un autre onglet : le fichier est présent **sans recharger** (EventBus `documents:created`).
6. Cliquer « Répondre librement » dans le bottom sheet pour valider que la sortie texte libre fonctionne (P10).

## 9. Lancer les tests

```bash
# Backend
cd backend && source .venv/bin/activate
pytest tests/unit/entreprise/test_fingerprint.py -v
pytest tests/integration/test_documents_api_extensions.py -v
pytest --cov=app/entreprise --cov=app/api/routes/entreprise_documents

# Frontend unit
cd frontend
pnpm vitest run tests/unit/
# Frontend E2E
pnpm test:e2e tests/e2e/documents-*.spec.ts
```

Coverage attendu ≥ 80 % sur `app/entreprise/**` et `frontend/app/components/documents/**`.

## 10. Troubleshooting

| Symptôme | Solution |
|---|---|
| `409 ocr_in_progress` au relaunch | Attendre la fin du cycle courant ou inspecter `ocr_status` |
| Upload bloqué à 0 % | Vérifier qu'un cookie d'auth est présent et que `NUXT_PUBLIC_API_BASE` pointe sur `8010` |
| Pre-flight retourne toujours 404 | Vérifier que `client_sha256` est bien hex 64 ; `crypto.subtle` requiert un contexte HTTPS ou `localhost` |
| Document supprimé toujours visible | Le client a un cache stale → le store invalide via EventBus `documents:deleted` ; vérifier l'écoute |
| `purge_documents` ne purge rien en dev | `purge_scheduled_at` peut être nul sur des documents pré-existants (avant migration F50) — supprimez-les puis re-supprimez |
