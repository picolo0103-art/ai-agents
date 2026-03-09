"""Demo mode — public, no auth. Prospects can test the platform."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agents import SalesAgent
from database.crud import create_demo_session, get_demo_session
from database.database import get_db

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoStartIn(BaseModel):
    company_name: str
    website: str
    sector: str
    description: Optional[str] = ""


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

    try:
        while True:
            data = await websocket.receive_text()
            msg  = json.loads(data).get("message", "").strip()
            if not msg: continue
            async for event in agent.chat_stream(msg):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
