<!--
  F40 T035-T037 — VizDataTable : table typée + virtualisation > 100 lignes
  ou pagination (mutuellement exclusives), tri, recherche, formatage money.
-->
<script setup lang="ts" generic="Row extends Record<string, unknown>">
import { computed, ref } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import VizSourcePin from './VizSourcePin.vue'
import VizEmptyState from './VizEmptyState.vue'
import { formatMoney, isMoneyValue } from '~/utils/moneyFormat'
import type { ColumnDef, DataTableProps } from '~/types/viz/chart'

const props = withDefaults(defineProps<DataTableProps<Row>>(), {
  emptyMessage: 'Aucune donnée disponible',
})

const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')
const search = ref<string>('')
const page = ref<number>(0)

function searchableColumns(): ColumnDef<Row>[] {
  return props.columns.filter((c) => c.searchable !== false && (c.searchable === true || c.type === 'text' || c.type === 'badge'))
}

const filteredRows = computed<Row[]>(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return props.rows
  const cols = searchableColumns()
  return props.rows.filter((row) => {
    for (const c of cols) {
      const v = row[c.key]
      if (typeof v === 'string' && v.toLowerCase().includes(q)) return true
    }
    return false
  })
})

const sortedRows = computed<Row[]>(() => {
  if (!sortKey.value) return filteredRows.value
  const k = sortKey.value as keyof Row & string
  const col = props.columns.find((c) => c.key === k)
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...filteredRows.value].sort((a, b) => {
    const va = a[k]
    const vb = b[k]
    if (col?.type === 'money') {
      const na = isMoneyValue(va) ? Number(va.amount) : Number.NEGATIVE_INFINITY
      const nb = isMoneyValue(vb) ? Number(vb.amount) : Number.NEGATIVE_INFINITY
      return (na - nb) * dir
    }
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb), 'fr-FR') * dir
  })
})

const useVirtual = computed<boolean>(() => sortedRows.value.length > 100 && !props.paginate)

const pageSize = computed<number>(() => props.paginate?.pageSize ?? 25)
const pagedRows = computed<Row[]>(() => {
  if (!props.paginate) return sortedRows.value
  const start = page.value * pageSize.value
  return sortedRows.value.slice(start, start + pageSize.value)
})
const pageCount = computed<number>(() => Math.max(1, Math.ceil(sortedRows.value.length / pageSize.value)))

function onSort(c: ColumnDef<Row>): void {
  if (c.sortable === false) return
  if (sortKey.value === c.key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  }
  else {
    sortKey.value = c.key
    sortDir.value = 'asc'
  }
}

function ariaSort(c: ColumnDef<Row>): 'ascending' | 'descending' | 'none' {
  if (sortKey.value !== c.key) return 'none'
  return sortDir.value === 'asc' ? 'ascending' : 'descending'
}

function alignClass(c: ColumnDef<Row>): string {
  if (c.align) return `viz-table__cell--${c.align}`
  if (c.type === 'number' || c.type === 'money') return 'viz-table__cell--right'
  return 'viz-table__cell--left'
}

function formatCell(c: ColumnDef<Row>, value: unknown): string {
  if (value === null || value === undefined) return ''
  if (c.type === 'money') {
    if (!isMoneyValue(value)) {
      // eslint-disable-next-line no-console
      console.warn(`[VizDataTable] cellule money invalide pour ${c.key} :`, value)
      return '--'
    }
    return formatMoney(value)
  }
  if (c.type === 'date') {
    try {
      const d = new Date(String(value))
      return new Intl.DateTimeFormat('fr-FR').format(d)
    }
    catch { return String(value) }
  }
  if (c.type === 'number') {
    return new Intl.NumberFormat('fr-FR').format(Number(value))
  }
  return String(value)
}

const liveStatus = computed<string>(
  () => `${sortedRows.value.length} ligne(s) affichée(s)`,
)

const VIRTUAL_ITEM_HEIGHT = 36

const virtualItems = computed(() =>
  sortedRows.value.map((row, i) => ({ __viz_idx: i, row })),
)
</script>

