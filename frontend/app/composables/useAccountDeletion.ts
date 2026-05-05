// F52 US2 — Composable wrapper du store accountDeletion.
import { computed } from 'vue'
import { useAccountDeletionStore } from '~/stores/accountDeletion'

export function useAccountDeletion() {
  const store = useAccountDeletionStore()

  const scheduledDate = computed(() => {
    if (!store.request) return null
    try {
      return new Date(store.request.scheduled_for).toLocaleDateString('fr-FR', {
        dateStyle: 'long',
      })
    } catch {
      return store.request.scheduled_for
    }
  })

  return {
    store,
    scheduledDate,
    load: () => store.load(),
    create: (
      payload: { confirmation_text: string; reason_motif?: string | null }
    ) => store.create(payload),
    cancel: () => store.cancel(),
  }
}
