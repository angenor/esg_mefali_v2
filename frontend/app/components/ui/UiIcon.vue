<script setup lang="ts">
// Wrapper léger autour de FontAwesome.
// L'API reste `<UiIcon name="home" class="w-5 h-5" />` : on traduit le nom
// shell-nav vers l'icône FA correspondante (pack `solid`).
import { computed } from 'vue'

interface Props {
  name: string
}

const props = defineProps<Props>()

const NAME_MAP: Record<string, string> = {
  home: 'house',
  building: 'building',
  briefcase: 'briefcase',
  'check-circle': 'circle-check',
  'chart-bar': 'chart-column',
  cloud: 'cloud',
  banknotes: 'money-bill',
  'document-text': 'file-lines',
  'document-check': 'file-circle-check',
  'book-open': 'book-open',
  cog: 'gear',
  bell: 'bell',
  chat: 'comment',
  user: 'user',
  more: 'ellipsis',
}

const faName = computed(() => NAME_MAP[props.name] ?? props.name)
</script>

<template>
  <FontAwesomeIcon :icon="['fas', faName]" />
</template>
