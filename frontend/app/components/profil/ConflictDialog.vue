<script setup lang="ts">
// F43 T009 — ConflictDialog : 3 choix (mine | theirs | cancel).
// role="alertdialog" : focus initial sur le bouton recommandé (« Garder ma valeur »).
// Animation gsap fade-in 150 ms (respecte prefers-reduced-motion).
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { gsap } from "gsap"
import { useFocusTrap } from "~/composables/useFocusTrap"
import { useReducedMotion } from "~/composables/useReducedMotion"
import { useT } from "~/composables/useT"

interface Props {
  open: boolean
  field: string
  yourValue: unknown
  currentValue: unknown
  /** Étiquette FR du champ — sinon affiche `field` brut. */
  fieldLabel?: string
}

type Choice = "mine" | "theirs" | "cancel"

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: "resolve", choice: Choice): void
}>()

const { t } = useT()
const dialogRef = ref<HTMLElement | null>(null)
const keepMineRef = ref<HTMLButtonElement | null>(null)
const reduced = useReducedMotion()
const trap = useFocusTrap(dialogRef, {
  initialFocus: undefined,
  returnFocus: true,
})

function format(value: unknown): string {
  if (value == null) return "—"
  if (typeof value === "object") {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

const yourFormatted = computed(() => format(props.yourValue))
const currentFormatted = computed(() => format(props.currentValue))

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape" && props.open) {
    e.preventDefault()
    emit("resolve", "cancel")
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      await nextTick()
      trap.activate()
      // Focus initial sur le bouton recommandé.
      keepMineRef.value?.focus()
      if (!reduced.value && dialogRef.value) {
        gsap.fromTo(
          dialogRef.value,
          { opacity: 0, y: -8 },
          { opacity: 1, y: 0, duration: 0.15, ease: "power1.out" },
        )
      }
      document.addEventListener("keydown", onKeydown, true)
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

function resolve(choice: Choice): void {
  emit("resolve", choice)
}
</script>

<template>
  <Teleport v-if="open" to="body">
    <div class="conflict-dialog" :data-reduced="reduced || undefined">
      <div class="conflict-dialog__overlay" @click="resolve('cancel')" />
      <div
        ref="dialogRef"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="conflict-dialog-title"
        aria-describedby="conflict-dialog-body"
        tabindex="-1"
        class="conflict-dialog__panel"
      >
        <header class="conflict-dialog__header">
          <h2 id="conflict-dialog-title" class="conflict-dialog__title">
            {{ t("profil.entreprise.conflict.title") }}
          </h2>
        </header>
        <div id="conflict-dialog-body" class="conflict-dialog__body">
          <p class="conflict-dialog__lead">
            {{ t("profil.entreprise.conflict.body") }}
          </p>
          <p class="conflict-dialog__field">
            {{ t("profil.entreprise.conflict.field_label", { field: fieldLabel ?? field }) }}
          </p>
          <dl class="conflict-dialog__values">
            <div>
              <dt>{{ t("profil.entreprise.conflict.your_value") }}</dt>
              <dd>{{ yourFormatted }}</dd>
            </div>
            <div>
              <dt>{{ t("profil.entreprise.conflict.current_value") }}</dt>
              <dd>{{ currentFormatted }}</dd>
            </div>
          </dl>
        </div>
        <footer class="conflict-dialog__footer">
          <button
            ref="keepMineRef"
            type="button"
            class="conflict-dialog__btn conflict-dialog__btn--primary"
            @click="resolve('mine')"
          >
            {{ t("profil.entreprise.conflict.keep_mine") }}
          </button>
          <button
            type="button"
            class="conflict-dialog__btn"
            @click="resolve('theirs')"
          >
            {{ t("profil.entreprise.conflict.keep_theirs") }}
          </button>
          <button
            type="button"
            class="conflict-dialog__btn conflict-dialog__btn--ghost"
            @click="resolve('cancel')"
          >
            {{ t("profil.entreprise.conflict.cancel") }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.conflict-dialog {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 1rem;
}
.conflict-dialog__overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
}
.conflict-dialog__panel {
  position: relative;
  background: #fff;
  border-radius: 0.75rem;
  max-width: 28rem;
  width: 100%;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  padding: 1.25rem 1.5rem;
}
.conflict-dialog__title {
  font-weight: 600;
  font-size: 1.125rem;
  color: #b45309;
}
.conflict-dialog__body {
  margin: 0.75rem 0 1.25rem;
  display: grid;
  gap: 0.5rem;
}
.conflict-dialog__values {
  display: grid;
  gap: 0.5rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  padding: 0.75rem;
}
.conflict-dialog__values div {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 0.5rem;
}
.conflict-dialog__values dt {
  font-weight: 600;
  color: #475569;
}
.conflict-dialog__values dd {
  color: #0f172a;
  word-break: break-word;
}
.conflict-dialog__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: flex-end;
}
.conflict-dialog__btn {
  border: 1px solid #cbd5e1;
  border-radius: 0.5rem;
  padding: 0.5rem 0.875rem;
  background: #fff;
  font-weight: 500;
  cursor: pointer;
}
.conflict-dialog__btn--primary {
  background: #15803d;
  color: #fff;
  border-color: #15803d;
}
.conflict-dialog__btn--ghost {
  border-color: transparent;
  color: #475569;
}
.conflict-dialog[data-reduced] .conflict-dialog__panel {
  animation: none;
}
</style>
