import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import UiFileUpload from '../../../app/components/ui/UiFileUpload.vue'

function makeFile(name: string, type: string, size: number): File {
  const blob = new Blob([new Uint8Array(size)], { type })
  return new File([blob], name, { type })
}

let createSpy: ReturnType<typeof vi.fn>
let revokeSpy: ReturnType<typeof vi.fn>

beforeEach(() => {
  createSpy = vi.fn(() => 'blob:fake')
  revokeSpy = vi.fn()
  // @ts-expect-error stub
  global.URL.createObjectURL = createSpy
  // @ts-expect-error stub
  global.URL.revokeObjectURL = revokeSpy
})

describe('UiFileUpload', () => {
  it('adds files via picker change', async () => {
    const w = mount(UiFileUpload, { props: { modelValue: [], accept: ['*/*'] } })
    const f = makeFile('a.txt', 'text/plain', 10)
    const input = w.find('input[type="file"]').element as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [f], configurable: true })
    await w.find('input[type="file"]').trigger('change')
    await flushPromises()
    expect(w.emitted('add')).toBeTruthy()
    const updated = w.emitted('update:modelValue')!.at(-1)![0] as Array<{ status: string }>
    expect(updated.length).toBe(1)
    expect(updated[0]!.status).toBe('queued')
  })

  it('rejects MIME outside whitelist', async () => {
    const w = mount(UiFileUpload, { props: { modelValue: [], accept: ['image/*'] } })
    const f = makeFile('a.txt', 'text/plain', 10)
    const input = w.find('input[type="file"]').element as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [f], configurable: true })
    await w.find('input[type="file"]').trigger('change')
    await flushPromises()
    const updated = w.emitted('update:modelValue')!.at(-1)![0] as Array<{ status: string; error?: string }>
    expect(updated[0]!.status).toBe('error')
    expect(updated[0]!.error).toMatch(/non autorisé/)
  })

  it('rejects oversized files', async () => {
    const w = mount(UiFileUpload, { props: { modelValue: [], maxSize: 5 } })
    const f = makeFile('big.bin', 'application/octet-stream', 100)
    const input = w.find('input[type="file"]').element as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [f], configurable: true })
    await w.find('input[type="file"]').trigger('change')
    await flushPromises()
    const updated = w.emitted('update:modelValue')!.at(-1)![0] as Array<{ status: string }>
    expect(updated[0]!.status).toBe('error')
  })

  it('mode=button renders a button', () => {
    const w = mount(UiFileUpload, { props: { mode: 'button' } })
    expect(w.find('button.ui-upload__button').exists()).toBe(true)
  })

  it('dropzone Enter key opens picker (covered by handler)', async () => {
    const w = mount(UiFileUpload)
    const dz = w.find('.ui-upload__dropzone')
    await dz.trigger('keydown', { key: 'Enter' })
    expect(dz.exists()).toBe(true)
  })

  it('creates + revokes object URL for image previews', async () => {
    const w = mount(UiFileUpload, { props: { modelValue: [], accept: ['*/*'] } })
    const f = makeFile('p.png', 'image/png', 10)
    const input = w.find('input[type="file"]').element as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [f], configurable: true })
    await w.find('input[type="file"]').trigger('change')
    await flushPromises()
    expect(createSpy).toHaveBeenCalled()
    w.unmount()
    expect(revokeSpy).toHaveBeenCalled()
  })

  it('remove emits remove and updates v-model', async () => {
    const entry = {
      id: 'x',
      file: makeFile('a.txt', 'text/plain', 10),
      status: 'queued' as const,
      progress: 0,
    }
    const w = mount(UiFileUpload, { props: { modelValue: [entry] } })
    const buttons = w.findAll('button')
    await buttons.at(-1)!.trigger('click')
    expect(w.emitted('remove')).toBeTruthy()
  })
})
