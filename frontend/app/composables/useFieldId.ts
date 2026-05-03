import { getCurrentInstance } from 'vue'

let counter = 0

// Génère un id stable côté SSR et client. Utilise `useId()` Nuxt 4 si disponible,
// sinon retombe sur un compteur module-scope (suffisant pour les tests + SSR single-pass).
export function useFieldId(prefix = 'ui'): string {
  const instance = getCurrentInstance() as
    | (ReturnType<typeof getCurrentInstance> & { uid?: number })
    | null
  // Vue 3 expose `uid` sur l'instance — stable par composant.
  const uid = instance?.uid ?? ++counter
  return `${prefix}-${uid}-${++counter}`
}
