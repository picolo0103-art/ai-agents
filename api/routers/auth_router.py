"""Register / Login / Me / Logout / Forgot-password endpoints."""
import re
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

from api.auth import clear_auth_cookie, create_token, get_current_user, set_auth_cookie
from api.email import APP_URL, send_reset_email, send_verify_email
from api.limiter import limiter
from database.crud import (authenticate, consume_reset_token, consume_verify_token,
                            create_reset_token, create_tenant, create_user,
                            create_verify_token, get_tenant_by_slug, get_user_by_email)
from database.database import get_db
from database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Format d'email invalide (ex: vous@entreprise.com)")
    return v

def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères")
    return v


class RegisterIn(BaseModel):
    company_name: str
    email: str
    password: str
    full_name: str = ""

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("company_name")
    @classmethod
    def check_company(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom de l'entreprise est obligatoire")
        return v.strip()


class LoginIn(BaseModel):
    email: str
    password: str


class ForgotPasswordIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)

class ResetPasswordIn(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")
        return v


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
        "id":        user.id,
        "email":     user.email,
        "full_name": user.full_name,
        "tenant_id": user.tenant_id,
        "is_admin":  user.is_admin,
    }

def _tenant_out(tenant) -> dict:
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, req: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(400, "Email déjà utilisé")

    slug   = _unique_slug(db, _slugify(req.company_name))
    tenant = create_tenant(db, name=req.company_name, slug=slug)
    user   = create_user(db, email=req.email, password=req.password,
                         full_name=req.full_name, tenant_id=tenant.id)
    token  = create_token(user.email)
    set_auth_cookie(response, token)

    # Send email verification link (non-blocking, fails silently)
    verify_token = create_verify_token(db, user.id)
    verify_url   = f"{APP_URL}/auth/verify-email?token={verify_token}"
    import asyncio
    asyncio.create_task(send_verify_email(user.email, verify_url))

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user":         _user_out(user),
        "tenant":       _tenant_out(tenant),
        "email_verification_sent": True,
    }


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, req: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = authenticate(db, req.email, req.password)
    if not user:
        raise HTTPException(401, "Email ou mot de passe incorrect")

    token = create_token(user.email)
    set_auth_cookie(response, token)

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user":         _user_out(user),
        "tenant":       _tenant_out(user.tenant),
    }


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Déconnecté"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {**_user_out(current_user), "tenant": _tenant_out(current_user.tenant)}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Consume the one-time email verification token."""
    ok = consume_verify_token(db, token)
    if not ok:
        raise HTTPException(400, "Lien invalide ou expiré. Reconnectez-vous pour recevoir un nouveau lien.")
    return {"message": "Email vérifié avec succès ! Vous pouvez maintenant utiliser toutes les fonctionnalités."}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, req: ForgotPasswordIn, db: Session = Depends(get_db)):
    """
    Always returns the same message to prevent email enumeration.
    In dev (no RESEND_API_KEY), the reset URL is printed to server logs.
    """
    user = get_user_by_email(db, req.email)
    if user:
        reset_token = create_reset_token(db, user.id)
        reset_url   = f"{APP_URL}/reset-password?token={reset_token.token}"
        await send_reset_email(user.email, reset_url)
    return {"message": "Si cet email est enregistré, vous recevrez un lien de réinitialisation sous peu."}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, req: ResetPasswordIn, db: Session = Depends(get_db)):
    ok = consume_reset_token(db, req.token, req.new_password)
    if not ok:
        raise HTTPException(400, "Lien invalide ou expiré. Veuillez refaire une demande.")
    return {"message": "Mot de passe mis à jour avec succès. Vous pouvez vous connecter."}
