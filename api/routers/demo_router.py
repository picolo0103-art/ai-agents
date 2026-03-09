"""Demo mode — public, no auth. Prospects can test the platform."""
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from agents import SalesAgent
from database.crud import create_demo_session, get_demo_session
from database.database import get_db

logger = logging.getLogger("agentai.demo")

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoStartIn(BaseModel):
    company_name: str
    website: str
    sector: str
    description: Optional[str] = ""

    @field_validator("company_name")
    @classmethod
    def check_company(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom de l'entreprise est obligatoire")
        return v.strip()[:200]

    @field_validator("website")
    @classmethod
    def check_website(cls, v: str) -> str:
        return v.strip()[:500]

    @field_validator("sector")
    @classmethod
    def check_sector(cls, v: str) -> str:
        return v.strip()[:200]

    @field_validator("description")
    @classmethod
    def check_description(cls, v: str) -> str:
        return (v or "").strip()[:1000]


def _build_demo_context(company_name: str, website: str, sector: str, description: str) -> str:
    return "\n".join([
        "━━━ MODE DÉMO — VOTRE ENTREPRISE ━━━",
        f"Entreprise : {company_name}",
        f"Site web : {website}",
        f"Secteur : {sector}",
        *([ f"Description : {description}"] if description else []),
        "",
        "MISSION DE L'AGENT :",
        "Tu es un expert commercial IA. Aide cette entreprise à :",
        "  1. Identifier ses clients idéaux (ICP)",
        "  2. Trouver des prospects qualifiés",
        "  3. Rédiger des emails de prospection personnalisés",
        "  4. Créer des messages LinkedIn percutants",
        "  5. Préparer un script de rendez-vous commercial",
        "Commence par analyser l'entreprise et proposer un plan d'action.",
        "━━━ FIN DÉMO ━━━",
    ])


@router.post("/start")
def start_demo(req: DemoStartIn, db: Session = Depends(get_db)):
    context = _build_demo_context(req.company_name, req.website, req.sector, req.description or "")
    session = create_demo_session(db, company_name=req.company_name,
                                  website=req.website, sector=req.sector, context=context)
    return {"session_id": session.id, "expires_in": "24h",
            "message": f"Session démo créée pour {req.company_name}"}


@router.websocket("/ws/{session_id}")
async def demo_ws(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    demo = get_demo_session(db, session_id)
    if not demo:
        await websocket.close(code=4004); return

    await websocket.accept()
    agent = SalesAgent(client_context=demo.context)

    await websocket.send_json({
        "type": "session_created",
        "company": demo.company_name,
        "message": f"🚀 Agent IA prêt pour {demo.company_name}",
    })

    _last_msg_time = 0.0  # per-connection rate limiter

    try:
        while True:
            data = await websocket.receive_text()
            msg  = json.loads(data).get("message", "").strip()
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

            # Truncate message to prevent prompt injection via oversized input
            msg = msg[:4000]

            try:
                async for event in agent.chat_stream(msg):
                    await websocket.send_json(event)
            except Exception as exc:
                logger.error("Demo agent error (session=%s): %s",
                             session_id, exc, exc_info=True)
                # Generic message to client — don't expose internal stack traces
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
