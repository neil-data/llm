import asyncio
from abc import ABC, abstractmethod
from core.event_bus import event_bus
from core.llm import call_kimi_json

class BaseAgent(ABC):
    """
    Every specialist agent:
      - subscribes to its sensor channel
      - receives a reading
      - calls Kimi K2.6 for reasoning
      - publishes a structured decision back to the bus
    """
    name: str = "base"
    sensor_channel: str = ""
    decision_channel: str = ""

    SYSTEM_PROMPT: str = ""

    async def run(self):
        queue = event_bus.subscribe(self.sensor_channel)
        print(f"[{self.name}] Agent started, listening on {self.sensor_channel}")
        while True:
            reading = await queue.get()
            decision = await self.reason(reading)
            decision["agent"] = self.name
            decision["sensor_reading"] = reading
            await event_bus.publish(self.decision_channel, decision)
            print(f"[{self.name}] Decision: {decision.get('action', 'none')}")

    async def reason(self, reading: dict) -> dict:
        return await call_kimi_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=f"Current sensor reading:\n{reading}",
            max_tokens=256,
        )
