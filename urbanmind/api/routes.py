import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from core.event_bus import event_bus
from core.llm import call_kimi
from ml.anomaly import feed_traffic, feed_energy, feed_environment

router = APIRouter()

# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "model": "moonshotai/kimi-k2.6", "project": "UrbanMind"}


# ─── Live sensor snapshots ────────────────────────────────────────────────────

@router.get("/sensors/latest")
async def sensors_latest():
    """Return the most recent reading from every sensor channel."""
    return event_bus.all_latest()

@router.get("/sensors/{domain}/history")
async def sensor_history(domain: str, n: int = 20):
    """Return the last N readings for a sensor domain."""
    channel = f"sensor.{domain}"
    history = event_bus.latest(channel, n)
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for domain: {domain}")
    return {"domain": domain, "readings": history}


# ─── Agent decisions ──────────────────────────────────────────────────────────

@router.get("/decisions/latest")
async def decisions_latest():
    """Return the most recent decision from each specialist agent."""
    channels = ["decision.traffic", "decision.energy", "decision.safety",
                "decision.environment", "decision.waste"]
    return {
        ch.replace("decision.", ""): event_bus.latest(ch, 1)
        for ch in channels
    }

@router.get("/orchestrator/latest")
async def orchestrator_latest():
    """Return the most recent city-wide orchestrator command."""
    history = event_bus.latest("orchestrator.command", 1)
    if not history:
        return {"message": "Orchestrator has not run yet. Try again in a few seconds."}
    return history[0]

@router.get("/orchestrator/history")
async def orchestrator_history(n: int = 10):
    return {"commands": event_bus.latest("orchestrator.command", n)}


# ─── ML anomaly endpoint ──────────────────────────────────────────────────────

@router.get("/anomaly/{domain}")
async def anomaly_check(domain: str):
    """Run anomaly detection on the latest reading for a domain."""
    channel = f"sensor.{domain}"
    readings = event_bus.latest(channel, 1)
    if not readings:
        raise HTTPException(status_code=404, detail=f"No data yet for: {domain}")
    reading = readings[0]
    if domain == "traffic":
        result = feed_traffic(reading)
    elif domain == "energy":
        result = feed_energy(reading)
    elif domain == "environment":
        result = feed_environment(reading)
    else:
        raise HTTPException(status_code=400, detail="Anomaly detection available for: traffic, energy, environment")
    return {"domain": domain, "reading": reading, "anomaly_result": result}


# ─── Direct Kimi K2.6 chat endpoint ──────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: str = "You are UrbanMind, a smart city AI assistant."
    show_thinking: bool = False        # set True to get reasoning traces too
    max_tokens: int = 1024

@router.post("/chat")
async def city_chat(req: ChatRequest):
    """
    Ask Kimi K2.6 anything about the city.
    - Automatically injects live sensor snapshot as context
    - Streams internally using your snippet pattern
    - Set show_thinking=true to receive Kimi's reasoning traces
    """
    sensor_snapshot = json.dumps(event_bus.all_latest(), indent=2)
    enriched_system = (
        req.context
        + f"\n\nCurrent city sensor snapshot:\n{sensor_snapshot}"
    )
    thinking, answer = await call_kimi(
        system_prompt=enriched_system,
        user_prompt=req.message,
        max_tokens=req.max_tokens,
        return_thinking=True,
    )
    response = {"reply": answer}
    if req.show_thinking:
        response["thinking"] = thinking
    return response


@router.websocket("/ws/chat-stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket streaming chat with Kimi K2.6.
    Send: {"message": "...", "show_thinking": true/false}
    Receive: {"type": "thinking"|"content"|"done", "text": "..."}
    Tokens stream in real-time exactly like your snippet.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            show_thinking = data.get("show_thinking", False)

            sensor_snapshot = json.dumps(event_bus.all_latest(), indent=2)
            system_prompt = (
                "You are UrbanMind, a smart city AI assistant.\n\n"
                f"Current city sensor snapshot:\n{sensor_snapshot}"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": message},
            ]
            from core.config import settings
            from core.llm import HEADERS, _build_payload
            import httpx

            payload = _build_payload(messages, max_tokens=2048)
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", settings.NVIDIA_INVOKE_URL,
                                          headers=HEADERS, json=payload) as resp:
                    async for raw_line in resp.aiter_lines():
                        if not raw_line or not raw_line.startswith("data: "):
                            continue
                        data_str = raw_line[6:]
                        if data_str.strip() == "[DONE]":
                            await websocket.send_json({"type": "done"})
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            if show_thinking and delta.get("reasoning_content"):
                                await websocket.send_json({
                                    "type": "thinking",
                                    "text": delta["reasoning_content"]
                                })
                            if delta.get("content"):
                                await websocket.send_json({
                                    "type": "content",
                                    "text": delta["content"]
                                })
                        except Exception:
                            continue
    except WebSocketDisconnect:
        pass


# ─── WebSocket — real-time city feed ─────────────────────────────────────────

@router.websocket("/ws/city-feed")
async def city_feed(websocket: WebSocket):
    """
    Stream live orchestrator commands to connected clients.
    Frontend dashboard connects here for real-time updates.
    """
    await websocket.accept()
    queue = event_bus.subscribe("orchestrator.command")
    try:
        while True:
            command = await queue.get()
            await websocket.send_json(command)
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/sensors")
async def sensor_feed(websocket: WebSocket):
    """Stream all sensor readings in real time."""
    await websocket.accept()
    queues = {
        ch: event_bus.subscribe(ch)
        for ch in ["sensor.traffic", "sensor.energy", "sensor.safety",
                   "sensor.environment", "sensor.waste"]
    }
    try:
        while True:
            for channel, q in queues.items():
                try:
                    data = q.get_nowait()
                    await websocket.send_json({"channel": channel, "data": data})
                except asyncio.QueueEmpty:
                    pass
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
