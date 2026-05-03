/**
 * useChatToolBridge — wire entre les events DOM émis par useChatStream/store
 * (`chat:tool-invoke`, `chat:bottom-sheet:dismiss-for-freetext`) et :
 *   - useChatBottomSheet.open(...)  pour ouvrir le sheet F39
 *   - useChatStore.setForceFreetext(true)  pour la re-classification
 *
 * F41 / US2 (T026, T029).
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { FREETEXT_EVENT_NAME, useChatBottomSheet } from '~/composables/useChatBottomSheet'
import { useChatStore } from '~/stores/chat'

const TOOL_INVOKE_EVENT = 'chat:tool-invoke'

export function useChatToolBridge(): void {
  const sheet = useChatBottomSheet()
  const store = useChatStore()

  function onToolInvoke(e: Event): void {
    const detail = (e as CustomEvent).detail as unknown
    if (!detail) return
    void sheet.open(detail)
  }

  function onFreetext(): void {
    store.setForceFreetext(true)
  }

  onMounted(() => {
    if (typeof window === 'undefined') return
    window.addEventListener(TOOL_INVOKE_EVENT, onToolInvoke as EventListener)
    window.addEventListener(FREETEXT_EVENT_NAME, onFreetext)
  })

  onBeforeUnmount(() => {
    if (typeof window === 'undefined') return
    window.removeEventListener(TOOL_INVOKE_EVENT, onToolInvoke as EventListener)
    window.removeEventListener(FREETEXT_EVENT_NAME, onFreetext)
  })
}
