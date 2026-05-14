import asyncio
from collections import defaultdict
from typing import Any

class EventBus:
    """
    Lightweight async pub/sub bus.
    Agents publish sensor readings and decisions here.
    Orchestrator subscribes to all channels.
    """
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._history: dict[str, list] = defaultdict(list)

    def subscribe(self, channel: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers[channel].append(q)
        return q

    async def publish(self, channel: str, data: Any):
        self._history[channel].append(data)
        if len(self._history[channel]) > 100:
            self._history[channel] = self._history[channel][-100:]
        for q in self._subscribers[channel]:
            await q.put(data)

    def latest(self, channel: str, n: int = 1) -> list:
        return self._history[channel][-n:]

    def all_latest(self) -> dict:
        """Return the most recent reading from every sensor channel."""
        return {ch: items[-1] for ch, items in self._history.items() if items}

event_bus = EventBus()
