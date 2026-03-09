"""Email utility — Resend.com integration with graceful dev fallback."""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("agentai.email")

RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", "").strip() or None
RESEND_FROM:    str            = os.getenv("RESEND_FROM", "AgentAI <noreply@agentai.co>")
APP_URL:        str            = os.getenv("APP_URL", "http://localhost:8000")


def _reset_html(reset_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8" /></head>
<body style="font-family:Inter,sans-serif;background:#0f1117;color:#e2e8f0;margin:0;padding:40px 0">
  <div style="max-width:480px;margin:0 auto;background:#1a1d27;border-radius:16px;border:1px solid #2e3147;overflow:hidden">
    <div style="background:linear-gradient(135deg,#6366f1,#818cf8);padding:32px;text-align:center">
      <div style="font-size:36px;margin-bottom:8px">🤖</div>
      <div style="font-size:20px;font-weight:700;color:#fff">AgentAI Platform</div>
    </div>
    <div style="padding:32px">
      <h2 style="margin:0 0 12px;font-size:20px;color:#e2e8f0">Réinitialisation de votre mot de passe</h2>
      <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:0 0 24px">
        Vous avez demandé à réinitialiser votre mot de passe. Cliquez sur le bouton ci-dessous.<br/>
        Ce lien est valable <strong style="color:#e2e8f0">1 heure</strong>.
      </p>
      <a href="{reset_url}" style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:14px">
        Réinitialiser mon mot de passe →
      </a>
      <p style="color:#64748b;font-size:12px;margin:24px 0 0">
        Si vous n'avez pas fait cette demande, ignorez cet email.<br/>
        Lien direct : <a href="{reset_url}" style="color:#818cf8">{reset_url}</a>
      </p>
    </div>
  </div>
</body>
</html>"""


async def send_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Send password-reset email via Resend.
    Falls back to console log when RESEND_API_KEY is not set (dev mode).
    Always returns True to avoid leaking whether an email exists.
    """
    if not RESEND_API_KEY:
        logger.info("[DEV — no RESEND_API_KEY] Reset URL for %s: %s", to_email, reset_url)
        return True

    payload = {
        "from":    RESEND_FROM,
        "to":      [to_email],
        "subject": "Réinitialisation de votre mot de passe AgentAI",
        "html":    _reset_html(reset_url),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                         "Content-Type": "application/json"},
                json=payload,
            )
            if res.status_code not in (200, 201):
                logger.error("Resend error %s: %s", res.status_code, res.text)
            return True          # always return True — no email enumeration
    except Exception as exc:
        logger.error("Email send failed: %s", exc, exc_info=True)
        return True
