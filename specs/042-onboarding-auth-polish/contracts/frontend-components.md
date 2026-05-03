# Contract — Frontend composants & composables (F42)

Définit les API publiques (props, slots, emits, valeurs de retour) des nouveaux artefacts frontend.

---

## Composables

### `useT(key, params?)` — `frontend/app/composables/useT.ts`

```ts
import frLocale from '~/locales/fr'

type Locale = typeof frLocale
type LocaleKey = keyof Locale

export function useT() {
  function t<K extends LocaleKey>(key: K, params?: Record<string, string | number>): string {
    let value: string = frLocale[key]
    if (params) for (const [k, v] of Object.entries(params)) value = value.replaceAll(`{${k}}`, String(v))
    return value
  }
  return { t }
}
```

**Contrat** :
- TypeScript échoue à la compilation si `key` n'existe pas dans `locales/fr.ts` (autocomplete + sécurité).
- `params` : substitution simple `{nom}` (pas de pluralisation pour MVP).

---

### `usePasswordStrength(password)` — `frontend/app/composables/usePasswordStrength.ts`

```ts
export interface PasswordStrengthResult {
  score: 0 | 1 | 2 | 3 | 4
  label: string
  feedback: { warning: string | null; suggestions: string[] }
  meetsBaseCriteria: boolean
  criteria: {
    length8: boolean
    uppercase: boolean
    digit: boolean
    symbol: boolean
  }
  isAcceptable: boolean
}

export function usePasswordStrength(password: Ref<string>): ComputedRef<PasswordStrengthResult>
```

**Règle** : `isAcceptable = meetsBaseCriteria && score >= 3`. Le bouton "Suivant"/"Enregistrer" est désactivé tant que `isAcceptable === false`.

**Implémentation** : wrap `@zxcvbn-ts/core` avec dictionnaire `language-fr` + `language-common`. Labels FR : `["Très faible", "Faible", "Acceptable", "Fort", "Très fort"]`.

---

### `useOnboardingTour()` — `frontend/app/composables/useOnboardingTour.ts`

```ts
export function useOnboardingTour() {
  const prefs = useUserPreferencesStore()
  const reduced = useReducedMotion()

  async function startIfPending(): Promise<void>
  async function start(): Promise<void>            // forcé, pour le menu Aide
  async function skip(): Promise<void>             // bouton "Passer" / ESC / outside
  async function dismissForever(): Promise<void>   // bouton "Ne plus afficher"
  async function complete(): Promise<void>         // dernière étape

  return { startIfPending, start, skip, dismissForever, complete }
}
```

**Contrat** :
- `startIfPending()` ne fait rien si `prefs.state !== 'pending'`.
- Toutes les transitions appellent `prefs.set(<new_state>)`.
- Si `reduced.value === true`, driver.js est instancié avec `{ animate: false, stagePadding: 0 }`.
- Sur viewport < 768 px, fallback modal plein écran (composant `FullscreenTourStep.vue`) au lieu de popovers driver.js — détection au démarrage.
- 6 étapes : sélecteurs `[data-tour="sidebar"]`, `[data-tour="profil"]`, `[data-tour="chat"]`, `[data-tour="bibliotheque"]`, `[data-tour="plan-action"]`, `[data-tour="parametres"]`. Si un sélecteur est introuvable, l'étape est sautée silencieusement (le tour ne crashe pas).

---

## Composants

### `<PasswordStrengthMeter password="..." />`

**Props** : `password: string` (obligatoire).
**Slots** : aucun.
**Emits** : `change` `(result: PasswordStrengthResult)` — émis à chaque changement, permet au parent de désactiver le bouton.
**A11y** : barre annotée `aria-label`, score dans un `<div role="status" aria-live="polite">`.

---

### `<PasswordVisibilityToggle v-model="visible" />`

**Props** : `visible: boolean` (v-model).
**Emits** : `update:visible` `(v: boolean)`.
**A11y** : `<button type="button" aria-pressed="<visible>" aria-label="Afficher le mot de passe">`.

---

### `<RegisterStepIdentifiants />`, `<RegisterStepEntreprise />`, `<RegisterStepConsentements />`

Chaque step émet `next` `(stepData)` quand validé, `previous` `()` pour revenir. Le parent `register.vue` orchestre l'état partagé en mémoire.

