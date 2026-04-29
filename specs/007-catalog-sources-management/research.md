# Phase 0 — Research (F07 Catalog Sources Management)

## R1 — Canonicalisation URL déterministe

**Decision** : Implémenter un utilitaire Python pur `canonicalize_url(url: str) -> str` qui applique exactement la suite d'opérations suivante :

1. Trim espaces.
2. Si pas de schéma, préfixer `https://`.
3. Forcer schéma `https://` (remplacer `http://` par `https://`).
4. Lower-case du host (sans toucher au path/query).
5. Retirer le préfixe `www.` du host.
6. Si path vide, normaliser à `/`.
7. Sinon, retirer le slash final du path (ex. `/policies/` → `/policies`).
8. Parser les query params, retirer ceux dont la clé matche `^(utm_.*|fbclid|gclid|mc_cid|mc_eid|_hsenc|_hsmi)$` (regex), reconstruire en triant les clés restantes (déterminisme).
9. Conserver le fragment tel quel (deep-link F03).

**Rationale** : règle déterministe, idempotente, testable. Compatible avec deep-link F03 (`#page=`, `#:~:text=`). Pas de dépendance externe — `urllib.parse` suffit.

**Alternatives considered** : librairies `url-normalize`, `furl` (rejetées : abstraction supplémentaire, comportement opaque, dérive de version sur retrait `www.`).

## R2 — HEAD probe HTTP non bloquant

**Decision** : `httpx.AsyncClient(timeout=5.0, follow_redirects=True)` ; capture des exceptions (`httpx.RequestError`, `httpx.HTTPStatusError`) ; retour d'un objet `{ ok: bool, status: int|None, error: str|None }`. Le service de création stocke un champ d'avertissement dans la réponse API (`head_warning`) sans bloquer la persistance.

**Rationale** : conforme FR-007 (warning, pas bloquant). httpx déjà présent (F03 client LLM via OpenRouter).

**Alternatives considered** : `aiohttp` (déjà non utilisé, éviterait double dépendance), GET au lieu de HEAD (rejeté : surcharge réseau, certains serveurs ne supportent pas HEAD → fallback GET range si nécessaire post-MVP).

## R3 — Recherche full-text Postgres avec accents

**Decision** : Ajouter via Alembic une colonne générée stockée :

```sql
ALTER TABLE source ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('french',
      unaccent(coalesce(title,'') || ' ' || coalesce(publisher,'') || ' ' || coalesce(notes,'')))
  ) STORED;
CREATE INDEX idx_source_search_vector ON source USING GIN (search_vector);
```

Et appliquer `unaccent` à la requête : `WHERE search_vector @@ websearch_to_tsquery('french', unaccent(:q))` ; tri `ORDER BY ts_rank_cd(...)`.

**Rationale** : tolérance aux accents (FR ESG), classement de pertinence, < 1s sur 5000 lignes (SC-005) avec GIN.

**Alternatives considered** : `pg_trgm` (mieux pour fuzzy court mais pertinence inférieure pour titres longs), embedding semantic search via Voyage (rejeté : surdimensionné pour 5000 sources, F07 reste lexical, l'embedding viendra avec F19+).

## R4 — Impact analysis : agrégation et expansion

**Decision** : Endpoint `GET /admin/sources/{id}/impact` retourne d'abord les compteurs agrégés en une seule requête multi-CTE (UNION ALL) sur les 8 catégories. Expansion via `GET /admin/sources/{id}/impact/{category}?page=N&page_size=M` pour la liste paginée (lazy).

**Rationale** : NFR-002 (< 500ms même si 1000+ objets) ; éviter de matérialiser tous les objets côté serveur. Indexes existants (FK `source_id`) suffisent.

**Alternatives considered** : matview rafraîchie (rejetée : staleness, complexité), pagination uniforme tout-en-un (rejetée : payload énorme).

## R5 — Workflow de double validation strictement serveur

**Decision** : Service `verify(source_id, actor_user_id)` : récupère source ; si `captured_by == actor_user_id`, lève `HTTPException(status_code=409, detail='SAME_USER_NOT_ALLOWED')` ; sinon transition statut + audit. Aucun flag config ne contourne cette règle.

**Rationale** : NFR-003 (impossible bypass via API) ; clarify Q1 (mode dégradé refusé). Robustesse face à attaques de type rejouage ou abus admin solo.

**Alternatives considered** : flag `single_admin_mode` (rejeté en clarify Q1), service-account bot (post-MVP éventuel).

## R6 — Versioning (F04) sur champs critiques

**Decision** : Helper `bump_source_version_if_critical_changed(before: SourceRow, after_payload: dict)` détecte les diffs sur `(url, version, publisher)` ; si oui, appel `versioning.bump_source_version(source_id, by=user_id)` qui crée une entrée `source_version`. Les diffs sur `notes`, `section`, `page`, `date_publi` ne déclenchent pas de bump.

**Rationale** : FR-013, NFR-004 ; respect du versioning F04.

## R7 — Page publique `noindex` et états visibles

**Decision** : Endpoint API public `GET /api/public/sources/{id}` filtre `WHERE verification_status IN ('verified','outdated')` ; sinon 404. Route Nuxt SSR `/sources/[id]` :

- Set `useHead({ meta: [{ name: 'robots', content: 'noindex,nofollow' }] })`.
- L'API ajoute aussi le header `X-Robots-Tag: noindex, nofollow`.
- Aucun sitemap exposé en MVP.

**Rationale** : clarify Q2 (404 sur pending) + Q5 (noindex). Plateforme fermée P7.

## R8 — Détection de doublon

**Decision** : Au save (POST), recherche `SELECT id FROM source WHERE canonical_url = :u AND page IS NOT DISTINCT FROM :p`. Si trouvé : retour `409 Conflict` avec `existing_id` ; le frontend propose un CTA "Réutiliser cette source". Contrainte unique fonctionnelle au niveau base : `CREATE UNIQUE INDEX ux_source_canonical_url_page ON source (canonical_url, coalesce(page, 0))`.

**Rationale** : FR-008. Idempotence côté UI/UX, mais protection forte au niveau DB.

## R9 — Tests et couverture

**Decision** : Coverage cible ≥ 80% (rappel rules). Tests par couche :

- Unit : canonicalize (table de cas), http_probe (mock httpx), permissions, search (sans DB via SQL parser).
- Integration : pytest-asyncio + base Postgres test (Docker), couvrant tout le flow CRUD/verify/mark-outdated/impact/search/public-page.
- Contract : valider les YAML OpenAPI contre l'app FastAPI (snapshot).
- E2E Playwright : un scénario complet "Admin A crée → Admin B vérifie → marque outdated → impact retourne snapshot intact".

## R10 — Déploiement & migrations

**Decision** : Une seule migration Alembic (`007_xxx_sources_indices_canonical.py`) avec : ajout `canonical_url TEXT`, backfill `canonical_url = canonicalize_url(url)` (script Python idempotent), `NOT NULL`, index unique `(canonical_url, coalesce(page,0))`, colonne générée `search_vector`, index GIN, extension `unaccent` créée si non présente.

**Rationale** : aucune nouvelle table (constraint imposée), seulement enrichissement.

## Unknowns résolus

Aucun NEEDS CLARIFICATION restant. Tous les points sont tranchés ici ou dans la section Clarifications du spec.
