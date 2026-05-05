import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '~': fileURLToPath(new URL('./app', import.meta.url)),
      '@': fileURLToPath(new URL('./app', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    include: [
      'tests/**/*.test.ts',
      'tests/**/*.spec.ts',
      'app/**/__tests__/**/*.test.ts',
      'app/**/__tests__/**/*.spec.ts',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary'],
      include: [
        'app/components/ui/**',
        // Composables consommés par les primitives F37 uniquement.
        // Les composables d'autres features (useAuth, useHealth, useCsrf, useSourceFetch, useVersionBadge)
        // ont leur propre coverage gate ailleurs.
        'app/composables/useFieldId.ts',
        'app/composables/useFloating.ts',
        'app/composables/useFocusTrap.ts',
        'app/composables/useMoneyFormat.ts',
        'app/composables/useReducedMotion.ts',
        'app/composables/useToast.ts',
        'app/utils/sanitize.ts',
        // F39 — bottom sheet engine
        'app/components/chat/bottom-sheet/**',
        'app/composables/useBottomSheetAnimation.ts',
        'app/composables/useBottomSheetSubmit.ts',
        'app/composables/useChatBottomSheet.ts',
        'app/stores/chatBottomSheet.ts',
        'app/utils/moneyPeg.ts',
        // F40 — viz library
        'app/components/viz/**',
        'app/composables/useChartTheme.ts',
        'app/stores/sources.ts',
        'app/utils/moneyFormat.ts',
        'app/utils/mermaidSanitize.ts',
        // F41 — chat conversational layer
        'app/components/chat/MessageMarkdown.vue',
        'app/components/chat/MessageBubbleUser.vue',
        'app/components/chat/MessageBubbleAssistant.vue',
        'app/components/chat/MessageError.vue',
        'app/components/chat/MessageInput.vue',
        'app/components/chat/ChatHistory.vue',
        'app/components/chat/ChatLayout.vue',
        'app/components/chat/ChatHeader.vue',
        'app/components/chat/ThreadList.vue',
        'app/components/chat/QuickReplies.vue',
        'app/components/chat/MemoryBadge.vue',
        'app/components/chat/TypingIndicator.vue',
        'app/composables/useMarkdownStream.ts',
        'app/composables/useChatEventBus.ts',
        'app/composables/useChatStream.ts',
        'app/composables/useChatScroll.ts',
        'app/composables/useChatOnboarding.ts',
        'app/stores/chat.ts',
        'app/types/chat.ts',
      ],
      thresholds: {
        lines: 80,
        branches: 80,
        functions: 80,
        statements: 80,
      },
    },
  },
})
