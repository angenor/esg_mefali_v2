<script setup lang="ts">
/**
 * TypingIndicator — 3 dots animés (gsap), neutralisé si prefers-reduced-motion.
 * F41 / US1 (T016).
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import gsap from 'gsap'
import { useReducedMotion } from '~/composables/useReducedMotion'

const dot1 = ref<HTMLElement | null>(null)
const dot2 = ref<HTMLElement | null>(null)
const dot3 = ref<HTMLElement | null>(null)
const reducedMotion = useReducedMotion()
let tl: gsap.core.Timeline | null = null

onMounted(() => {
  if (reducedMotion.value) return
  const targets = [dot1.value, dot2.value, dot3.value].filter(Boolean) as HTMLElement[]
  if (targets.length === 0) return
  tl = gsap.timeline({ repeat: -1 })
  tl.to(targets, {
    y: -3,
    duration: 0.32,
    ease: 'sine.inOut',
    stagger: 0.12,
    yoyo: true,
    repeat: 1,
  })
})

onBeforeUnmount(() => {
  tl?.kill()
})
</script>

<template>
  <div class="chat-typing" role="status" aria-label="Assistant en train d'écrire">
    <span ref="dot1" class="chat-typing__dot" />
    <span ref="dot2" class="chat-typing__dot" />
    <span ref="dot3" class="chat-typing__dot" />
  </div>
</template>

<style scoped>
.chat-typing {
  display: inline-flex;
  gap: 0.3rem;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: rgb(var(--color-bg-muted, 243 244 246));
  border-radius: 16px;
  width: fit-content;
}
.chat-typing__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--color-fg-muted, 107 114 128));
  display: inline-block;
}
@media (prefers-reduced-motion: reduce) {
  .chat-typing__dot:nth-child(2) { opacity: 0.7; }
  .chat-typing__dot:nth-child(3) { opacity: 0.4; }
}
</style>
