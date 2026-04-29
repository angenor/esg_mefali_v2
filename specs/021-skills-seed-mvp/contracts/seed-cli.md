# Contract — Seed Skills CLI

## Invocation

```bash
python -m backend.scripts.seed_skills [--force] [--dry-run] [--only NAME ...] [--seeds-dir PATH]
```

## Arguments

| Arg | Default | Description |
|-----|---------|-------------|
| `--force` | false | Réécrit les skills `published` modifiées manuellement. |
| `--dry-run` | false | Calcule le diff sans toucher la BDD. |
| `--only` | tous | Filtre les skills à seeder (par `name`). Répétable. |
| `--seeds-dir` | `backend/scripts/seeds/skills` | Override du répertoire de fixtures. |

## Exit codes

| Code | Sens |
|------|------|
| 0 | OK : 0 skill skippée. |
| 1 | ≥ 1 skill skippée pour tool inconnu OU erreur sur golden example. |
| 2 | Erreur fatale (DB indisponible, fixtures malformées). |

## Stdout (ligne finale, JSON)

```json
{
  "created": 0,
  "updated": 0,
  "skipped": 0,
  "published": 3,
  "draft": 8,
  "golden_examples": 15,
  "duration_ms": 1234
}
```

## Logs

- INFO par skill : `[skill_name] action={created|updated|noop} status={draft|published} version=N`.
- WARNING : sources non verified, force non appliqué, audit log indisponible.
- ERROR : tool inconnu, fixture invalide.

## Erreurs structurées

```json
{"level":"error","skill":"skill_score_gcf","code":"tool_unknown","unknown":["bad_tool"]}
```

## Idempotence

- Re-run sans changement → `created=0 updated=0 skipped=0` et version inchangée.
- Re-run avec content_hash modifié → `updated++`, `version` bumpé.

## Préconditions

- Migrations F19+F20 appliquées.
- `DATABASE_URL` valide.
- Modules backend importables.
