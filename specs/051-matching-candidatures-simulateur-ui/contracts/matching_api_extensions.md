# Contracts — Matching API extensions (F51)

Ces contrats étendent F25. Tous les schémas Pydantic v2 ont `extra='forbid'`.

## 1. `GET /me/projets/{projet_id}/matching` (existant — F25, rappel)

Renvoie les offres scorées pour un projet donné. Auth : PME.

```jsonc
// 200 OK
{
  "items": [
    {
      "offre_id": "uuid",
      "score": 0.87,
      "rang": 1,
      "nom": "Ligne verte BICC 2024",
      "intermediaire": { "id": "uuid", "nom": "BICC", "geolocation": { "lat": 5.31, "lng": -4.04 } },
      "type": "credit",
      "montant_min": { "amount": "10000", "currency": "EUR" },
      "montant_max": { "amount": "500000", "currency": "EUR" },
      "duree_min_mois": 12,
      "duree_max_mois": 84,
      "secteurs": ["renouvelable", "agriculture"]
    }
  ],
  "count": 10
}
```

## 2. `GET /me/offres` (NOUVEAU)

Catalogue d'offres **non scoré** pour découverte hors projet ou bypass empty state. Auth : PME.

Query params (tous optionnels) :

- `type`: `credit | subvention | garantie | autre`
- `montant_min_eur`: int (le filtrage se fait en EUR équivalent — conversion XOF→EUR via parité 655.957 si nécessaire)
- `montant_max_eur`: int
- `duree_min_mois`: int
- `duree_max_mois`: int
- `intermediaire_id`: UUID
- `secteur`: string (lowercase, e.g. `renouvelable`)
- `q`: string (recherche fulltext sur `nom + description`)
- `limit`: int [1..50] default 20
- `cursor`: opaque pagination cursor (post-MVP, `null` au MVP).

Response :

```jsonc
{
  "items": [
    {
      "offre_id": "uuid",
      "nom": "Ligne verte BICC 2024",
      "intermediaire": { "id": "uuid", "nom": "BICC", "geolocation": null | { "lat": "...", "lng": "..." } },
      "type": "credit",
      "montant_min": { "amount": "10000", "currency": "EUR" },
      "montant_max": { "amount": "500000", "currency": "EUR" },
      "duree_min_mois": 12,
      "duree_max_mois": 84,
      "secteurs": ["renouvelable"],
      "accepted_languages": ["fr"]
    }
  ],
  "count": 1,
  "next_cursor": null
}
```

Erreurs : 401 (no auth), 403 (no account).

## 3. `GET /me/offres/{offre_id}` (NOUVEAU)

Détail offre pour le drawer. Auth : PME.

```jsonc
{
  "offre_id": "uuid",
  "nom": "...",
  "description": "...",
  "intermediaire": { "id": "uuid", "nom": "BICC", "url": "https://...", "geolocation": null | {...} },
  "type": "credit",
  "montant_min": {...},
  "montant_max": {...},
  "duree_min_mois": 12,
  "duree_max_mois": 84,
  "secteurs": ["renouvelable"],
  "documents_requis": [
    { "key": "k_kbis", "label": "Extrait Kbis < 3 mois", "format": "pdf|image" }
  ],
  "conditions": ["Condition A...", "..."],
  "lien_externe": "https://...",
  "source_id": "uuid"
}
```

Erreurs : 404 si non publiée ou non visible (RLS via `offre.published_at IS NOT NULL`).

## 4. `GET /me/fonds/{fonds_id}/intermediaires-comparator` (existant F25)

Inchangé. Utilisé par `/matching/compare` lorsque la PME compare des offres d'un même fonds.

---

## Erreurs communes

| Code HTTP | `code` | Cas |
|---|---|---|
| 400 | `invalid_filter` | montant_min > montant_max, duree négatif, etc. |
| 401 | (FastAPI default) | Pas de JWT |
| 403 | `no_account` | User sans `account_id` |
| 404 | `offre_not_found` | Offre inexistante / non publiée |
