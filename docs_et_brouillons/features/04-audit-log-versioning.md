# F04 — Audit Log Append-Only & Versioning

**Phase** : 0 — Fondations transversales
**Modules brainstorm** : 0.4 (Audit Log), 0.5 (Versioning Référentiels et Candidatures)
**Dépendances** : F01, F02
**Estimation** : 2 jours

## Contexte et objectif

Deux invariants critiques de la plateforme sont posés ici :

1. **Audit log append-only** — toute mutation (manuelle, LLM, import) est journalisée avec qui, quand, quoi, ancienne valeur, nouvelle valeur, source du changement. Quasi-réglementaire en finance pour défense en cas de litige.
2. **Versioning des Référentiels et des Candidatures** — la taxonomie GCF, BOAD, UEMOA, etc. évolue. Une candidature soumise en mars 2026 contre la taxonomie GCF v2.3 doit pouvoir être défendue en 2028 même si GCF est passée à v3.0. Solution : snapshot JSON immuable au dépôt + versions datées des référentiels.

Ces deux mécanismes sont **transversaux** : ils sont consommés par toutes les features qui suivent (mutations, scoring, génération de dossiers, attestations). Les implémenter mal en F04 = ré-écrire 30 features plus tard.

## User Stories

### US1 — Toute mutation métier est journalisée (P1)
**En tant qu'**équipe ESG Mefali (compliance),
**je veux** que toute insertion, modification ou suppression sur les tables métier (Entreprise, Projet, Candidature, Score, Attestation, etc.) soit enregistrée dans un `audit_log` append-only,
**afin de** pouvoir reconstituer l'historique exact en cas d'audit ou de litige.

**Test indépendant** : modifier un champ d'une entreprise via l'API → vérifier qu'une ligne `audit_log` apparaît avec `entity_type='entreprise'`, `field='nom'`, `old_value='X'`, `new_value='Y'`, `source_of_change='manual'`, `user_id`, `account_id`, `timestamp`. Tenter un `UPDATE audit_log SET ...` ou `DELETE FROM audit_log` → bloqué (politique RLS + revoke des privilèges WRITE/DELETE pour les rôles applicatifs).

### US2 — La source du changement est tracée (P1)
**En tant qu'**auditeur,
**je veux** distinguer si une mutation provient d'une saisie manuelle, d'une action LLM, ou d'un import,
**afin de** pouvoir analyser les patterns d'erreur et de comportement du LLM.

**Champs** : `source_of_change ENUM('manual','llm','import','admin','system')`.

### US3 — La PME consulte l'historique de ses actions (P2)
**En tant que** PME,
**je veux** voir un journal "Historique des actions" listant les modifications faites sur mes données (par moi, par mes collaborateurs, par le LLM agissant en mon nom),
**afin de** comprendre ce qui a changé et qui l'a changé.

Vue lecture seule, paginée, filtrable par entité et par type de changement. Sera intégrée dans F32 (dashboard PME).

### US4 — Les Référentiels sont versionnés (P1)
**En tant que** garant de la cohérence métier,
**je veux** que chaque `Referentiel` ait `version`, `valid_from`, `valid_to`,
**afin de** que les évolutions du référentiel GCF/BOAD/UEMOA ne cassent pas l'historique des scores et candidatures.

**Scénarios** :
1. Référentiel GCF v2.3 actif (`valid_from=2025-01-01`, `valid_to=NULL`) → utilisable.
2. Admin publie GCF v3.0 → automatiquement `valid_to=2026-04-01` est posé sur v2.3 et `valid_from=2026-04-01` sur v3.0.
3. Une candidature soumise le 2026-03-15 référence v2.3 dans son snapshot et reste calculable.

### US5 — Les Critères, Indicateurs, Formules, Seuils sont versionnés (P1)
**En tant que** dev backend,
**je veux** le même mécanisme `version + valid_from + valid_to` sur les sous-objets des référentiels,
**afin de** assurer la traçabilité fine.

### US6 — Les Candidatures stockent un snapshot immuable (P1)
**En tant que** PME ou auditeur,
**je veux** qu'au moment de la soumission d'une candidature, un snapshot JSON figé soit attaché contenant : projet (état complet), critères de l'offre, référentiel actif, scores calculés, sources mobilisées,
**afin de** pouvoir défendre la candidature même si l'offre/référentiel évolue après dépôt.

**Scénarios** :
1. Soumission candidature → `Candidature.snapshot_json` rempli, `submitted_at` posé.
2. Le référentiel évolue 6 mois plus tard → la candidature reste calculable contre son snapshot.
3. Admin peut "recalculer" un score historique contre le snapshot pour audit.

### US7 — Badge "Évalué selon Référentiel X v2.3 du 15/03/2026" (P2)
**En tant qu'**utilisateur,
**je veux** voir clairement contre quelle version d'un référentiel mes scores ont été calculés,
**afin de** comprendre la traçabilité.

## Exigences fonctionnelles

