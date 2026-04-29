# F15 — Schémas Pydantic des tools de réponse

Tous les schémas DOIVENT déclarer `model_config = ConfigDict(extra="forbid")`.

## _common.py

- `Option` : `value` (str, 1..128), `label` (str, 1..256), `description` (str | None, 0..512).

## ask_qcu

- `question` (str, 1..1024)
- `options` (list[Option], 2..7)
- `allow_other` (bool, default False)

## ask_qcm

- `question` (str, 1..1024)
- `options` (list[Option], 2..20)
- `min_select` (int | None, ≥1)
- `max_select` (int | None, ≥1)
- Validator : si min/max présents, min ≤ max ≤ len(options).

## ask_yes_no

- `question` (str, 1..1024)
- `yes_label` (str, default "Oui", 1..64)
- `no_label` (str, default "Non", 1..64)

## ask_select

- `question` (str, 1..1024)
- `options` (list[Option] | None)
- `options_endpoint` (str | None, doit commencer par "/")
- `multi` (bool, default False)
- Validator : XOR options vs options_endpoint (exactement un des deux).

## ask_number

- `MoneySpec` : `currency` ∈ {"XOF", "EUR"}.
- `question` (str, 1..1024)
- `unit` (str, 1..32)
- `min`, `max` (float | None) ; si présents, min ≤ max.
- `step` (float | None, > 0)
- `money` (MoneySpec | None)

## ask_date / ask_date_range (P2)

- `AskDatePayload` : `question`, `min_date`, `max_date`, `default` (date | None).
- `AskDateRangePayload` : `question`, `min_date`, `max_date`, `default_start`, `default_end`.

## ask_rating (P2)

- `question`, `scale` ∈ {"1-5", "1-10"}.

## ask_file_upload

- `AttachTo` : `entity_type` ∈ {"projet", "entreprise"}, `entity_id` (UUID | None).
- `question` (str, 1..1024)
- `attach_to` (AttachTo)
- `accepted_mime` (list[str], 1..10)
- `max_size_mb` (int, 1..100)

## show_form (P2)

- `FormField` : `name` (regex `^[a-z_][a-z0-9_]*$`), `type` ∈ {"text","number","date","select","yes_no"}, `label`, `required` (bool, default True), `options` (list[Option] | None).
- `title` (str, 1..256)
- `fields` (list[FormField], 1..20)
- `submit_label` (str, default "Valider", 1..64)

## show_summary_card

- `SummaryField` : `label` (1..128), `value` (0..2048), `source` (str | None, 0..256).
- `SummaryAction` : `label` (1..64), `kind` ∈ {"confirm","edit","cancel"}.
- `title` (str, 1..256)
- `fields` (list[SummaryField], 1..30)
- `actions` (list[SummaryAction], 1..5)

## Anti-XSS commun

Validator `_no_html` partagé : `re.compile(r"[<>]")` ; lève ValueError si une balise est détectée. Appliqué via `@field_validator` sur tous les champs textuels exposés à l'utilisateur (`question`, `title`, `label`, `description`, `value`, `submit_label`, `yes_label`, `no_label`, `unit`).

## Convention d'enregistrement

Chaque module expose `register()` ; `app/orchestrator/tools/__init__.py:register_response_tools()` appelle tous les `register()` dans l'ordre alphabétique.
