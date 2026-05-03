/**
 * Peg fixe FCFA ↔ EUR — F39 R9, constitution P5.
 *
 * Source : peg défini par la convention monétaire UEMOA (1 EUR = 655.957 XOF).
 * Le backend l'expose comme constante sourcée (cf. migration `0001_initial_schema`
 * et seeds des `Source`s monétaires) ; côté frontend on duplique strictement la
 * valeur pour permettre la conversion live dans `AskNumber.vue` sans aller-retour
 * réseau. Toute évolution backend (très improbable — c'est un peg légal) DOIT être
 * répercutée ici dans la même PR.
 *
 * Précision : on travaille en `BigInt` pour éviter toute dérive `Number`. Les
 * montants restent toujours typés `string` côté wrapper (cf. data-model
 * `ToolResponse.value.amount: Decimal`).
 */

export const XOF_PER_EUR = '655.957'

// Représentation interne : 655957 / 1000  → numérateur/dénominateur entier.
const PEG_NUM = 655_957n
const PEG_DEN = 1_000n

function parseDecimal(input: string): { sign: 1n | -1n; intPart: bigint; fracPart: bigint; fracDigits: number } {
  if (typeof input !== 'string') throw new TypeError('moneyPeg: amount must be a string')
  const trimmed = input.trim()
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) {
    throw new RangeError(`moneyPeg: invalid decimal "${input}"`)
  }
  const sign: 1n | -1n = trimmed.startsWith('-') ? -1n : 1n
  const unsigned = trimmed.replace(/^-/, '')
  const [intStr, fracStr = ''] = unsigned.split('.')
  return {
    sign,
    intPart: BigInt(intStr ?? '0'),
    fracPart: fracStr.length > 0 ? BigInt(fracStr) : 0n,
    fracDigits: fracStr.length,
  }
}

function toScaled(input: string, scale: number): bigint {
  const { sign, intPart, fracPart, fracDigits } = parseDecimal(input)
  let scaled = intPart * 10n ** BigInt(scale)
  if (fracDigits > 0) {
    if (fracDigits <= scale) {
      scaled += fracPart * 10n ** BigInt(scale - fracDigits)
    } else {
      // Tronque (banker's-rounding non requis : on garde 6 décimales internes).
      scaled += fracPart / 10n ** BigInt(fracDigits - scale)
    }
  }
  return sign * scaled
}

function fromScaled(value: bigint, scale: number, decimals: number): string {
  const sign = value < 0n ? '-' : ''
  const abs = value < 0n ? -value : value
  const factor = 10n ** BigInt(scale)
  const intPart = abs / factor
  const fracPart = abs % factor

  if (decimals === 0) return `${sign}${intPart.toString()}`

  // Tronque ou pad la partie fractionnaire.
  let fracStr = fracPart.toString().padStart(scale, '0')
  if (decimals < scale) {
    fracStr = fracStr.slice(0, decimals)
  } else if (decimals > scale) {
    fracStr = fracStr.padEnd(decimals, '0')
  }
  return `${sign}${intPart.toString()}.${fracStr}`
}

export interface ConvertOptions {
  decimals?: number // défaut: 2 pour EUR, 0 pour XOF
}

// 1 EUR = 655.957 XOF. amount EUR → amount XOF.
export function eurToXof(amount: string, opts: ConvertOptions = {}): string {
  const decimals = opts.decimals ?? 0
  const scale = 6 // précision interne
  const scaled = toScaled(amount, scale)
  const result = (scaled * PEG_NUM) / PEG_DEN
  return fromScaled(result, scale, decimals)
}

// amount XOF → amount EUR.
export function xofToEur(amount: string, opts: ConvertOptions = {}): string {
  const decimals = opts.decimals ?? 2
  const scale = 6
  const scaled = toScaled(amount, scale)
  const result = (scaled * PEG_DEN) / PEG_NUM
  return fromScaled(result, scale, decimals)
}
