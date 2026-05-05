<script setup lang="ts">
/**
 * /chat — redirige vers le dernier thread ou crée un thread vide.
 * F41 / US1 (T020).
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '~/stores/chat'

definePageMeta({ middleware: ['pme-only'] })

const router = useRouter()
const store = useChatStore()

onMounted(async () => {
  await store.loadThreads()
  const last = store.threads[0]
  if (last) {
    await router.replace(`/chat/${last.id}`)
    return
  }
  const created = await store.newThread()
  if (created) await router.replace(`/chat/${created.id}`)
})
</script>

<template>
  <div class="chat-loading" role="status" aria-live="polite">
    Chargement…
  </div>
</template>

<style scoped>
.chat-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100dvh;
  color: rgb(var(--color-fg-muted, 107 114 128));
}
</style>
