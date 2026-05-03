// F40 T046 — Invariants statiques I1 et I2.
// I1 : aucun `<input>`, `<button type="submit">`, ni `v-model` exposé dans les
// composants viz (display-only — P10 / SC-008). Exception : VizDataTable a un
// `<input type="search">` interne qui n'écrit aucun état métier (filtre local).
// I2 : aucun littéral `amount: <number>` (Money typé strict — P5 / SC-009).
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const VIZ_DIR = dirname(HERE) // app/components/viz

function listVueFiles(dir: string): string[] {
  const out: string[] = []
  for (const name of readdirSync(dir)) {
    if (name === '__tests__' || name === 'internal') continue
    const full = join(dir, name)
    const s = statSync(full)
    if (s.isDirectory()) out.push(...listVueFiles(full))
    else if (name.endsWith('.vue')) out.push(full)
  }
  return out
}

const FILES = listVueFiles(VIZ_DIR)
const ALLOW_INPUT_FILES = new Set(['VizDataTable.vue']) // recherche full-text locale

describe('viz library — invariants statiques', () => {
  it('I1 : aucun <input> / submit / v-model exposé hors VizDataTable', () => {
    const violations: string[] = []
    for (const f of FILES) {
      const base = f.split('/').pop() ?? f
      const src = readFileSync(f, 'utf8')
      if (!ALLOW_INPUT_FILES.has(base)) {
        if (/<input\b/.test(src)) violations.push(`${base}: <input> détecté`)
      }
      if (/type=["']submit["']/.test(src)) violations.push(`${base}: button type=submit détecté`)
      // v-model exposé sur élément public (heuristique : v-model dans <template> hors search)
      const tplStart = src.indexOf('<template>')
      const tpl = tplStart >= 0 ? src.slice(tplStart) : ''
      const vmodels = tpl.match(/v-model[\w:.-]*=/g) ?? []
      for (const _ of vmodels) {
        if (!ALLOW_INPUT_FILES.has(base) && !/v-model="search"/.test(tpl)) {
          violations.push(`${base}: v-model présent en template`)
          break
        }
      }
    }
    expect(violations).toEqual([])
  })

  it('I2 : aucun littéral { amount: <number> } dans le code source', () => {
    const violations: string[] = []
    for (const f of FILES) {
      const src = readFileSync(f, 'utf8')
      if (/amount\s*:\s*\d/.test(src)) {
        violations.push(`${f}: littéral amount numérique détecté`)
      }
    }
    expect(violations).toEqual([])
  })
})
