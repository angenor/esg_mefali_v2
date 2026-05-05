# Phase 1 — Data Model

> Cette feature **ne crée aucune nouvelle table**. Toutes les entités persistées appartiennent à F24 (rapports) et F30 (attestations) et sont accédées en lecture / mutation existante via les endpoints déjà livrés. Ce document décrit (a) les entités côté backend telles que vues par l'UI et (b) les états de la machine côté UI ajoutés pour cette feature.

## 1. Entités existantes (lecture)

### Rapport (table `rapports`, propriété F24)

Champs utilisés par l'UI :

| Champ | Type | UI | Notes |
|---|---|---|---|
| `id` | UUID | clé interne | jamais affichée |
| `account_id` | UUID | masqué | RLS |
| `type` | enum `conformite` \| `carbone` \| `candidature` | colonne « Type » | libellé via dictionnaire FR |
| `referentiel_id` | UUID nullable | méta dans drawer | résolu en libellé via catalog |
| `period_from`, `period_to` | date | colonne « Période » | format `MMM YYYY → MMM YYYY` |
| `created_at` | datetime | colonne « Date » | format `dd/MM/yyyy` |
| `size_bytes` | int | colonne « Taille » | format humain (KB, MB) |
| `status` | enum `ready` \| `generating` \| `failed` | colonne « Statut » + chip couleur | |
| `download_filename` | string | nom de fichier téléchargé | |
| `hash_sha256` | string | méta dans drawer | preuve d'intégrité |

Endpoints utilisés (F24) :

- `GET /me/rapports` → liste paginée.
- `POST /me/rapports/generate` → crée une demande, retourne l'`id` de génération.
- `GET /me/rapports/generate/{id}/stream` *(à confirmer Phase 2 — fallback `GET /me/rapports/generate/{id}` polling)* → événements `progress` / `done` / `failed`.
- `GET /me/rapports/{id}/download` → téléchargement direct.
- `GET /me/rapports/{id}/preview-url` *(à confirmer Phase 2)* → `{url, expires_at}` URL signée TTL ≤ 5 min.

### Attestation (table `attestations`, propriété F30)

Champs utilisés par l'UI authentifiée et publique :

| Champ | UI auth | UI publique | Notes |
|---|---|---|---|
| `public_id` | colonne (court) | clé URL | opaque non-énumérable |
| `type` | colonne « Type » | en haut de la page | libellé via dictionnaire (FR/EN) |
| `status` | chip | bandeau si `revoked` | enum `active` \| `expired` \| `revoked` |
| `issued_at` | colonne « Émise » | section dates | |
| `expires_at` | colonne « Expire » | section dates | |
| `revoked_at` | masqué si null | bandeau si présent | |
| `revoke_reason` | masqué | bandeau si présent | enum fermé (voir ci-dessous) |
| `entity_legal_name` | colonne | titre | |
| `payload` | masqué | corps de page | dict structuré KPI + sources |
| `signature_valid` | masqué | badge ✓/✗ | calculé côté serveur |

Endpoints utilisés (F30) :

