"""
Run in PowerShell:
    python test_api.py

Tests Groq (free) and NVIDIA (credits) and updates your .env automatically.
"""
import requests, json, re

def test_groq(key: str) -> bool:
    print("\n[Groq] Testing...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Reply with just: OK"}],
        "max_tokens": 10,
        "stream": True,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        print(f"[Groq] HTTP status: {resp.status_code}")
        if resp.status_code == 200:
            parts = []
            for line in resp.iter_lines():
                if line:
                    s = line.decode().lstrip("data: ").strip()
                    if s and s != "[DONE]":
                        try:
                            d = json.loads(s)["choices"][0].get("delta", {})
                            if d.get("content"):
                                parts.append(d["content"])
                        except: pass
            print(f"[Groq] Response: {''.join(parts)}")
            return True
        else:
            print(f"[Groq] Error: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[Groq] Failed: {e}")
        return False

def test_nvidia(key: str) -> bool:
    print("\n[NVIDIA] Testing Kimi K2.6...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": "moonshotai/kimi-k2.6",
        "messages": [{"role": "user", "content": "Reply with just: OK"}],
        "max_tokens": 20,
        "temperature": 1.0,
        "top_p": 1.0,
        "stream": True,
        "chat_template_kwargs": {"thinking": False},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        print(f"[NVIDIA] HTTP status: {resp.status_code}")
        if resp.status_code == 200:
            parts = []
            for line in resp.iter_lines():
                if line:
                    s = line.decode().lstrip("data: ").strip()
                    if s and s != "[DONE]":
                        try:
                            d = json.loads(s)["choices"][0].get("delta", {})
                            if d.get("content"):
                                parts.append(d["content"])
                        except: pass
            print(f"[NVIDIA] Response: {''.join(parts)}")
            return True
        elif resp.status_code == 429:
            print("[NVIDIA] 429 — credits exhausted. Get a new key at build.nvidia.com")
        elif resp.status_code == 403:
            print("[NVIDIA] 403 — key invalid or expired.")
        else:
            print(f"[NVIDIA] Error: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[NVIDIA] Failed: {e}")
        return False

def update_env(key: str, var: str):
    try:
        with open(".env", "r") as f:
            env = f.read()
        if var in env:
            new_env = re.sub(rf"{var}=.*", f"{var}={key}", env)
        else:
            new_env = env.rstrip() + f"\n{var}={key}\n"
        with open(".env", "w") as f:
            f.write(new_env)
        print(f"[OK] .env updated with {var}")
    except Exception as e:
        print(f"[WARN] Could not update .env: {e}")

def update_provider(provider: str):
    try:
        with open(".env", "r") as f:
            env = f.read()
        if "PROVIDER=" in env:
            new_env = re.sub(r"PROVIDER=.*", f"PROVIDER={provider}", env)
        else:
            new_env = env.rstrip() + f"\nPROVIDER={provider}\n"
        with open(".env", "w") as f:
            f.write(new_env)
        print(f"[OK] PROVIDER set to: {provider}")
    except Exception as e:
        print(f"[WARN] Could not update .env: {e}")

print("=" * 50)
print("  UrbanMind — API Connection Test")
print("=" * 50)
print("\nOption 1: Groq (FREE — get key at console.groq.com)")
print("Option 2: NVIDIA NIM (credits — get key at build.nvidia.com)")
print("\nWhich do you want to test?")
print("  1 = Groq (recommended — free, fast)")
print("  2 = NVIDIA Kimi K2.6")
print("  3 = Test both")
choice = input("\nEnter 1, 2, or 3: ").strip()

if choice in ("1", "3"):
    groq_key = input("\nPaste your Groq API key (gsk_...): ").strip()
    if test_groq(groq_key):
        update_env(groq_key, "GROQ_API_KEY")
        update_provider("groq")
        print("\n[READY] Groq is working! Run: python main.py")

if choice in ("2", "3"):
    nvidia_key = input("\nPaste your NVIDIA API key (nvapi-...): ").strip()
    if test_nvidia(nvidia_key):
        update_env(nvidia_key, "NVIDIA_API_KEY")
        update_provider("nvidia")
        print("\n[READY] NVIDIA Kimi K2.6 is working! Run: python main.py")

if choice not in ("1", "2", "3"):
    print("Invalid choice.")