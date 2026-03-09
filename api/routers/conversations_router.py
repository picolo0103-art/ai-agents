"""Conversation history — list, read, delete."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database.crud import delete_conversation, get_conversation, get_conversations
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/conversations", tags=["conversations"])

AGENT_ICONS = {
    "support":    "🎧",
    "sales":      "📈",
    "automation": "⚙️",
    "content":    "✍️",
}

def _conv_out(c) -> dict:
    return {
        "id":         c.id,
        "agent_type": c.agent_type,
        "agent_icon": AGENT_ICONS.get(c.agent_type, "🤖"),
        "title":      c.title or "Nouvelle conversation",
        "msg_count":  c.msg_count or 0,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat(),
    }

def _msg_out(m) -> dict:
    return {
        "id":         m.id,
        "role":       m.role,
        "content":    m.content,
        "created_at": m.created_at.isoformat(),
    }


@router.get("")
def list_conversations(
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convs = get_conversations(db, user.tenant_id, limit=limit)
    return {"conversations": [_conv_out(c) for c in convs]}


@router.get("/{conversation_id}")
def get_conversation_detail(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = get_conversation(db, conversation_id, user.tenant_id)
    if not c:
        raise HTTPException(404, "Conversation introuvable")
    return {
        "conversation": _conv_out(c),
        "messages":     [_msg_out(m) for m in c.messages],
    }


@router.delete("/{conversation_id}")
def remove_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = delete_conversation(db, conversation_id, user.tenant_id)
    if not ok:
        raise HTTPException(404, "Conversation introuvable")
    return {"message": "Conversation supprimée"}
