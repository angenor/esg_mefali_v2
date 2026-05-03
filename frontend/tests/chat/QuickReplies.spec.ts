/**
 * F41 / US8 (T052). QuickReplies : visibilité conditionnelle + emit pick.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import QuickReplies from '~/components/chat/QuickReplies.vue'

describe('QuickReplies', () => {
  it("ne rend rien quand suggestions est vide", () => {
    const wrapper = mount(QuickReplies, { props: { suggestions: [] } })
    expect(wrapper.find('.quick-replies').exists()).toBe(false)
  })

  it("rend jusqu'à 3 chips", () => {
    const wrapper = mount(QuickReplies, {
      props: { suggestions: ['a', 'b', 'c', 'd'] },
    })
    expect(wrapper.findAll('.quick-replies__chip')).toHaveLength(3)
  })

  it("émet `pick` avec le contenu du chip cliqué", async () => {
    const wrapper = mount(QuickReplies, {
      props: { suggestions: ['Continuer', 'Reformuler'] },
    })
    await wrapper.findAll('.quick-replies__chip')[0]!.trigger('click')
    expect(wrapper.emitted('pick')).toBeTruthy()
    expect(wrapper.emitted('pick')![0]).toEqual(['Continuer'])
  })
})
