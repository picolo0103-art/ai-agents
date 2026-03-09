"""CRUD helpers — one function per operation, thin and testable."""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from database.models import (CompanyProfile, Conversation, DemoSession,
                              Message, PasswordResetToken, Tenant, User)


# ── Password (bcrypt direct — compatible with all versions) ───────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


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


# ── Conversations ──────────────────────────────────────────────────────────────

def create_conversation(db: Session, *, user_id: str, tenant_id: str,
                        agent_type: str, title: str = "") -> Conversation:
    c = Conversation(user_id=user_id, tenant_id=tenant_id,
                     agent_type=agent_type, title=title)
    db.add(c); db.commit(); db.refresh(c)
    return c

def update_conversation_title(db: Session, conversation_id: str, title: str) -> None:
    c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if c and not c.title:
        c.title = title[:120]
        db.commit()

def add_message(db: Session, *, conversation_id: str, role: str, content: str) -> Message:
    m = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(m)
    # bump conversation updated_at + msg_count
    c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if c:
        c.updated_at = datetime.utcnow()
        c.msg_count  = (c.msg_count or 0) + 1
    db.commit()
    return m

def get_conversations(db: Session, tenant_id: str, limit: int = 30):
    return (db.query(Conversation)
              .filter(Conversation.tenant_id == tenant_id)
              .order_by(Conversation.updated_at.desc())
              .limit(limit).all())

def get_conversation(db: Session, conversation_id: str,
                     tenant_id: str) -> Optional[Conversation]:
    return (db.query(Conversation)
              .filter(Conversation.id == conversation_id,
                      Conversation.tenant_id == tenant_id)
              .first())

def delete_conversation(db: Session, conversation_id: str, tenant_id: str) -> bool:
    c = get_conversation(db, conversation_id, tenant_id)
    if not c:
        return False
    db.delete(c); db.commit()
    return True


# ── Password Reset ────────────────────────────────────────────────────────────

def create_reset_token(db: Session, user_id: str) -> PasswordResetToken:
    """Invalidate any previous tokens for this user, then create a fresh one."""
    db.query(PasswordResetToken)\
      .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used == False)\
      .update({"used": True})
    db.commit()
    t = PasswordResetToken(
        user_id    = user_id,
        token      = secrets.token_urlsafe(48),
        expires_at = datetime.utcnow() + timedelta(hours=1),
    )
    db.add(t); db.commit(); db.refresh(t)
    return t

def get_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    """Return token only if valid (not used + not expired)."""
    t = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not t or t.used or t.expires_at < datetime.utcnow():
        return None
    return t

def consume_reset_token(db: Session, token: str, new_password: str) -> bool:
    """Validate token, update password, mark token used. Returns success."""
    t = get_reset_token(db, token)
    if not t:
        return False
    user = db.query(User).filter(User.id == t.user_id).first()
    if not user:
        return False
    user.hashed_password = hash_password(new_password)
    t.used = True
    db.commit()
    return True


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_tenant_stats(db: Session, tenant_id: str) -> dict:
    from sqlalchemy import func
    total_conv = db.query(func.count(Conversation.id))\
                   .filter(Conversation.tenant_id == tenant_id).scalar() or 0
    total_msg  = db.query(func.count(Message.id))\
                   .join(Conversation)\
                   .filter(Conversation.tenant_id == tenant_id).scalar() or 0
    # per-agent counts
    agent_rows = (db.query(Conversation.agent_type, func.count(Conversation.id))
                    .filter(Conversation.tenant_id == tenant_id)
                    .group_by(Conversation.agent_type).all())
    by_agent = {row[0]: row[1] for row in agent_rows}
    # today
    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_msg = db.query(func.count(Message.id))\
                  .join(Conversation)\
                  .filter(Conversation.tenant_id == tenant_id,
                          Message.created_at >= today_start).scalar() or 0
    return {
        "total_conversations": total_conv,
        "total_messages":      total_msg,
        "messages_today":      today_msg,
        "by_agent":            by_agent,
    }
