<script setup lang="ts">
// F38 T062 — TheRouteProgress (barre de progression Nuxt)
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useReducedMotion } from '~/composables/useReducedMotion'

const reduced = useReducedMotion()
const visible = ref(false)
const barRef = ref<HTMLElement | null>(null)

let cleanupStart: (() => void) | null = null
let cleanupFinish: (() => void) | null = null

async function animateTo(percent: number, duration: number): Promise<void> {
  if (!barRef.value) return
  if (reduced.value) {
    barRef.value.style.transform = `scaleX(${percent / 100})`
    return
  }
  try {
    const { gsap } = await import('gsap')
    gsap.to(barRef.value, {
      scaleX: percent / 100,
      duration,
      ease: 'power1.out',
    })
  } catch {
    barRef.value.style.transform = `scaleX(${percent / 100})`
  }
}

async function fadeOut(): Promise<void> {
  if (!barRef.value) return
  if (reduced.value) {
    barRef.value.style.opacity = '0'
    return
  }
  try {
    const { gsap } = await import('gsap')
    gsap.to(barRef.value, { opacity: 0, duration: 0.2 })
  } catch {
    barRef.value.style.opacity = '0'
  }
}

function onStart(): void {
  visible.value = true
  if (barRef.value) {
    barRef.value.style.transform = 'scaleX(0)'
    barRef.value.style.opacity = '1'
  }
  void animateTo(80, 0.4)
}

function onFinish(): void {
  void animateTo(100, 0.1)
  setTimeout(() => {
    void fadeOut()
    setTimeout(() => {
      visible.value = false
    }, 220)
  }, 110)
}

onMounted(() => {
  const nuxt = useNuxtApp()
  cleanupStart = nuxt.hook('page:start', onStart)
  cleanupFinish = nuxt.hook('page:finish', onFinish)
})

onBeforeUnmount(() => {
  cleanupStart?.()
  cleanupFinish?.()
})
</script>

<template>
  <div
    v-if="visible"
    class="pointer-events-none fixed inset-x-0 top-0 z-[9999] h-0.5"
    aria-hidden="true"
    data-testid="route-progress"
  >
    <div
      ref="barRef"
      class="h-full origin-left bg-brand-500"
      style="transform: scaleX(0); opacity: 1;"
    />
  </div>
</template>
