// Helper de test : monte un composant temporaire pour exercer les
// composables Vue avec lifecycle hooks. Inspire de la doc Vue Test Utils.

import { createApp, type App } from "vue"

export function withSetup<T>(composable: () => T): [T, App] {
  let result!: T
  const app = createApp({
    setup() {
      result = composable()
      return () => {}
    },
  })
  app.mount(document.createElement("div"))
  return [result, app]
}
