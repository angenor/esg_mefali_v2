"""F12 - Tests pub/sub events projets."""

from __future__ import annotations

import asyncio

import pytest

from app.projets import events


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_returns_zero():
    delivered = await events.publish("aaa", {"type": "test"})
    assert delivered == 0


@pytest.mark.asyncio
async def test_subscribe_receives_message():
    aid = "test-account-1"

    async def consume():
        gen = events.subscribe(aid)
        async for msg in gen:
            if msg.startswith(":"):
                continue
            return msg

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    n = await events.publish(aid, {"type": "projet.created", "projet_id": "x"})
    assert n == 1
    msg = await asyncio.wait_for(task, timeout=2.0)
    assert "projet.created" in msg


def test_publish_sync_no_loop_does_not_raise():
    # Outside an event loop should just be a no-op.
    events.publish_sync("aaa", {"type": "test"})


def test_subscriber_count_when_empty():
    assert events.subscriber_count("never-subscribed") == 0
