/**
 * F41 / US3 (T034). useChatEventBus : propagation, no-loop guard.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useChatEventBus, __resetChatEventBus } from '~/composables/useChatEventBus'
import type { EventBusEvent } from '~/types/chat'

function makeEvent(source: EventBusEvent['source']): EventBusEvent {
  return {
    eventType: 'entity_updated',
    entityType: 'entreprise',
    entityId: 'e1',
    source,
    ts: '2026-05-03T12:00:00Z',
  }
}

describe('useChatEventBus', () => {
  beforeEach(() => {
    __resetChatEventBus()
  })

  it('emit est reçu par les listeners passifs', () => {
    const bus = useChatEventBus()
    const seen: EventBusEvent[] = []
    bus.on('entity_updated', (e) => seen.push(e))
    bus.emit('entity_updated', makeEvent('manual'))
    expect(seen).toHaveLength(1)
  })

  it("ignoreLlmSource bloque les events source: 'llm'", () => {
    const bus = useChatEventBus()
    const seen: EventBusEvent[] = []
    bus.on('entity_updated', (e) => seen.push(e), { ignoreLlmSource: true })
    bus.emit('entity_updated', makeEvent('llm'))
    bus.emit('entity_updated', makeEvent('manual'))
    expect(seen).toHaveLength(1)
    expect(seen[0]?.source).toBe('manual')
  })

  it("les listeners sans option reçoivent les events 'llm'", () => {
    const bus = useChatEventBus()
    const seen: EventBusEvent[] = []
    bus.on('entity_updated', (e) => seen.push(e))
    bus.emit('entity_updated', makeEvent('llm'))
    expect(seen).toHaveLength(1)
  })

  it('off désinscrit le listener', () => {
    const bus = useChatEventBus()
    const seen: EventBusEvent[] = []
    const offFn = bus.on('entity_updated', (e) => seen.push(e))
    offFn()
    bus.emit('entity_updated', makeEvent('manual'))
    expect(seen).toHaveLength(0)
  })
})
