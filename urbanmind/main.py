import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from core.event_bus import event_bus
from core.sensor_simulator import start_simulator
from agents.orchestrator import OrchestratorAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start sensor simulator and orchestrator on boot
    simulator_task = asyncio.create_task(start_simulator())
    orchestrator_task = asyncio.create_task(OrchestratorAgent().run())
    yield
    simulator_task.cancel()
    orchestrator_task.cancel()

app = FastAPI(
    title="UrbanMind — Smart City AI Backend",
    description="Multi-agent autonomous system powered by Kimi K2.5 via NVIDIA NIM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
