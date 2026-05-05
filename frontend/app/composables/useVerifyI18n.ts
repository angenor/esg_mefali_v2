// F49 T019 — Composable bilingue FR/EN scope contrôlé pour /verify/[id].vue.
//
// Chargement des dictionnaires statiques depuis `~/i18n/verify/{lang}.json`.
// Persistance via cookie `mefali_verify_lang` (lu côté serveur dès la première
// requête, donc le SSR ne flashe pas).

import { computed, ref, isRef, type Ref } from "vue"
import frDict from "~/i18n/verify/fr.json"
import enDict from "~/i18n/verify/en.json"

export type VerifyLang = "fr" | "en"

const COOKIE_NAME = "mefali_verify_lang"
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365 // 1 an

const DICTS: Record<VerifyLang, Record<string, unknown>> = {
  fr: frDict as Record<string, unknown>,
  en: enDict as Record<string, unknown>,
}

function readCookieLang(): VerifyLang {
  if (typeof document === "undefined") return "fr"
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${COOKIE_NAME}=([^;]+)`),
  )
  const v = match?.[1]
  return v === "en" ? "en" : "fr"
}

function writeCookieLang(lang: VerifyLang): void {
  if (typeof document === "undefined") return
  document.cookie = `${COOKIE_NAME}=${lang}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`
}

function resolvePath(
  obj: Record<string, unknown>,
  path: string,
): string | undefined {
  const parts = path.split(".")
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let cur: any = obj
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return undefined
    cur = cur[p]
  }
  return typeof cur === "string" ? cur : undefined
}

export function useVerifyI18n(initialLang?: VerifyLang | Ref<VerifyLang>) {
  const lang = isRef(initialLang)
    ? initialLang
    : ref<VerifyLang>((initialLang as VerifyLang | undefined) ?? readCookieLang())

  function setLang(next: VerifyLang) {
    if (!isRef(initialLang)) {
      ;(lang as Ref<VerifyLang>).value = next
    }
    writeCookieLang(next)
  }

  function t(key: string, vars?: Record<string, string | number>): string {
    const dict = DICTS[lang.value]
    let str = resolvePath(dict, key)
    if (str === undefined) {
      // Fallback FR si la clé manque en EN
      const fallback = resolvePath(DICTS.fr, key)
      str = fallback ?? key
    }
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replaceAll(`{${k}}`, String(v))
      }
    }
    return str
  }

  const dateFormatter = computed<(d: Date | string) => string>(() => {
    return (d) => {
      const dt = typeof d === "string" ? new Date(d) : d
      if (Number.isNaN(dt.getTime())) return ""
      const fmt =
        lang.value === "en"
          ? new Intl.DateTimeFormat("en-US", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })
          : new Intl.DateTimeFormat("fr-FR", {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            })
      return fmt.format(dt)
    }
  })

  return {
    lang,
    setLang,
    t,
    dateFormatter,
  }
}
