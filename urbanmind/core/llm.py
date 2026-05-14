import json
import base64
import httpx
from pathlib import Path
from core.config import settings

_http = httpx.AsyncClient(timeout=120.0)

# ── Headers per provider ───────────────────────────────────────────────────────

def _headers(provider: str = None) -> dict:
    p = provider or settings.PROVIDER
    if p == "groq":
        return {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
    return {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

def _invoke_url(provider: str = None) -> str:
    p = provider or settings.PROVIDER
    if p == "groq":
        return f"{settings.GROQ_BASE_URL}/chat/completions"
    return settings.NVIDIA_INVOKE_URL

def _model(provider: str = None) -> str:
    p = provider or settings.PROVIDER
    return settings.GROQ_MODEL if p == "groq" else settings.NVIDIA_MODEL


# ── Image helpers ──────────────────────────────────────────────────────────────

def read_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def image_content(path_or_url: str) -> dict:
    if path_or_url.startswith("http"):
        return {"type": "image_url", "image_url": {"url": path_or_url}}
    ext = Path(path_or_url).suffix.lstrip(".").lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{read_b64(path_or_url)}"}}


# ── Payload builder ────────────────────────────────────────────────────────────

def _build_payload(messages: list, max_tokens: int, provider: str = None) -> dict:
    p = provider or settings.PROVIDER
    payload = {
        "model": _model(p),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7 if p == "groq" else 1.0,
        "top_p": 1.0,
        "stream": True,
    }
    if p == "nvidia":
        payload["chat_template_kwargs"] = {"thinking": settings.THINKING_MODE}
    return payload


# ── Streaming SSE parser ───────────────────────────────────────────────────────

async def _stream_response(payload: dict, provider: str = None) -> tuple[str, str]:
    """Returns (thinking_text, answer_text). Works for both Groq and NVIDIA."""
    p = provider or settings.PROVIDER
    thinking_parts, content_parts = [], []

    async with _http.stream("POST", _invoke_url(p),
                             headers=_headers(p), json=payload) as resp:
        resp.raise_for_status()
        async for raw_line in resp.aiter_lines():
            if not raw_line:
                continue
            # Groq sends "data: {...}" lines; NVIDIA same format
            line = raw_line.lstrip("data: ").strip() if raw_line.startswith("data:") else raw_line
            if not line or line == "[DONE]":
                break
            try:
                chunk = json.loads(line)
                delta = chunk["choices"][0].get("delta", {})
                if delta.get("reasoning_content"):
                    thinking_parts.append(delta["reasoning_content"])
                if delta.get("content"):
                    content_parts.append(delta["content"])
            except Exception:
                continue

    return "".join(thinking_parts), "".join(content_parts)


# ── Public API ────────────────────────────────────────────────────────────────

async def call_kimi(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    images: list = None,
    return_thinking: bool = False,
    provider: str = None,
):
    p = provider or settings.PROVIDER
    if images and p == "groq":
        # Groq vision only on specific models — use text only
        user_content = user_prompt
    elif images:
        user_content = [{"type": "text", "text": user_prompt}]
        for img in images:
            user_content.append(image_content(img))
    else:
        user_content = user_prompt

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ]
    payload = _build_payload(messages, max_tokens, p)
    thinking, answer = await _stream_response(payload, p)
    return (thinking, answer) if return_thinking else answer


async def call_kimi_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    images: list = None,
    provider: str = None,
) -> dict:
    json_system = system_prompt + "\n\nRespond ONLY with valid JSON. No markdown, no preamble."
    answer = await call_kimi(json_system, user_prompt, max_tokens, images=images, provider=provider)
    clean = answer.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)


# ── Sync test helper ───────────────────────────────────────────────────────────

def ask_sync(prompt: str, max_tokens: int = 512) -> str:
    import requests as req_lib
    p = settings.PROVIDER
    payload = {
        "model": _model(p),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7 if p == "groq" else 1.0,
        "top_p": 1.0,
        "stream": True,
    }
    if p == "nvidia":
        payload["chat_template_kwargs"] = {"thinking": False}

    resp = req_lib.post(_invoke_url(p), headers=_headers(p), json=payload, stream=True, timeout=60)
    parts = []
    for line in resp.iter_lines():
        if line:
            decoded = line.decode("utf-8")
            s = decoded.lstrip("data: ").strip() if decoded.startswith("data:") else decoded
            if s and s != "[DONE]":
                try:
                    delta = json.loads(s)["choices"][0].get("delta", {})
                    if delta.get("content"):
                        parts.append(delta["content"])
                except Exception:
                    pass
    return "".join(parts)