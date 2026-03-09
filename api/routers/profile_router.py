"""Company profile — get / update."""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database.crud import get_profile, upsert_profile
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    company_name:   Optional[str]       = None
    website:        Optional[str]       = None
    sector:         Optional[str]       = None
    description:    Optional[str]       = None
    services:       Optional[List[str]] = None
    target_clients: Optional[List[str]] = None
    tone:           Optional[str]       = None
    language:       Optional[str]       = None
    faq:            Optional[str]       = None
    extra_docs:     Optional[str]       = None
    promo_codes:    Optional[List[str]] = None
    rules:          Optional[List[str]] = None


@router.get("")
def get_company_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, user.tenant_id)
    return {"profile": profile.to_dict() if profile else None}


@router.put("")
def update_company_profile(data: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = {k: v for k, v in data.dict().items() if v is not None}
    profile = upsert_profile(db, user.tenant_id, payload)
    return {"profile": profile.to_dict(), "message": "Profil mis à jour ✓"}
