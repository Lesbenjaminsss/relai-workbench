import aiohttp

from config import OLLAMA_MODEL, OLLAMA_URL


async def health():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                data = await r.json()
                return {
                    "online": True,
                    "models": [m.get("name") for m in data.get("models", [])],
                }
    except Exception as exc:
        return {"online": False, "error": str(exc)}


async def chat(messages, model=None, temperature=0.4):
    """Ollama /api/chat ile sohbet tamamlama (stream yok)."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 120, "num_ctx": 1024},
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as r:
            if r.status != 200:
                text = await r.text()
                raise RuntimeError(f"Ollama hatası ({r.status}): {text[:300]}")
            data = await r.json()
            return data.get("message", {}).get("content", "")