| Step | Champs | Validation locale |
|---|---|---|
| 1 — Identifiants | email, password (+ confirmation) | email RFC + password.isAcceptable |
| 2 — Entreprise | raison sociale (>= 2 chars), secteur (autocomplete F08) | obligatoires |
| 3 — Consentements | checkbox CGU, checkbox RGPD | les deux cochées |

Le compte est **créé en une seule requête** au step 3 — la fin du wizard appelle `POST /auth/register` avec les 3 stepDatas agrégés.

---

### `<RegisterProgressBar :step="1|2|3" :total="3" />`

Barre 3 segments + label `Étape {step} sur {total}`.

---

### `<ResendCooldownButton :email="..." :on-send="async () => …" :cooldown-seconds="60" />`

Bouton qui :
- Affiche label dynamique `Renvoyer le lien` ou `Renvoyer dans {n} s`.
- Lit/écrit `localStorage[`resend-cooldown:${email}`]`.
- Désactive l'appel pendant le cooldown.

**Emits** : `sent` `()` après envoi réussi, `failed` `(err)` sinon.

---

### `<EmailVerificationBanner />`

Bandeau sticky top app — visible uniquement si `useAuth().user.value?.email_verified_at == null`.
- CTA "Renvoyer le lien" → `<ResendCooldownButton>` cliquant sur `/auth/email/resend`.
- Bouton "X" pour replier le bandeau pour la session courante (ne change pas le backend).
- A11y : `role="region" aria-label="Vérification email"`.

---

### `<EmptyStateLanding />`

Affiché quand `useEntrepriseStore().completion_pct < 50`.
- Hero : titre, sous-titre.
- CTA principal : `Compléter mon profil en 5 minutes` → `router.push('/profil')`.
- 3 cartes `<EmptyStateCard>` (icône, titre, description courte, lien optionnel).

---

### `<OnboardingTourTrigger />`

Petit bouton dans le menu Aide (App Shell — F38). `@click` → `useOnboardingTour().start()`. Toujours fonctionnel quel que soit `onboarding_state`.

---

### `<PublicHero />`, `<PublicBenefitsGrid />`, `<PublicTestimonial />`

Sections de la homepage publique. Composants atomiques sans prop dynamique pour MVP (textes via `useT`). `<PublicHero>` contient le CTA principal `Créer un compte` → `router.push('/register')`.

---

## Layout `auth.vue`

`frontend/app/layouts/auth.vue` :
- Grid 2 colonnes ≥ 1024 px (illustration | contenu), 50/50.
- 1 colonne 768–1023 px (illustration plus petite ou cachée selon design final).
- 1 colonne pleine largeur < 768 px (illustration cachée).
- `<slot />` reçoit le contenu de la page (login/register/forgot/reset).
- `definePageMeta({ layout: 'auth', public: true })` est attendu sur les pages utilisatrices.

---

## i18n — fichier `frontend/app/locales/fr.ts`

Exporte un objet `default` avec **toutes** les chaînes utilisées par cette feature. Exemple :

```ts
export default {
  // Login
  'auth.login.title': 'Connexion',
  'auth.login.cta': 'Se connecter',
  'auth.login.remember': 'Rester connecté pendant 30 jours',
  'auth.login.forgot': 'Mot de passe oublié ?',
  'auth.login.error': 'Identifiants invalides.',
  'auth.password.show': 'Afficher le mot de passe',
  'auth.password.hide': 'Masquer le mot de passe',
  // Register
  'auth.register.title': 'Créer un compte',
  'auth.register.step1.title': 'Vos identifiants',
  // ... etc.
  // Forgot
  'auth.forgot.confirmation': 'Si cette adresse est valide, vous recevrez un lien dans quelques minutes.',
  // Reset
  'auth.reset.success': 'Mot de passe mis à jour. Veuillez vous reconnecter.',
  // Onboarding
  'onboarding.tour.skip': 'Passer',
  'onboarding.tour.dismiss': 'Ne plus afficher',
  'onboarding.tour.next': 'Suivant',
  'onboarding.tour.finish': 'Terminer',
  // Empty state
  'empty.title': 'Bienvenue sur ESG Mefali',
  'empty.cta': 'Compléter mon profil en 5 minutes',
  // Public
  'public.hero.title': 'La finance verte simplifiée pour les PME ouest-africaines',
  // ... etc.
} as const
```

**Contrainte** : aucune autre source de chaînes FR pour cette feature ; un audit grep est prévu en CI (cf. quickstart).