- **FR-001** : Table `audit_log` : `id BIGSERIAL, user_id UUID NULL, account_id UUID NULL, timestamp TIMESTAMPTZ DEFAULT now(), entity_type TEXT, entity_id UUID, field TEXT NULL, old_value JSONB NULL, new_value JSONB NULL, source_of_change ENUM, request_id TEXT, ip TEXT NULL, notes TEXT NULL`.
- **FR-002** : Privilèges Postgres : le rôle applicatif a `INSERT` sur `audit_log` mais **pas** `UPDATE` ni `DELETE`. Seul un rôle d'archive (post-MVP) peut purger après N années.
- **FR-003** : Helper backend `record_audit(entity_type, entity_id, field?, old, new, source_of_change)` appelé par les services métier sur chaque mutation. Ne pas se reposer sur des triggers DB en MVP (trop opaques pour le LLM source-of-change).
- **FR-004** : Pour les mutations LLM, le helper est invoqué automatiquement par le décorateur des tools de mutation (Phase 3, F17). Cette feature livre le helper, pas les tools.
- **FR-005** : Endpoint `GET /audit-log?entity_type=&entity_id=&from=&to=&source_of_change=&page=` accessible à la PME pour son compte (RLS) et aux admins pour tout.
- **FR-006** : Export CSV/JSON de l'audit log par compte (pour audit externe).
- **FR-007** : Sur **toutes** les tables des entités versionnées (`referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`), ajouter `version INT NOT NULL DEFAULT 1, valid_from TIMESTAMPTZ NOT NULL DEFAULT now(), valid_to TIMESTAMPTZ NULL`.
- **FR-008** : Helper `publish_new_version(entity)` qui : ferme la version active (`valid_to = now()`), insère la nouvelle (`version + 1, valid_from = now(), valid_to = NULL`), conserve le `parent_id` ou la chaîne de versions.
- **FR-009** : Une vue ou helper `get_active(entity_type, id, at_timestamp?)` qui retourne la version active d'un objet (par défaut `now()`, sinon point dans le temps pour audit).
- **FR-010** : Sur la table `candidature`, colonne `snapshot_json JSONB NOT NULL` à la soumission. Un schéma JSON strict définit la forme du snapshot (sera enrichi par F25/F26).
- **FR-011** : Endpoint `POST /candidatures/{id}/recompute-from-snapshot` qui re-calcule le score depuis le snapshot — utile pour démontrer en cas d'audit.
- **FR-012** : Composant Vue `<VersionBadge :referentiel-id :version :date>` pour afficher "Évalué selon Référentiel GCF v2.3 du 15/03/2026".

## Exigences non-fonctionnelles

- **NFR-001** : L'audit log doit supporter au moins 100 inserts/seconde sans dégrader les requêtes utilisateur (table partitionnée par mois post-MVP, mais index sur `(entity_type, entity_id, timestamp)` dès le MVP).
- **NFR-002** : Les valeurs `old_value`/`new_value` ne doivent **jamais** contenir de mots de passe, JWT, refresh tokens, ou données chiffrées sensibles. Ces champs sont blacklistés dans le helper.
- **NFR-003** : La taille du snapshot d'une candidature reste raisonnable (< 500 KB en pratique). Compresser avec `gzip` côté Postgres si > 100 KB (TOAST automatique).
- **NFR-004** : Les exports CSV/JSON respectent l'isolation par compte (RLS).

## Entités clés

- **AuditLog** (FR-001).
- Tables versionnées (extension de schémas existants) : `referentiel`, `indicateur`, `critere`, `formule`, `seuil`, `facteur_emission`, `template`.
- `Candidature.snapshot_json` (extension de schéma).

## Success Criteria

- **SC-001** : 100% des mutations sur les entités métier (testé via tests d'intégration) génèrent une ligne `audit_log`.
- **SC-002** : Tentative de `UPDATE` ou `DELETE` sur `audit_log` depuis le rôle app → erreur Postgres (privilèges révoqués).
- **SC-003** : Une candidature soumise puis recalculée depuis son snapshot 1 an plus tard donne le même score (au cent près).
- **SC-004** : `publish_new_version` ferme proprement la version précédente sans gap ni overlap (testé par invariant SQL).

## Hors-scope MVP

- Partitionnement de l'audit log (post-MVP, à activer quand volume > 10M lignes).
- Purge automatique après N années (post-MVP, dépend de la politique légale).
- UI admin de "diff entre 2 versions d'un référentiel".
- Reproduction non-fluide de l'historique côté UI (visualisation timeline avancée).

## Risques et points de vigilance

- **Coûts I/O** : un audit log mal indexé devient un goulot. Index composite `(account_id, entity_type, entity_id, timestamp DESC)` indispensable.
- **`source_of_change='llm'`** : nécessite que F17 (tools de mutation LLM) appelle systématiquement le helper. Sera matérialisé par un décorateur Python sur les handlers de tools.
- **Snapshot vs versioning** : ne pas dupliquer. Le snapshot d'une candidature **stocke les ID + version** des entités utilisées, et duplique uniquement la donnée volatile (réponses PME, calculs intermédiaires). La donnée stable (référentiel) reste accessible via `get_active(... at=submitted_at)`.
- **Gestion des conflits de version** : si 2 admins éditent un référentiel en même temps, l'un des deux doit recevoir une erreur de version optimiste (`version_at_load != version_in_db`). Pattern simple : `If-Match` HTTP header.
