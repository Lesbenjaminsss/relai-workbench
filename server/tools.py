import ast
import json
import math
import operator
import re

import aiohttp
from bs4 import BeautifulSoup

TOOL_DESCRIPTIONS = """Kullandığın tek bir aracı şu JSON formatında çağırabilirsin:
{"tool": "calculator", "args": {"expression": "2+2"}}
{"tool": "weather", "args": {"city": "Ankara"}}
{"tool": "web_search", "args": {"query": "...", "limit": 5}}
Eğer araç gerekmiyorsa doğrudan cevabını yaz, JSON kullanma."""

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod: operator.mod,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Desteklenmeyen ifade")


async def calculator(expression: str):
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return f"Sonuç: {result}"
    except Exception as exc:
        return f"Hesaplama hatası: {exc}"


async def weather(city: str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "tr", "format": "json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                data = await r.json()
            loc = (data.get("results") or [None])[0]
            if not loc:
                return f"'{city}' şehri bulunamadı."
            async with s.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": loc["latitude"],
                    "longitude": loc["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r2:
                w = await r2.json()
            cur = w.get("current", {})
            daily = w.get("daily", {})
            return (
                f"{loc['name']} hava durumu: {cur.get('temperature_2m')}°C, "
                f"nem %{cur.get('relative_humidity_2m')}, rüzgar {cur.get('wind_speed_10m')} km/s. "
                f"Bugün min {daily.get('temperature_2m_min', [None])[0]}°C, "
                f"maks {daily.get('temperature_2m_max', [None])[0]}°C."
            )
    except Exception as exc:
        return f"Hava durumu alınamadı: {exc}"


async def web_search(query: str, limit: int = 5):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                html = await r.text()
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for item in soup.select(".result")[:limit]:
            a = item.select_one(".result__a")
            sn = item.select_one(".result__snippet")
            if a:
                results.append(f"- {a.get_text(' ', strip=True)}: {sn.get_text(' ', strip=True) if sn else ''}")
        if not results:
            return "Arama sonucu bulunamadı."
        return "Web arama sonuçları:\n" + "\n".join(results)
    except Exception as exc:
        return f"Arama hatası: {exc}"


TOOLS = {
    "calculator": lambda args: calculator(args.get("expression", "")),
    "weather": lambda args: weather(args.get("city", "")),
    "web_search": lambda args: web_search(args.get("query", ""), int(args.get("limit", 5))),
}


def parse_tool_call(text):
    """Model cevabindan arac cagrısını çıkarır; yoksa None. Ic ice JSON'u destekler."""
    candidates = []
    start = None
    depth = 0
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : i + 1])
                start = None
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and obj.get("tool") in TOOLS:
                return obj
        except Exception:
            continue
    return None


async def run_tool(call):
    name = call["tool"]
    args = call.get("args", {})
    if not isinstance(args, dict):
        args = {}
    fn = TOOLS[name]
    result = fn(args)
    if hasattr(result, "__await__"):
        result = await result
    return name, str(result)
