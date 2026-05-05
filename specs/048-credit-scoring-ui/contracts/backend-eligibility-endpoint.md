# Contract — `GET /me/credit-score/eligibility`

## Purpose

Évaluer à la volée l'éligibilité de la PME courante à chaque dispositif de financement vert du catalogue actif. Alimente US3 (badges) et US3 AS1/AS2 (modal détail + raison principale + critères exhaustifs).

## Request

`GET /me/credit-score/eligibility?entreprise_id={uuid}`

| Param | In | Type | Required | Default | Description |
|--|--|--|--|--|--|
| `entreprise_id` | query | UUID | non | dérivé de l'utilisateur | override admin (héritage F29) |

**Auth** : `Depends(get_current_pme)`.

## Response 200

```json
{
  "items": [
    {
      "code": "boad_vert",
      "label": "BOAD-vert",
      "description": "Ligne de crédit verte de la Banque Ouest-Africaine de Développement…",
      "status": "eligible",
      "primary_reason": null,
      "criteria": [
        {"code":"min_combine_score","label":"Score crédit ≥ 60","threshold":"60","actual":"72","met":true,"blocking":true},
        {"code":"min_subscore_engagement_esg","label":"Engagement ESG ≥ 50","threshold":"50","actual":"65","met":true,"blocking":true},
        {"code":"required_min_size","label":"Taille minimum PME","threshold":"pme","actual":"pme","met":true,"blocking":true}
      ],
      "matching_offer_query": "instrument=ligne_credit&dispositif=boad_vert",
      "source_id": "5e2a-…-verified-source-uuid",
      "version": 1,
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_to": null
    },
    {
      "code": "ecobank_green_lending",
      "label": "Ecobank Green Lending",
      "description": "Programme de prêts verts Ecobank pour PME…",
      "status": "not_eligible",
      "primary_reason": "Score crédit < 70 requis (actuel : 72 — d'autres critères manquent)",
      "criteria": [
        {"code":"min_combine_score","label":"Score crédit ≥ 70","threshold":"70","actual":"72","met":true,"blocking":true},
        {"code":"min_subscore_solidite_financiere","label":"Solidité financière ≥ 75","threshold":"75","actual":"70","met":false,"blocking":true},
        {"code":"excluded_sectors","label":"Secteur non exclu","threshold":"none","actual":"agroalimentaire","met":true,"blocking":true}
      ],
      "matching_offer_query": "instrument=pret&dispositif=ecobank_green_lending",
      "source_id": "9b1c-…-verified-source-uuid",
      "version": 1,
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_to": null
    }
  ],
  "evaluated_at": "2026-05-04T08:30:00Z",
  "catalog_version_max": 1
}
```

Schéma : `EligibilityListOut` / `EligibilityBadgeOut` / `CriterionEvalOut` (cf. `data-model.md`).

**Statut `incomplete`** : utilisé quand un critère bloquant dépend d'un sous-score `null` (ex. ESG non renseigné). `primary_reason` contient le motif.

## Response errors

| Code | Cas | Body |
|--|--|--|
| 401 | JWT manquant | `{detail: "Not authenticated"}` |
| 422 | `entreprise_id` non rattachée | `{detail: {code: "entreprise_required", ...}}` |

Pas de 404 catalogue vide → `{items: []}` 200.

## Sourçage (P1)

Chaque `EligibilityBadgeOut` expose `source_id` pointant vers une `Source` `verified` (document officiel BOAD/SUNREF/Ecobank). Le test cas (7) vérifie l'existence et le statut de la source.

## Versioning (P4)

Chaque dispositif porte `version` + `valid_from` + `valid_to`. L'endpoint ne retourne que les règles actives (`valid_from <= now < valid_to or valid_to is None`). Un changement de seuil → nouvelle version, l'ancienne reste consultable côté audit (post-MVP).

## RLS

Évalue strictement contre le `credit_score` et l'`entreprise` du tenant courant. Aucune lecture cross-tenant.

## Audit

Lecture pure — pas d'audit.

## Tests pytest associés

`backend/tests/credit/test_eligibility_endpoint.py` (8 cas, cf. plan.md).
