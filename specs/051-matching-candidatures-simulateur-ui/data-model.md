# Phase 1 — Data Model: F51

**Branch**: `051-matching-candidatures-simulateur-ui` | **Date**: 2026-05-05

Ce document décrit les **extensions DB** introduites par F51. Aucun nouveau référentiel ; seules deux tables sont touchées : extension de `candidature` (existante) et nouvelle table `simulation_savee`.

Toutes les valeurs Money sont stockées dans des sous-objets JSONB `{amount: numeric_text, currency: 'XOF'|'EUR'}` côté `candidature.draft_snapshot_json` et `simulation_savee.results_json` (P5).

---

## 1. Extension table `candidature`

Table existante (F26/F34). Colonnes ajoutées par migration `0051` :

| Colonne | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `step_courant` | `SMALLINT` | NOT NULL | `1` | Étape actuelle du wizard ∈ [1..5]. |
| `progression_pct` | `SMALLINT` | NOT NULL | `0` | Pourcentage de complétion calculé côté serveur ∈ [0..100]. |
| `draft_snapshot_json` | `JSONB` | NULL | `'{}'::jsonb` | Buffer brut de saisie wizard, mutable jusqu'à la soumission. |
| `submitted_at` | `TIMESTAMPTZ` | NULL | `NULL` | Horodatage de soumission. NULL = brouillon. NOT NULL = figée. |
| `submitted_snapshot_json` | `JSONB` | NULL | `NULL` | **Snapshot intangible** (P4). NULL avant soumission, NOT NULL et immuable après. |

Contraintes :

- `CHECK (step_courant BETWEEN 1 AND 5)`
- `CHECK (progression_pct BETWEEN 0 AND 100)`
- `CHECK ((submitted_at IS NULL AND submitted_snapshot_json IS NULL) OR (submitted_at IS NOT NULL AND submitted_snapshot_json IS NOT NULL))`

Index :

- Partiel `idx_candidature_drafts ON candidature(account_id, updated_at DESC) WHERE statut = 'brouillon'` — table candidatures récentes.
- `idx_candidature_submitted ON candidature(account_id, submitted_at DESC) WHERE submitted_at IS NOT NULL` — vue historique soumissions.

### Trigger d'immuabilité

```sql
CREATE OR REPLACE FUNCTION trg_candidature_no_mutation_after_submit()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.submitted_at IS NOT NULL THEN
    -- Après soumission, draft_snapshot_json et submitted_snapshot_json sont gelés.
    IF NEW.draft_snapshot_json IS DISTINCT FROM OLD.draft_snapshot_json THEN
      RAISE EXCEPTION 'P4 violation: draft_snapshot_json is frozen after submission';
    END IF;
    IF NEW.submitted_snapshot_json IS DISTINCT FROM OLD.submitted_snapshot_json THEN
      RAISE EXCEPTION 'P4 violation: submitted_snapshot_json is immutable';
    END IF;
    IF NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
      RAISE EXCEPTION 'P4 violation: submitted_at is immutable';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER candidature_no_mutation_after_submit
  BEFORE UPDATE ON candidature
  FOR EACH ROW EXECUTE FUNCTION trg_candidature_no_mutation_after_submit();
```

Les colonnes `statut`, `step_courant`, `progression_pct` restent mutables après soumission (admin F34 transitionne le statut, par ex. `soumise → en_revue`).

### RLS (héritée de la table)

La table `candidature` porte déjà la politique `tenant_isolation` (P2) : `USING (account_id = current_setting('app.current_account_id')::uuid)`. Aucune modification.

### Forme de `draft_snapshot_json`

```jsonc
{
  "step1": {
    "offre_id": "uuid",
    "projet_id": "uuid"
  },
  "step2": {
    // Snapshot pris en lecture seule depuis profil entreprise au début du wizard.
    // Modifiable uniquement via /profil ; ré-importé si l'user clique "rafraîchir".
    "entreprise_snapshot_at": "ts",
    "entreprise": { /* champs profil PME */ }
  },
  "step3": {
    "documents_links": [{ "document_id": "uuid", "checklist_key": "k_bicc_2024" }],
    "checklist_completed": ["k_bicc_2024", "..."]
  },
  "step4": {
    "reponses_libres": [{ "question": "string", "reponse": "string", "asked_at": "ts" }]
  },
  "step5": {
    "user_acknowledged_intangible": true,
    "user_confirmed_at": "ts"
  }
}
```

### Forme de `submitted_snapshot_json` (immuable)

```jsonc
{
  "schema_version": "1",
  "submitted_at": "ts",
  "entreprise": { /* copie figée */ },
  "projet": { /* copie figée */ },
  "offre": { /* copie figée */ },
  "skills_used": [
    { "skill_id": "uuid", "version": "1.2.0", "valid_from": "...", "valid_to": "..." }
  ],
  "indicateurs_valid_from_to": [
    { "indicateur_id": "uuid", "valid_from": "...", "valid_to": "..." }
  ],
  "draft_payload": { /* copie integrale du draft_snapshot_json à la soumission */ },
  "documents": [
    { "document_id": "uuid", "fingerprint_sha256": "hex", "checklist_key": "..." }
  ]
}
```

---

## 2. Nouvelle table `simulation_savee`

