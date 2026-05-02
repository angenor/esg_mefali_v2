# F15 — Manual / automated test log

## Automated

- `pytest -q tests/tools/ tests/orchestrator/` → **105 passed**.
- Coverage `app/orchestrator/tools/` : **99.13 %** (≥ 80 % required).
  - `__init__.py` 100 %
  - `_common.py` 100 %
  - `ask_qcu.py` 100 %
  - `ask_qcm.py` 100 %
  - `ask_yes_no.py` 100 %
  - `ask_select.py` 94 % (lignes 33, 37 — branche `options is None` couverte mais une variante au seuil ; non bloquant)
  - `ask_number.py` 100 %
  - `ask_file_upload.py` 100 %
  - `show_summary_card.py` 100 %
- `ruff check app/orchestrator/tools/ tests/tools/` → **All checks passed** après `--fix` (UP037 supprime 3 self-types quotés).

## Régression — pré-existante (NON F15)

- `tests/chat/test_messages_api.py` et `tests/unit/test_migration_smoke.py` échouent sur **main aussi** (DB locale non migrée — `relation "account_user" does not exist`). Vérifié via `git stash && pytest && git stash pop` : mêmes échecs sans les modifications F15. Aucune régression imputable à F15.

## Tests manuels reportés (DEFERRED)

- Frontend bottom sheet : non livré (DEFERRED).
- Bascule "Répondre librement" : à valider lorsque le frontend sera livré.
- POST `/me/chat/threads/{id}/messages` avec `payload_json` issu d'un tool : repose sur F13 déjà mergé ; vérification end-to-end reportée à la livraison frontend.

## Périmètre P2 DEFERRED

- `ask_date`, `ask_date_range`, `ask_rating`, `show_form` : reportés à itération suivante. Schémas documentés dans `specs/015-tools-reponse-bottom-sheet/contracts/tools-schemas.md`.
- Validation client miroir (zod / valibot) : reportée itération 2.
- Virtualisation listes longues : reportée itération 2.
