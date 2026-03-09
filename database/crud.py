"""CRUD helpers — one function per operation, thin and testable."""
import json
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database.models import CompanyProfile, DemoSession, Tenant, User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)


# ── Tenant ────────────────────────────────────────────────────────────────────

def get_tenant(db: Session, tenant_id: str) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()

def get_tenant_by_slug(db: Session, slug: str) -> Optional[Tenant]:
    return db.query(Tenant).filter(Tenant.slug == slug).first()

def create_tenant(db: Session, name: str, slug: str) -> Tenant:
    t = Tenant(name=name, slug=slug)
    db.add(t); db.commit(); db.refresh(t)
    return t


# ── User ──────────────────────────────────────────────────────────────────────

def get_user(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, *, email: str, password: str,
                full_name: str, tenant_id: str, is_admin: bool = True) -> User:
    u = User(email=email, hashed_password=hash_password(password),
             full_name=full_name, tenant_id=tenant_id, is_admin=is_admin)
    db.add(u); db.commit(); db.refresh(u)
    return u

def authenticate(db: Session, email: str, password: str) -> Optional[User]:
    u = get_user_by_email(db, email)
    return u if (u and verify_password(password, u.hashed_password)) else None


# ── Company Profile ───────────────────────────────────────────────────────────

def get_profile(db: Session, tenant_id: str) -> Optional[CompanyProfile]:
    return db.query(CompanyProfile).filter(CompanyProfile.tenant_id == tenant_id).first()

def upsert_profile(db: Session, tenant_id: str, data: dict) -> CompanyProfile:
    p = get_profile(db, tenant_id)
    if not p:
        p = CompanyProfile(tenant_id=tenant_id)
        db.add(p)

    list_fields = {"services", "target_clients", "promo_codes", "rules"}
    for k, v in data.items():
        if v is None:
            continue
        if k in list_fields:
            setattr(p, k, json.dumps(v if isinstance(v, list) else [v], ensure_ascii=False))
        elif hasattr(p, k):
            setattr(p, k, v)

    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return p


# ── Demo Session ──────────────────────────────────────────────────────────────

def create_demo_session(db: Session, *, company_name: str,
                        website: str, sector: str, context: str) -> DemoSession:
    s = DemoSession(
        company_name=company_name, website=website,
        sector=sector, context=context,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(s); db.commit(); db.refresh(s)
    return s

def get_demo_session(db: Session, session_id: str) -> Optional[DemoSession]:
    s = db.query(DemoSession).filter(DemoSession.id == session_id).first()
    if s and s.expires_at < datetime.utcnow():
        return None
    return s
