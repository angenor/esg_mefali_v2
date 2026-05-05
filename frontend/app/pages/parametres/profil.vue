<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SettingsLayout from '~/components/parametres/SettingsLayout.vue'
import ProfileForm from '~/components/parametres/ProfileForm.vue'
import EmailChangeBottomSheet from '~/components/parametres/EmailChangeBottomSheet.vue'
import PasswordChangeBottomSheet from '~/components/parametres/PasswordChangeBottomSheet.vue'

definePageMeta({
  layout: 'default',
  middleware: ['pme-only'],
  breadcrumb: [{ label: 'Paramètres' }, { label: 'Profil' }],
  title: 'Profil',
})

interface Me {
  email: string
  email_pending?: string | null
}

const me = ref<Me | null>(null)
const emailSheet = ref(false)
const passwordSheet = ref(false)

const currentEmail = computed(() => me.value?.email ?? '')
const pendingEmail = computed(() => me.value?.email_pending ?? null)

async function refreshMe() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string
  me.value = await $fetch<Me>(`${apiBase}/me`, { credentials: 'include' })
}

onMounted(() => {
  void refreshMe()
})

function onSent(_newEmail: string) {
  void refreshMe()
}
</script>

<template>
  <SettingsLayout>
    <ProfileForm
      :email="currentEmail"
      :email-pending="pendingEmail"
      @change-email="emailSheet = true"
      @change-password="passwordSheet = true"
    />
    <EmailChangeBottomSheet
      v-model="emailSheet"
      :current-email="currentEmail"
      @sent="onSent"
    />
    <PasswordChangeBottomSheet v-model="passwordSheet" />
  </SettingsLayout>
</template>
