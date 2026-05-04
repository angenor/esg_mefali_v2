# Data Model — F47 Empreinte carbone UI

**Date** : 2026-05-04
**Phase** : 1 (Design & Contracts)
**Statut** : Aucun changement de schéma SQL. Seuls les **contrats Pydantic** sont enrichis (ajout d'un champ optionnel) et de nouveaux **DTO de réponse** apparaissent.

## 1. Entités persistées (existantes — non modifiées)

### 1.1 `carbon_footprint` (F28, table existante)

Snapshot complet d'une empreinte carbone à un instant `t` pour `(account_id, year)`. Append-only (jamais d'UPDATE/DELETE).

| Colonne | Type | Contraintes | Rôle pour F47 |
|---|---|---|---|
| `id` | UUID | PK | Identifie un calcul |
| `account_id` | UUID FK→`account.id` | NOT NULL, RLS | Cloisonnement tenant (P2) |
| `entreprise_id` | UUID NULL | — | Multi-entreprise futur |
| `year` | int | NOT NULL | Période couverte |
| `source_data_json` | JSONB | NOT NULL | Liste des `CarbonSourceItem` soumis (rejouable par `recompute`) |
| `total_tco2e` | Numeric(18,6) | NOT NULL | KPI synthèse |
| `by_scope_json` | JSONB | NOT NULL | `{ "1": Decimal, "2": Decimal, "3": Decimal }` en kgCO2e |
| `breakdown_json` | JSONB | NOT NULL | Liste des `CarbonBreakdownLineOut` (snapshot immuable, P4) |
| `factor_versions_json` | JSONB | NOT NULL | Liste `[{ factor_id, version, valid_from, source_id }]` |
| `computed_at` | timestamptz | NOT NULL | Horodatage du calcul |
| `version` | int | NOT NULL, default 1 | Incrémenté à chaque recalcul (`max(version)+1` pour la même `year`) |

**Invariants F47** :
- L'« empreinte courante » d'une `year` = la row avec `computed_at` max pour cette `(account_id, year)`.
- L'historique d'une année = toutes les rows triées desc par `computed_at`.
- L'index multi-année = la row avec `computed_at` max **par year**, triée desc par year.

### 1.2 `facteur_emission` (F09, table existante)

Versionné, non réécrit. Consommé en lecture par `service.compute_footprint` via `app.catalog.facteurs_emission.lookup.get_facteur(code, pays_iso2, at)`.

| Colonne | Type | Rôle pour F47 |
|---|---|---|
| `id` | UUID | PK |
| `code` | str | Match avec `CarbonSourceItem.code` |
| `pays_iso2` | str(2) NULL | Modulation pays |
| `value` | Numeric | `kgCO2e/<unit>` |
| `unit` | str | Ex. `kWh`, `litre`, `kg`, `km` |
| `scope` | str | `"1"`, `"2"`, `"3"` |
| `categorie` | str | `combustion_fixe`, `electricite`, `achats`, … |
| `version` | int | Versionnement P4 |
| `valid_from` | date | |
| `valid_to` | date NULL | |
| `source_id` | UUID FK→`source.id` | Source vérifiée du facteur |

### 1.3 `source` (F09, table existante)

Justificatif vérifié (statut `verified`/`pending`/`revoked`). Nouvellement référencée par les **lignes** d'activité (champ `source_id` ajouté à `CarbonSourceItem` — voir §2.1).

### 1.4 `audit_event` (F03, table existante)

Append-only, un événement par mutation. F47 produit deux nouveaux types d'événements :

| `entity` | `field` | `source_of_change` | `old` / `new` | Émis par |
|---|---|---|---|---|
| `carbon_footprint` | `edit-line` | `manual` | `{ code, quantity, source_id, country }` | `POST /me/carbon/{year}/edit-line` |
| `carbon_footprint` | `recompute` | `manual` | `{ trigger: "user", footprint_id_before, footprint_id_after }` | `POST /me/carbon/{year}/recompute` |

