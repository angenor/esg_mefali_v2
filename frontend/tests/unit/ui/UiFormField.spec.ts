import { describe, it, expect } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { Form } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import UiFormField from '../../../app/components/ui/UiFormField.vue'
import UiInput from '../../../app/components/ui/UiInput.vue'

describe('UiFormField', () => {
  it('renders label and helper, propagates ARIA describedby', () => {
    const w = mount(UiFormField, {
      props: { label: 'Nom', helper: 'votre nom' },
      slots: {
        default: (slotProps: Record<string, unknown>) =>
          h('input', {
            ...slotProps,
            'data-testid': 'ctrl',
          }),
      },
    })
    expect(w.text()).toContain('Nom')
    expect(w.text()).toContain('votre nom')
    const ctrl = w.find('[data-testid="ctrl"]')
    expect(ctrl.attributes('aria-describedby')).toBeTruthy()
  })

  it('exposes vee-validate state when name + Form are present', async () => {
    const schema = toTypedSchema(z.object({ email: z.string().email('Email invalide') }))
    const Wrapper = defineComponent({
      components: { Form, UiFormField, UiInput },
      template: `
        <Form :validation-schema="schema" v-slot="{ handleSubmit }">
          <form @submit.prevent="handleSubmit(() => {})">
            <UiFormField name="email" label="Email">
              <template #default="bindings">
                <UiInput v-bind="bindings" />
              </template>
            </UiFormField>
            <button type="submit">go</button>
          </form>
        </Form>
      `,
      setup: () => ({ schema }),
    })
    const w = mount(Wrapper)
    await w.find('input').setValue('not-an-email')
    await w.find('input').trigger('blur')
    await w.find('button').trigger('click')
    await new Promise((r) => setTimeout(r, 10))
    expect(w.text().toLowerCase()).toContain('email invalide')
  })
})
