# Contract — Composants & composables (F43)

## 1. Pages

### 1.1 `pages/profil/entreprise.vue`
- **Layout** : `default` (sidebar + bottom nav).
- **Auth** : page protégée (middleware `auth` existant).
- **Données SSR** : `useEntrepriseStore().loadAll()` via `useAsyncData`.
- **Slots / sections** :
  - `<EntrepriseHeader />` (barre complétion + boutons globaux : Historique, Aller au chat).
  - 5 `<SectionCard />` (Identité, Taille, Localisation, Gouvernance, Pratiques).
  - `<ConflictDialog />` global, monté en téléport.
  - `<HistoryDrawer />` (P2, ouvert via bouton « Historique » par section).

### 1.2 `pages/profil/projets/index.vue`
- Liste `<ProjetCard />` ou `<ProjetEmptyState />` si aucun projet actif.
- Bouton « Nouveau projet » → ouvre `<ProjetWizard />`.

### 1.3 `pages/profil/projets/[id].vue`
- 5 sections : Identité, Description, Localisation, Budget, Documents.
- `<ProjetDocuments />` consomme `useProjetsStore().documents(id)`.
- Bouton « Supprimer » → `UiModal` confirmation → `softDelete(id)`.

## 2. Composants nouveaux

### 2.1 `components/profil/EntrepriseHeader.vue`
**Props** :
```ts
{ percentage: number; missing: MissingFeatureBlock[] }
```
**Émet** : `open-history` (sans payload).

### 2.2 `components/profil/SectionCard.vue`
**Props** :
```ts
{
  title: string
  fields: FieldDescriptor[]
  data: Record<string, unknown>
  saving: Record<string, boolean>
  errors: Record<string, string | null>
}
```
**Émet** :
- `update:field` → `{ field: string; value: unknown }`
- `open-history`
- `toggle-edit`

Comportement : bascule lecture ↔ édition au clic ; appelle `useEntrepriseProfile().patchField` en émettant `update:field`.

### 2.3 `components/profil/MoneyField.vue`
**Props** :
```ts
{ modelValue: { amount: string; currency: 'XOF'|'EUR'|'USD' } | null; label: string; required?: boolean }
```
**Émet** : `update:modelValue` ; valeur **toujours sérialisée en string** (Decimal → toString) côté output ; jamais en `Number`.

Affiche en mode lecture : `1 250 000 FCFA · ≈ 1 905,76 €` (conversion live XOF↔EUR via `useDecimal`). USD : pas de conversion live (R7) → mention « ≈ – ».

### 2.4 `components/profil/CountryMultiSelect.vue`
**Props** : `{ modelValue: string[]; max?: number }`.
Affiche en tête : `BJ, BF, CI, GW, ML, NE, SN, TG` (UEMOA) puis `CV, GH, GM, LR, NG, SL` (CEDEAO élargie) puis le reste alphabétique. Recherche par nom ou code. Refuse toute saisie hors liste.

### 2.5 `components/profil/ProjetCard.vue`
**Props** : `{ projet: ProjetSummary }`.
Affiche : nom, badge statut (label localisé R2), secteur, date màj, badge score ESG (couleur : vert ≥ 75, orange 50–74, rouge < 50), sous-badge « Candidature en cours » si `has_active_candidature`.

### 2.6 `components/profil/ProjetWizard.vue`
**Props** : `{ open: boolean }`.
**Émet** : `close`, `created` → `ProjetRead`.
**Animation** : gsap 200 ms x-translate à chaque transition.
**Validation** : Zod par step ; `Suivant` désactivé tant que le step courant échoue.
**A11y** : focus trap, `aria-labelledby`, échap = confirm-close (perte des données — confirmation).

### 2.7 `components/profil/ConflictDialog.vue`
**Props** :
```ts
{
  field: string
  yourValue: unknown
  currentValue: unknown
  open: boolean
}
```
**Émet** : `resolve` → `'mine' | 'theirs' | 'cancel'`.
**A11y** : `role="alertdialog"`, focus initial sur l'option recommandée (« Garder ma valeur »).

### 2.8 `components/profil/HistoryDrawer.vue`
**Props** : `{ entity: 'entreprise' | 'projet'; entityId?: string; open: boolean }`.
Charge `/me/audit-log` paginé (curseur). Affiche par carte d'évènement : champ, ancienne, nouvelle, auteur, ts, source (badge `manual` / `llm` / `import` / `admin`).

