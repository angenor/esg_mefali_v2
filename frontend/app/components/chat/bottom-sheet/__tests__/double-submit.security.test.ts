/**
 * T047 — Test double-submission (SC-007).
 *
 * Cible : `useBottomSheetSubmit` garantit qu'une seule requête POST part même
 * si l'utilisateur enchaîne clics et `Enter` rapidement (1000 itérations).
 *
 * Pourquoi 1000 cycles : SC-007 du spec exige <0.1 % de doubles soumissions.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import AskYesNo from '../AskYesNo.vue'

vi.mock('gsap', () => ({
  gsap: {
    fromTo: (_t: unknown, _f: unknown, o: { onComplete?: () => void } = {}) => {
      o.onComplete?.()
      return {}
    },
    to: (_t: unknown, o: { onComplete?: () => void } = {}) => {
      o.onComplete?.()
      return {}
    },
  },
  default: { fromTo: () => {}, to: () => {} },
}))

const fetchMock = vi.fn()
beforeEach(() => {
  setActivePinia(createPinia())
  fetchMock.mockReset()
  ;(globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch
})

const baseInstruction = {
  tool: 'ask_yes_no' as const,
  payload: { question: 'Êtes-vous une SARL ?' },
  context: {
    thread_id: '11111111-1111-1111-1111-111111111111',
    message_id: '22222222-2222-2222-2222-222222222222',
  },
}

describe('Double-submission guard (SC-007)', () => {
  it('1000 clics rapprochés sur AskYesNo → exactement 1 POST observé', async () => {
    let resolvePost: ((r: Response) => void) | null = null
    const pending = new Promise<Response>((r) => {
      resolvePost = r
    })
    fetchMock.mockReturnValue(pending)

    const w = mount(AskYesNo, { props: { instruction: baseInstruction }, attachTo: document.body })
    await nextTick()

    const yesBtn = w.find('[data-testid="ask-yes-no-yes"]')
    // Salve de 1000 clics + 1000 dispatch keydown Enter avant que le serveur ne réponde.
    for (let i = 0; i < 1000; i++) {
      // pas d'await intentionnel : on enchaîne sans laisser inFlight redescendre.
      void yesBtn.trigger('click')
      // Enter sur le bouton focalisé déclenche click natif — équivalent au clic.
      void yesBtn.trigger('keydown.enter')
    }
    await nextTick()

    expect(fetchMock).toHaveBeenCalledTimes(1)

    // On résout la requête en attente puis on confirme qu'aucune autre n'est partie après.
    resolvePost!(
      new Response(
        JSON.stringify({ id: 'msg-1', thread_id: 't', role: 'pme', content: 'Oui', created_at: 'now' }),
        { status: 200 },
      ),
    )
    await nextTick()
    await nextTick()
    expect(fetchMock).toHaveBeenCalledTimes(1)

    w.unmount()
  })
})
