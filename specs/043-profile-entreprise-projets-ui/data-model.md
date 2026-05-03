# Phase 1 — Data Model (F43)

> Note : F43 ne modifie **aucune** table, aucun schéma backend. Ce document décrit (a) les entités consommées par l'UI et leurs invariants, (b) les ViewModels Pinia/composables construits côté front pour servir les pages.

## 1. Entités backend consommées (lecture seule du point de vue F43)

### 1.1 Entreprise (alias `EntrepriseRead`)

Source : `backend/app/entreprise/schemas.py::EntrepriseRead`. Une seule instance par compte (1↔1 avec `account`).

| Champ                          | Type                          | Optionnel | Notes invariants                                          |
|--------------------------------|-------------------------------|-----------|-----------------------------------------------------------|
| `id`                           | UUID                          | non       | identité.                                                 |
| `account_id`                   | UUID                          | non       | RLS (P2).                                                 |
| `version`                      | int                           | non       | concurrence optimiste ; incrémentée à chaque PATCH réussi.|
| **Identité**                   |                               |           |                                                           |
| `raison_sociale`               | string                        | oui       |                                                           |
| `forme_juridique`              | string                        | oui       |                                                           |
| `secteur_principal`            | string                        | oui       | enum dérivé de `/me/entreprise/sectors`.                  |
| `annee_creation`               | int                           | oui       | borné [1900, année courante].                             |
| **Taille**                     |                               |           |                                                           |
| `taille_ca`                    | `MoneyOut { amount, currency }` | oui     | P5 — Decimal côté front (R1).                              |
| `taille_effectif`              | int                           | oui       | borné [0, 1e6].                                            |
| **Localisation**               |                               |           |                                                           |
| `localisation_siege_pays_iso2` | string ISO2                   | oui       | validé serveur.                                            |
| `zones_operation_pays_iso2`    | string[] (ISO2)               | oui       | UEMOA/CEDEAO en cluster front (R8).                        |
| **Gouvernance / Pratiques**    | divers                        | oui       | hérité F11.                                                |
| `field_meta`                   | `dict[field, EntrepriseFieldMeta]` | oui  | provenance & last_updated par champ (P3 audit).            |

### 1.2 Projet (`ProjetRead`)

Source : `backend/app/projets/schemas.py::ProjetRead`. N projets par compte (cap MVP : 1 projet « principal » + brouillons).

| Champ                          | Type                          | Optionnel | Notes invariants                                          |
|--------------------------------|-------------------------------|-----------|-----------------------------------------------------------|
| `id`                           | UUID                          | non       |                                                           |
| `account_id`                   | UUID                          | non       | RLS.                                                       |
| `version`                      | int                           | non       | concurrence optimiste.                                     |
| `nom`                          | string                        | non       | obligatoire à la création.                                 |
| `description`                  | string                        | oui       |                                                            |
| `secteur`                      | string                        | oui       | aligné secteur entreprise.                                 |
| `type_impact`                  | string ∈ enum F12             | oui       | (`mitigation_carbone`, …, `autre`).                        |
| `localisation_pays_iso2`       | string ISO2                   | oui       |                                                            |
| `localisation_region`          | string                        | oui       | libre.                                                     |
| `localisation_lat`             | Decimal                       | oui       | exposer **uniquement** si schéma F12 le supporte.          |
| `localisation_lng`             | Decimal                       | oui       | idem.                                                      |
| `budget`                       | `MoneyOut`                    | oui       | P5.                                                        |
| `horizon_mois`                 | int                           | oui       | [1, 240].                                                  |
| `maturite`                     | string ∈ enum F12             | oui       | (`ideation`, …, `replication`).                            |
| `structure_financement`        | string ∈ enum F12             | oui       | (`subvention`, `pret_concessionnel`, `equity`, `blending`).|
| `statut`                       | string ∈ enum F12 (5 valeurs) | non       | `brouillon, en_recherche_financement, finance, en_execution, cloture` (R2).|
| `score_esg`                    | int 0-100                     | oui       | calcul F23 ; UI lit, n'écrit pas.                          |
| `created_at`, `updated_at`     | datetime                      | non       |                                                            |
| `deleted_at`                   | datetime                      | oui       | soft delete (US 5 / FR-016).                               |

### 1.3 DocumentProjet (`DocumentProjetRead`)

| Champ           | Type     | Notes                                              |
|-----------------|----------|----------------------------------------------------|
| `id`            | UUID     |                                                    |
| `projet_id`     | UUID     |                                                    |
| `nom`           | string   | nom de fichier original.                           |
| `mime`          | string   | dans `ALLOWED_MIME_TYPES` UI (R9).                 |
| `taille_octets` | int      | ≤ 25 MB (R9).                                      |
| `type_doc`      | string   | enum F12 (`faisabilite`, `business_plan`, `etude_impact`, `lettre_soutien`, `photo`, `autre`). |
| `created_at`    | datetime |                                                    |

### 1.4 CompletenessOut

