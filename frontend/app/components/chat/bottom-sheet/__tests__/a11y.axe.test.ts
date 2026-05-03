/**
 * T049 — Audit accessibilité (NFR-005).
 *
 * Exécute `axe-core` sur chaque wrapper rendu et vérifie qu'aucune violation
 * de niveau `serious` ou `critical` n'est levée. Niveaux `moderate`/`minor`
 * ne bloquent pas le test mais restent visibles dans la sortie pour suivi.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import axe from 'axe-core'

import AskYesNo from '../AskYesNo.vue'
import AskQcu from '../AskQcu.vue'
import AskQcm from '../AskQcm.vue'
import AskNumber from '../AskNumber.vue'
import AskDate from '../AskDate.vue'
import AskRating from '../AskRating.vue'
import ShowSummaryCard from '../ShowSummaryCard.vue'

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

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  document.body.innerHTML = ''
})

const ctx = {
  thread_id: '11111111-1111-1111-1111-111111111111',
  message_id: '22222222-2222-2222-2222-222222222222',
}

interface AxeViolation {
  id: string
  impact: 'minor' | 'moderate' | 'serious' | 'critical' | null
  description: string
  nodes: { html: string }[]
}

async function auditElement(el: Element): Promise<AxeViolation[]> {
  // happy-dom n'expose pas getComputedStyle pour toutes les règles ; on désactive
  // les règles dépendant du rendu réel (color-contrast, viewport).
  const result = (await axe.run(el as unknown as Element, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    rules: {
      'color-contrast': { enabled: false },
      region: { enabled: false },
    },
  })) as { violations: AxeViolation[] }
  return result.violations
}

function blockingOnly(violations: AxeViolation[]): AxeViolation[] {
  return violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
}

describe('axe-core — wrappers F39', () => {
  it('AskYesNo : aucune violation serious/critical', async () => {
    const w = mount(AskYesNo, {
      props: {
        instruction: { tool: 'ask_yes_no', payload: { question: 'Q ?' }, context: ctx },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('AskQcu : aucune violation serious/critical', async () => {
    const w = mount(AskQcu, {
      props: {
        instruction: {
          tool: 'ask_qcu',
          payload: {
            question: 'Q ?',
            options: [
              { value: 'a', label: 'A' },
              { value: 'b', label: 'B' },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('AskQcm : aucune violation serious/critical', async () => {
    const w = mount(AskQcm, {
      props: {
        instruction: {
          tool: 'ask_qcm',
          payload: {
            question: 'Q ?',
            options: [
              { value: 'a', label: 'A' },
              { value: 'b', label: 'B' },
            ],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('AskNumber : aucune violation serious/critical', async () => {
    const w = mount(AskNumber, {
      props: {
        instruction: { tool: 'ask_number', payload: { question: 'Combien ?', unit: 'kg' }, context: ctx },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('AskDate : aucune violation serious/critical', async () => {
    const w = mount(AskDate, {
      props: {
        instruction: { tool: 'ask_date', payload: { question: 'Quand ?' }, context: ctx },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('AskRating : aucune violation serious/critical', async () => {
    const w = mount(AskRating, {
      props: {
        instruction: { tool: 'ask_rating', payload: { question: 'Note ?', scale: 5 }, context: ctx },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })

  it('ShowSummaryCard : aucune violation serious/critical', async () => {
    const w = mount(ShowSummaryCard, {
      props: {
        instruction: {
          tool: 'show_summary_card',
          payload: {
            title: 'Récap',
            rows: [{ label: 'Champ', value: 'Valeur' }],
          },
          context: ctx,
        },
      },
      attachTo: document.body,
    })
    await nextTick()
    const v = await auditElement(document.body)
    expect(blockingOnly(v)).toEqual([])
    w.unmount()
  })
})
