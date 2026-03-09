"""Company profile — get / update."""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database.crud import get_profile, upsert_profile
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    company_name:   Optional[str]       = Field(None, max_length=200)
    website:        Optional[str]       = Field(None, max_length=500)
    sector:         Optional[str]       = Field(None, max_length=200)
    description:    Optional[str]       = Field(None, max_length=2000)
    services:       Optional[List[str]] = None
    target_clients: Optional[List[str]] = None
    tone:           Optional[str]       = Field(None, max_length=100)
    language:       Optional[str]       = Field(None, max_length=10)
    faq:            Optional[str]       = Field(None, max_length=10000)
    extra_docs:     Optional[str]       = Field(None, max_length=10000)
    promo_codes:    Optional[List[str]] = None
    rules:          Optional[List[str]] = None

    @field_validator("services", "target_clients", "promo_codes", "rules", mode="before")
    @classmethod
    def check_list_length(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Maximum 50 éléments par liste")
        return v

    @field_validator("services", "target_clients", "promo_codes", "rules", mode="after")
    @classmethod
    def truncate_list_items(cls, v):
        if v is None:
            return v
        return [str(item)[:200] for item in v]


@router.get("")
def get_company_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, user.tenant_id)
    return {"profile": profile.to_dict() if profile else None}


@router.put("")
def update_company_profile(data: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    profile = upsert_profile(db, user.tenant_id, payload)
    return {"profile": profile.to_dict(), "message": "Profil mis à jour ✓"}
