import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
WEBHOOK_PATH = "/telegram"


async def set_webhook() -> dict:
    if not (BOT_TOKEN and BASE_URL):
        return {"error": "TELEGRAM_BOT_TOKEN or RENDER_EXTERNAL_URL missing"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{TG_API}/setWebhook", json={"url": BASE_URL + WEBHOOK_PATH})
    log.info("setWebhook: %s %s", r.status_code, r.text[:200])
    return {"status": r.status_code, "body": r.json()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await set_webhook()
    except Exception:
        log.exception("setWebhook failed")
    yield


app = FastAPI(lifespan=lifespan)


class Msg(BaseModel):
    session: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


@app.post("/api/chat")
async def chat(m: Msg):
    try:
        return {"reply": await ai.ask("web:" + m.session, m.message)}
    except Exception:
        log.exception("web chat failed")
        raise HTTPException(500, "AI request failed")


async def tg_send(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=30) as c:
        for i in range(0, len(text), 4000):
            r = await c.post(
                f"{TG_API}/sendMessage",
                json={"chat_id": chat_id, "text": text[i : i + 4000]},
            )
            if r.status_code != 200:
                log.error("sendMessage %s: %s", r.status_code, r.text[:300])


async def handle_update(update: dict) -> None:
    msg = update.get("message") or {}
    text = msg.get("text")
    chat_id = (msg.get("chat") or {}).get("id")
    if not text or not chat_id:
        return

    if text.startswith("/start"):
        await tg_send(
            chat_id,
            "សួស្តី! ខ្ញុំជា AI Engineer។ សួរខ្ញុំអំពី programming, electronics "
            "ឬបញ្ហាបច្ចេកទេសបាន។\nប្រើ /reset ដើម្បីចាប់ផ្ដើមសន្ទនាថ្មី។",
        )
        return
    if text.startswith("/reset"):
        ai.reset("tg:" + str(chat_id))
        await tg_send(chat_id, "បានចាប់ផ្ដើមសន្ទនាថ្មី។")
        return

    try:
        reply = await ai.ask("tg:" + str(chat_id), text)
    except Exception:
        log.exception("telegram ask failed")
        reply = "មានបញ្ហា សូមព្យាយាមម្តងទៀត។"
    await tg_send(chat_id, reply)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, background: BackgroundTasks):
    update = await request.json()
    background.add_task(handle_update, update)
    return {"ok": True}


@app.get("/debug")
async def debug():
    """Open /debug in a browser to see what is wrong. Shows no secrets."""
    out = {
        "telegram_token_set": bool(BOT_TOKEN),
        "render_external_url": BASE_URL or None,
        "gemini_key_set": bool(ai.API_KEY),
        "gemini_key_starts_with": ai.API_KEY[:4] if ai.API_KEY else None,
        "gemini_model": ai.MODEL,
    }
    try:
        out["set_webhook"] = await set_webhook()
    except Exception as e:
        out["set_webhook"] = {"error": repr(e)}

    if BOT_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{TG_API}/getWebhookInfo")
            info = r.json().get("result", {})
            out["webhook_info"] = {
                "url": info.get("url"),
                "pending_update_count": info.get("pending_update_count"),
                "last_error_message": info.get("last_error_message"),
            }
        except Exception as e:
            out["webhook_info"] = {"error": repr(e)}

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                ai.URL,
                headers={"X-goog-api-key": ai.API_KEY},
                json={"contents": [{"parts": [{"text": "Say hi"}]}]},
            )
        out["gemini_test"] = {"status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        out["gemini_test"] = {"error": repr(e)}
    return out


@app.get("/")
async def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
