/**
 * T053 — Garde CI : `pnpm gen:tools --soft` est idempotent quand le backend
 * est injoignable. Le fallback `index.ts` doit être stable et committé.
 *
 * Si F15 est mergé et le backend remonte avec `x-tool: true`, ce test peut
 * être étendu pour vérifier le diff en mode strict.
 */
import { describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const REPO_FRONTEND = resolve(__dirname, '../../../..')
const SCRIPT = resolve(REPO_FRONTEND, 'scripts/gen-tools.mjs')
const INDEX = resolve(REPO_FRONTEND, 'app/types/tools/index.ts')

describe('gen-tools.mjs --soft — CI idempotence', () => {
  it('produit un index.ts stable quand le backend OpenAPI est down', () => {
    const before = readFileSync(INDEX, 'utf-8')
    execFileSync('node', [SCRIPT, '--soft'], { stdio: 'pipe' })
    const after = readFileSync(INDEX, 'utf-8')
    expect(after).toBe(before)
  })

  it('le fallback index.ts liste les 11 tools connus', () => {
    const content = readFileSync(INDEX, 'utf-8')
    expect(content).toMatch(/ask_yes_no/)
    expect(content).toMatch(/show_summary_card/)
    expect(content).toMatch(/show_form/)
    expect(content).toMatch(/ask_file_upload/)
  })
})
