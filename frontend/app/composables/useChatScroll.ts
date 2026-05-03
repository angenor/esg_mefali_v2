/**
 * useChatScroll — scroll-pinning de l'historique chat.
 *
 * Référence : specs/041-chat-conversational-layer/research.md R7.
 * Auto-scroll vers le bas tant que l'utilisateur n'a pas scrollé manuellement
 * vers le haut ; reprend dès qu'il revient à moins de SCROLL_RESUME_THRESHOLD
 * pixels du bas. Respecte `prefers-reduced-motion`.
 */
import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

const SCROLL_RESUME_THRESHOLD = 64

export interface UseChatScroll {
  isPinned: Ref<boolean>
  scrollToBottom: (smooth?: boolean) => void
  observe: () => void
  unobserve: () => void
}

export function useChatScroll(
  containerRef: Ref<HTMLElement | null>,
  contentRef: Ref<HTMLElement | null>,
): UseChatScroll {
  const isPinned = ref(true)
  let resizeObserver: ResizeObserver | null = null

  function distanceFromBottom(el: HTMLElement): number {
    return el.scrollHeight - el.scrollTop - el.clientHeight
  }

  function prefersReducedMotion(): boolean {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function scrollToBottom(smooth = true): void {
    const el = containerRef.value
    if (!el) return
    const behavior: ScrollBehavior = smooth && !prefersReducedMotion() ? 'smooth' : 'auto'
    el.scrollTo({ top: el.scrollHeight, behavior })
  }

  function handleScroll(): void {
    const el = containerRef.value
    if (!el) return
    isPinned.value = distanceFromBottom(el) <= SCROLL_RESUME_THRESHOLD
  }

  function observe(): void {
    const container = containerRef.value
    const content = contentRef.value
    if (!container || !content) return
    container.addEventListener('scroll', handleScroll, { passive: true })
    resizeObserver = new ResizeObserver(() => {
      if (isPinned.value) scrollToBottom(false)
    })
    resizeObserver.observe(content)
  }

  function unobserve(): void {
    const container = containerRef.value
    if (container) container.removeEventListener('scroll', handleScroll)
    resizeObserver?.disconnect()
    resizeObserver = null
  }

  onMounted(() => {
    observe()
    scrollToBottom(false)
  })

  onBeforeUnmount(() => {
    unobserve()
  })

  return { isPinned, scrollToBottom, observe, unobserve }
}
