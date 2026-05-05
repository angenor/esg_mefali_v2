// F42 — Composable de traduction FR (typage strict sur les clés du locale)
import frLocale from "~/locales/fr"

type Locale = typeof frLocale
export type LocaleKey = keyof Locale

export function useT() {
  function t(key: LocaleKey, params?: Record<string, string | number>): string {
    let value: string = frLocale[key]
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        value = value.replaceAll(`{${k}}`, String(v))
      }
    }
    return value
  }
  return { t }
}
