# Phase 0 — Research : Scoring ESG MVP

**Feature** : 023-scoring-esg-multi-referentiels
**Date** : 2026-04-29

## Décisions

### D1 — Formule unique en MVP : `weighted_sum` avec renormalisation

**Décision** : `score_global = sum(weight_i * normalized_value_i) / sum(weight_i)` où la somme porte uniquement sur les indicateurs **couverts** (valeur disponible et valide). Les indicateurs manquants ne pénalisent pas le score (ils sont signalés dans `indicateurs_manquants` pour action utilisateur).

**Alternatives** :
- (A) Pénaliser les manquants en gardant le dénominateur sur la somme totale des poids → score systématiquement bas, peu utile en début de parcours.
- (B) Renormalisation (retenue) → score représente la maturité sur ce qu'on sait, l'utilisateur voit ce qu'il manque pour augmenter coverage.
- (C) Formule `custom` (eval JSON safe) → reportée post-MVP.

**Conséquence** : test déterministe simple, comportement intuitif "plus tu remplis, plus précis".

### D2 — Normalisation par type

| `value_type` | Règle |
|---|---|
| `numeric` avec `seuil_min, seuil_max` | linéaire : `clamp((v - min)/(max - min) * 100, 0, 100)` |
| `numeric` sans seuils | `clamp(v, 0, 100)` (on suppose la valeur déjà 0-100) |
| `boolean` | `100` si vrai, `0` si faux |
| `enum` avec `enum_values=[...]` ordonnées | `index/(len-1) * 100` |
| `text` ou `json` | exclu en `manquants` (`reason="unsupported_value_type"`) |

### D3 — Mapping valeur PME : dictionnaire en code

**Décision** : un dictionnaire `VALUE_SOURCE_MAP: dict[str, Callable[[EntrepriseRow], Any]]` indexé par `indicateur.code`. Pour MVP, on supporte les colonnes plates de `EntrepriseRow` (taille_effectifs, taille_ca_amount, secteur_code, etc.) plus quelques sondes JSONB sur `gouvernance_json` et `pratiques_actuelles_json`. Si l'indicateur n'est pas dans le map → manquant `value_source_unmapped`.

**Alternatives** :
- (A) Champ `indicateur.value_source_path` JSON en DB → migration F09 requise. Reporté post-MVP.
- (B) Map en code (retenu) → simple, testable, évolutif sans migration.

### D4 — Snapshot version référentiel

**Décision** : on stocke `referentiel_id` (FK) + `referentiel_version: int`. Pas de copie complète des indicateurs : la table `referentiel` est versionnée par F09 (`logical_id` + `version` + `valid_from`/`valid_to`), donc reproductible.

### D5 — Append-only

**Décision** : chaque recalcul = nouvelle ligne `score_calculation`. Le "score courant" pour `(account_id, entity_id, referentiel_id)` est obtenu via `ORDER BY computed_at DESC LIMIT 1`. Index dédié `(account_id, entity_type, entity_id, referentiel_id, computed_at DESC)`.

### D6 — Audit

**Décision** : un appel `record_audit(entity_type='score_calculation', entity_id=row.id, source_of_change='manual', field='compute', new={referentiel_code, score_global})` par calcul. Pas de mutation, donc pas de `old`.

### D7 — RLS

**Décision** : politique RLS calquée sur les tables F11/F12 :
```sql
CREATE POLICY score_calculation_tenant ON score_calculation
  USING (account_id = current_setting('app.current_account_id', true)::uuid);
```
Plus une policy admin lecture tout (cohérent F02). Insertion via `WITH CHECK` même condition.

### D8 — Couverture nulle, division par zéro

**Décision** : si `sum(weights_couverts) == 0` ou aucun indicateur couvert → `score_global = NULL` (pas 0). Idem `scores_by_pillar.X = NULL` pour un pilier sans indicateur couvert. Le test `dépister piliers vides` consomme cette règle.

### D9 — Endpoints

- `GET /me/scoring/{entity_type}/{entity_id}` → liste des **derniers** scores par référentiel publié (peut déclencher un calcul à la volée si aucun score persisté ; sinon retourne le plus récent).
- `GET /me/scoring/{entity_type}/{entity_id}/{referentiel_code}` → détail dernier calcul.
- `POST /me/scoring/{entity_type}/{entity_id}/recompute?referentiel=<code>` → force un nouveau calcul, persiste, retourne.

`entity_type` ∈ `{entreprise, projet}` ; pour MVP, `projet` accepté côté contrat mais le résolveur de valeurs ne sait lire que `entreprise` → tous les indicateurs reviennent en manquants pour `entity_type=projet`. À traiter dans une feature future.

### D10 — Tests

- Unitaires : normalizer (par type), engine (couverture partielle, déterminisme, division par zéro), value_source (lookup, fallback).
- Intégration : 3 endpoints (200 OK, 404 référentiel inexistant, 404 cross-tenant via fixture deux comptes).
- Fixture : un référentiel test `TEST_REF` avec 4 indicateurs (2 E numériques, 1 S boolean, 1 G enum) + une `entreprise` complète + une autre vide.
