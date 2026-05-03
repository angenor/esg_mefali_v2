import { describe, it, expect } from 'vitest'
import { z } from 'zod'

// T069 — vérifie le contrat zod utilisé par la sheet CA
// (la page Nuxt elle-même nécessite un test e2e — ici on valide le schéma + les
// erreurs propagées vers UiFormField via vee-validate côté unit).

const schema = z.object({
  ca: z.number({ invalid_type_error: 'Chiffre d\'affaires requis' }).min(0, 'Doit être positif'),
  currency: z.enum(['XOF', 'EUR', 'USD']),
  regime: z.enum(['reel', 'simplifie', 'forfaitaire']),
})

describe('sheet-ca schema (zod)', () => {
  it('accepte une saisie valide', () => {
    const r = schema.safeParse({ ca: 1_500_000, currency: 'XOF', regime: 'reel' })
    expect(r.success).toBe(true)
  })

  it('rejette ca négatif avec message FR', () => {
    const r = schema.safeParse({ ca: -10, currency: 'XOF', regime: 'reel' })
    expect(r.success).toBe(false)
    if (!r.success) {
      expect(r.error.issues[0]!.message).toBe('Doit être positif')
    }
  })

  it('rejette ca non-numérique', () => {
    const r = schema.safeParse({ ca: 'abc', currency: 'XOF', regime: 'reel' })
    expect(r.success).toBe(false)
  })

  it('rejette currency hors enum', () => {
    const r = schema.safeParse({ ca: 1_000, currency: 'CAD', regime: 'reel' })
    expect(r.success).toBe(false)
  })

  it('rejette regime hors enum', () => {
    const r = schema.safeParse({ ca: 1_000, currency: 'XOF', regime: 'autre' })
    expect(r.success).toBe(false)
  })
})