### 2.9 `components/profil/ProjetDocuments.vue`
**Props** : `{ projetId: string }`.
Liste + bouton téléverser (utilise `UiFileUpload` existant). Validation MIME/size cliente (R9). Aperçu thumbnail pour image, icône PDF/DOCX/XLSX sinon.

### 2.10 `components/profil/ProjetEmptyState.vue`
Reuse `UiEmptyState` (F37) avec illustration `assets/images/empty-projets.svg` et CTA « Créez votre premier projet ».

## 3. Composables

### 3.1 `useEntrepriseProfile()`
```ts
interface UseEntrepriseProfile {
  data: ComputedRef<EntrepriseRead | null>
  version: ComputedRef<number | null>
  saving: ComputedRef<Record<string, boolean>>
  errors: ComputedRef<Record<string, string | null>>
  patchField: (field: string, value: unknown) => void  // debounced
  flushNow: () => Promise<void>                        // teste autosave
  conflict: ComputedRef<ConflictBlock | null>
  resolveConflict: (choice: 'mine' | 'theirs' | 'cancel') => Promise<void>
}
```

### 3.2 `useProjet(id)`
Symétrique à `useEntrepriseProfile`, scoped à un projet précis.

### 3.3 `useProjetWizard()`
```ts
interface UseProjetWizard {
  step: Ref<1|2|3|4>
  data: WizardData
  errors: ComputedRef<Record<string, string | null>>
  canAdvance: ComputedRef<boolean>
  next(): void
  prev(): void
  submit(): Promise<ProjetRead>
}
```

### 3.4 `useDecimal()`
```ts
interface UseDecimal {
  D: typeof Decimal
  add(a: string, b: string): string
  multiply(a: string, b: string): string
  format(amount: string, currency: 'XOF'|'EUR'|'USD'): string
  convertXofEur(amount: string, from: 'XOF'|'EUR', to: 'XOF'|'EUR'): string
  PEG_XOF_EUR: string  // '655.957'
}
```

## 4. Stores Pinia

### 4.1 `stores/entreprise.ts` (extension)
Ajouts vs version actuelle : `data`, `version`, `saving`, `errors`, `conflict`, `pendingChanges`. Migration : la propriété `completionPct` actuelle reste accessible via `completion?.percentage`.

### 4.2 `stores/projets.ts` (nouveau)
Cf. data-model § 2.2.

## 5. Locales (extrait `frontend/app/locales/fr.ts`)

```ts
export default {
  // ...
  profil: {
    entreprise: {
      title: 'Profil entreprise',
      sections: {
        identite: 'Identité',
        taille: 'Taille',
        localisation: 'Localisation',
        gouvernance: 'Gouvernance',
        pratiques: 'Pratiques',
      },
      autosave: { saved: 'Enregistré il y a {seconds}s', error: 'Modifications non sauvegardées', retrying: 'Nouvelle tentative…' },
      completion: { label: 'Profil complété à {pct}%', missing: 'Champs manquants : {fields}' },
      conflict: {
        title: 'Modification simultanée',
        body: 'Le chat a modifié ce champ pendant votre saisie.',
        keep_mine: 'Garder ma valeur',
        keep_theirs: 'Garder la valeur du chat',
        cancel: 'Annuler',
      },
      flash: { external_update: 'Mis à jour par le chat' },
    },
    projets: {
      title: 'Projets',
      empty: { title: 'Aucun projet', cta: 'Créez votre premier projet' },
      card: { ago: 'Mis à jour il y a {time}', score: 'Score ESG : {score}/100' },
      statuses: {
        brouillon: 'Brouillon',
        en_recherche_financement: 'En recherche de financement',
        finance: 'Financé',
        en_execution: 'En exécution',
        cloture: 'Clôturé',
      },
      derived: { candidature_en_cours: 'Candidature en cours' },
      wizard: {
        title: 'Nouveau projet',
        steps: { 1: 'Description', 2: 'Impact', 3: 'Localisation', 4: 'Budget' },
        actions: { next: 'Suivant', prev: 'Précédent', submit: 'Créer le projet' },
      },
      delete: {
        confirm_title: 'Supprimer ce projet ?',
        confirm_body: 'Vous pourrez le restaurer pendant 30 jours.',
        confirm_cta: 'Supprimer',
      },
    },
  },
}
```
