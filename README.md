# UrbanMind — Smart City Multi-Agent AI Backend

Autonomous smart city command system powered by **Kimi K2.6** via **NVIDIA NIM**.  
5 specialist AI agents (traffic, energy, safety, environment, waste) feed into a master  
orchestrator that cross-reasons and issues unified city-wide commands.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python FastAPI + async |
| LLM | Kimi K2.6 (`moonshotai/kimi-k2.6`) via NVIDIA NIM |
| ML | scikit-learn IsolationForest (online anomaly detection) |
| Messaging | In-memory async event bus (Redis-ready) |
| Real-time | WebSocket live feeds |

---

## Setup

```bash
# 1. Clone / enter project
cd urbanmind

# 2. Create virtual env
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your NVIDIA NIM key
cp .env.example .env
# Edit .env and set: NVIDIA_API_KEY=nvapi-YOUR_KEY_HERE
# Get a free key at: https://build.nvidia.com

# 5. Run
python main.py
```

Server starts at: http://localhost:8000

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/sensors/latest` | All latest sensor readings |
| GET | `/sensors/{domain}/history?n=20` | Last N readings for a domain |
| GET | `/decisions/latest` | Latest decision from each agent |
| GET | `/orchestrator/latest` | Latest city-wide command |
| GET | `/orchestrator/history?n=10` | Last N orchestrator commands |
| GET | `/anomaly/{domain}` | ML anomaly check (traffic/energy/environment) |
| POST | `/chat` | Ask Kimi K2.6 about the city (injects live sensor state) |
| WS | `/ws/city-feed` | WebSocket — live orchestrator commands |
| WS | `/ws/sensors` | WebSocket — live sensor readings |

Docs: http://localhost:8000/docs

---

## Chat Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Is the city under stress right now? What should be done?"}'
```

Kimi K2.6 automatically receives the live sensor snapshot and reasons over it.

---

## Architecture

```
IoT Sensors (simulated)
    │
    ▼
FastAPI Event Bus
    │
    ├──▶ TrafficAgent ──▶ Kimi K2.6 ──▶ decision.traffic
    ├──▶ EnergyAgent  ──▶ Kimi K2.6 ──▶ decision.energy
    ├──▶ SafetyAgent  ──▶ Kimi K2.6 ──▶ decision.safety
    ├──▶ EnvAgent     ──▶ Kimi K2.6 ──▶ decision.environment
    └──▶ WasteAgent   ──▶ Kimi K2.6 ──▶ decision.waste
                                              │
                                              ▼
                                    OrchestratorAgent
                                    (Kimi K2.6 cross-reasoning)
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                     ▼
                            REST endpoints         WebSocket feed
                            /orchestrator/latest   /ws/city-feed

ML Layer (scikit-learn IsolationForest)
    └── Runs in parallel on traffic, energy, environment streams
        Flags anomalies → available at /anomaly/{domain}
```

---

## Domains

- **traffic** — vehicle density, speed, incidents → signal timing, rerouting
- **energy** — grid load, voltage, kWh → load shedding, renewable boost
- **safety** — crowd density, CCTV anomalies → patrol dispatch, alerts
- **environment** — AQI, noise, temperature → public advisories, mitigations
- **waste** — bin fill levels → pickup scheduling, route optimization

---

## Hackathon Tips

- The `/chat` endpoint is your demo killer feature — type any city question and get a live AI answer with real sensor context.
- WebSocket `/ws/city-feed` powers your frontend dashboard with zero polling.
- `/anomaly/energy` shows ML working alongside LLM — good for judges.
- Tune `ORCHESTRATOR_INTERVAL` (default 10s) lower for faster demo updates.
