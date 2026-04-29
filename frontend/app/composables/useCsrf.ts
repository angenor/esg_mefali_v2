// F02 T029 — Lecture cookie CSRF + helper d'en-tête
export function useCsrf() {
  const getCsrfFromCookie = (): string => {
    if (import.meta.server) return ""
    const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
    return m ? decodeURIComponent(m[1]) : ""
  }

  const withCsrf = (headers: Record<string, string> = {}): Record<string, string> => {
    const t = getCsrfFromCookie()
    return t ? { ...headers, "X-CSRF-Token": t } : headers
  }

  return { getCsrfFromCookie, withCsrf }
}
