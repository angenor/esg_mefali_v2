"""F13 — Tests unitaires de l'EventBus (FR-005, FR-027 cross-tenant isolation)."""

from __future__ import annotations

import asyncio

import pytest

from app.chat import event_bus


@pytest.mark.asyncio
async def test_publish_then_subscribe_receives_event():
    aid = "00000000-0000-0000-0000-000000000aaa"
    received: list[str] = []

    async def consume():
        async for msg in event_bus.subscribe(aid):
            if msg.startswith(":"):
                continue
            received.append(msg)
            return

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    delivered = await event_bus.publish(aid, {"type": "entity_updated", "data": {"entity_type": "x", "entity_id": "1"}})
    assert delivered == 1
    await asyncio.wait_for(consumer, timeout=2.0)
    assert received and "entity_updated" in received[0]


@pytest.mark.asyncio
async def test_cross_tenant_isolation():
    aid_a = "00000000-0000-0000-0000-000000000aaa"
    aid_b = "00000000-0000-0000-0000-000000000bbb"
    received_b: list[str] = []

    async def consume():
        async for msg in event_bus.subscribe(aid_b):
            if msg.startswith(":"):
                continue
            received_b.append(msg)
            return

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await event_bus.publish(aid_a, {"type": "entity_updated", "data": {"x": 1}})
    # Wait briefly: B should NOT receive
    try:
        await asyncio.wait_for(consumer, timeout=0.5)
    except TimeoutError:
        pass
    consumer.cancel()
    assert received_b == []
