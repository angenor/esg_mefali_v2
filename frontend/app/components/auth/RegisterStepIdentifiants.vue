<script setup lang="ts">
// F42 T025 — Step 1 : email + mot de passe
import { computed, ref } from "vue"
import PasswordStrengthMeter from "./PasswordStrengthMeter.vue"
import PasswordVisibilityToggle from "./PasswordVisibilityToggle.vue"
import { usePasswordStrength } from "~/composables/usePasswordStrength"
import { useT } from "~/composables/useT"

interface StepData {
  email: string
  password: string
}

const props = defineProps<{ initial?: Partial<StepData> }>()
const emit = defineEmits<{ (e: "next", data: StepData): void }>()

const { t } = useT()

const email = ref(props.initial?.email ?? "")
const password = ref(props.initial?.password ?? "")
const passwordConfirm = ref(props.initial?.password ?? "")
const showPwd = ref(false)
const showPwdConfirm = ref(false)
const submitted = ref(false)

const strength = usePasswordStrength(password)

const passwordsMatch = computed(
  () => password.value.length > 0 && password.value === passwordConfirm.value,
)
const emailValid = computed(() =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value),
)
const canSubmit = computed(
  () => emailValid.value && strength.value.isAcceptable && passwordsMatch.value,
)

function onSubmit() {
  submitted.value = true
  if (!canSubmit.value) return
  emit("next", { email: email.value.trim(), password: password.value })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="onSubmit" data-testid="step-identifiants">
    <h2 class="text-lg font-semibold">{{ t("auth.register.step1.title") }}</h2>

    <div>
      <label for="r-email" class="block text-sm font-medium">{{ t("auth.register.step1.email") }}</label>
      <input
        id="r-email"
        v-model="email"
        type="email"
        required
        autocomplete="email"
        class="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-brand-500"
      />
    </div>

    <div>
      <label for="r-pwd" class="block text-sm font-medium">{{ t("auth.register.step1.password") }}</label>
      <div class="mt-1 relative">
        <input
          id="r-pwd"
          v-model="password"
          :type="showPwd ? 'text' : 'password'"
          required
          autocomplete="new-password"
          class="w-full border rounded-lg px-3 py-2 pr-12 focus:ring-2 focus:ring-brand-500"
        />
        <div class="absolute inset-y-0 right-2 flex items-center">
          <PasswordVisibilityToggle v-model:visible="showPwd" />
        </div>
      </div>
      <div class="mt-2">
        <PasswordStrengthMeter :password="password" />
      </div>
    </div>

    <div>
      <label for="r-pwd2" class="block text-sm font-medium">{{ t("auth.register.step1.password_confirm") }}</label>
      <div class="mt-1 relative">
        <input
          id="r-pwd2"
          v-model="passwordConfirm"
          :type="showPwdConfirm ? 'text' : 'password'"
          required
          autocomplete="new-password"
          class="w-full border rounded-lg px-3 py-2 pr-12 focus:ring-2 focus:ring-brand-500"
        />
        <div class="absolute inset-y-0 right-2 flex items-center">
          <PasswordVisibilityToggle v-model:visible="showPwdConfirm" />
        </div>
      </div>
      <p
        v-if="submitted && !passwordsMatch"
        class="text-xs text-red-600 mt-1"
      >
        {{ t("auth.register.step1.password_mismatch") }}
      </p>
      <p
        v-if="submitted && passwordsMatch && !strength.isAcceptable"
        class="text-xs text-red-600 mt-1"
      >
        {{ t("auth.register.step1.password_weak") }}
      </p>
    </div>

    <div class="flex justify-end">
      <button
        type="submit"
        :disabled="!canSubmit"
        class="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium px-5 py-2 rounded-lg"
      >
        {{ t("auth.register.next") }}
      </button>
    </div>
  </form>
</template>
