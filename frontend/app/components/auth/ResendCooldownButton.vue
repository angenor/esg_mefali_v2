<script setup lang="ts">
// F42 T050 — Bouton avec cooldown localStorage
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useT } from "~/composables/useT"

const props = withDefaults(
  defineProps<{
    email: string
    cooldownSeconds?: number
    label?: string
    cooldownLabel?: string
    onSend?: () => Promise<void>
  }>(),
  { cooldownSeconds: 60 },
)

const emit = defineEmits<{
  (e: "sent"): void
  (e: "failed", err: unknown): void
}>()

const { t } = useT()

const remaining = ref(0)
const sending = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const storageKey = computed(() => `resend-cooldown:${props.email.toLowerCase()}`)

function tick() {
  if (typeof window === "undefined") return
  const expires = Number(window.localStorage.getItem(storageKey.value) ?? "0")
  const left = Math.max(0, Math.ceil((expires - Date.now()) / 1000))
  remaining.value = left
  if (left === 0 && timer) {
    clearInterval(timer)
    timer = null
  }
}

function startTimer() {
  if (timer) clearInterval(timer)
  tick()
  timer = setInterval(tick, 250)
}

async function trigger() {
  if (sending.value || remaining.value > 0) return
  sending.value = true
  try {
    if (props.onSend) await props.onSend()
    if (typeof window !== "undefined") {
      const expires = Date.now() + props.cooldownSeconds * 1000
      window.localStorage.setItem(storageKey.value, String(expires))
    }
    startTimer()
    emit("sent")
  } catch (err) {
    emit("failed", err)
  } finally {
    sending.value = false
  }
}

onMounted(startTimer)
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <button
    type="button"
    :disabled="remaining > 0 || sending"
    class="text-sm underline text-brand-700 hover:text-brand-800 disabled:opacity-50 disabled:no-underline"
    @click="trigger"
  >
    <span v-if="remaining > 0">
      {{ cooldownLabel ?? t("auth.forgot.resend_cooldown", { n: remaining }) }}
    </span>
    <span v-else>{{ label ?? t("auth.forgot.resend") }}</span>
  </button>
</template>
