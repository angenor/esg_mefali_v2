// F42 — usePasswordStrength : zxcvbn-ts wrapper avec critères stricts
import { computed, type ComputedRef, type Ref } from "vue"
import { zxcvbnOptions, zxcvbn } from "@zxcvbn-ts/core"
import * as zxcvbnCommon from "@zxcvbn-ts/language-common"
import * as zxcvbnFr from "@zxcvbn-ts/language-fr"

let configured = false
function configureOnce(): void {
  if (configured) return
  zxcvbnOptions.setOptions({
    translations: zxcvbnFr.translations,
    graphs: zxcvbnCommon.adjacencyGraphs,
    dictionary: {
      ...zxcvbnCommon.dictionary,
      ...zxcvbnFr.dictionary,
    },
  })
  configured = true
}

export interface PasswordCriteria {
  length12: boolean
  uppercase: boolean
  digit: boolean
  symbol: boolean
}

export interface PasswordStrengthResult {
  score: 0 | 1 | 2 | 3 | 4
  label: string
  feedback: { warning: string | null; suggestions: string[] }
  meetsBaseCriteria: boolean
  criteria: PasswordCriteria
  isAcceptable: boolean
}

const LABELS: Record<0 | 1 | 2 | 3 | 4, string> = {
  0: "Très faible",
  1: "Faible",
  2: "Acceptable",
  3: "Fort",
  4: "Très fort",
}

export function usePasswordStrength(
  password: Ref<string>,
): ComputedRef<PasswordStrengthResult> {
  configureOnce()
  return computed<PasswordStrengthResult>(() => {
    const pwd = password.value || ""
    const criteria: PasswordCriteria = {
      length12: pwd.length >= 12,
      uppercase: /[A-Z]/.test(pwd),
      digit: /\d/.test(pwd),
      symbol: /[^A-Za-z0-9]/.test(pwd),
    }
    const meetsBaseCriteria =
      criteria.length12 && criteria.uppercase && criteria.digit && criteria.symbol

    if (!pwd) {
      return {
        score: 0,
        label: LABELS[0],
        feedback: { warning: null, suggestions: [] },
        meetsBaseCriteria: false,
        criteria,
        isAcceptable: false,
      }
    }

    const result = zxcvbn(pwd)
    const score = result.score as 0 | 1 | 2 | 3 | 4
    return {
      score,
      label: LABELS[score],
      feedback: {
        warning: result.feedback.warning || null,
        suggestions: result.feedback.suggestions || [],
      },
      meetsBaseCriteria,
      criteria,
      isAcceptable: meetsBaseCriteria && score >= 3,
    }
  })
}