<template>
  <div class="viz-table-wrap">
    <div v-if="props.columns.some((c) => c.searchable !== false)" class="viz-table__toolbar">
      <input
        v-model="search"
        class="viz-table__search"
        type="search"
        placeholder="Rechercher…"
        :aria-label="'Rechercher dans le tableau'"
      >
    </div>
    <span class="sr-only" role="status" aria-live="polite">{{ liveStatus }}</span>

    <table v-if="!useVirtual" class="viz-table" role="table" :aria-label="props.ariaLabel ?? 'Tableau'">
      <thead>
        <tr>
          <th
            v-for="c in props.columns"
            :key="c.key"
            scope="col"
            :aria-sort="ariaSort(c)"
            :class="alignClass(c)"
          >
            <button
              v-if="c.sortable !== false"
              type="button"
              class="viz-table__sortbtn"
              @click="onSort(c)"
            >
              {{ c.label }}
              <span v-if="sortKey === c.key" aria-hidden="true">{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
            </button>
            <span v-else>{{ c.label }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="pagedRows.length === 0">
          <td :colspan="props.columns.length">
            <VizEmptyState :message="props.emptyMessage" height="6rem" />
          </td>
        </tr>
        <tr v-for="(row, idx) in pagedRows" :key="idx">
          <td v-for="c in props.columns" :key="c.key" :class="alignClass(c)">
            <slot
              :name="`cell-${c.key}`"
              :row="row"
              :value="row[c.key]"
              :format="formatCell(c, row[c.key])"
            >
              <span v-if="c.type === 'badge'" class="viz-table__badge">
                {{ formatCell(c, row[c.key]) }}
              </span>
              <template v-else>{{ formatCell(c, row[c.key]) }}</template>
            </slot>
            <slot
              v-if="(row as { source_id?: string }).source_id && c === props.columns[props.columns.length - 1]"
              name="cell-source"
              :row="row"
            >
              <VizSourcePin :source_id="(row as { source_id: string }).source_id" />
            </slot>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="viz-table__virtual" role="table" :aria-label="props.ariaLabel ?? 'Tableau virtualisé'">
      <div class="viz-table__virtual-head">
        <div
          v-for="c in props.columns"
          :key="c.key"
          class="viz-table__virtual-th"
          :class="alignClass(c)"
        >
          <button
            v-if="c.sortable !== false"
            type="button"
            class="viz-table__sortbtn"
            @click="onSort(c)"
          >
            {{ c.label }}
            <span v-if="sortKey === c.key" aria-hidden="true">{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
          </button>
          <span v-else>{{ c.label }}</span>
        </div>
      </div>
      <RecycleScroller
        :items="virtualItems"
        :item-size="VIRTUAL_ITEM_HEIGHT"
        :buffer="200"
        key-field="__viz_idx"
        class="viz-table__scroll"
      >
        <template #default="{ item }">
          <div class="viz-table__virtual-row" :data-row="(item as { __viz_idx: number }).__viz_idx">
            <div
              v-for="c in props.columns"
              :key="c.key"
              class="viz-table__virtual-td"
              :class="alignClass(c)"
            >
              {{ formatCell(c, ((item as { row: Record<string, unknown> }).row)[c.key]) }}
            </div>
          </div>
        </template>
      </RecycleScroller>
    </div>

    <nav v-if="props.paginate && pageCount > 1" class="viz-table__pager" aria-label="Pagination">
      <button type="button" :disabled="page === 0" @click="page = Math.max(0, page - 1)">Précédent</button>
      <span>Page {{ page + 1 }} / {{ pageCount }}</span>
      <button type="button" :disabled="page + 1 >= pageCount" @click="page = Math.min(pageCount - 1, page + 1)">Suivant</button>
    </nav>
  </div>
</template>

<style scoped>
@import "vue-virtual-scroller/dist/vue-virtual-scroller.css";

.viz-table-wrap { width: 100%; }
.viz-table__toolbar { margin-bottom: .5rem; }
.viz-table__search {
  width: 100%; max-width: 18rem;
  padding: .35rem .6rem;
  border: 1px solid var(--color-neutral-300, #d4d4d4);
  border-radius: .375rem;
  font-size: .85rem;
}
.viz-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.viz-table th, .viz-table td { padding: .5rem .75rem; border-bottom: 1px solid var(--color-neutral-200, #e5e5e5); }
.viz-table th { background: var(--color-neutral-50, #fafafa); text-align: left; font-weight: 600; }
.viz-table__cell--right { text-align: right; font-variant-numeric: tabular-nums; }
.viz-table__cell--center { text-align: center; }
.viz-table__sortbtn {
  background: none; border: none; padding: 0; cursor: pointer; font: inherit; color: inherit;
}
.viz-table__sortbtn:focus-visible {
  outline: 2px solid var(--color-info-500, #0ea5e9);
  outline-offset: 2px;
}
.viz-table__badge {
  display: inline-flex; padding: .15rem .5rem; border-radius: 999px;
  background: var(--color-neutral-100, #f5f5f5);
  font-size: .75rem;
}
.viz-table__virtual { width: 100%; border: 1px solid var(--color-neutral-200, #e5e5e5); border-radius: .375rem; overflow: hidden; }
.viz-table__virtual-head { display: flex; background: var(--color-neutral-50, #fafafa); }
.viz-table__virtual-th { flex: 1; padding: .5rem .75rem; font-weight: 600; }
.viz-table__scroll { height: 24rem; }
.viz-table__virtual-row { display: flex; height: 36px; align-items: center; border-bottom: 1px solid var(--color-neutral-100, #f5f5f5); }
.viz-table__virtual-td { flex: 1; padding: 0 .75rem; }
.viz-table__pager { display: flex; align-items: center; justify-content: flex-end; gap: .5rem; margin-top: .5rem; font-size: .85rem; }
.viz-table__pager button { padding: .25rem .5rem; border: 1px solid var(--color-neutral-300, #d4d4d4); border-radius: .25rem; background: white; cursor: pointer; }
.viz-table__pager button:disabled { opacity: .5; cursor: not-allowed; }
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
</style>
