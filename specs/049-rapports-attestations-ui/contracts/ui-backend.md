# Contrats UI ↔ Backend (F49)

> Cette feature ne définit pas de nouveaux contrats publics ; elle consomme F24 et F30. Ce document précise les requêtes/réponses utilisées et les **trois additions backend mineures** identifiées en Phase 0.

## A. Endpoints existants (F24 — rapports)

### A.1 `GET /me/rapports`

Liste paginée des rapports de la PME courante.

```http
GET /me/rapports?limit=50&offset=0
Authorization: Bearer <jwt>
```

Réponse 200 :

```json
{
  "items": [
    {
      "id": "uuid",
      "type": "conformite|carbone|candidature",
      "referentiel_id": "uuid|null",
      "period_from": "2025-01-01",
      "period_to": "2025-12-31",
      "created_at": "2026-05-04T10:30:00Z",
      "size_bytes": 1245678,
      "status": "ready|generating|failed",
      "download_filename": "rapport-conformite-2025.pdf",
      "hash_sha256": "abc123…"
    }
  ],
  "total": 17
}
```

### A.2 `POST /me/rapports/generate`

Lance une génération asynchrone.

```http
POST /me/rapports/generate
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "type": "conformite",
  "referentiel_id": "uuid",
  "period_from": "2025-01-01",
  "period_to": "2025-12-31"
}
```

Réponse 202 :

```json
{ "generation_id": "uuid", "status": "pending" }
```

### A.3 `GET /me/rapports/{id}/download`

Téléchargement direct du PDF (existant).

## B. Additions backend Phase 2 (mineures)

### B.1 `GET /me/rapports/generate/{generation_id}/stream` (SSE — NEW)

Flux d'événements `text/event-stream` :

```
event: progress
data: {"step":"layout","percent":45}

event: done
data: {"rapport_id":"uuid","download_filename":"…"}

event: failed
data: {"error":"reason_code"}
```

- `Last-Event-ID` honoré pour la reprise après déconnexion.
- Auth : session PME ; RLS sur `account_id`.
- Si non livré, fallback UI : `GET /me/rapports/generate/{id}` polling 1 s.

### B.2 `GET /me/rapports/{id}/preview-url` (NEW)

Retourne une URL signée TTL ≤ 5 min permettant l'aperçu inline dans une `<iframe>`.

```http
GET /me/rapports/{id}/preview-url
Authorization: Bearer <jwt>
```

Réponse 200 :

```json
{
  "url": "https://app.esg-mefali.com/storage/preview?t=…&sig=…",
  "expires_at": "2026-05-04T10:35:00Z"
}
```

L'URL servant le PDF doit valider la signature **et** vérifier que `account_id` correspond. Aucune URL d'aperçu permanente.

### B.3 `label_en` sur indicateurs publics (NEW, optionnel)

Sur `GET /verify/{public_id}/json`, chaque KPI émis dans `payload.indicators[]` peut porter un `label_en` :

```json
{
  "code": "co2_intensity",
  "label": "Intensité carbone",
  "label_en": "Carbon intensity",
  "value": 32.5,
  "unit": "kgCO2e/kFCFA",
  "source_id": "uuid"
}
```

Si `label_en` absent, l'UI affiche `label` même en mode EN.

## C. Endpoints existants (F30 — attestations)

### C.1 `GET /me/attestations`

```http
GET /me/attestations
Authorization: Bearer <jwt>
```

Réponse 200 :

```json
[
  {
    "id": "uuid",
    "public_id": "att_abc123",
    "type": "conformite_esg|bilan_carbone|score_credit|dossier_candidature",
    "status": "active|expired|revoked",
    "issued_at": "2026-04-01T00:00:00Z",
    "expires_at": "2027-04-01T00:00:00Z",
    "revoked_at": null,
    "revoke_reason": null,
    "verify_url": "https://app.esg-mefali.com/verify/att_abc123"
  }
]
```

### C.2 `POST /me/attestations/{id}/revoke`

```http
POST /me/attestations/{id}/revoke
Authorization: Bearer <jwt>
Content-Type: application/json

{ "reason": "erreur_emission|donnees_invalidees|demande_pme|expiration_anticipee|autre" }
```

Réponse 200 :

```json
{ "id": "uuid", "status": "revoked", "revoked_at": "2026-05-04T10:40:00Z", "revoke_reason": "erreur_emission" }
```

Effet : invalidation explicite du cache CDN sur `/verify/{public_id}` (cf. R1).

### C.3 `GET /verify/{public_id}/json` (public, sans auth)

Source de vérité du SSR Nuxt.

```http
GET /verify/att_abc123/json
```

Réponse 200 :

```json
{
  "public_id": "att_abc123",
  "type": "conformite_esg",
  "entity_legal_name": "ACME SARL",
  "status": "active",
  "issued_at": "2026-04-01T00:00:00Z",
  "expires_at": "2027-04-01T00:00:00Z",
  "revoked_at": null,
  "revoke_reason": null,
  "signature_valid": true,
  "payload": {
    "indicators": [
      {
        "code": "co2_intensity",
        "label": "Intensité carbone",
        "label_en": "Carbon intensity",
        "value": 32.5,
        "unit": "kgCO2e/kFCFA",
        "source_id": "src_xyz"
      }
    ],
    "sources": [
      { "id": "src_xyz", "title": "GHG Protocol Corporate Standard", "url": "https://…", "verified_at": "2026-01-15T00:00:00Z" }
    ]
  }
}
```

Cas d'erreur :
- `404 Not Found` si l'identifiant est inconnu ou s'il appartient à un autre tenant — pas de `403` (P2).
- `200` avec `signature_valid: false` si la signature ne valide pas (l'UI affiche le badge ✗).
- `200` avec `status: "revoked"` et `revoke_reason` rempli si révoquée.

### C.4 `GET /verify/{public_id}/download` (public)

PDF signé téléchargeable directement, exposé sur la page publique (FR-013 — preuve téléchargeable).

## D. Cache et headers

Sur la page Nuxt SSR `/verify/[id]`, après l'appel `GET /verify/{id}/json` :

```ts
setResponseHeader(event, 'Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=60')
setResponseHeader(event, 'Content-Language', lang)  // "fr" ou "en"
```

À la révocation côté backend, l'invalidation du cache CDN est déclenchée (purger l'URL `/verify/{public_id}` et `/verify/{public_id}/json`). Hors prod, le TTL ≤ 60 s est suffisant pour SC-009.

## E. Schémas i18n statiques (front, hors backend)

Fichiers JSON livrés avec le front :

```
frontend/app/i18n/verify/fr.json
frontend/app/i18n/verify/en.json
```

Couvrent : libellés statiques, `RevokeReason`, `AttestationType`, formats de date.
