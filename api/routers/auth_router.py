"""Register / Login / Me endpoints."""
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import create_token, get_current_user
from database.crud import authenticate, create_tenant, create_user, get_tenant_by_slug, get_user_by_email
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    company_name: str
    email: str
    password: str
    full_name: str = ""

class LoginIn(BaseModel):
    email: str
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:50]

def _unique_slug(db: Session, base: str) -> str:
    slug, i = base, 1
    while get_tenant_by_slug(db, slug):
        slug = f"{base}-{i}"; i += 1
    return slug

def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "tenant_id": user.tenant_id,
        "is_admin": user.is_admin,
    }

def _tenant_out(tenant) -> dict:
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
def register(req: RegisterIn, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(400, "Email déjà utilisé")

    slug   = _unique_slug(db, _slugify(req.company_name))
    tenant = create_tenant(db, name=req.company_name, slug=slug)
    user   = create_user(db, email=req.email, password=req.password,
                         full_name=req.full_name, tenant_id=tenant.id)

    return {
        "access_token": create_token(user.email),
        "token_type": "bearer",
        "user": _user_out(user),
        "tenant": _tenant_out(tenant),
    }


@router.post("/login")
def login(req: LoginIn, db: Session = Depends(get_db)):
    user = authenticate(db, req.email, req.password)
    if not user:
        raise HTTPException(401, "Email ou mot de passe incorrect")

    return {
        "access_token": create_token(user.email),
        "token_type": "bearer",
        "user": _user_out(user),
        "tenant": _tenant_out(user.tenant),
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {**_user_out(current_user), "tenant": _tenant_out(current_user.tenant)}
