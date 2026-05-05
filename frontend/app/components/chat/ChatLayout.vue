<script setup lang="ts">
/**
 * ChatLayout — 2-cols (sidebar + main).
 *
 * F41 / US1 (T019). Sidebar masquée < 768 px (drawer toggle). Slots
 * `header`, `sidebar`, `history`, `input`.
 */
import { ref } from 'vue'

const sidebarOpen = ref(false)

function toggleSidebar(): void {
  sidebarOpen.value = !sidebarOpen.value
}

function closeSidebar(): void {
  sidebarOpen.value = false
}
</script>

<template>
  <div class="chat-layout">
    <aside class="chat-layout__sidebar" :class="{ 'chat-layout__sidebar--open': sidebarOpen }">
      <slot name="sidebar" />
    </aside>
    <div v-if="sidebarOpen" class="chat-layout__overlay" @click="closeSidebar" aria-hidden="true" />
    <main class="chat-layout__main">
      <header class="chat-layout__header">
        <button
          type="button"
          class="chat-layout__menu"
          aria-label="Ouvrir la liste des conversations"
          @click="toggleSidebar"
        >
          <span aria-hidden="true">☰</span>
        </button>
        <slot name="header" />
      </header>
      <section class="chat-layout__history">
        <slot name="history" />
      </section>
      <footer class="chat-layout__input">
        <slot name="input" />
      </footer>
    </main>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  width: 100%;
  background: rgb(var(--color-bg, 249 250 251));
}
.chat-layout__sidebar {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
  overflow-y: auto;
}
.chat-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-layout__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgb(var(--color-border, 229 231 235));
  background: rgb(var(--color-bg-elevated, 255 255 255));
}
.chat-layout__history {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chat-layout__menu {
  display: none;
  width: 2rem;
  height: 2rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 6px;
}
.chat-layout__overlay {
  position: fixed;
  inset: 0;
  background: rgb(0 0 0 / 0.4);
  z-index: 30;
  display: none;
}
@media (max-width: 767px) {
  .chat-layout__sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 40;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .chat-layout__sidebar--open { transform: translateX(0); }
  .chat-layout__menu { display: inline-flex; align-items: center; justify-content: center; }
  .chat-layout__overlay { display: block; }
}
@media (prefers-reduced-motion: reduce) {
  .chat-layout__sidebar { transition: none; }
}
</style>
