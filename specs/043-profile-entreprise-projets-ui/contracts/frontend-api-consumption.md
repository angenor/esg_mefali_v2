# Contract — API consommée par F43 (frontend)

F43 n'expose aucun nouvel endpoint. Ce contrat fige les hypothèses d'**input/output** que l'UI assume vis-à-vis des routes existantes (F11, F12-profile, F22). Toute divergence détectée à l'implémentation devient un défaut bloquant.

## 1. Profil entreprise

### 1.1 `GET /me/entreprise`
- **Auth** : cookie de session (`AuthSessionMiddleware`).
- **Réponse 200** : `EntrepriseRead` (cf. data-model § 1.1).
- **Erreurs** : `401` non authentifié → redirection `/login` ; `404` jamais (la création s'opère côté F02 register).
- **Usage UI** : appelé en SSR au mount de `/profil/entreprise`.

### 1.2 `PATCH /me/entreprise`
- **Body** : `EntreprisePatchIn` (champs partiels) + `version: int` obligatoire.
- **Réponse 200** : `EntrepriseRead` mis à jour (avec `version + 1`).
- **Réponse 409** : `ConflictOut` (cf. data-model § 1.5). Le front ouvre `ConflictDialog`.
- **Réponse 422** : erreur Pydantic ; le front affiche le message dans le `UiFormField` correspondant via `aria-describedby`.
- **Idempotence** : non garantie (PATCH multiple = N versions), justifie le debounce 800 ms.
- **Audit** : append-only via `audit_log` (P3, `source_of_change='manual'`) — comportement backend, le front n'a rien à fournir.

### 1.3 `GET /me/entreprise/completeness`
- **Réponse 200** : `CompletenessOut`.
- **Usage UI** : appelé après `loadAll()` puis re-déclenché après chaque PATCH réussi.

### 1.4 `GET /me/entreprise/sectors`
- **Réponse 200** : `list[SectorOut]` (référentiel sectoriel statique).
- **Usage UI** : pré-charge au mount du `SectorSelect` ; cacheable côté front (TTL session).

### 1.5 `GET /me/entreprise/events` (SSE)
- **MVP F43** : non consommé (R5).

## 2. Projets

### 2.1 `GET /me/projets`
- **Réponse 200** : `ProjetListOut { items: ProjetSummary[], total }`.
- **Pagination** : non requise au MVP (≤ 5 projets par PME).

### 2.2 `POST /me/projets`
- **Body** : `ProjetCreate` (au minimum `{ nom }` ; les autres champs du wizard étapes 2–4 sont envoyés en un seul payload).
- **Réponse 201** : `ProjetRead`.
- **Erreur 422** : message d'erreur localisé par étape côté front.

### 2.3 `GET /me/projets/{id}`
- **Réponse 200** : `ProjetRead`.
- **Erreur 404** : projet inexistant ou cross-tenant (P2 — masque l'existence).

### 2.4 `PATCH /me/projets/{id}`
- Identique à 1.2 mais sur `ProjetPatch`. `409 ConflictOut` géré par `ConflictDialog`.

### 2.5 `DELETE /me/projets/{id}`
- **Réponse 204**.
- **Effet** : soft delete (`deleted_at = now()`). Réversible 30 j (US 5).

### 2.6 `POST /me/projets/{id}/transition`
- **MVP F43** : non utilisé directement par l'UI (réservé tool LLM).

### 2.7 `POST /me/projets/{id}/duplicate`
- **MVP F43** : non utilisé.

### 2.8 `GET /me/projets/{id}/documents`
- **Réponse 200** : `DocumentProjetRead[]`.

### 2.9 `POST /me/projets/{id}/documents`
- **Multipart** : `file` + `type_doc`.
- **Validation cliente** : MIME ∈ `{pdf, jpg, png, docx, xlsx}`, taille ≤ 25 Mo.
- **Validation serveur** : whitelist plus large (R9) ; le client est plus strict.
- **Réponse 201** : `DocumentProjetRead`.

### 2.10 `DELETE /me/projets/{id}/documents/{doc_id}`
- **Réponse 204**.

## 3. Audit

### 3.1 `GET /me/audit-log?entity=entreprise|projet&entity_id=...`
- **Réponse 200** : `AuditLogPage { items: AuditEntry[], next_cursor? }`.
- **Usage UI (US 6 — P2)** : `HistoryDrawer.vue`.

## 4. Schémas d'erreurs partagés

| Code HTTP | Forme                                                    | Action UI |
|-----------|----------------------------------------------------------|-----------|
| 400       | `{ detail: string }`                                     | toast erreur générique. |
| 401       | `{ detail: 'unauthenticated' }`                          | redirect `/login`. |
| 404       | `{ detail: 'not_found' }`                                | redirect `/profil/projets` + toast. |
| 409       | `ConflictOut`                                            | ouvre `ConflictDialog`. |
| 422       | `{ detail: ValidationError[] }` (FastAPI)                | mappe sur `UiFormField`. |
| 5xx       | `{ detail?: string }`                                    | bannière persistante + retry exponentiel. |

## 5. Headers et cookies

- `credentials: include` sur tous les `$fetch` (cookie session).
- Pas de header CSRF requis pour `GET` ; pour `PATCH/POST/DELETE`, le middleware backend valide le cookie + origine (cf. middleware existant). Le composable `useCsrf` gère le token au besoin (existant F02).
