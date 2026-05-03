/**
 * useChatOnboarding — driver.js tour 4 étapes pour le premier chat.
 *
 * F41 / US6 (T042). Référence : research.md R5.
 * Flag canonique : `account_settings.onboarding_chat_seen` côté backend (F11).
 * Fallback : `localStorage` clé `chat.onboarding.seen.{accountId}`.
 */
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useAuthStore } from '~/stores/auth'

const FLAG_PREFIX = 'chat.onboarding.seen.'

interface UseChatOnboarding {
  maybeStart: () => Promise<void>
  markSeen: () => Promise<void>
  forceStart: () => void
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.()
  return String(cfg?.public?.apiBase ?? 'http://localhost:8010').replace(/\/$/, '')
}

function localKey(accountId: string): string {
  return `${FLAG_PREFIX}${accountId || 'anon'}`
}

async function readBackendFlag(): Promise<boolean | null> {
  try {
    const res = await fetch(`${apiBase()}/me/account/settings`, {
      credentials: 'include',
      headers: { accept: 'application/json' },
    })
    if (!res.ok) return null
    const data = (await res.json()) as { onboarding_chat_seen?: boolean }
    return Boolean(data.onboarding_chat_seen)
  } catch {
    return null
  }
}

async function writeBackendFlag(): Promise<boolean> {
  try {
    const res = await fetch(`${apiBase()}/me/account/settings`, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify({ onboarding_chat_seen: true }),
    })
    return res.ok
  } catch {
    return false
  }
}

function startTour(onComplete: () => void): void {
  if (typeof window === 'undefined') return
  const d = driver({
    showProgress: true,
    nextBtnText: 'Suivant',
    prevBtnText: 'Précédent',
    doneBtnText: 'Terminé',
    steps: [
      {
        element: '.chat-input__field',
        popover: {
          title: 'Écrivez librement',
          description: 'Posez vos questions ESG en langage naturel. Cmd+Enter envoie.',
        },
      },
      {
        element: '.chat-input__attach',
        popover: {
          title: 'Pièce jointe',
          description: "Ajoutez un document (facture, attestation) pour enrichir l'analyse.",
        },
      },
      {
        element: '.thread-list',
        popover: {
          title: 'Conversations',
          description: "Retrouvez vos discussions passées et démarrez de nouveaux fils.",
        },
      },
      {
        element: '.chat-layout__header',
        popover: {
          title: "Architecture haut/bas",
          description: "Le haut affiche les réponses et visualisations. Le bas accueille votre saisie ou un formulaire dédié quand l'assistant en demande un.",
        },
      },
    ],
    onDestroyed: onComplete,
  })
  d.drive()
}

export function useChatOnboarding(): UseChatOnboarding {
  const auth = useAuthStore()
  const accountId = (): string => String(auth.user?.account_id ?? '')

  async function isSeen(): Promise<boolean> {
    const remote = await readBackendFlag()
    if (remote !== null) return remote
    if (typeof window === 'undefined') return true
    return window.localStorage.getItem(localKey(accountId())) === '1'
  }

  async function markSeen(): Promise<void> {
    const ok = await writeBackendFlag()
    if (!ok && typeof window !== 'undefined') {
      window.localStorage.setItem(localKey(accountId()), '1')
    }
  }

  async function maybeStart(): Promise<void> {
    if (typeof window === 'undefined') return
    if (await isSeen()) return
    setTimeout(() => {
      startTour(() => { void markSeen() })
    }, 350)
  }

  function forceStart(): void {
    if (typeof window === 'undefined') return
    startTour(() => { void markSeen() })
  }

  return { maybeStart, markSeen, forceStart }
}
