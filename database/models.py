"""SQLAlchemy ORM models — multi-tenant SaaS."""
import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database.database import Base


def _uuid():
    return str(uuid.uuid4())


class Tenant(Base):
    """One row = one client company."""
    __tablename__ = "tenants"

    id         = Column(String(36), primary_key=True, default=_uuid)
    slug       = Column(String(100), unique=True, index=True, nullable=False)
    name       = Column(String(200), nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users        = relationship("User",           back_populates="tenant", cascade="all, delete-orphan")
    profile      = relationship("CompanyProfile", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    demo_sessions = relationship("DemoSession",  back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """Platform user — belongs to one tenant."""
    __tablename__ = "users"

    id              = Column(String(36), primary_key=True, default=_uuid)
    tenant_id       = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(200), default="")
    is_admin        = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")


class CompanyProfile(Base):
    """Detailed company profile — one per tenant. Feeds agent context."""
    __tablename__ = "company_profiles"

    id           = Column(String(36), primary_key=True, default=_uuid)
    tenant_id    = Column(String(36), ForeignKey("tenants.id"), unique=True, nullable=False, index=True)

    # Core identity
    company_name    = Column(String(200), default="")
    website         = Column(String(500), default="")
    sector          = Column(String(200), default="")
    description     = Column(Text, default="")

    # Sales context (stored as JSON arrays)
    services        = Column(Text, default="[]")   # ["Service A", "Service B"]
    target_clients  = Column(Text, default="[]")   # ["PME", "E-commerce"]
    promo_codes     = Column(Text, default="[]")   # ["CODE10 -10%"]
    rules           = Column(Text, default="[]")   # ["Ne pas promettre X"]

    # Communication
    tone            = Column(String(100), default="professionnel")
    language        = Column(String(10),  default="fr")

    # Knowledge base (free text — injected verbatim into prompt)
    faq             = Column(Text, default="")
    extra_docs      = Column(Text, default="")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="profile")

    # ── Helpers ──────────────────────────────────────────────────────────

    def _parse(self, field: str):
        val = getattr(self, field) or "[]"
        try:
            return json.loads(val)
        except Exception:
            return []

    def to_dict(self):
        return {
            "company_name":   self.company_name,
            "website":        self.website,
            "sector":         self.sector,
            "description":    self.description,
            "services":       self._parse("services"),
            "target_clients": self._parse("target_clients"),
            "promo_codes":    self._parse("promo_codes"),
            "rules":          self._parse("rules"),
            "tone":           self.tone,
            "language":       self.language,
            "faq":            self.faq,
            "extra_docs":     self.extra_docs,
            "updated_at":     self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_agent_context(self) -> str:
        """Render profile as a system-prompt block for agents."""
        lines = ["━━━ PROFIL ENTREPRISE ━━━"]
        if self.company_name: lines.append(f"Entreprise : {self.company_name}")
        if self.sector:       lines.append(f"Secteur : {self.sector}")
        if self.website:      lines.append(f"Site web : {self.website}")
        if self.description:  lines.append(f"Description : {self.description}")
        if self.tone:         lines.append(f"Ton à adopter : {self.tone}")

        svcs = self._parse("services")
        if svcs: lines.append(f"Services/Produits : {', '.join(svcs)}")

        targets = self._parse("target_clients")
        if targets: lines.append(f"Clients cibles : {', '.join(targets)}")

        if self.faq:
            lines.append(f"FAQ & informations clés :\n{self.faq}")
        if self.extra_docs:
            lines.append(f"Documentation :\n{self.extra_docs}")

        rules = self._parse("rules")
        if rules:
            lines.append("Règles impératives :")
            for r in rules:
                lines.append(f"  ⚠ {r}")

        codes = self._parse("promo_codes")
        if codes:
            lines.append(f"Codes promo : {', '.join(codes)}")

        lines.append("━━━ FIN PROFIL ━━━")
        return "\n".join(lines)


class DemoSession(Base):
    """Temporary session for prospects testing the platform (no auth)."""
    __tablename__ = "demo_sessions"

    id           = Column(String(36), primary_key=True, default=_uuid)
    tenant_id    = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    company_name = Column(String(200), default="")
    website      = Column(String(500), default="")
    sector       = Column(String(200), default="")
    context      = Column(Text, default="")
    created_at   = Column(DateTime, default=datetime.utcnow)
    expires_at   = Column(DateTime)

    tenant = relationship("Tenant", back_populates="demo_sessions")


class Conversation(Base):
    """A chat session between a user and one agent."""
    __tablename__ = "conversations"

    id         = Column(String(36), primary_key=True, default=_uuid)
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id  = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    agent_type = Column(String(50), nullable=False)
    title      = Column(String(500), default="")
    msg_count  = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan", order_by="Message.created_at")
    user   = relationship("User")
    tenant = relationship("Tenant")


class Message(Base):
    """Single message inside a Conversation."""
    __tablename__ = "messages"

    id              = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role            = Column(String(20), nullable=False)   # "user" | "assistant"
    content         = Column(Text, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
