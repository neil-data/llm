import asyncio
import json
from core.event_bus import event_bus
from core.llm import call_kimi_json
from core.config import settings
from agents.specialists import TrafficAgent, EnergyAgent, SafetyAgent, EnvironmentAgent, WasteAgent

ORCHESTRATOR_SYSTEM = """
You are UrbanMind, the master orchestrator AI for a smart city.
You receive simultaneous decisions from 5 specialist agents:
  - traffic, energy, safety, environment, waste

Your job:
1. Detect CONFLICTS (e.g. traffic wants a road open, safety wants it closed)
2. Detect CORRELATIONS (e.g. high AQI + high traffic = reduce vehicle flow)
3. Issue a unified city-wide action plan that resolves conflicts sensibly

Respond ONLY in this exact JSON format:
{
  "overall_city_status": "normal|elevated|critical",
  "conflicts_detected": ["conflict description" or empty list],
  "correlations_detected": ["correlation insight" or empty list],
  "unified_actions": ["action 1", "action 2", ...],
  "priority_domain": "traffic|energy|safety|environment|waste|none",
  "summary": "one sentence plain-English city status summary"
}
No markdown. Only JSON.
"""

class OrchestratorAgent:
    def __init__(self):
        self.decision_channels = [
            "decision.traffic",
            "decision.energy",
            "decision.safety",
            "decision.environment",
            "decision.waste",
        ]
        # Start all specialist agents
        self.specialists = [
            TrafficAgent(),
            EnergyAgent(),
            SafetyAgent(),
            EnvironmentAgent(),
            WasteAgent(),
        ]
        # In-memory log of orchestrator decisions (last 50)
        self.log: list[dict] = []

    async def run(self):
        # Launch all specialist agents concurrently
        specialist_tasks = [
            asyncio.create_task(agent.run()) for agent in self.specialists
        ]

        print("[Orchestrator] All specialist agents launched. Starting reasoning loop...")

        # Reasoning loop — every ORCHESTRATOR_INTERVAL seconds,
        # pull the latest decision from each specialist and cross-reason
        while True:
            await asyncio.sleep(settings.ORCHESTRATOR_INTERVAL)
            await self._reason_and_command()

    async def _reason_and_command(self):
        # Gather latest decision from each specialist channel
        latest = event_bus.all_latest()
        agent_decisions = {
            ch.replace("decision.", ""): latest[ch]
            for ch in self.decision_channels
            if ch in latest
        }

        if len(agent_decisions) < 2:
            print("[Orchestrator] Not enough agent decisions yet, waiting...")
            return

        user_prompt = (
            "Here are the latest decisions from all specialist agents:\n"
            + json.dumps(agent_decisions, indent=2)
        )

        try:
            result = await call_kimi_json(
                system_prompt=ORCHESTRATOR_SYSTEM,
                user_prompt=user_prompt,
                max_tokens=512,
            )
            import time
            result["timestamp"] = time.time()
            result["agent_decisions"] = agent_decisions

            # Store in log
            self.log.append(result)
            if len(self.log) > 50:
                self.log = self.log[-50:]

            # Publish city-wide command
            await event_bus.publish("orchestrator.command", result)

            print(f"[Orchestrator] City status: {result.get('overall_city_status')} | {result.get('summary')}")

        except Exception as e:
            print(f"[Orchestrator] Reasoning error: {e}")
