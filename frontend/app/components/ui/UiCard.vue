<script setup lang="ts">
interface Props {
  padded?: boolean
  elevation?: 'none' | 'sm' | 'md' | 'lg'
}

withDefaults(defineProps<Props>(), {
  padded: true,
  elevation: 'sm',
})
</script>

<template>
  <section class="ui-card" :data-padded="padded || undefined" :data-elevation="elevation">
    <header v-if="$slots.header" class="ui-card__header">
      <slot name="header" />
    </header>
    <div class="ui-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="ui-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.ui-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  color: var(--color-text);
  display: flex;
  flex-direction: column;
}
.ui-card[data-elevation='sm'] { box-shadow: var(--shadow-sm); }
.ui-card[data-elevation='md'] { box-shadow: var(--shadow-md); }
.ui-card[data-elevation='lg'] { box-shadow: var(--shadow-lg); }
.ui-card[data-padded] .ui-card__body { padding: var(--space-4); }
.ui-card__header,
.ui-card__footer {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  font-weight: var(--font-weight-medium);
}
.ui-card__footer {
  border-top: 1px solid var(--color-border);
  border-bottom: 0;
}
</style>
