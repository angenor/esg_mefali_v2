import { useId as vueUseId } from 'vue'

let fallbackCounter = 0

/**
 * Génère un id stable côté SSR et client.
 *
 * Vue 3.5+ expose `useId()` qui garantit la même valeur entre SSR et CSR
 * (préfixée par l'app id, stable par composant). On l'utilise en
 * priorité ; le fallback (compteur module-scope) ne s'applique qu'aux
 * appels hors instance Vue (utilitaires de test).
 *
 * Avant ce fix, `useFieldId` retournait `${prefix}-${uid}-${++counter}`
 * avec un counter module-scope qui divergeait entre SSR et CSR
 * (`ui-textarea-12337-33` côté serveur vs `ui-textarea-18-1` côté
 * client), causant un Hydration attribute mismatch sur tous les
 * `<UiTextarea>` (FR-frontend bug 2.5).
 */
export function useFieldId(prefix = 'ui'): string {
  const id = vueUseId()
  if (id) return `${prefix}-${id}`
  // Fallback test/non-instance — id incrément local non transféré SSR.
  fallbackCounter += 1
  return `${prefix}-fb-${fallbackCounter}`
}
