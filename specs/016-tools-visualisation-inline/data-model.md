# Data Model — F16 Tools de Visualisation Inline

## Vue d'ensemble

Aucune nouvelle table. Les payloads des tools sont stockés dans `chat_message.payload_json` (F13, JSONB). Toutes les structures décrites ici sont des **schémas Pydantic v2** (in-memory) consommés par le `TOOL_REGISTRY` global F14 et persistés tels-quels dans la colonne JSONB.

Conventions communes :
- `model_config = ConfigDict(extra="forbid")`.
- Champs texte exposés à l'utilisateur passés via `no_html` (helper F15).
- `value` numériques typées `Decimal`, sérialisées en string en JSON (cf. R2).
- `source_ids: list[int] = Field(min_length=1)` obligatoire sauf exceptions notées.
- `alt_text: str = Field(min_length=1, max_length=512)` obligatoire sur tous les tools.
- Les `date` sont au format ISO 8601 `YYYY-MM-DD`, validées par regex `^\d{4}-\d{2}-\d{2}$`.

## Mixins partagés (`_viz_common.py`)

```python
class AltTextMixin(BaseModel):
    alt_text: str = Field(min_length=1, max_length=512)

class SourceRequiredMixin(BaseModel):
    source_ids: list[int] = Field(min_length=1, max_length=20)
```

## Schémas par tool (P1)

### show_kpi_card
```
label: str (1..128, no_html)
value: Decimal
unit: str (1..32, no_html)
delta: { value: Decimal, period: str (no_html, 1..32) } | None
source_ids: list[int] (>=1)
alt_text: str (>=1)
```

### show_progress_bar
```
label: str (1..128, no_html)
current: Decimal
target: Decimal (> 0)
unit: str | None (no_html, 0..32)
source_ids: list[int] (>=1)
alt_text: str
```

### show_radar_chart
```
title: str (1..256, no_html)
axes: list[str] (3..12, chaque <=64, no_html)
series: list[{ name: str (1..64, no_html), values: list[Decimal] }]
  contrainte: len(values) == len(axes) pour chaque série
  contrainte: 1 <= len(series) <= 5
source_ids: list[int] (>=1)
alt_text: str
```

### show_bar_chart
```
title: str (1..256, no_html)
x_label: str (no_html, 0..64)
y_label: str (no_html, 0..64)
bars: list[{ label: str (no_html), value: Decimal }] (1..20)
source_ids: list[int] (>=1)
alt_text: str
```

### show_line_chart
```
title: str (1..256, no_html)
x_label: str (no_html, 0..64)
y_label: str (no_html, 0..64)
series: list[{ name: str (no_html), points: list[{x: str|Decimal, y: Decimal}] }] (1..5)
  contrainte: 1 <= len(points) <= 50
source_ids: list[int] (>=1)
alt_text: str
```

### show_pie_chart / show_donut_chart
```
title: str (1..256, no_html)
slices: list[{ label: str (no_html), value: Decimal (>= 0) }] (2..10)
  contrainte: somme(slice.value) > 0
source_ids: list[int] (>=1)
alt_text: str
```

### show_timeline
```
title: str (1..256, no_html)
items: list[{
  date: str ISO 8601 (YYYY-MM-DD, regex validé),
  label: str (1..128, no_html),
  status: Literal["done", "in_progress", "pending"]
}] (1..20)
orientation: Literal["horizontal", "vertical"]
alt_text: str
# source_ids optionnel (jalons sans chiffres)
```

### show_comparison_table
```
title: str (1..256, no_html)
columns: list[str (no_html, 1..64)] (2..5)
rows: list[{
  label: str (no_html, 1..128),
  values: list[str | Decimal]   # textes passés à no_html, decimaux sérialisés string
}] (1..5)
  contrainte: chaque row.values a la même longueur que columns
source_ids: list[int] (>=1)
alt_text: str
```

### show_match_card
```
projet_id: int (> 0)
offre_id: int (> 0)
score: int (0..100)
criteres_couverts: list[str (no_html, 1..256)] (max 20)
criteres_manquants: list[str (no_html, 1..256)] (max 20)
link: str (regex ^/[A-Za-z0-9/_\-?=&%.]+$)   # chemin interne uniquement
source_ids: list[int] (>=1)
alt_text: str
```

## Schémas P2 (DEFERRABLE)

### show_map
```
title: str (no_html, 1..256)
markers: list[{
  lat: Decimal (-90..90),
  lng: Decimal (-180..180),
  label: str (no_html, 1..128),
  kind: Literal["entreprise", "projet", "intermediaire", "zone_impact"]
}] (1..50)
center: { lat: Decimal, lng: Decimal } | None
zoom: int (1..18) | None
alt_text: str
# source_ids optionnel
```

### show_mermaid
```
code: str (5..4096) — validé via mermaid_validator (cf. research.md R1)
alt_text: str
# source_ids optionnel
```

## Validation Mermaid (`mermaid_validator.py`, P2)

- Premier mot-clé autorisé : `flowchart`, `graph`, `sequenceDiagram`, `stateDiagram(-v2)?`, `gantt`, `classDiagram`, `erDiagram`.
- Rejet si match regex `click\s+\w+\s+href\s+["']https?://`.
- Rejet si match `<script` (case-insensitive).
- Rejet si match `%%\{init.*<\s*script`.
- Rejet si longueur > 4096 ou < 5.
- API : `validate_mermaid(code: str) -> None` (lève `ValueError`).

## Persistance

`chat_message.payload_json` (F13) — JSONB. Pas de migration. Le pipeline F14 :
1. Reçoit un tool_call du LLM.
2. Valide via `TOOL_REGISTRY[tool_name].schema(**args)`.
3. Sérialise (`model_dump(mode="json")`) et écrit dans `chat_message.payload_json`.
4. En cas d'échec, boucle retry F14.

`payload.rendered_at: str (ISO 8601 datetime)` — ajouté automatiquement par F13 lors de l'écriture (utilisé pour US13 — badge front).