```sql
CREATE TABLE simulation_savee (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id      UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES account_user(id),
  label           VARCHAR(120) NOT NULL,
  projet_id       UUID NULL REFERENCES projet(id) ON DELETE SET NULL,
  offre_id        UUID NULL REFERENCES offre(id) ON DELETE SET NULL,
  hypotheses_json JSONB NOT NULL,
  results_json    JSONB NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ NULL,

  CONSTRAINT simulation_savee_label_len CHECK (char_length(label) BETWEEN 1 AND 120)
);

CREATE INDEX idx_simulation_savee_account_recent
  ON simulation_savee(account_id, created_at DESC)
  WHERE deleted_at IS NULL;

ALTER TABLE simulation_savee ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON simulation_savee
  USING (account_id = current_setting('app.current_account_id')::uuid);

REVOKE UPDATE, DELETE ON simulation_savee FROM mefali_app;
GRANT INSERT, SELECT ON simulation_savee TO mefali_app;
-- DELETE/UPDATE désactivés sauf `deleted_at` via fonction stockée audit-tracée.
```

### Forme de `hypotheses_json`

```jsonc
{
  "montant": { "amount": "150000", "currency": "EUR" },
  "duree_mois": 60,
  "type_investissement": "renouvelable_solaire",
  "part_subvention_pct": 30
}
```

### Forme de `results_json`

```jsonc
{
  "mensualites": [{ "mois": 1, "amount": "2530.45", "currency": "EUR" }, ...],
  "cout_total": { "amount": "151827.00", "currency": "EUR" },
  "economie_estimee": { "amount": "12000.00", "currency": "EUR" },
  "co2_evite_t": "8.5",
  "decomposition_pct": { "principal": 65, "interets": 12, "subvention": 23 },
  "computed_at": "ts",
  "formula_refs": [{ "formula_id": "uuid", "version": "1.0.0" }]
}
```

### Cap historique

Cap **50 simulations actives par account_id** (purge soft post-MVP). Au-delà, le `POST /me/simulations/{id}/save` renvoie `409 Conflict` avec code `quota_exceeded` et instruction de supprimer une ancienne.

---

## 3. États et transitions

### `candidature.statut`

États existants F34 : `brouillon | soumise | en_revue | acceptee | refusee`.

```text
brouillon ──submit──▶ soumise
soumise ───admin────▶ en_revue
en_revue ──admin────▶ acceptee | refusee
```

F51 ajoute uniquement la transition `brouillon → soumise` côté PME (via `POST /submit`). Les autres transitions restent admin (F34).

### `candidature.step_courant`

```text
1 (offre+projet) → 2 (snapshot) → 3 (documents) → 4 (réponses) → 5 (récap) → submit
```

`progression_pct` calculé côté serveur :

- step 1 valide → 20 %
- step 2 confirmé → 40 %
- checklist documents complète → 60 %
- réponses libres ≥ 1 par question requise → 80 %
- step 5 atteint avec acknowledgment → 100 %

### `simulation_savee.deleted_at`

`NULL` (active) → `NOT NULL` (soft-deleted, invisible en liste mais conservé pour audit).

---

## 4. RLS — récapitulatif

| Table | Politique | Status |
|---|---|---|
| `candidature` | `tenant_isolation` (existante) | héritée |
| `simulation_savee` | `tenant_isolation` (nouvelle) | ajoutée par migration |
| `offre` | `published_only_for_pme` (existante F08) | héritée |

Cross-tenant access → 404 (P2).

---

## 5. Audit append-only

| Action | `entity` | `field` | `source_of_change` |
|---|---|---|---|
| Wizard step changed | `candidature` | `step_courant` | `manual` |
| Submission | `candidature` | `submitted_at` | `manual` |
| Save simulation | `simulation_savee` | `id` (insert) | `manual` |
| Soft-delete simulation | `simulation_savee` | `deleted_at` | `manual` |

Pas d'audit pour : autosave intermédiaire `draft_snapshot_json`, modification filtres URL, ajout/retrait comparateur (état UI local).

---

## 6. Migration `0051_candidatures_wizard_simulateur_savee.py`

Opérations :

1. `ALTER TABLE candidature ADD COLUMN step_courant SMALLINT NOT NULL DEFAULT 1`
2. `ALTER TABLE candidature ADD COLUMN progression_pct SMALLINT NOT NULL DEFAULT 0`
3. `ALTER TABLE candidature ADD COLUMN draft_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb`
4. `ALTER TABLE candidature ADD COLUMN submitted_at TIMESTAMPTZ`
5. `ALTER TABLE candidature ADD COLUMN submitted_snapshot_json JSONB`
6. CHECK constraints (3)
7. CREATE FUNCTION + TRIGGER `candidature_no_mutation_after_submit`
8. CREATE INDEX partiel sur drafts + submitted
9. CREATE TABLE `simulation_savee` + CHECK + INDEX + RLS POLICY + GRANT/REVOKE

Backfill : pour les candidatures `statut='brouillon'` existantes (rares, MVP en cours), `step_courant=1, progression_pct=0`. Pour `statut IN ('soumise','en_revue','acceptee','refusee')` antérieures, `submitted_at = updated_at` (ou date de seed) et `submitted_snapshot_json = '{}'::jsonb` avec `schema_version: "0"` (snapshots historiques de schema 0 = données legacy non reproductibles, marquées explicitement).

Tests migration : `pytest backend/tests/migrations/test_0051_upgrade_downgrade.py` couvrant aller-retour.
