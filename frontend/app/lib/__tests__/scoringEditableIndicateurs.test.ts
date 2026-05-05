// F46 T004 — Vérifie le miroir manuel de backend/app/scoring/value_source.py.
import { describe, expect, it } from 'vitest'
import {
  SCORING_EDITABLE_INDICATEUR_CODES,
  SCORING_INDICATEUR_TO_ENTREPRISE_PATH,
} from '../scoringEditableIndicateurs'

describe('scoringEditableIndicateurs', () => {
  it('contient les codes indicateurs MVP attendus', () => {
    const expected = [
      'EFFECTIFS_TOTAL',
      'CA_AMOUNT',
      'PAYS_SIEGE',
      'GOUVERNANCE_BOARD_INDEPENDENCE',
      'PRATIQUE_POLITIQUE_RSE',
    ]
    for (const code of expected) {
      expect(SCORING_EDITABLE_INDICATEUR_CODES.has(code)).toBe(true)
    }
  })

  it('a une entrée dans le Record pour chaque code du Set', () => {
    for (const code of SCORING_EDITABLE_INDICATEUR_CODES) {
      expect(SCORING_INDICATEUR_TO_ENTREPRISE_PATH[code]).toBeDefined()
    }
  })

  it('chaque entrée Record est typée correctement', () => {
    for (const [code, path] of Object.entries(SCORING_INDICATEUR_TO_ENTREPRISE_PATH)) {
      expect(typeof path.field).toBe('string')
      expect(['number', 'string', 'boolean', 'money']).toContain(path.type)
      if (path.jsonPath !== undefined) {
        expect(typeof path.jsonPath).toBe('string')
      }
      // Tous les codes mappés doivent être dans le Set d'éditables.
      expect(SCORING_EDITABLE_INDICATEUR_CODES.has(code)).toBe(true)
    }
  })
})
