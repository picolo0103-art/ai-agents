"""FastAPI application — SaaS multi-tenant with auth, profiles, demo mode."""
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agentai")

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.limiter import limiter

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents import AutomationAgent, ContentAgent, SalesAgent, SupportAgent
from api.auth import get_current_user_ws
from api.routers.auth_router import router as auth_router
from api.routers.billing_router import router as billing_router
from api.routers.conversations_router import router as conv_router
from api.routers.demo_router import router as demo_router
from api.routers.profile_router import router as profile_router
from api.routers.stats_router import router as stats_router
from config.settings import settings
from database.crud import (add_message, check_and_increment_messages,
                           create_conversation, get_profile,
                           update_conversation_title)
from database.database import get_db, init_db
from database.models import User

AGENT_TYPES = {
    "support":    SupportAgent,
    "sales":      SalesAgent,
    "automation": AutomationAgent,
    "content":    ContentAgent,
}

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend")

# limiter is imported from api.limiter


# ── App lifecycle ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fast: CREATE TABLE IF NOT EXISTS only — no ALTER TABLE, no lock contention.
    init_db()

    # ── Background: DB column migrations with retry ─────────────────────────
    # ALTER TABLE … ADD COLUMN needs ACCESS EXCLUSIVE lock.  During a rolling
    # deploy the old instance holds connections that can block it for minutes.
    # Running migrations in a background task lets the app yield immediately,
    # pass Render's /health check, and trigger the old-instance shutdown.
    # Once the old instance is gone the lock is free and the next retry succeeds.
    async def _migrate_with_retry():
        import asyncio as _aio
        from database.database import run_migrations
        attempt = 0
        while True:
            try:
                await _aio.to_thread(run_migrations)
                logger.info("DB migrations applied successfully (attempt %d)", attempt + 1)
                return
            except Exception as exc:
                attempt += 1
                wait = min(20, attempt * 4)   # 4 s, 8 s, 12 s, 16 s, 20 s …
                logger.info(
                    "Migration blocked (attempt %d) — retry in %ds: %s",
                    attempt, wait, exc,
                )
                await _aio.sleep(wait)

    # ── Background: pre-warm Groq connection ───────────────────────────────
    async def _prewarm():
        try:
            import httpx
            from groq import AsyncGroq
            _gc = AsyncGroq(
                api_key=settings.groq_api_key,
                timeout=httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0),
            )
            await _gc.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            logger.info("Groq connection pre-warmed successfully")
        except Exception as _e:
            logger.warning("Groq pre-warm failed (non-fatal): %s", _e)

    import asyncio as _asyncio
    _asyncio.create_task(_migrate_with_retry())
    _asyncio.create_task(_prewarm())
    logger.info("%s v%s — SaaS mode ready", settings.app_name, settings.app_version)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — origins from env var (comma-separated) or wildcard in dev.
# allow_credentials=True requires explicit origins, not "*".
_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=("*" not in _origins),
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(profile_router)
app.include_router(demo_router)
app.include_router(conv_router)
app.include_router(stats_router)


# ── Static pages ───────────────────────────────────────────────────────────────

def _html(name: str) -> HTMLResponse:
    path = os.path.join(FRONTEND, name)
    try:
        with open(path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        raise HTTPException(404, f"Page {name} introuvable")

@app.get("/",          response_class=HTMLResponse)
def root():            return _html("home.html")

@app.get("/login",     response_class=HTMLResponse)
def login_page():      return _html("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():  return _html("dashboard.html")

@app.get("/demo",           response_class=HTMLResponse)
def demo_page():            return _html("demo.html")

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page():  return _html("reset-password.html")

@app.get("/terms",   response_class=HTMLResponse)
def terms_page():    return _html("terms.html")

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page():  return _html("privacy.html")


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    stripe_ok  = bool(os.getenv("STRIPE_SECRET_KEY", "").strip())
    price_pro  = bool(os.getenv("STRIPE_PRICE_PRO", "").strip())
    price_ent  = bool(os.getenv("STRIPE_PRICE_ENTERPRISE", "").strip())
    return {"status": "ok", "version": settings.app_version, "mode": "saas",
            "stripe": stripe_ok, "price_pro": price_pro, "price_ent": price_ent}


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


# ── Authenticated WebSocket ────────────────────────────────────────────────────

@app.websocket("/ws/{agent_type}")
async def websocket_chat(
    websocket: WebSocket,
    agent_type: str,
    token: str = Query(default=""),
    db=Depends(get_db),
):
    if agent_type not in AGENT_TYPES:
        await websocket.close(code=4000); return

    user: User = await get_current_user_ws(token=token, db=db)
    if not user:
        await websocket.close(code=4001); return

    await websocket.accept()

    # Load tenant's company profile
    profile = get_profile(db, user.tenant_id)
    client_context = profile.to_agent_context() if profile and profile.company_name else ""

    agent = AGENT_TYPES[agent_type](client_context=client_context)

    # Create a conversation record
    conversation = create_conversation(
        db, user_id=user.id, tenant_id=user.tenant_id, agent_type=agent_type
    )

    await websocket.send_json({
        "type":           "session_created",
        "session_id":     conversation.id,
        "agent_name":     agent.name,
        "tenant_name":    user.tenant.name,
        "has_profile":    bool(client_context),
        "conversation_id": conversation.id,
    })

    _last_msg_time = 0.0  # per-connection rate limiter

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg = payload.get("message", "").strip()
            if not msg: continue

            # Per-message rate limit: max 1 message per second
            now = time.monotonic()
            if now - _last_msg_time < 1.0:
                await websocket.send_json({
                    "type": "error",
                    "message": "Envoyez vos messages moins vite 🙏"
                })
                continue
            _last_msg_time = now

            if msg.lower() in ("/reset", "reset"):
                agent.reset()
                await websocket.send_json({"type": "reset"})
                continue

            # Plan limit check (free = 100 messages/month)
            if not check_and_increment_messages(db, user.tenant_id):
                await websocket.send_json({
                    "type":    "limit_reached",
                    "message": "Vous avez atteint la limite de 100 messages/mois du plan Gratuit.",
                })
                continue

            # Persist user message
            add_message(db, conversation_id=conversation.id, role="user", content=msg)
            update_conversation_title(db, conversation.id, msg)

            # Stream & accumulate assistant response
            full_response = ""
            try:
                async for event in agent.chat_stream(msg):
                    await websocket.send_json(event)
                    if event["type"] == "token":
                        full_response += event["text"]
                    elif event["type"] == "end" and full_response:
                        add_message(db, conversation_id=conversation.id,
                                    role="assistant", content=full_response)
                        full_response = ""
            except Exception as exc:
                logger.error("Agent error (user=%s agent=%s): %s",
                             user.email, agent_type, exc, exc_info=True)
                # Send a generic message — don't expose internal details to client
                is_conn = any(k in str(exc).lower()
                              for k in ("connect", "timeout", "network", "502", "503"))
                client_msg = (
                    "Le serveur IA est en cours de démarrage. Réessayez dans quelques secondes."
                    if is_conn else
                    "Une erreur est survenue. Réessayez ou rechargez la page."
                )
                await websocket.send_json({"type": "error", "message": client_msg})

    except WebSocketDisconnect:
        pass
