"""
Authoritative Realtime Event Bus for NIRA Live Core.
Amazon Developer Hackathon 2026.

Provides asynchronous pub/sub streaming to FastAPI SSE (Server-Sent Events)
and WebSockets so the Live Dashboard receives instantaneous authoritative state changes.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Set, AsyncGenerator
from datetime import datetime, timezone

logger = logging.getLogger("NIRA.LiveCore.RealtimeBus")


class RealtimeBus:
    """
    High-performance in-memory async pub/sub bus.
    Broadcasts authoritative core state changes, incident transitions, and telemetry.
    """

    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Registers a new client subscriber queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        async with self._lock:
            self._subscribers.add(q)
        logger.debug(f"[RealtimeBus] Client subscribed (Total: {len(self._subscribers)})")
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        """Unregisters an active subscriber queue."""
        async with self._lock:
            self._subscribers.discard(q)
        logger.debug(f"[RealtimeBus] Client unsubscribed (Remaining: {len(self._subscribers)})")

    async def publish(self, topic: str, data: Dict[str, Any]):
        """Broadcasts payload to all active client queues asynchronously."""
        message = {
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

        async with self._lock:
            subscribers_snapshot = list(self._subscribers)

        for q in subscribers_snapshot:
            try:
                if q.full():
                    # Evict oldest event to prevent slow subscriber head-of-line blocking
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(message)
            except Exception as e:
                logger.debug(f"[RealtimeBus] Publish error for subscriber: {e}")

    def publish_sync(self, topic: str, data: Dict[str, Any]):
        """Synchronous wrapper to publish from non-async contexts or background threads."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(topic, data))
            else:
                loop.run_until_complete(self.publish(topic, data))
        except RuntimeError:
            # If no running event loop in thread, log and pass
            pass

    async def sse_event_stream(self) -> AsyncGenerator[str, None]:
        """Async generator yielding Server-Sent Events formatted strings."""
        q = await self.subscribe()
        try:
            # Yield initial connection confirmation
            init_msg = json.dumps({"topic": "connection_established", "status": "LIVE_CORE_ACTIVE"})
            yield f"event: connected\ndata: {init_msg}\n\n"

            while True:
                msg = await q.get()
                topic = msg.get("topic", "message")
                payload_str = json.dumps(msg)
                yield f"event: {topic}\ndata: {payload_str}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await self.unsubscribe(q)


# Singleton Realtime Bus instance
_global_bus = RealtimeBus()


def get_realtime_bus() -> RealtimeBus:
    global _global_bus
    return _global_bus
