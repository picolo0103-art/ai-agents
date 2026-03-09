"""FastAPI application — SaaS multi-tenant with auth, profiles, demo mode."""
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import AutomationAgent, ContentAgent, SalesAgent, SupportAgent
from api.auth import get_current_user_ws
from api.routers.auth_router import router as auth_router
from api.routers.demo_router import router as demo_router
from api.routers.profile_router import router as profile_router
from config.settings import settings
from database.crud import get_profile
from database.database import get_db, init_db
from database.models import User

AGENT_TYPES = {
    "support":    SupportAgent,
    "sales":      SalesAgent,
    "automation": AutomationAgent,
    "content":    ContentAgent,
}

_sessions: Dict[str, object] = {}

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"🚀 {settings.app_name} v{settings.app_version} — SaaS mode")
    yield
    _sessions.clear()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(demo_router)


# ── Static pages ──────────────────────────────────────────────────────────────

def _html(name: str) -> HTMLResponse:
    with open(os.path.join(FRONTEND, name), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/",          response_class=HTMLResponse)
def root():            return _html("login.html")

@app.get("/login",     response_class=HTMLResponse)
def login_page():      return _html("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():  return _html("dashboard.html")

@app.get("/demo",      response_class=HTMLResponse)
def demo_page():       return _html("demo.html")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version, "mode": "saas"}


@app.get("/agents")
def list_agents():
    return {"agents": [
        {"type": "support",    "name": "Support Client",         "icon": "🎧",
         "description": "Répond aux questions clients, vérifie les commandes et gère les remboursements.",
         "capabilities": ["Recherche base de connaissances", "Statut commandes", "Création tickets", "Remboursements"]},
        {"type": "sales",      "name": "Sales & Prospection",    "icon": "📈",
         "description": "Génère des prospects qualifiés, rédige des emails et prépare des rendez-vous.",
         "capabilities": ["Analyse entreprise", "Qualification BANT", "Emails personnalisés", "Scripts commercial"]},
        {"type": "automation", "name": "Automatisation Interne", "icon": "⚙️",
         "description": "Analyse les données, génère des rapports et automatise les tâches répétitives.",
         "capabilities": ["Analyse de données", "Génération rapports", "Notifications équipes", "Automatisation"]},
        {"type": "content",    "name": "Marketing & Contenu",    "icon": "✍️",
         "description": "Crée du contenu marketing adapté au secteur et à la voix de l'entreprise.",
         "capabilities": ["Création de contenu", "Recherche marché", "Campagnes", "Idées créatives"]},
    ]}


# ── Authenticated WebSocket ───────────────────────────────────────────────────

@app.websocket("/ws/{agent_type}")
async def websocket_chat(
    websocket: WebSocket,
    agent_type: str,
    token: str = Query(default=""),
    db=Depends(get_db),
):
    if agent_type not in AGENT_TYPES:
        await websocket.close(code=4000); return

    # Auth via token query param
    user: User = await get_current_user_ws(token=token, db=db)
    if not user:
        await websocket.close(code=4001); return

    await websocket.accept()
    session_id = str(uuid.uuid4())

    # Load this tenant's company profile from DB
    profile = get_profile(db, user.tenant_id)
    client_context = profile.to_agent_context() if profile and profile.company_name else ""

    agent = AGENT_TYPES[agent_type](client_context=client_context)
    _sessions[session_id] = agent

    await websocket.send_json({
        "type": "session_created",
        "session_id": session_id,
        "agent_name": agent.name,
        "tenant_name": user.tenant.name,
        "has_profile": bool(client_context),
    })

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg = payload.get("message", "").strip()
            if not msg: continue

            if msg.lower() in ("/reset", "reset"):
                agent.reset()
                await websocket.send_json({"type": "reset"}); continue

            try:
                async for event in agent.chat_stream(msg):
                    await websocket.send_json(event)
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})

    except WebSocketDisconnect:
        _sessions.pop(session_id, None)
