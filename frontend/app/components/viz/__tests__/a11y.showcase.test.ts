// F40 T045 — Audit axe-core sur la showcase F40 (WCAG 2.1 AA, SC-011).
// On monte un sous-ensemble représentatif (les composants statiques, sans
// chart.js qui exige canvas — happy-dom n'a pas de canvas) et on vérifie
// qu'aucune violation `serious`/`critical` n'est détectée.
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import axe from 'axe-core'
import { defineComponent, h } from 'vue'
import VizKPICard from '~/components/viz/VizKPICard.vue'
import VizSourcePin from '~/components/viz/VizSourcePin.vue'
import VizLoadingState from '~/components/viz/VizLoadingState.vue'
import VizEmptyState from '~/components/viz/VizEmptyState.vue'
import VizDataTable from '~/components/viz/VizDataTable.vue'
import { __setSourcesFetcher } from '~/stores/sources'
import { TABLE_COLUMNS, makeTableRows, KPI_SAMPLES, SOURCE_VALID } from '~/utils/__tests__/fixtures/viz'

describe('a11y — showcase subset', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __setSourcesFetcher(async () => new Response(JSON.stringify(SOURCE_VALID), { status: 200 }))
  })

  it('aucune violation serious/critical (axe-core, WCAG 2.1 AA)', async () => {
    const Showcase = defineComponent({
      components: { VizKPICard, VizSourcePin, VizLoadingState, VizEmptyState, VizDataTable },
      setup() {
        return () => h('main', [
          h('h1', 'Viz Showcase a11y'),
          ...KPI_SAMPLES.map((k, i) => h(VizKPICard, { key: i, ...k })),
          h(VizSourcePin, { source_id: 'src_demo' }),
          h(VizLoadingState, { height: '6rem' }),
          h(VizEmptyState),
          h(VizDataTable, { rows: makeTableRows(8), columns: TABLE_COLUMNS } as never),
        ])
      },
    })

    const w = mount(Showcase, { attachTo: document.body })

    const results = await axe.run(w.element as HTMLElement, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      resultTypes: ['violations'],
    })

    const blocking = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
    if (blocking.length > 0) {
      // eslint-disable-next-line no-console
      console.error('axe violations:', JSON.stringify(blocking, null, 2))
    }
    expect(blocking).toEqual([])
    w.unmount()
  })
})
