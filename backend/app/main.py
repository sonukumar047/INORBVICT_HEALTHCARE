from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.routers import flow_chat, rag_chat
import os, json
from typing import Any

class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"
    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

app = FastAPI(title="AI Chatbot API", version="1.0.0", default_response_class=UTF8JSONResponse)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

os.makedirs("data/documents", exist_ok=True)
os.makedirs("vector_db", exist_ok=True)

app.include_router(flow_chat.router)
app.include_router(rag_chat.router)

if os.path.exists("../frontend/static"):
    app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404, media_type="text/html; charset=utf-8")

@app.get("/health")
async def health():
    return {"status": "healthy", "charset": "utf-8", "version": "1.0.0"}
