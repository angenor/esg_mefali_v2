<script setup lang="ts">
// F42 T028 — Wizard register 3 steps
import { ref } from "vue"
import RegisterProgressBar from "~/components/auth/RegisterProgressBar.vue"
import RegisterStepIdentifiants from "~/components/auth/RegisterStepIdentifiants.vue"
import RegisterStepEntreprise from "~/components/auth/RegisterStepEntreprise.vue"
import RegisterStepConsentements from "~/components/auth/RegisterStepConsentements.vue"
import { useT } from "~/composables/useT"

definePageMeta({
  layout: "auth",
  public: true,
  title: "Créer un compte",
})

const { t } = useT()
const router = useRouter()
const { register } = useAuth()

interface Draft {
  email: string
  password: string
  raison_sociale: string
  secteur: string
  cgu: boolean
  rgpd: boolean
}

const TOTAL = 3
const currentStep = ref<1 | 2 | 3>(1)
const submitting = ref(false)
const error = ref<string | null>(null)

const draft = ref<Draft>({
  email: "",
  password: "",
  raison_sociale: "",
  secteur: "",
  cgu: false,
  rgpd: false,
})

function onStep1(data: { email: string; password: string }) {
  draft.value = { ...draft.value, ...data }
  currentStep.value = 2
}

function onStep2(data: { raison_sociale: string; secteur: string }) {
  draft.value = { ...draft.value, ...data }
  currentStep.value = 3
}

async function onStep3(data: { cgu: boolean; rgpd: boolean }) {
  draft.value = { ...draft.value, ...data }
  error.value = null
  submitting.value = true
  try {
    await register({ email: draft.value.email, password: draft.value.password })
    await router.push("/onboarding/welcome")
  } catch (e: unknown) {
    const code = (e as { data?: { detail?: { code?: string } } })?.data?.detail?.code
    error.value =
      code === "email_already_used"
        ? t("auth.register.error_email_used")
        : t("auth.register.error_generic")
  } finally {
    submitting.value = false
  }
}

function goBack() {
  if (currentStep.value > 1) currentStep.value = (currentStep.value - 1) as 1 | 2
}
</script>

<template>
  <main class="max-w-md w-full mx-auto py-8 px-4 space-y-6" data-testid="register-wizard">
    <header class="space-y-2">
      <h1 class="text-2xl font-bold">{{ t("auth.register.title") }}</h1>
      <p class="text-sm text-gray-600">{{ t("auth.register.subtitle") }}</p>
    </header>

    <RegisterProgressBar :step="currentStep" :total="TOTAL" />

    <RegisterStepIdentifiants
      v-if="currentStep === 1"
      :initial="{ email: draft.email, password: draft.password }"
      @next="onStep1"
    />
    <RegisterStepEntreprise
      v-else-if="currentStep === 2"
      :initial="{ raison_sociale: draft.raison_sociale, secteur: draft.secteur }"
      @next="onStep2"
      @previous="goBack"
    />
    <RegisterStepConsentements
      v-else
      :initial="{ cgu: draft.cgu, rgpd: draft.rgpd }"
      :submitting="submitting"
      @next="onStep3"
      @previous="goBack"
    />

    <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

    <p class="text-sm text-gray-600 text-center">
      {{ t("auth.register.have_account") }}
      <NuxtLink to="/login" class="underline text-brand-700">
        {{ t("auth.register.login_link") }}
      </NuxtLink>
    </p>
  </main>
</template>
