import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import axe from 'axe-core'

import UiButton from '../../app/components/ui/UiButton.vue'
import UiInput from '../../app/components/ui/UiInput.vue'
import UiTextarea from '../../app/components/ui/UiTextarea.vue'
import UiNumber from '../../app/components/ui/UiNumber.vue'
import UiSelect from '../../app/components/ui/UiSelect.vue'
import UiRadioGroup from '../../app/components/ui/UiRadioGroup.vue'
import UiCheckboxGroup from '../../app/components/ui/UiCheckboxGroup.vue'
import UiSwitch from '../../app/components/ui/UiSwitch.vue'
import UiSlider from '../../app/components/ui/UiSlider.vue'
import UiCard from '../../app/components/ui/UiCard.vue'
import UiBadge from '../../app/components/ui/UiBadge.vue'
import UiTag from '../../app/components/ui/UiTag.vue'
import UiAvatar from '../../app/components/ui/UiAvatar.vue'
import UiEmptyState from '../../app/components/ui/UiEmptyState.vue'
import UiSkeleton from '../../app/components/ui/UiSkeleton.vue'
import UiSpinner from '../../app/components/ui/UiSpinner.vue'
import UiProgress from '../../app/components/ui/UiProgress.vue'
import UiFormField from '../../app/components/ui/UiFormField.vue'

const opts = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B' },
]

const Showcase = defineComponent({
  components: {
    UiButton, UiInput, UiTextarea, UiNumber, UiSelect, UiRadioGroup,
    UiCheckboxGroup, UiSwitch, UiSlider, UiCard, UiBadge, UiTag, UiAvatar,
    UiEmptyState, UiSkeleton, UiSpinner, UiProgress, UiFormField,
  },
  setup() {
    return { opts }
  },
  render() {
    return h('main', [
      h('h1', 'Showcase'),
      h(UiButton, { ariaLabel: 'Action' }, () => 'Bouton'),
      h(UiFormField, { label: 'Texte' }, {
        default: ({ id }: { id: string }) => h(UiInput, { id, modelValue: '' }),
      }),
      h(UiFormField, { label: 'Description' }, {
        default: ({ id }: { id: string }) => h(UiTextarea, { id, modelValue: '' }),
      }),
      h(UiFormField, { label: 'Montant' }, {
        default: ({ id }: { id: string }) =>
          h(UiNumber, { id, modelValue: null, mode: 'money', currency: 'XOF' }),
      }),
      h(UiFormField, { label: 'Choix' }, {
        default: ({ id }: { id: string }) =>
          h(UiSelect, { id, modelValue: null, options: opts }),
      }),
      h(UiFormField, { label: 'Régime' }, {
        default: ({ id }: { id: string }) =>
          h(UiRadioGroup, { id, modelValue: 'a', options: opts }),
      }),
      h(UiFormField, { label: 'Tags' }, {
        default: ({ id }: { id: string }) =>
          h(UiCheckboxGroup, { id, modelValue: [], options: opts }),
      }),
      h(UiSwitch, { ariaLabel: 'Notifications' }),
      h(UiSlider, { ariaLabel: 'Volume', modelValue: 50 }),
      h(UiCard, null, () => 'Carte'),
      h(UiBadge, null, () => 'Tag'),
      h(UiTag, { removable: true, ariaLabel: 'Filtre' }, () => 'Filtre'),
      h(UiAvatar, { name: 'Aïssatou Diallo' }),
      h(UiEmptyState, { title: 'Vide', description: 'Aucun élément', actionLabel: 'Créer' }),
      h(UiSkeleton, { lines: 3 }),
      h(UiSpinner),
      h(UiProgress, { modelValue: 40, ariaLabel: 'Progression' }),
    ])
  },
})

describe('Showcase a11y (axe-core)', () => {
  it('0 violation critique ou sérieuse', async () => {
    const w = mount(Showcase, { attachTo: document.body })
    // Laisser au DOM le temps de se stabiliser
    await new Promise((r) => setTimeout(r, 0))

    const results = await axe.run(w.element as HTMLElement, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    })

    const blockers = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    )

    if (blockers.length > 0) {
      // Aide au debug : afficher les violations
      // eslint-disable-next-line no-console
      console.error(
        blockers.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })),
      )
    }

    expect(blockers).toHaveLength(0)

    w.unmount()
  })
})
