# Contract — Tool payloads (mirror Pydantic backend)

**Date** : 2026-05-03
**Source de vérité** : Pydantic backend de F15. Ce document décrit la **forme attendue** côté frontend après génération `pnpm gen:tools`. En cas d'écart, le backend gagne et le frontend regénère.

Notation : `Decimal` = string décimale (ex. `"655.957"`) ; `ISO4217` = string 3 lettres ; `UUID` = string ; `MIME` = string.

## `ask_qcu`

**Payload (instruction)**
```ts
{
  question: string,
  options: { value: string, label: string, description?: string }[],   // 2..10
  allow_other?: boolean   // défaut false
}
```

**Response (PME → backend)**
```ts
{
  tool: "ask_qcu",
  value: string,         // value de l'option choisie OU "other" si allow_other et choix Autre
  label: string,         // label affiché (ou texte libre si "other")
}
```

UI : `UiRadioGroup` ; option « Autre » ouvre un `UiInput` requis si sélectionnée.

## `ask_qcm`

**Payload**
```ts
{
  question: string,
  options: { value: string, label: string }[],
  min_select?: number,   // défaut 0
  max_select?: number    // défaut len(options)
}
```

**Response**
```ts
{
  tool: "ask_qcm",
  value: string[],       // valeurs sélectionnées, length ∈ [min_select, max_select]
  label: string          // « 2 sur 5 » ou liste compacte
}
```

UI : `UiCheckboxGroup` + compteur live `X sur N (min M, max P)`.

## `ask_yes_no`

**Payload**
```ts
{
  question: string,
  yes_label?: string,    // défaut "Oui"
  no_label?: string      // défaut "Non"
}
```

**Response**
```ts
{ tool: "ask_yes_no", value: boolean, label: "Oui" | "Non" | string }
```

## `ask_select`

**Payload**
```ts
{
  question: string,
  options?: { value: string, label: string }[],            // source synchrone
  options_endpoint?: string,                                // OU source async paginée
  search_placeholder?: string,
  multiple?: boolean    // défaut false (single select)
}
```
Exactement un de `options` OU `options_endpoint` est défini.

**Response (multiple=false)**
```ts
{ tool: "ask_select", value: string, label: string }
```

**Response (multiple=true)**
```ts
{ tool: "ask_select", value: string[], label: string }
```

UI : `UiCombobox` + recherche focus auto + virtualisation `vue-virtual-scroller` au-delà de 50 options. Clavier `↑/↓/Entrée/ESC`.

## `ask_number`

**Payload**
```ts
{
  question: string,
  unit?: string,                              // "tCO2e", "%", "FCFA", "EUR", etc.
  min?: number,
  max?: number,
  step?: number,                              // défaut 1 ; 0.01 pour money
  money?: { currency: ISO4217 }               // active la conversion live au peg si XOF/EUR
}
```

**Response**
```ts
{
  tool: "ask_number",
  value: { amount: Decimal, currency?: ISO4217, unit?: string },
  label: string                               // "1 500 000 FCFA (≈ 2 287 €)"
}
```

Conversion live : si `money.currency === "XOF"` ou `"EUR"`, afficher l'autre montant via le peg fixe `655.957`. Sinon, pas de conversion live (post-MVP).

## `ask_date` / `ask_date_range`

**Payload (single)**
```ts
{ question: string, min?: ISODate, max?: ISODate }
```

**Payload (range)**
```ts
{ question: string, min?: ISODate, max?: ISODate, max_span_days?: number }
```

**Response**
```ts
{ tool: "ask_date", value: ISODate, label: string }
{ tool: "ask_date_range", value: { start: ISODate, end: ISODate }, label: string }
```

UI : `UiDatePicker` / `UiDateRangePicker` locale `fr` + `firstDayOfWeek=1`.

## `ask_rating`

**Payload**
```ts
{ question: string, scale: 5 | 10, style?: "stars" | "numeric" }
```

**Response**
```ts
{ tool: "ask_rating", value: number /* 1..scale */, label: string }
```

Clavier : touches `1`..`9`, `0` pour 10 si `scale=10`.

## `ask_file_upload`

**Payload**
```ts
{
  question: string,
  attach_to: "entreprise" | "projet",
  projet_id?: UUID,                  // requis si attach_to="projet"
  accepted_mime?: MIME[],            // défaut: ["application/pdf", "image/png", "image/jpeg"]
  max_size_bytes?: number            // défaut: 10 * 1024 * 1024
}
```

**Response**
```ts
{
  tool: "ask_file_upload",
  value: { doc_id: UUID, filename: string, mime: MIME, size: number },
  label: string                      // "Document chargé : <filename>"
}
```

UI : `UiFileUpload` ; routing endpoint :
- `attach_to === "entreprise"` → POST `/v1/entreprise/documents` (F22)
- `attach_to === "projet"` → POST `/v1/projets/{projet_id}/documents` (F12)

Progression via `XMLHttpRequest`. Erreur (`mime`, `size`, réseau) reste in-sheet avec message FR ; bouton « Annuler » émet un event LLM `{tool: "ask_file_upload", error: <code>}` (FR-019).

## `show_form`

**Payload**
```ts
{
  title: string,
  fields: Array<
    | { name: string, label: string, type: "text" | "textarea", required?: boolean, max_length?: number }
    | { name: string, label: string, type: "number", required?: boolean, min?: number, max?: number, unit?: string }
    | { name: string, label: string, type: "date", required?: boolean }
    | { name: string, label: string, type: "select", required?: boolean, options: { value: string, label: string }[] }
    | { name: string, label: string, type: "checkbox", required?: boolean }
  >
}
```

**Response**
```ts
{
  tool: "show_form",
  value: Record<string, string | number | boolean | null>,
  label: string                       // résumé court "Formulaire complété (N champs)"
}
```

Validation zod générée champ par champ ; soumission bloquée tant qu'invalide.

## `show_summary_card`

**Payload**
```ts
{
  title: string,
  rows: Array<{ label: string, value: string, source_id?: UUID, source_label?: string }>,
  ok_label?: string,        // défaut "Valider"
  edit_label?: string,      // défaut "Corriger"
  cancel_label?: string     // défaut "Annuler"
}
```

**Response (Valider)**
```ts
{ tool: "show_summary_card", value: { action: "validate" }, label: "Récap validé" }
```

**Response (Corriger)** — ferme le sheet **sans** POST applicatif ; émet `dismiss-for-freetext` + un message backend signal :
```ts
{ tool: "show_summary_card", value: { action: "correct" }, label: "Correction demandée" }
```

**Response (Annuler)** :
```ts
{ tool: "show_summary_card", value: { action: "cancel" }, label: "Récap annulé" }
```

Sources : `source_id` rendu en badge non interactif côté MVP (lecture seule), `source_label` sanitizé.
