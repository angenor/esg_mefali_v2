# Data Model — F23 Scoring ESG MVP

**Feature** : 023-scoring-esg-multi-referentiels
**Date** : 2026-04-29

## Nouvelle table : `score_calculation`

| Colonne | Type | Contraintes | Description |
|---|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` | Identifiant unique du calcul |
| `account_id` | UUID | NOT NULL, FK `account(id)` | Tenant (RLS) |
| `entity_type` | TEXT | NOT NULL, CHECK in (`entreprise`, `projet`) | Type d'entité scorée |
| `entity_id` | UUID | NOT NULL | ID de l'entreprise ou du projet |
| `referentiel_id` | UUID | NOT NULL, FK `referentiel(id)` | Référentiel résolu au moment du calcul |
| `referentiel_version` | INT | NOT NULL | Version du référentiel snapshot (cohérent F04) |
| `referentiel_code` | TEXT | NOT NULL | Dénormalisation lecture (filtre rapide par code) |
| `score_global` | NUMERIC(7,4) | NULL | Score 0–100 ou NULL si non calculable |
| `scores_by_pillar` | JSONB | NOT NULL, default `{}` | Ex. `{"E": 75.50, "S": null, "G": 60.00}` |
| `details_json` | JSONB | NOT NULL, default `{}` | Détails couverts/manquants/sources_used |
| `coverage_ratio` | NUMERIC(5,4) | NULL | Ratio (poids couverts / poids total) ou NULL |
| `computed_at` | TIMESTAMPTZ | NOT NULL, default `now()` | Horodatage UTC ISO 8601, ex. `2026-04-29T12:00:00Z` |
| `computed_by` | UUID | NULL, FK `account_user(id)` | User déclencheur (NULL si système) |

### Index

- PK `score_calculation_pkey` sur `id`.
- `ix_score_calc_lookup` sur `(account_id, entity_type, entity_id, referentiel_id, computed_at DESC)` — pour récupérer le dernier calcul.
- `ix_score_calc_referentiel_code` sur `(account_id, referentiel_code)` partial WHERE `score_global IS NOT NULL`.

### RLS

```sql
ALTER TABLE score_calculation ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_calculation FORCE ROW LEVEL SECURITY;

CREATE POLICY score_calc_tenant_select ON score_calculation
  FOR SELECT
  USING (account_id = current_setting('app.current_account_id', true)::uuid);

CREATE POLICY score_calc_tenant_insert ON score_calculation
  FOR INSERT
  WITH CHECK (account_id = current_setting('app.current_account_id', true)::uuid);

CREATE POLICY score_calc_admin_all ON score_calculation
  USING (current_setting('app.current_role', true) = 'admin');
```

(Aucun UPDATE / DELETE — table append-only ; pas de policy écriture autre que INSERT.)

## Forme de `details_json`

```json
{
  "indicateurs_couverts": [
    {
      "indicateur_id": "11111111-1111-1111-1111-111111111111",
      "indicateur_code": "EFFECTIFS_TOTAL",
      "pillar": "S",
      "value": 42,
      "normalized_value": 70.0,
      "weight": 1.5,
      "contribution": 105.0,
      "source_id": "22222222-2222-2222-2222-222222222222"
    }
  ],
  "indicateurs_manquants": [
    {
      "indicateur_id": "33333333-3333-3333-3333-333333333333",
      "indicateur_code": "GOUVERNANCE_BOARD_INDEPENDENCE",
      "pillar": "G",
      "reason": "value_source_unmapped"
    }
  ],
  "sources_used": [
    "22222222-2222-2222-2222-222222222222"
  ]
}
```

### Reasons (énumération)

- `value_absent` — la PME n'a pas renseigné la valeur source.
- `value_source_unmapped` — pas de mapping dans `VALUE_SOURCE_MAP`.
- `unsupported_value_type` — `value_type` non géré (text/json).
- `invalid_value` — valeur hors `enum_values` ou type incompatible.
- `referentiel_indicateur_misconfig` — pas de `source_id` côté `referentiel_indicateur`.

## Migration Alembic — `0016_f23_score_calculation`

- Crée la table `score_calculation` avec colonnes ci-dessus.
- Crée les index.
- Active RLS + policies.
- Reverse : DROP table.

## Pas de modification F09

Aucun changement de schéma sur `referentiel`, `indicateur`, `referentiel_indicateur`. Le mapping valeur source vit en code (`VALUE_SOURCE_MAP`) pour MVP.
