import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import UiSlider from '../../../app/components/ui/UiSlider.vue'

describe('UiSlider (single)', () => {
  it('rend role=slider + ARIA values', () => {
    const w = mount(UiSlider, { props: { modelValue: 50, min: 0, max: 100, ariaLabel: 'Volume' } })
    const thumb = w.find('[role="slider"]')
    expect(thumb.attributes('aria-valuemin')).toBe('0')
    expect(thumb.attributes('aria-valuemax')).toBe('100')
    expect(thumb.attributes('aria-valuenow')).toBe('50')
    expect(thumb.attributes('aria-label')).toBe('Volume')
  })

  it('ArrowRight incrémente de step', async () => {
    const w = mount(UiSlider, { props: { modelValue: 50, step: 5, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'ArrowRight' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([55])
  })

  it('ArrowLeft décrémente de step', async () => {
    const w = mount(UiSlider, { props: { modelValue: 50, step: 5, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'ArrowLeft' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([45])
  })

  it('Home va à min, End va à max', async () => {
    const w = mount(UiSlider, { props: { modelValue: 50, min: 0, max: 100, ariaLabel: 'X' } })
    const thumb = w.find('[role="slider"]')
    await thumb.trigger('keydown', { key: 'Home' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([0])
    await thumb.trigger('keydown', { key: 'End' })
    expect(w.emitted('update:modelValue')?.[1]).toEqual([100])
  })

  it('PageUp/PageDown utilisent un step plus grand', async () => {
    const w = mount(UiSlider, { props: { modelValue: 50, min: 0, max: 100, step: 1, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'PageUp' })
    const v = (w.emitted('update:modelValue')![0]![0]) as number
    expect(v).toBeGreaterThan(50)
  })

  it('clamp à max', async () => {
    const w = mount(UiSlider, { props: { modelValue: 100, max: 100, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'ArrowRight' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([100])
  })

  it('snap au step', async () => {
    const w = mount(UiSlider, { props: { modelValue: 47, step: 5, min: 0, max: 100, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'ArrowRight' })
    const v = w.emitted('update:modelValue')![0]![0] as number
    expect(v % 5).toBe(0)
  })

  it('disabled : pas d\'event', async () => {
    const w = mount(UiSlider, { props: { modelValue: 50, disabled: true, ariaLabel: 'X' } })
    await w.find('[role="slider"]').trigger('keydown', { key: 'ArrowRight' })
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })
})

describe('UiSlider (range)', () => {
  it('rend deux thumbs avec aria-label distincts', () => {
    const w = mount(UiSlider, {
      props: { range: true, modelValue: [20, 80] },
    })
    const thumbs = w.findAll('[role="slider"]')
    expect(thumbs).toHaveLength(2)
    expect(thumbs[0]!.attributes('aria-valuenow')).toBe('20')
    expect(thumbs[1]!.attributes('aria-valuenow')).toBe('80')
  })

  it('thumb low ne dépasse pas thumb high', async () => {
    const w = mount(UiSlider, { props: { range: true, modelValue: [50, 60], step: 20 } })
    const thumbs = w.findAll('[role="slider"]')
    await thumbs[0]!.trigger('keydown', { key: 'ArrowRight' }) // 50→70 mais bloqué par 60
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })

  it('thumb high ne descend pas sous thumb low', async () => {
    const w = mount(UiSlider, { props: { range: true, modelValue: [50, 60], step: 20 } })
    const thumbs = w.findAll('[role="slider"]')
    await thumbs[1]!.trigger('keydown', { key: 'ArrowLeft' }) // 60→40 bloqué par 50
    expect(w.emitted('update:modelValue')).toBeFalsy()
  })

  it('range : update émet [low, high]', async () => {
    const w = mount(UiSlider, { props: { range: true, modelValue: [20, 80], step: 5 } })
    const thumbs = w.findAll('[role="slider"]')
    await thumbs[0]!.trigger('keydown', { key: 'ArrowRight' })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([[25, 80]])
  })
})
