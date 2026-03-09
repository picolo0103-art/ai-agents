"""Usage statistics per tenant."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database.crud import get_tenant_stats
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/stats", tags=["stats"])

AGENT_NAMES = {
    "support":    "Support Client",
    "sales":      "Sales & Prospection",
    "automation": "Automatisation",
    "content":    "Marketing & Contenu",
}

@router.get("")
def usage_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw = get_tenant_stats(db, user.tenant_id)
    # Enrich by_agent with display names
    by_agent = [
        {
            "type":  k,
            "name":  AGENT_NAMES.get(k, k),
            "count": v,
        }
        for k, v in raw["by_agent"].items()
    ]
    by_agent.sort(key=lambda x: x["count"], reverse=True)
    return {
        "total_conversations": raw["total_conversations"],
        "total_messages":      raw["total_messages"],
        "messages_today":      raw["messages_today"],
        "by_agent":            by_agent,
    }
