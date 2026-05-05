// F40 T038 — VizDataTable tests : virtualisation, tri money, recherche, pagination, money invalide.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import VizDataTable from '~/components/viz/VizDataTable.vue'
import type { ColumnDef } from '~/types/viz/chart'

interface Row {
  id: string
  nom: string
  montant: { amount: string; currency: string }
}

const COLS: ColumnDef<Row>[] = [
  { key: 'id', label: 'ID', type: 'text' },
  { key: 'nom', label: 'Nom', type: 'text', searchable: true },
  { key: 'montant', label: 'Montant', type: 'money' },
]

function makeRows(n: number): Row[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `id-${i}`,
    nom: i % 3 === 0 ? `Alpha-${i}` : `Beta-${i}`,
    montant: { amount: String(1000 + i), currency: 'EUR' },
  }))
}

const STUBS = { RecycleScroller: { props: ['items'], template: '<div class="rc-stub" :data-len="items.length"><slot v-if="items.length" :item="items[0]"/></div>' } }

describe('VizDataTable', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('rend une table classique pour ≤ 100 lignes', () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(50), columns: COLS } as never,
    })
    expect(w.find('table.viz-table').exists()).toBe(true)
    expect(w.find('.viz-table__virtual').exists()).toBe(false)
  })

  it('bascule en virtualisation au-delà de 100 lignes (sans paginate)', () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(500), columns: COLS } as never,
      global: { stubs: STUBS },
    })
    expect(w.find('.viz-table__virtual').exists()).toBe(true)
    expect(w.find('table.viz-table').exists()).toBe(false)
    // sortedRows count delivered to RecycleScroller
    expect(w.find('.rc-stub').attributes('data-len')).toBe('500')
  })

  it('paginate désactive la virtualisation', () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(500), columns: COLS, paginate: { pageSize: 25 } } as never,
    })
    expect(w.find('table.viz-table').exists()).toBe(true)
    expect(w.find('.viz-table__virtual').exists()).toBe(false)
    expect(w.findAll('tbody tr').length).toBeLessThanOrEqual(26)
  })

  it('formate la colonne money via Intl', () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(3), columns: COLS } as never,
    })
    expect(w.text()).toMatch(/€/)
  })

  it('money brut (number) → warning console + cellule "--"', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const rows = [{ id: '1', nom: 'X', montant: 1000 as unknown as Row['montant'] }]
    const w = mount(VizDataTable, {
      props: { rows, columns: COLS } as never,
    })
    expect(w.text()).toContain('--')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('tri money : clic sur l\'entête bascule asc/desc', async () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(5), columns: COLS } as never,
    })
    const ths = w.findAll('th')
    const moneyTh = ths[2]
    expect(moneyTh).toBeTruthy()
    expect(moneyTh!.attributes('aria-sort')).toBe('none')
    await moneyTh!.get('button').trigger('click')
    expect(moneyTh!.attributes('aria-sort')).toBe('ascending')
    await moneyTh!.get('button').trigger('click')
    expect(moneyTh!.attributes('aria-sort')).toBe('descending')
  })

  it('recherche filtre les lignes (colonne searchable)', async () => {
    const w = mount(VizDataTable, {
      props: { rows: makeRows(10), columns: COLS } as never,
    })
    const initial = w.findAll('tbody tr').length
    expect(initial).toBeGreaterThan(0)
    await w.get('input[type="search"]').setValue('Alpha')
    const after = w.findAll('tbody tr').length
    expect(after).toBeLessThan(initial)
  })
})
