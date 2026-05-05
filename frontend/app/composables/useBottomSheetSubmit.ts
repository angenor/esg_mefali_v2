/**
 * useBottomSheetSubmit — POST /me/chat/threads/{thread_id}/messages (F14/F15).
 *
 * Garanties (cf. specs/039-bottom-sheet-engine/contracts/chat-message-submit.md) :
 *  - body strict `{ content, payload_json, context_json }`
 *  - déduplication via flag `inFlight` (R7) — pas d'Idempotency-Key
 *  - mapping FR des codes 400/401/404/409/422/5xx
 *  - aucun retry automatique
 */
import { computed, type Ref, ref } from 'vue'
import { useChatBottomSheetStore } from '~/stores/chatBottomSheet'
import type { ToolName, ToolResponse, ToolResponseValue } from '~/types/tools/contracts'

export interface SubmitArgs<T extends ToolName> {
  threadId: string
  inResponseToMessageId: string
  tool: T
  value: ToolResponseValue<T>
  label: string
  metadata?: Record<string, unknown>
}

export type SubmitErrorCode = '400' | '401' | '404' | '409' | '422' | '5xx' | 'network'

export interface SubmitResult {
  ok: boolean
  status: number
  errorCode?: SubmitErrorCode
  errorMessage?: string
  message?: { id: string; thread_id: string; role: string; content: string; created_at: string }
}

const ERROR_FR: Record<SubmitErrorCode, { message: string; retriable: boolean }> = {
  '400': { message: 'Réponse refusée par le serveur (format invalide).', retriable: false },
  '401': { message: 'Session expirée — veuillez vous reconnecter.', retriable: false },
  '404': { message: 'Conversation introuvable.', retriable: false },
  '409': { message: 'Cette question a déjà été traitée.', retriable: false },
  '422': { message: 'Donnée invalide — vérifiez votre saisie.', retriable: false },
  '5xx': { message: 'Erreur serveur — réessayez dans un instant.', retriable: true },
  network: { message: 'Connexion impossible — vérifiez votre réseau.', retriable: true },
}

export interface UseBottomSheetSubmit {
  inFlight: Readonly<Ref<boolean>>
  isSubmitting: Readonly<Ref<boolean>> // alias
  submit<T extends ToolName>(args: SubmitArgs<T>): Promise<SubmitResult>
  errorMessage: (code: SubmitErrorCode) => string
}

export function useBottomSheetSubmit(): UseBottomSheetSubmit {
  const store = useChatBottomSheetStore()
  const inFlight = ref(false)

  function classify(status: number): SubmitErrorCode {
    if (status === 400) return '400'
    if (status === 401) return '401'
    if (status === 404) return '404'
    if (status === 409) return '409'
    if (status === 422) return '422'
    if (status >= 500) return '5xx'
    return '400'
  }

  async function submit<T extends ToolName>(args: SubmitArgs<T>): Promise<SubmitResult> {
    if (inFlight.value) {
      return { ok: false, status: 0, errorCode: '409', errorMessage: 'Soumission déjà en cours.' }
    }
    inFlight.value = true
    store.markInFlight(true)
    store.setError(null)

    const payload: ToolResponse = {
      tool: args.tool,
      value: args.value,
      label: args.label,
      ...(args.metadata ? { metadata: args.metadata } : {}),
    } as ToolResponse

    const body = JSON.stringify({
      content: args.label,
      payload_json: payload,
      context_json: { in_response_to_message_id: args.inResponseToMessageId, tool: args.tool },
    })

    const apiBase =
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (globalThis as any).useRuntimeConfig?.()?.public?.apiBase ?? 'http://localhost:8010'
    const url = `${String(apiBase).replace(/\/$/, '')}/me/chat/threads/${args.threadId}/messages`

    try {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json', accept: 'application/json' },
        body,
      })
      if (res.ok) {
        const message = await res.json()
        return { ok: true, status: res.status, message }
      }
      const code = classify(res.status)
      const { message } = ERROR_FR[code]
      store.setError(message)
      return { ok: false, status: res.status, errorCode: code, errorMessage: message }
    } catch {
      const { message } = ERROR_FR.network
      store.setError(message)
      return { ok: false, status: 0, errorCode: 'network', errorMessage: message }
    } finally {
      inFlight.value = false
      store.markInFlight(false)
    }
  }

  return {
    inFlight: computed(() => inFlight.value),
    isSubmitting: computed(() => inFlight.value),
    submit,
    errorMessage: (code) => ERROR_FR[code].message,
  }
}

export const __test__ = { ERROR_FR }