- `GET /me/attestations` → liste authentifiée.
- `POST /me/attestations/{id}/revoke` → body `{reason: enum}`.
- `GET /verify/{public_id}` → page HTML publique (Nuxt SSR consomme `/verify/{public_id}/json`).
- `GET /verify/{public_id}/json` → payload public (sans données d'autres tenants).
- `GET /verify/{public_id}/download` → PDF signé téléchargeable.

### Source (table `sources`, propriété catalogue)

Champs lus côté UI publique (lecture seule, exposés via `payload` de l'attestation) :

| Champ | UI publique | Notes |
|---|---|---|
| `id` | tooltip | référence interne |
| `title` | libellé du repère | |
| `url` | lien externe | s'ouvre dans nouvel onglet `rel="noopener noreferrer"` |
| `verified_at` | tooltip | preuve de validation |

## 2. Énumérations contrôlées (exposées côté UI)

### `RevokeReason`

| Code | Libellé FR | Libellé EN |
|---|---|---|
| `erreur_emission` | Erreur d'émission | Issuance error |
| `donnees_invalidees` | Données invalidées | Data invalidated |
| `demande_pme` | Demande de la PME | At PME's request |
| `expiration_anticipee` | Expiration anticipée | Early expiration |
| `autre` | Autre motif | Other reason |

> Toujours exposée publiquement (FR-012). Texte libre **interdit**.

### `RapportType`

| Code | Libellé FR |
|---|---|
| `conformite` | Conformité |
| `carbone` | Carbone |
| `candidature` | Candidature |

### `AttestationType` (catalogue F30, dictionnaire bilingue requis pour `/verify`)

| Code | Libellé FR | Libellé EN |
|---|---|---|
| `conformite_esg` | Conformité ESG | ESG Compliance |
| `bilan_carbone` | Bilan carbone | Carbon footprint |
| `score_credit` | Score crédit | Credit score |
| `dossier_candidature` | Dossier de candidature | Application file |

### `RapportStatus` (UI uniquement — projection des statuts backend)

| Code | UI |
|---|---|
| `ready` | chip vert « Prêt » |
| `generating` | chip orange « En cours » + spinner |
| `failed` | chip rouge « Échec » + bouton « Réessayer » |

## 3. États de la machine UI (génération de rapport)

```
        ┌──────────────┐      submit       ┌────────────┐
        │  modal idle  │ ────────────────> │  pending   │
        └──────────────┘                   └─────┬──────┘
                                                 │ SSE open
                                                 ▼
                                          ┌────────────┐
              error/timeout               │  running   │
              ◄────────────────────────── └─────┬──────┘
                                                 │ done
                                                 ▼
                                          ┌────────────┐
                                          │  ready     │
                                          └─────┬──────┘
                                                 │ user click
                                                 ▼
                                          ┌────────────┐
                                          │ downloaded │
                                          └────────────┘
```

Persistance côté UI : store Pinia `useReportsStore` avec `pending: Map<id, GenerationState>`. À l'arrivée sur `/rapports`, le store rappelle `GET /me/rapports/generate/<id>` pour chaque ID encore `pending` ou `running`, et reconnecte le SSE si nécessaire.

## 4. Stores Pinia (résumé)

### `useReportsStore`

```ts
state: {
  reports: Rapport[]              // table
  pending: Map<string, GenState>  // générations en cours
  loading: boolean
  error: string | null
}
actions: {
  fetchAll()
  generate(payload: GenerateRequest): Promise<string>  // returns generationId
  subscribeStream(generationId: string)
  cancelStream(generationId: string)
  downloadPreviewUrl(rapportId: string): Promise<{url, expiresAt}>
}
```

### `useAttestationsStore`

```ts
state: {
  attestations: Attestation[]
  loading: boolean
  error: string | null
}
actions: {
  fetchAll()
  revoke(id: string, reason: RevokeReason): Promise<void>
  buildVerifyUrl(publicId: string): string  // ${APP_URL}/verify/${publicId}
  buildQrPng(publicId: string): Promise<Blob>  // qrcode lib, level=H
}
```

## 5. Invariants vérifiés par l'UI

- **INV-1** (P2) : aucun appel n'est fait sans session pour `/me/...` ; sur 401, redirige vers login.
- **INV-2** (FR-007) : la table affiche uniquement les rapports/attestations renvoyés par l'API `me/...` ; pas de filtrage côté client supposant un autre `account_id`.
- **INV-3** (FR-014) : aucune validation cryptographique côté client ; `signature_valid` provient du backend.
- **INV-4** (FR-016) : le rendu critique de `/verify/{id}` (verdict + identité + dates + KPI) est intégralement présent dans le HTML SSR avant hydratation ; testé via `curl --no-buffer | grep`.
- **INV-5** (FR-002) : aucune URL de PDF persistée côté front au-delà de `expires_at`.
