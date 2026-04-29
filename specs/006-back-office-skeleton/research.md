# Research — F06 Back-Office Skeleton

## R1. FastAPI router factory pour CRUD générique

- **Decision** : Pattern `EntityRegistry` + `make_crud_router(spec: EntitySpec)` retournant un `APIRouter` ; chaque entité catalogue déclare un `EntitySpec` (table SQLAlchemy, schémas Pydantic Read/Create/Update, `sources_relation` callable, `searchable_fields`).
- **Rationale** : Découplage maximal — F07/F08/F09/F20 ajoutent des `EntitySpec` sans toucher F06. Pydantic v2 generics bien supportés. Aligne avec invariants (tous endpoints homogènes ⇒ tests réutilisables).
- **Alternatives** : (a) subclassing `BaseAdminRouter` — plus verbeux, casse l'extensibilité ; (b) router unique stateful — viole la séparation par entité.

## R2. Cursor-based pagination

- **Decision** : Keyset pagination sur `(created_at DESC, id DESC)` ; cursor = base64 JSON `{"created_at": iso, "id": uuid}`. Limit défaut 50, max 200. Réponse `{items, next_cursor, total_estimate}` (estimation via `pg_class.reltuples` pour éviter `COUNT(*)` coûteux ; total exact possible via flag `?count=exact`).
- **Rationale** : Stable sous écriture concurrente, pas de double-vue, performant sur 10k+ lignes (NFR-001).
- **Alternatives** : offset+limit (viole NFR-001 à scale) ; pure rowid (non portable).

## R3. Optimistic locking via If-Match + version

- **Decision** : Réutiliser la colonne `version` de F04 comme ETag. `GET` renvoie `ETag: "v{version}"`. `PUT` et `POST /publish` exigent `If-Match: "v{version}"` ; mismatch → 412. Cohérent avec F04 `publish_new_version`.
- **Rationale** : Standard HTTP RFC 7232, déjà implémenté en F04. Pas de nouveau mécanisme.
- **Alternatives** : timestamps (jitter) ; locks pessimistes (latence).

## R4. Recherche `/admin/search` — `pg_trgm`

- **Decision** : Extension `pg_trgm` (sur la base existante, vérifier activation), index GIN trigram sur `name`, `publisher`, `external_id` de chaque table catalogue. Requête `WHERE name ILIKE '%q%' OR publisher ILIKE '%q%' OR external_id ILIKE '%q%'` ; tri `similarity(name, q) DESC` ; limit 10 par type. Requêtes parallèles via `asyncio.gather`.
- **Rationale** : Tolère typos, simple, déjà standard PG. Pas d'embeddings (réservé F23+). `q` minimum 2 chars pour éviter scans plein.
- **Alternatives** : `tsvector` FTS (overkill pour 10k lignes, perte simplicité) ; Voyage embeddings (hors scope MVP).

## R5. Nuxt 4 layouts isolés

- **Decision** : `layouts/admin.vue` avec scope CSS via classe racine `.admin-shell` ; Tailwind `@apply` limité à variables admin (`--admin-bg`, `--admin-fg`, etc.) définies dans `assets/styles/admin.css`. Chaque page `/admin/**` déclare `definePageMeta({ layout: 'admin', middleware: 'admin' })`.
- **Rationale** : Évite fuite des styles PME (gsap, palette verte). Permet un tree-shaking propre.
- **Alternatives** : layouts conditionnels via slot — plus fragile.

## R6. localStorage draft (offline-friendly)

- **Decision** : Composable `useAdminDraft(entityType, entityId)` ; clé `admin:draft:{entityType}:{entityId|new}:{userId}` ; auto-save via `useDebounceFn(persist, 1500)` ; à la reprise, comparaison `version` localStorage vs `version` serveur ⇒ confirmation modale si server > local.
- **Rationale** : Couvre NFR-002. Scope par utilisateur évite la fuite multi-comptes sur poste partagé.
- **Alternatives** : IndexedDB (overkill pour ≤ 50 KB) ; sessionStorage (perdu à fermeture).

## R7. Palette admin

- **Decision** : Variables CSS sobres (gris froid + accents fonctionnels) ; densité table 32 px par ligne ; contraste WCAG AA garanti ; pas d'animation gsap (NFR-003) ; transitions CSS basiques (≤ 150 ms).
- **Rationale** : Densité d'information, lecture rapide, distinction visuelle nette du PME.
- **Alternatives** : réutiliser palette PME (rejeté — viole NFR-003).

## R8. Audit helper

- **Decision** : Réutiliser `app.audit.write_event(...)` de F04. F06 ajoute un wrapper `write_admin_event(user_id, entity_type, entity_id, action, before, after)` qui force `source_of_change='admin'`. Toujours dans la même transaction SQLAlchemy que la mutation (rollback global garanti).
- **Rationale** : Cohérence P3, pas de duplication, atomicité.
- **Alternatives** : ajouter audit hors transaction (viole P3 sur erreurs).

## R9. Démonstration `demo_indicator`

- **Decision** : Table catalogue minimaliste introduite uniquement pour F06, marquée `# F06 demo entity — superseded by F09 Indicateur` ; suppression planifiée à F09 via migration.
- **Rationale** : Permet d'écrire les tests E2E du workflow draft→published sans dépendre de F09.
- **Alternatives** : tester avec une fixture pure mock (rejeté — perd la garantie de cohérence base + RLS).

## R10. Stats catalog (sidebar)

- **Decision** : `GET /admin/stats/catalog` exécute en parallèle `SELECT status, COUNT(*) FROM <table> GROUP BY status` pour chaque entité enregistrée (registry) ; pas de cache MVP.
- **Rationale** : Simple/testable (clarification Q3). Sur ≤ 10k objets répartis ≤ 12 tables, latence < 500 ms.
- **Alternatives** : cache 30 s in-memory (deferred post-MVP) ; matérialized view (over-engineered).
