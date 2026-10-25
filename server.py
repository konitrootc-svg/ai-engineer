from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai

app = FastAPI()


class Msg(BaseModel):
    session: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


@app.post("/api/chat")
async def chat(m: Msg):
    try:
        return {"reply": await ai.ask("web:" + m.session, m.message)}
    except Exception:
        raise HTTPException(500, "AI request failed")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
