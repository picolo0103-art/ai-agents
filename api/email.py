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


def _verify_html(verify_url: str) -> str:
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
      <h2 style="margin:0 0 12px;font-size:20px;color:#e2e8f0">Vérifiez votre adresse email</h2>
      <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:0 0 24px">
        Merci de vous être inscrit ! Cliquez sur le bouton ci-dessous pour activer votre compte.<br/>
        Ce lien est valable <strong style="color:#e2e8f0">24 heures</strong>.
      </p>
      <a href="{verify_url}" style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:14px">
        Vérifier mon email →
      </a>
      <p style="color:#64748b;font-size:12px;margin:24px 0 0">
        Si vous n'avez pas créé de compte, ignorez cet email.<br/>
        Lien direct : <a href="{verify_url}" style="color:#818cf8">{verify_url}</a>
      </p>
    </div>
  </div>
</body>
</html>"""


def _welcome_html(company_name: str, dashboard_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8" /></head>
<body style="font-family:Inter,sans-serif;background:#0f1117;color:#e2e8f0;margin:0;padding:40px 0">
  <div style="max-width:520px;margin:0 auto;background:#1a1d27;border-radius:16px;border:1px solid #2e3147;overflow:hidden">
    <div style="background:linear-gradient(135deg,#6366f1,#818cf8);padding:32px;text-align:center">
      <div style="font-size:36px;margin-bottom:8px">🤖</div>
      <div style="font-size:20px;font-weight:700;color:#fff">Bienvenue sur AgentAI Platform</div>
    </div>
    <div style="padding:32px">
      <h2 style="margin:0 0 12px;font-size:20px;color:#e2e8f0">Votre espace est prêt, {company_name} ! 🚀</h2>
      <p style="color:#94a3b8;font-size:14px;line-height:1.7;margin:0 0 24px">
        Vos 4 agents IA sont configurés et prêts à travailler pour vous.<br/>
        Commencez par personnaliser votre profil entreprise pour des résultats optimaux.
      </p>
      <div style="background:#242736;border-radius:12px;padding:20px;margin-bottom:24px">
        <p style="margin:0 0 12px;font-size:13px;font-weight:600;color:#e2e8f0">Vos agents disponibles :</p>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div style="font-size:13px;color:#94a3b8">🎧 <strong style="color:#e2e8f0">Support Client</strong> — Répond 24h/24 à vos clients</div>
          <div style="font-size:13px;color:#94a3b8">📈 <strong style="color:#e2e8f0">Sales & Prospection</strong> — Emails et scripts de vente BANT</div>
          <div style="font-size:13px;color:#94a3b8">⚙️ <strong style="color:#e2e8f0">Automatisation</strong> — Rapports et analyse de données</div>
          <div style="font-size:13px;color:#94a3b8">✍️ <strong style="color:#e2e8f0">Marketing & Contenu</strong> — Articles, posts, campagnes</div>
        </div>
      </div>
      <a href="{dashboard_url}" style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:14px">
        Accéder à mon tableau de bord →
      </a>
      <p style="color:#64748b;font-size:12px;margin:24px 0 0">
        Des questions ? Répondez directement à cet email, on est là pour vous aider.<br/>
        <a href="{dashboard_url}" style="color:#818cf8">AgentAI Platform</a>
      </p>
    </div>
  </div>
</body>
</html>"""


async def send_welcome_email(to_email: str, company_name: str) -> bool:
    """Send welcome email after successful email verification."""
    dashboard_url = f"{APP_URL}/dashboard"
    if not RESEND_API_KEY:
        logger.info("[DEV — no RESEND_API_KEY] Welcome email for %s (%s)", to_email, company_name)
        return True
    payload = {
        "from":    RESEND_FROM,
        "to":      [to_email],
        "subject": f"Bienvenue sur AgentAI, {company_name} ! Vos agents sont prêts 🚀",
        "html":    _welcome_html(company_name, dashboard_url),
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
            return True
    except Exception as exc:
        logger.error("Welcome email send failed: %s", exc, exc_info=True)
        return True


async def send_verify_email(to_email: str, verify_url: str) -> bool:
    """Send email-verification link. Falls back to console log in dev mode."""
    if not RESEND_API_KEY:
        logger.info("[DEV — no RESEND_API_KEY] Verify URL for %s: %s", to_email, verify_url)
        return True
    payload = {
        "from":    RESEND_FROM,
        "to":      [to_email],
        "subject": "Vérifiez votre adresse email — AgentAI",
        "html":    _verify_html(verify_url),
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
            return True
    except Exception as exc:
        logger.error("Verify email send failed: %s", exc, exc_info=True)
        return True


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
