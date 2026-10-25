import os
import httpx

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.getenv("AI_MODEL", "gemini-flash-latest")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM = (
    "You are AI Engineer, a friendly assistant for programming, "
    "electronics and technical problems. Reply in the same language the "
    "user writes in (Khmer or English). Keep answers clear and practical, "
    "and put code in fenced code blocks."
)

_history: dict[str, list[dict]] = {}


async def ask(user_id: str, text: str) -> str:
    h = _history.setdefault(str(user_id), [])
    h.append({"role": "user", "parts": [{"text": text}]})
    del h[:-20]  # keep the last 20 messages
    while h and h[0]["role"] != "user":
        h.pop(0)

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": h,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(URL, headers={"X-goog-api-key": API_KEY}, json=payload)
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        answer = "".join(p.get("text", "") for p in parts) or "..."
    except Exception:
        h.pop()
        raise

    h.append({"role": "model", "parts": [{"text": answer}]})
    return answer


def reset(user_id: str) -> None:
    _history.pop(str(user_id), None)