## 2. Schémas Pydantic (modifications + nouveautés)

### 2.1 `CarbonSourceItem` (modifié — extension rétrocompatible)

```python
class CarbonSourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., ge=0)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_id: UUID | None = Field(default=None)  # NOUVEAU — None accepté pour rétrocompat
```

**Règle d'application** :
- `POST /me/carbon/compute` (existant) : `source_id` accepté `None` (pas de validation supplémentaire).
- `POST /me/carbon/{year}/edit-line` (nouveau) : `source_id` requis non null + le service vérifie que la `Source` existe, est du même `account_id`, et a `statut == "verified"`.

### 2.2 `CarbonIndexEntryOut` (nouveau)

```python
class CarbonIndexEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    footprint_id: UUID
    year: int
    total_tco2e: Decimal
    computed_at: datetime
    version: int
```

### 2.3 `CarbonIndexOut` (nouveau)

```python
class CarbonIndexOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entries: list[CarbonIndexEntryOut]  # triées desc par year
```

### 2.4 `CarbonRecomputeResponse` (nouveau)

Identique à `CarbonResultOut` (réponse de `POST /me/carbon/compute`) avec en plus le `previous_footprint_id` pour permettre à l'UI de calculer un delta optionnel.

```python
class CarbonRecomputeResponse(CarbonResultOut):
    previous_footprint_id: UUID | None
```

### 2.5 `CarbonEditLineRequest` (nouveau)

```python
class CarbonEditLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., ge=0)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source_id: UUID  # OBLIGATOIRE
```

### 2.6 `CarbonEditLineResponse` (nouveau)

Idem `CarbonResultOut` + delta optionnel et identifiant de la ligne mutée.

```python
class CarbonEditLineResponse(CarbonResultOut):
    previous_footprint_id: UUID
    edited_line_code: str
```

## 3. Modèle conceptuel côté frontend

### 3.1 Types TS miroirs (`frontend/app/types/carbon.ts`)

```ts
export type Scope = "1" | "2" | "3"
export type CarbonPosteCode = string  // e.g. "combustion_fixe", "electricite", ...

export interface CarbonBreakdownLine {
  code: string
  quantity: string  // Decimal sérialisé
  unit: string
  factorId: string
  factorValue: string  // Decimal
  factorSourceId: string
  factorVersion: number
  scope: Scope
  categorie: string
  kgco2e: string  // Decimal
  sourceId: string | null  // null si héritée d'un compute legacy sans source
}

export interface CarbonFootprint {
  id: string
  year: number
  totalTco2e: string
  byScope: { "1": string; "2": string; "3": string }  // kgCO2e
  byCategory: Record<string, string>
  breakdown: CarbonBreakdownLine[]
  factorVersions: Array<{ factorId: string; version: number; validFrom: string; sourceId: string }>
  computedAt: string
  version: number
}

export interface CarbonIndexEntry {
  footprintId: string
  year: number
  totalTco2e: string
  computedAt: string
  version: number
}
```

### 3.2 Modèle dérivé : « ligne virtuelle » groupée par scope/poste

`groupCarbonByScope.ts` produit :

```ts
export interface ScopePosteGroup {
  scope: Scope
  posteCode: CarbonPosteCode
  posteLabel: string  // i18n
  lines: CarbonBreakdownLine[]
  subtotalKgCo2e: string  // Decimal somme des lines
}

export interface ScopeBreakdown {
  scope: Scope
  totalKgCo2e: string
  groups: ScopePosteGroup[]  // un par poste attendu, vide si non renseigné
  expectedPostesCount: number
  filledPostesCount: number
}

export type GroupedBreakdown = Record<Scope, ScopeBreakdown>
```

### 3.3 Modèle dérivé : couverture

`computeCarbonCoverage.ts` produit :

