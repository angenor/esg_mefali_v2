# Contract — Backend Edit-Line Endpoint (F47)

**Route** : `POST /me/carbon/{year}/edit-line`
**Méthode** : `POST`
**Auth** : `Depends(get_current_pme)` — JWT requis ; `account_id` extrait pour RLS.
**Tags OpenAPI** : `carbon`
**Status** : nouveau (livré par F47).

## Path parameters

| Nom | Type | Contraintes |
|---|---|---|
| `year` | `int` | `2000 ≤ year ≤ 2100` ; hors borne → 422 |

## Request body — `CarbonEditLineRequest`

```jsonc
{
  "code": "electricite",
  "quantity": "45000",
  "country": "CI",            // optionnel ISO-3166-1 alpha-2
  "source_id": "8e3f12c4-..."  // OBLIGATOIRE, doit pointer vers Source verified du tenant
}
```

| Champ | Type | Contraintes |
|---|---|---|
| `code` | `str` | `1..100` non vide ; doit avoir un facteur catalogue actif (sinon 404) |
| `quantity` | `Decimal` | `≥ 0` |
| `country` | `str?` | ISO-3166-1 alpha-2 (2 caractères) si fourni |
| `source_id` | `UUID` | **obligatoire**, doit appartenir au tenant et avoir `statut = "verified"` |

## Response — `200 OK` — `CarbonEditLineResponse`

Idem `CarbonResultOut` + :

```jsonc
{
  "id": "f8e0c2c4-...",                 // nouvelle empreinte
  "year": 2026,
  "total_tco2e": "12.301000",
  "by_scope_kgco2e": { "1": "...", "2": "...", "3": "..." },
  "by_category_kgco2e": { ... },
  "breakdown": [ /* avec la ligne mutée à jour */ ],
  "factor_versions": [ ... ],
  "previous_footprint_id": "f8e0c2c4-...",
  "edited_line_code": "electricite"
}
```

## Erreurs

| Code | Body | Quand |
|---|---|---|
| 401 | unauthorized | JWT manquant |
| 403 | no_account | Utilisateur sans `account_id` |
| 404 | `{"code":"footprint_not_found"}` | Aucune empreinte pour `(account_id, year)` (D11 : pas d'init implicite) |
| 404 | `{"code":"factor_not_found"}` | `code` sans facteur actif pour `pays_iso2`/`year` |
| 400 | `{"code":"source_not_verified"}` | `source_id` introuvable, autre tenant, ou statut ≠ `verified` |
| 422 | Pydantic standard | `quantity < 0`, `source_id` manquant, `country` invalide |

## Effets de bord

1. Charge le **dernier** `carbon_footprint(account_id, year)` → `source_data_json`.
2. Reconstruit `list[CarbonSourceItem]` :
   - Si `code` présent → remplace l'item (quantity, country, source_id).
   - Si `code` absent → ajoute un nouvel item.
3. Vérifie `Source(source_id).statut == "verified"` ET `Source.account_id == account_id`.
4. Appelle `service.compute_footprint(...)` → nouvelle row `carbon_footprint` (`version = previous.version + 1`).
5. Insère 1 `audit_event` :
   - `entity = "carbon_footprint"`
   - `field = "edit-line"`
   - `source_of_change = MANUAL`
   - `old = { code, quantity: <ancienne ou null si ajout>, source_id: <ancienne ou null> }`
   - `new = { code, quantity: <nouvelle>, source_id: <nouvelle>, country }`

## Tests (`backend/tests/carbon/test_edit_line_endpoint.py`)

1. Ligne existante S2 électricité (50 000 kWh) → édition à 45 000 kWh → 200, nouvelle row, breakdown reflète la nouvelle valeur, audit OK.
2. `source_id` manquant → 422 (Pydantic).
3. `source_id` pointe vers une `Source` `pending` → 400 `source_not_verified`.
4. `source_id` appartient à un autre tenant → 400 `source_not_verified` (404 si politique stricte tenant masking sur la Source — à confirmer dans `app.catalog.sources`).
5. `code` inexistant dans le dernier `source_data_json` (ex. ajout d'un poste manquant) → ligne **ajoutée**, total recalculé.
6. `code` sans facteur actif → 404 `factor_not_found`.
7. `quantity = -1` → 422.
8. Cross-tenant (year sans empreinte chez le tenant courant) → 404 `footprint_not_found`.
9. JWT manquant → 401.
10. Audit insertion vérifiée (entité, field, old, new).
