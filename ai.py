import os
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-6")

SYSTEM = (
    "You are AI Engineer, a friendly assistant for programming, "
    "electronics and technical problems. Reply in the same language the "
    "user writes in (Khmer or English). Keep answers clear and practical, "
    "and put code in fenced code blocks."
)

_history: dict[str, list[dict]] = {}


async def ask(user_id: str, text: str) -> str:
    h = _history.setdefault(str(user_id), [])
    h.append({"role": "user", "content": text})
    del h[:-20]  # keep the last 20 messages
    while h and h[0]["role"] != "user":
        h.pop(0)

    resp = await client.messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM, messages=h
    )
    answer = "".join(b.text for b in resp.content if b.type == "text")
    h.append({"role": "assistant", "content": answer})
    return answer


def reset(user_id: str) -> None:
    _history.pop(str(user_id), None)
