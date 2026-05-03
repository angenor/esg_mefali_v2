import { describe, it, expect } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useFieldId } from '../../../app/composables/useFieldId'

function mountIds(n: number) {
  const ids: string[] = []
  const Comp = defineComponent({
    setup() {
      ids.push(useFieldId('test'))
      return () => h('div')
    },
  })
  for (let i = 0; i < n; i++) mount(Comp)
  return ids
}

describe('useFieldId', () => {
  it('generates unique ids across instances', () => {
    const ids = mountIds(3)
    expect(new Set(ids).size).toBe(3)
    ids.forEach((id) => expect(id).toMatch(/^test-/))
  })

  it('returns the same id when called once per setup (stable per component)', () => {
    let captured: string | null = null
    const Comp = defineComponent({
      setup() {
        captured = useFieldId('stable')
        return () => h('div')
      },
    })
    const w = mount(Comp)
    const before = captured
    w.vm.$forceUpdate()
    expect(captured).toBe(before)
  })
})
