# Phase 1 — Data Model (F21)

F21 ne crée **aucune nouvelle table**. Il consomme les modèles existants F19/F20.

## Entités existantes utilisées

### `Skill` (F19, `backend/app/models/skill.py`)

| Champ | Type | Note F21 |
|-------|------|----------|
| `id` | UUID | généré |
| `name` | TEXT | clé d'idempotence (ex. `skill_esg_diagnostic`) |
| `version` | INTEGER | bump si content_hash change |
| `domain` | TEXT | ex. `diagnostic_esg`, `score_gcf`, `dossier` |
| `prompt_expert` | TEXT | ≤ 1500 tokens (~6000 chars) |
| `procedure` | TEXT | étapes numérotées markdown |
| `tool_whitelist` | TEXT[] | validé contre `TOOL_REGISTRY` F14 |
| `activation_rules` | JSONB | validé via `parse_rules` F19 |
| `golden_examples` | JSONB | liste de 5 dicts (cf. ci-dessous) |
| `status` | ENUM | `draft` ou `published` |
| `valid_from`, `valid_to` | TIMESTAMPTZ | nullable |
| `created_at`, `updated_at` | TIMESTAMPTZ | gérés par script |

### `SkillSource` (F19)

Composite `(skill_id, source_id)`. Lien n-n vers `source` (F07).

### `Source` (F07, `backend/app/models/source.py`)

Pré-existant. Champ `verification_status` ∈ {pending, verified, rejected}. Le seed F21 exige `verification_status='verified'` pour autoriser `published`.

## Format Golden Example (élément JSONB)

```json
{
  "input_message": "Je suis une PME agro de 80 employes",
  "page_context": "/profil/projets/<uuid>",
  "intent": "analyse",
  "expected_tool": "show_radar_chart",
  "expected_payload_partial": {"axes": ["Impact", "Paradigm", "SDG"]}
}
```

Contraintes :
- `expected_tool` DOIT être dans la `tool_whitelist` de la skill.
- `intent` ∈ {analyse, mutation, navigation, question}.

## Format YAML fixture (entrée seed)

```yaml
name: skill_esg_diagnostic
version: 1
domain: diagnostic_esg
language_default: fr
status_target: published
sources:
  - {publisher: "ADEME", title_match: "Base Carbone"}
  - {publisher: "Mefali", title_match: "Referentiel ESG"}
activation_rules:
  any:
    - {field: "page", op: "starts_with", value: "/diagnostic"}
    - {field: "intent", op: "eq", value: "analyse"}
tool_whitelist:
  - ask_qcu
  - show_radar_chart
prompt_expert: |
  Tu es l'expert ESG Mefali. Etape 1 ...
procedure: |
  1. Extraire E/S/G.
  2. Completer la grille.
golden_examples:
  - input_message: "exemple"
    page_context: "/diagnostic"
    intent: "analyse"
    expected_tool: "show_radar_chart"
    expected_payload_partial: {axes: [E, S, G]}
```

Sources identifiées par couple (publisher, title_match) — UUID résolus par le script à l'exécution.

## Invariants

- `name` unique → upsert by name.
- `published` exige : sources résolues toutes `verified` + tools tous connus + ≥ 5 golden examples + prompt sous budget.
- Si tools inconnus → SKIP (pas d'insert).
- Si sources non verified → bascule `draft`.
- Update idempotent si content_hash inchangé : pas de bump version, pas d'admin_event redondant.
