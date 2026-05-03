<script setup lang="ts">
// F43 T028 — MoneyField : saisie Decimal/devise + affichage parallèle XOF↔EUR (P5).
//
// Contrats :
//   - `modelValue.amount` est TOUJOURS un `string` (sérialisation Decimal). Number interdit.
//   - `currency ∈ {XOF, EUR, USD}`.
//   - Affichage live de la conversion XOF↔EUR via le peg fixe `useDecimal`.
//   - USD : pas de conversion live (R7) → mention « ≈ – ».
import { computed, ref, watch } from "vue"
import { useDecimal, type Currency } from "~/composables/useDecimal"
import { useFieldId } from "~/composables/useFieldId"

export interface MoneyValue {
  amount: string
  currency: Currency
}

interface Props {
  modelValue?: MoneyValue | null
  label?: string
  required?: boolean
  disabled?: boolean
  error?: string
  id?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  label: "",
  required: false,
  disabled: false,
  error: undefined,
  id: undefined,
})

const emit = defineEmits<{
  (e: "update:modelValue", v: MoneyValue | null): void
}>()

const { format, convertXofEur } = useDecimal()
const localId = props.id ?? useFieldId("ui-money")
const errorId = `${localId}-err`

const amountRaw = ref<string>(props.modelValue?.amount ?? "")
const currency = ref<Currency>(props.modelValue?.currency ?? "XOF")

watch(
  () => props.modelValue,
  (v) => {
    amountRaw.value = v?.amount ?? ""
    currency.value = v?.currency ?? "XOF"
  },
)

function isValidDecimal(s: string): boolean {
  return /^-?\d+(\.\d+)?$/.test(s.trim())
}

function emitChange(): void {
  const trimmed = amountRaw.value.trim().replace(",", ".")
  if (trimmed === "") {
    emit("update:modelValue", null)
    return
  }
  if (!isValidDecimal(trimmed)) return
  emit("update:modelValue", { amount: trimmed, currency: currency.value })
}

function onAmountInput(e: Event): void {
  amountRaw.value = (e.target as HTMLInputElement).value
  emitChange()
}

function onCurrencyChange(e: Event): void {
  currency.value = (e.target as HTMLSelectElement).value as Currency
  emitChange()
}

const parallel = computed<string>(() => {
  const trimmed = amountRaw.value.trim().replace(",", ".")
  if (trimmed === "" || !isValidDecimal(trimmed)) return ""
  if (currency.value === "USD") return "≈ –"
  const target = currency.value === "XOF" ? "EUR" : "XOF"
  try {
    const converted = convertXofEur(trimmed, currency.value, target)
    return `≈ ${format(converted, target)}`
  } catch {
    return ""
  }
})

const displayMain = computed<string>(() => {
  const trimmed = amountRaw.value.trim().replace(",", ".")
  if (trimmed === "" || !isValidDecimal(trimmed)) return ""
  try {
    return format(trimmed, currency.value)
  } catch {
    return ""
  }
})
</script>

<template>
  <div class="money-field" :data-error="!!error || undefined">
    <div class="money-field__row">
      <input
        :id="localId"
        type="text"
        inputmode="decimal"
        class="money-field__amount"
        :value="amountRaw"
        :disabled="disabled"
        :aria-label="label || 'Montant'"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error ? errorId : undefined"
        :aria-required="required || undefined"
        @input="onAmountInput"
      />
      <select
        class="money-field__currency"
        :value="currency"
        :disabled="disabled"
        :aria-label="'Devise'"
        @change="onCurrencyChange"
      >
        <option value="XOF">FCFA</option>
        <option value="EUR">€</option>
        <option value="USD">$</option>
      </select>
    </div>
    <p v-if="displayMain" class="money-field__display" data-testid="money-display">
      {{ displayMain }}
      <span v-if="parallel" class="money-field__parallel">· {{ parallel }}</span>
    </p>
    <p v-if="error" :id="errorId" class="money-field__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.money-field {
  display: grid;
  gap: 0.25rem;
}
.money-field__row {
  display: grid;
  grid-template-columns: 1fr 6rem;
  gap: 0.5rem;
}
.money-field__amount,
.money-field__currency {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.45rem 0.625rem;
  font: inherit;
  background: #fff;
  color: #0f172a;
}
.money-field__amount {
  text-align: right;
}
.money-field[data-error] .money-field__amount,
.money-field[data-error] .money-field__currency {
  border-color: #dc2626;
}
.money-field__amount:focus,
.money-field__currency:focus {
  outline: 2px solid #15803d;
  outline-offset: 1px;
}
.money-field__display {
  color: #0f172a;
  font-size: 0.875rem;
  font-weight: 500;
}
.money-field__parallel {
  color: #475569;
  font-weight: 400;
}
.money-field__error {
  color: #b91c1c;
  font-size: 0.8125rem;
}
</style>
