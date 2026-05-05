<script setup lang="ts">
import { computed, ref } from 'vue'
import type { UiSize } from '~/types/ui'

interface Props {
  src?: string
  name?: string
  shape?: 'circle' | 'square'
  size?: UiSize
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  src: undefined,
  name: undefined,
  shape: 'circle',
  size: 'md',
  ariaLabel: undefined,
})

const failed = ref(false)

const initials = computed(() => {
  if (!props.name) return ''
  return props.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('')
})

const showImage = computed(() => !!props.src && !failed.value)
</script>

<template>
  <span
    class="ui-avatar"
    :data-shape="shape"
    :data-size="size"
    role="img"
    :aria-label="ariaLabel ?? name ?? 'Avatar'"
  >
    <img
      v-if="showImage"
      :src="src"
      :alt="''"
      class="ui-avatar__img"
      @error="failed = true"
    />
    <span v-else class="ui-avatar__initials" aria-hidden="true">{{ initials || '?' }}</span>
  </span>
</template>

<style scoped>
.ui-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-muted);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-weight: var(--font-weight-medium);
  overflow: hidden;
  user-select: none;
}
.ui-avatar[data-shape='circle'] { border-radius: 50%; }
.ui-avatar[data-shape='square'] { border-radius: var(--radius-sm); }
.ui-avatar[data-size='sm'] { width: 24px; height: 24px; font-size: var(--font-size-xs); }
.ui-avatar[data-size='md'] { width: 36px; height: 36px; font-size: var(--font-size-sm); }
.ui-avatar[data-size='lg'] { width: 48px; height: 48px; font-size: var(--font-size-base); }
.ui-avatar__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
