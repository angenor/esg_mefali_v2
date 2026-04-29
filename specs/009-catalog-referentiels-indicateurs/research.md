# Research — F09 Catalogue Référentiels, Indicateurs, Critères, Documents Requis, Facteurs d'Émission

## R1. RLS catalogue global

**Décision**: réutiliser la politique alternative F08 mot pour mot.
```sql
CREATE POLICY catalog_<table>_rls ON <table>
USING (
  current_setting('app.role', true) = 'admin'
  OR (current_setting('app.role', true) = 'pme' AND status = 'published')
);
```
Pas de colonne `account_id` sur tables catalogue (catalogue global). Pour Critères/DocumentRequis liés à un fonds donné, l'isolation reste la même : `pme` ne lit que `published`.

## R2. DSL JSON sandboxé

**Décision**: parser récursif Python pur dans `backend/app/catalog/criteres/dsl.py`, ~80 lignes.
- Schéma Pydantic v2 strict (`extra='forbid'`) pour `{op, left, right}`.
- Whitelist opérateurs : `==, !=, >=, <=, >, <, in, not_in, and, or, not`.
- Whitelist feuilles : `{indicateur:CODE}`, `{context:KEY}`, `{literal:VALUE}`.
- Profondeur ≤ 6 niveaux ; payload ≤ 8 KB (validé en amont du parser).
- Tri-state : `True | False | Undecidable` (undecidable si feuille `indicateur` absente du contexte).
- Pas d'import dynamique, pas de getattr, pas de `eval`/`exec`.

**Alternative rejetée**: jsonlogic (lib externe) — surcoût de dépendance, contrôle plus difficile sur la profondeur et le sandbox.

## R3. Versioning facteur_emission par fenêtre

**Décision**: trigger Postgres `BEFORE INSERT` qui, pour un nouveau `(code, pays_iso2)` avec `valid_from = X`, met à jour le précédent enregistrement actif (`valid_to IS NULL OR valid_to > X`) en `valid_to = X - INTERVAL '1 day'`.
**Helper backend** `get_facteur(code, pays_iso2=None, at=None)`:
1. Si `at` non fourni → `at = now()`.
2. SELECT WHERE `code=:c AND (pays_iso2=:p OR pays_iso2 IS NULL) AND valid_from <= :at AND (valid_to IS NULL OR valid_to >= :at)` ORDER BY `pays_iso2 NULLS LAST, valid_from DESC` LIMIT 1.

## R4. Index facteur_emission

```sql
CREATE INDEX idx_facteur_emission_lookup
  ON facteur_emission (code, pays_iso2, valid_from DESC);
```
Couvre 95% des lookups F28. Pas d'index partiel `WHERE valid_to IS NULL` car les versions actives changent.

## R5. Validation poids référentiel

**Décision**: epsilon = 0.01 ; somme acceptée si `99.99 <= sum(poids) <= 100.01`.
Validateur retourne erreur structurée `{code: 'WEIGHTS_SUM_INVALID', actual: 95.0, expected: 100.0, epsilon: 0.01}`.

## R6. Stockage `value_type`

- `numeric` & `percentage` → `DECIMAL(18,6)` ; `percentage` validé Pydantic [0, 100].
- `boolean` → JSON `{"value": true|false}`.
- `enum` → JSON `{"value": "<one of enum_values>"}`.
- `text` → JSON `{"value": "..."}`.
Homogénéiser via colonne `value_json JSONB` côté table de réponse PME (hors-scope F09 mais design coordonné avec F12).

## R7. Suppression vs archive

- `draft` jamais publié : hard delete autorisé.
- `published`/`archived` : pas de DELETE ; transition `archive` uniquement.
- Audit append-only enregistre toutes transitions.

## R8. `formula_type=custom`

MVP : stocké, non évalué (F23 fallback `weighted_sum`). Le validateur publish exige `formula_expression IS NOT NULL` si `formula_type='custom'`. Évaluation reportée post-MVP.