```ts
export interface CoverageSnapshot {
  scope1Pct: number  // 0..100
  scope2Pct: number
  scope3Pct: number
  globalPct: number
  isLow: boolean  // true si globalPct < 60
}
```

### 3.4 État du store Pinia `useCarbonStore`

```ts
interface CarbonStoreState {
  index: CarbonIndexEntry[] | null  // multi-année
  indexLoadedAt: number | null      // pour TTL 60s
  footprints: Record<number, CarbonFootprint | null>  // par year
  loadingFootprint: Record<number, boolean>
  loadingRecompute: Record<number, boolean>
  loadingEditLine: Record<number, boolean>
  errorByYear: Record<number, string | null>
  wizardDraft: WizardDraft | null  // hydraté depuis localStorage
  selectedYear: number  // année courante affichée
}
```

## 4. Diagramme de séquence — Édition d'une ligne (US3)

```text
PME ──clique "Modifier" sur ligne S2 électricité──▶ EditLineDrawer.vue
                                                       │
                                                       ▼
                                              ChatBottomSheet (ask_form)
                                                       │
PME ──saisit 45000 kWh + sélectionne source────────────▶ useCarbonEdit.submit()
                                                       │
                                                       ▼
                            POST /me/carbon/{year}/edit-line
                                                       │
                                                       ▼
                            service.edit_line(account, year, payload)
                              ├─ load latest CarbonFootprint(account, year) → source_data_json
                              ├─ assert payload.source_id ∈ verified Sources(account)
                              ├─ rebuild list[CarbonSourceItem] (replace by code, append if absent)
                              ├─ service.compute_footprint(...)  # nouvelle row carbon_footprint
                              └─ record_audit(entity="carbon_footprint", field="edit-line",
                                              source_of_change=MANUAL, old, new)
                                                       │
                                                       ▼
                            200 OK CarbonEditLineResponse
                                                       │
useCarbonStore.applyFootprint(year, response)──────────┘
EventBus.emit("entity_updated", { entity: "carbon_footprint", year })
EventBus.emit("context_invalidated", { entity: "carbon_footprint" })  # P8
```

## 5. Règles de validation côté backend

| Règle | Endpoint | Action |
|---|---|---|
| `source_id` obligatoire et `Source.statut == verified` | `POST .../edit-line` | 400 `source_not_verified` sinon |
| `source_id` appartient au tenant | `POST .../edit-line` | 404 (tenant masking, P2) sinon |
| `quantity ≥ 0` | `POST .../edit-line` | 422 (Pydantic) sinon |
| `code` connu dans le catalogue facteur (pour `pays_iso2`/`year`) | `POST .../edit-line`, `POST .../recompute` | 404 `factor_not_found` sinon |
| `year` doit avoir au moins un `carbon_footprint` existant | `POST .../recompute`, `POST .../edit-line` (par défaut on autorise l'edit-line à initialiser une empreinte vide ; voir D11) | 404 `footprint_not_found` si absent et politique strict |
| Pas plus d'1 recompute toutes les 5 secondes par tenant | `POST .../recompute` | 429 (SlowAPI) sinon |

**D11 (clarification)** : `edit-line` exige une empreinte préexistante (sinon `404 footprint_not_found`). La création « vierge » se fait via le wizard empty-state qui appelle `POST /me/carbon/compute` directement.

## 6. Constantes partagées (frontend)

`frontend/app/lib/groupCarbonByScope.ts` exporte :

```ts
export const CARBON_EXPECTED_POSTS_BY_SCOPE: Record<Scope, ReadonlyArray<CarbonPosteCode>> = {
  "1": ["combustion_fixe", "combustion_mobile", "fugitives"],
  "2": ["electricite", "vapeur", "chaleur", "froid"],
  "3": ["achats", "transport_amont", "dechets", "deplacements", "transport_aval"],
}
```

Cette liste est **MVP-figée** : aucune configuration runtime. L'extension à 15 catégories Scope 3 est post-MVP.
