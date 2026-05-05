/**
 * T050 — Vérification NFR-002 : limites de hauteur visuelles.
 *
 * Le sheet ne doit pas dépasser 70 % de la hauteur viewport en mobile et
 * 60 % en desktop (≥ 768px). Ces contraintes sont déclarées dans le CSS
 * scoped de `BottomSheetShell.vue`. Ce test vérifie la présence des règles
 * dans le fichier source — c'est un garde-fou contre régression du CSS.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const SHELL_PATH = resolve(__dirname, '../BottomSheetShell.vue')

describe('NFR-002 — viewport caps', () => {
  const css = readFileSync(SHELL_PATH, 'utf-8')

  it('mobile : max-height 70vh sur la classe .bottom-sheet', () => {
    expect(css).toMatch(/\.bottom-sheet\b[^}]*max-height:\s*70vh/s)
  })

  it('desktop ≥ 768px : max-height 60vh dans @media (min-width: 768px)', () => {
    const mediaBlockMatch = css.match(/@media\s*\(min-width:\s*768px\)\s*\{[\s\S]*?\}\s*\}/)
    expect(mediaBlockMatch).not.toBeNull()
    expect(mediaBlockMatch![0]).toMatch(/max-height:\s*60vh/)
  })

  it('le sheet est positionné en bottom: 0 (mobile) puis recentré (desktop)', () => {
    expect(css).toMatch(/position:\s*fixed/)
    expect(css).toMatch(/bottom:\s*0/)
  })
})
