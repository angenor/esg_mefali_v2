<script setup lang="ts">
// F43 T046 — ProjetWizard : orchestre les 4 steps + transitions gsap + ESC=confirm-close.
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { gsap } from "gsap"
import { useFocusTrap } from "~/composables/useFocusTrap"
import { useReducedMotion } from "~/composables/useReducedMotion"
import { useT } from "~/composables/useT"
import { useProjetWizard } from "~/composables/useProjetWizard"
import type { ProjetRead } from "~/stores/projets"
import ProjetWizardStep1 from "./ProjetWizardStep1.vue"
import ProjetWizardStep2 from "./ProjetWizardStep2.vue"
import ProjetWizardStep3 from "./ProjetWizardStep3.vue"
import ProjetWizardStep4 from "./ProjetWizardStep4.vue"

interface Props {
  open: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "close"): void
  (e: "created", projet: ProjetRead): void
}>()

const { t } = useT()
const dialogRef = ref<HTMLElement | null>(null)
const stepContainerRef = ref<HTMLElement | null>(null)
const reduced = useReducedMotion()
const trap = useFocusTrap(dialogRef, { returnFocus: true })

const wizard = useProjetWizard()
const submitting = ref(false)
const submitError = ref<string | null>(null)

const stepLabel = computed(() => {
  const k = `profil.projets.wizard.step.${wizard.step.value}` as
    | "profil.projets.wizard.step.1"
    | "profil.projets.wizard.step.2"
    | "profil.projets.wizard.step.3"
    | "profil.projets.wizard.step.4"
  return t(k)
})

function onUpdateStep(payload: unknown): void {
  Object.assign(wizard.data[`step${wizard.step.value}` as keyof typeof wizard.data], payload as object)
}

async function animateTransition(): Promise<void> {
  if (reduced.value || !stepContainerRef.value) return
  await nextTick()
  gsap.fromTo(
    stepContainerRef.value,
    { opacity: 0, x: 20 },
    { opacity: 1, x: 0, duration: 0.2, ease: "power1.out" },
  )
}

function next(): void {
  if (!wizard.canAdvance.value) return
  wizard.next()
  void animateTransition()
}

function prev(): void {
  wizard.prev()
  void animateTransition()
}

async function submit(): Promise<void> {
  if (!wizard.canAdvance.value || submitting.value) return
  submitting.value = true
  submitError.value = null
  try {
    const created = await wizard.submit()
    emit("created", created)
    wizard.reset()
    emit("close")
  } catch (err: unknown) {
    submitError.value = (err as Error).message ?? "Erreur"
  } finally {
    submitting.value = false
  }
}

function requestClose(): void {
  const hasInput = Object.values(wizard.data).some((s) =>
    Object.values(s).some((v) => v !== "" && v !== null && v !== undefined),
  )
  if (hasInput) {
    if (!window.confirm(t("profil.projets.wizard.cancel_confirm"))) return
  }
  wizard.reset()
  emit("close")
}

function onKeydown(e: KeyboardEvent): void {
  if (!props.open) return
  if (e.key === "Escape") {
    e.preventDefault()
    requestClose()
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick()
      trap.activate()
      document.addEventListener("keydown", onKeydown, true)
      void animateTransition()
    } else {
      trap.deactivate()
      document.removeEventListener("keydown", onKeydown, true)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  trap.deactivate()
  document.removeEventListener("keydown", onKeydown, true)
})
</script>

<template>
  <Teleport v-if="open" to="body">
    <div class="projet-wizard">
      <div class="projet-wizard__overlay" @click="requestClose" />
      <div
        ref="dialogRef"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wiz-title"
        tabindex="-1"
        class="projet-wizard__panel"
      >
        <header class="projet-wizard__header">
          <h2 id="wiz-title" class="projet-wizard__title">{{ t("profil.projets.wizard.title") }}</h2>
          <p class="projet-wizard__step-label">
            <span aria-current="step">{{ wizard.step.value }} / 4</span> — {{ stepLabel }}
          </p>
        </header>

        <div ref="stepContainerRef" class="projet-wizard__body">
          <ProjetWizardStep1
            v-if="wizard.step.value === 1"
            :data="wizard.data.step1"
            :errors="wizard.errors.value"
            @update:data="onUpdateStep"
          />
          <ProjetWizardStep2
            v-else-if="wizard.step.value === 2"
            :data="wizard.data.step2"
            :errors="wizard.errors.value"
            @update:data="onUpdateStep"
          />
          <ProjetWizardStep3
            v-else-if="wizard.step.value === 3"
            :data="wizard.data.step3"
            :errors="wizard.errors.value"
            @update:data="onUpdateStep"
          />
          <ProjetWizardStep4
            v-else
            :data="wizard.data.step4"
            :errors="wizard.errors.value"
            @update:data="onUpdateStep"
          />
        </div>

        <p v-if="submitError" class="projet-wizard__submit-error" role="alert">
          {{ submitError }}
        </p>

        <footer class="projet-wizard__footer">
          <button
            type="button"
            class="projet-wizard__btn projet-wizard__btn--ghost"
            @click="requestClose"
          >
            {{ t("profil.projets.wizard.cancel") }}
          </button>
          <button
            v-if="wizard.step.value > 1"
            type="button"
            class="projet-wizard__btn"
            @click="prev"
          >
            {{ t("profil.projets.wizard.prev") }}
          </button>
          <button
            v-if="wizard.step.value < 4"
            type="button"
            class="projet-wizard__btn projet-wizard__btn--primary"
            :disabled="!wizard.canAdvance.value"
            @click="next"
          >
            {{ t("profil.projets.wizard.next") }}
          </button>
          <button
            v-else
            type="button"
            class="projet-wizard__btn projet-wizard__btn--primary"
            :disabled="!wizard.canAdvance.value || submitting"
            @click="submit"
          >
            {{ submitting ? "…" : t("profil.projets.wizard.submit") }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.projet-wizard {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 1rem;
}
.projet-wizard__overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
}
.projet-wizard__panel {
  position: relative;
  background: #fff;
  border-radius: 0.875rem;
  width: 100%;
  max-width: 36rem;
  padding: 1.5rem 1.75rem;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  display: grid;
  gap: 1rem;
  max-height: 90vh;
  overflow-y: auto;
}
.projet-wizard__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
}
.projet-wizard__step-label {
  font-size: 0.8125rem;
  color: #475569;
}
.projet-wizard__step-label [aria-current="step"] {
  font-weight: 600;
  color: #15803d;
}
.projet-wizard__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.projet-wizard__btn {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem 0.875rem;
  background: #fff;
  font-weight: 500;
  cursor: pointer;
}
.projet-wizard__btn--primary {
  background: #15803d;
  color: #fff;
  border-color: #15803d;
}
.projet-wizard__btn--primary:disabled {
  background: #94a3b8;
  border-color: #94a3b8;
  cursor: not-allowed;
}
.projet-wizard__btn--ghost {
  border-color: transparent;
  color: #475569;
}
.projet-wizard__submit-error {
  color: #b91c1c;
  font-size: 0.8125rem;
}
</style>
