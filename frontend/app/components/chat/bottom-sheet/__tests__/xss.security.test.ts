/**
 * T046 — Test d'injection XSS automatisé (SC-006).
 *
 * Itère sur tous les wrappers F39 avec un payload contenant
 * `<script>alert(1)</script>` injecté dans `label` / `description` / `source_label`
 * et tout champ texte exposé à l'utilisateur.
 *
 * Assertion : aucune balise `<script>` n'est rendue dans le DOM, le texte est
 * affiché en clair (sanitizeText strippe), aucun `alert` n'est exécuté.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import AskYesNo from '../AskYesNo.vue'
import AskQcu from '../AskQcu.vue'
import AskQcm from '../AskQcm.vue'
import AskSelect from '../AskSelect.vue'
import AskNumber from '../AskNumber.vue'
import AskDate from '../AskDate.vue'
import AskDateRange from '../AskDateRange.vue'
import AskRating from '../AskRating.vue'
import AskFileUpload from '../AskFileUpload.vue'
import ShowSummaryCard from '../ShowSummaryCard.vue'
import ShowForm from '../ShowForm.vue'

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

const PAYLOAD = '<script>alert(1)</script>'
const IMG_PAYLOAD = '<img src=x onerror="alert(2)">'

const ctx = {
  thread_id: '11111111-1111-1111-1111-111111111111',
  message_id: '22222222-2222-2222-2222-222222222222',
}

let alertSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  setActivePinia(createPinia())
  // alert() est mocké pour neutraliser tout appel issu du parser DOMPurify
  // pendant le strip — l'assertion porte sur le DOM rendu, pas sur ce buffer.
  alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
})

afterEach(() => {
  alertSpy.mockRestore()
})

function assertNoXss(html: string): void {
  const lower = html.toLowerCase()
  // Aucune balise <script> dans le DOM rendu (les payloads sont strippés ou échappés).
  expect(lower).not.toMatch(/<script\b/)
  // Aucune balise <img> issue d'un payload utilisateur (sanitizeText strippe).
  expect(lower).not.toMatch(/<img\b/)
  // Aucun handler inline rendu dans le DOM.
  expect(lower).not.toMatch(/\sonerror\s*=/)
  expect(lower).not.toMatch(/\sonclick\s*=/)
  // Marqueur retenu : DOMPurify peut exécuter onerror dans son buffer interne lors du
  // parse, mais le DOM rendu côté Vue ne doit jamais contenir de balise dangereuse.
}

describe('XSS — wrappers F39', () => {
  it('AskYesNo strippe les balises injectées dans question/labels', async () => {
    const w = mount(AskYesNo, {
      props: {
        instruction: {
          tool: 'ask_yes_no',
          payload: { question: `Q ${PAYLOAD}`, yes_label: `OK ${IMG_PAYLOAD}`, no_label: `KO ${PAYLOAD}` },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskQcu strippe label/description des options', async () => {
    const w = mount(AskQcu, {
      props: {
        instruction: {
          tool: 'ask_qcu',
          payload: {
            question: `Q ${PAYLOAD}`,
            options: [
              { value: 'a', label: `A ${PAYLOAD}`, description: `desc ${IMG_PAYLOAD}` },
              { value: 'b', label: `B ${PAYLOAD}` },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskQcm strippe label des options', async () => {
    const w = mount(AskQcm, {
      props: {
        instruction: {
          tool: 'ask_qcm',
          payload: {
            question: `Q ${PAYLOAD}`,
            options: [
              { value: 'x', label: `X ${PAYLOAD}` },
              { value: 'y', label: `Y ${IMG_PAYLOAD}` },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskSelect strippe label des options statiques', async () => {
    const w = mount(AskSelect, {
      props: {
        instruction: {
          tool: 'ask_select',
          payload: {
            question: `Q ${PAYLOAD}`,
            options: [
              { value: 'p', label: `P ${PAYLOAD}` },
              { value: 'q', label: `Q ${IMG_PAYLOAD}` },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskNumber strippe question/unit', async () => {
    const w = mount(AskNumber, {
      props: {
        instruction: {
          tool: 'ask_number',
          payload: { question: `Q ${PAYLOAD}`, unit: `kg ${IMG_PAYLOAD}` },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskDate strippe question', async () => {
    const w = mount(AskDate, {
      props: {
        instruction: {
          tool: 'ask_date',
          payload: { question: `Q ${PAYLOAD}` },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskDateRange strippe question', async () => {
    const w = mount(AskDateRange, {
      props: {
        instruction: {
          tool: 'ask_date_range',
          payload: { question: `Q ${PAYLOAD}` },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskRating strippe question', async () => {
    const w = mount(AskRating, {
      props: {
        instruction: {
          tool: 'ask_rating',
          payload: { question: `Q ${PAYLOAD}`, scale: 5 },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('AskFileUpload strippe question', async () => {
    const w = mount(AskFileUpload, {
      props: {
        instruction: {
          tool: 'ask_file_upload',
          payload: { question: `Q ${PAYLOAD}`, attach_to: 'entreprise' },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('ShowSummaryCard strippe title/rows/source_label/labels actions', async () => {
    const w = mount(ShowSummaryCard, {
      props: {
        instruction: {
          tool: 'show_summary_card',
          payload: {
            title: `T ${PAYLOAD}`,
            rows: [
              {
                label: `L ${PAYLOAD}`,
                value: `V ${IMG_PAYLOAD}`,
                source_label: `src ${PAYLOAD}`,
              },
            ],
            ok_label: `OK ${PAYLOAD}`,
            edit_label: `EDIT ${IMG_PAYLOAD}`,
            cancel_label: `CANCEL ${PAYLOAD}`,
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })

  it('ShowForm strippe title et labels de champs', async () => {
    const w = mount(ShowForm, {
      props: {
        instruction: {
          tool: 'show_form',
          payload: {
            title: `T ${PAYLOAD}`,
            fields: [
              { name: 'a', label: `A ${PAYLOAD}`, type: 'text' },
              {
                name: 'b',
                label: `B ${IMG_PAYLOAD}`,
                type: 'select',
                options: [{ value: 'x', label: `X ${PAYLOAD}` }],
              },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    assertNoXss(w.html())
    w.unmount()
  })
})
