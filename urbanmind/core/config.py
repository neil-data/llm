import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── NVIDIA NIM (Kimi K2.6) ──────────────────────────────────────────────
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "nvapi-YOUR_NEW_KEY_HERE")
    NVIDIA_INVOKE_URL: str = "https://integrate.api.nvidia.com/v1/chat/completions"

    # ── Groq (free fallback — no credits needed) ────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Active provider: "nvidia" or "groq" ────────────────────────────────
    PROVIDER: str = os.getenv("PROVIDER", "groq")

    # Model used (auto-set based on provider in llm.py)
    NVIDIA_MODEL: str = "moonshotai/kimi-k2.6"

    THINKING_MODE: bool = False
    ORCHESTRATOR_INTERVAL: int = 30
    SENSOR_INTERVAL: int = 10

    class Config:
        env_file = ".env"

settings = Settings()