Source : `/me/entreprise/completeness`. Lue à chaque ouverture de page entreprise et après chaque PATCH réussi.

| Champ                          | Type                                  | Notes |
|--------------------------------|---------------------------------------|-------|
| `percentage`                   | int 0–100                             | barre `EntrepriseHeader`. |
| `missing_required_for_features`| list[`{ feature_code, missing_fields[] }`] | tooltip champs manquants. |

### 1.5 ConflictOut

Retourné en `409` par `PATCH /me/entreprise` et `PATCH /me/projets/{id}`.

```ts
type ConflictOut = {
  code: 'version_conflict'
  current_version: number
  your_version: number
  // payload backend complet de l'entité (re-fetch implicite)
}
```

## 2. ViewModels frontend

### 2.1 `useEntrepriseStore` (étendu)

État Pinia (extension de l'existant `frontend/app/stores/entreprise.ts`) :

```ts
interface EntrepriseState {
  data: EntrepriseRead | null
  version: number | null
  completion: { percentage: number; missing: MissingFeatureBlock[] } | null
  loading: boolean
  saving: { [field: string]: boolean }
  errors: { [field: string]: string | null }
  conflict: { field: string; your: unknown; current: unknown } | null
  pendingChanges: { [field: string]: unknown } // pour bannière offline
}
```

Actions :
- `loadAll()` : `GET /me/entreprise` + `GET /me/entreprise/completeness` en parallèle.
- `patchField(field, value)` : enfile le changement, debounce 800 ms, `AbortController`.
- `resolveConflict(choice: 'mine' | 'theirs' | 'cancel')` : envoie le PATCH avec la valeur retenue ou re-fetch.
- `applyExternalUpdate(payload)` : chemin déclenché par `useChatEventBus`.

### 2.2 `useProjetsStore` (nouveau)

```ts
interface ProjetsState {
  list: ProjetSummary[]
  byId: Map<UUID, ProjetRead>
  versionById: Map<UUID, number>
  loading: boolean
  saving: { [projetId: string]: { [field: string]: boolean } }
  errors: { [projetId: string]: { [field: string]: string | null } }
  conflicts: { [projetId: string]: ConflictBlock | null }
}
```

Actions :
- `loadList()` : `GET /me/projets`.
- `loadOne(id)` : `GET /me/projets/{id}` + `GET /me/projets/{id}/documents`.
- `create(payload)` : `POST /me/projets` (utilisé par wizard).
- `patchField(id, field, value)` : équivalent entreprise.
- `softDelete(id)` : `DELETE /me/projets/{id}`.
- `transition(id, statut_cible)` : `POST /me/projets/{id}/transition` (réservé évolutions de statut explicites — non utilisé en autosave).

### 2.3 `useProjetWizardState`

```ts
type WizardStep = 1 | 2 | 3 | 4
type WizardData = {
  step1: { nom: string; description: string }
  step2: { secteur: string; type_impact: string }
  step3: { localisation_pays_iso2: string; localisation_region: string; lat?: Decimal; lng?: Decimal }
  step4: { budget: MoneyIn; horizon_mois: number }
}
```

Validation par step via Zod schemas (R6). Soumission finale = `POST /me/projets` avec mapping vers `ProjetCreate`.

## 3. Invariants front ↔ back

| Invariant                                      | Mécanisme                                                                 |
|------------------------------------------------|---------------------------------------------------------------------------|
| Money toujours `{Decimal, ISO 4217}`           | `MoneyField.vue` + `useDecimal` ; `Number` interdit (lint custom à confirmer en tasks). |
| `version` envoyé à chaque PATCH                | `useEntrepriseProfile` / `useProjet` injectent `version` automatiquement. |
| Pays = ISO2 strict                             | `CountryMultiSelect.vue` n'autorise que des codes issus de la liste interne. |
| Soft delete réversible 30 j                    | UI : bouton « Restaurer » dans la liste avec filtre « Récemment supprimés » (post-MVP, hors scope F43 P1). |
| Conflit chat ↔ user                            | flux R4 + R5 ; aucun écrasement silencieux.                                |
| Saisie atomique champ par champ                | PATCH partiel, jamais le profil entier.                                   |

## 4. Transitions d'état (Projet — vue dérivée)

```
brouillon ──► en_recherche_financement ──► finance ──► en_execution ──► cloture
       \                                                     │
        \                                                    ▼
         ────► (soft delete ⇒ deleted_at not null) ◄────────┘
```

L'UI MVP ne gère **pas** explicitement les transitions de statut (laissées au tool LLM `update_projet_statut` ou à l'admin). La page détail affiche le statut courant et le sous-badge dérivé « Candidature en cours » si applicable (R2).

## 5. Champs sensibles RGPD

Aucun champ de cette feature n'introduit de PII supplémentaire au-delà de ce que F11/F12 déclarent déjà au registre. La feature n'expose pas de données personnelles d'une PME à une autre (tout passe par RLS).
