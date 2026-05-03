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
    include: ['tests/**/*.test.ts', 'tests/**/*.spec.ts'],
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
