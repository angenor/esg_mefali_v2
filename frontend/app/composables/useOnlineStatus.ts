// F38 T007 — Statut en ligne (SSR-safe)
import { ref, onMounted, onBeforeUnmount, type Ref } from 'vue'

export function useOnlineStatus(): { isOnline: Readonly<Ref<boolean>> } {
  const isOnline = ref(true)

  onMounted(() => {
    if (typeof window === 'undefined') return
    isOnline.value = window.navigator.onLine
    const onOnline = () => {
      isOnline.value = true
    }
    const onOffline = () => {
      isOnline.value = false
    }
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)

    onBeforeUnmount(() => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    })
  })

  return { isOnline }
}
