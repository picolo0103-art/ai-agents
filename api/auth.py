"""JWT authentication helpers — Bearer header + httpOnly cookie dual support."""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database.database import get_db
from database.crud import get_user_by_email
from database.models import User

SECRET_KEY  = os.getenv("SECRET_KEY", "changeme-use-a-long-random-string-in-production")
ALGORITHM   = "HS256"
TOKEN_DAYS  = 7
COOKIE_NAME = "access_token"

_bearer = HTTPBearer(auto_error=False)


def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(days=TOKEN_DAYS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    """Set a secure httpOnly cookie carrying the JWT."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,          # HTTPS only in production
        samesite="lax",
        max_age=TOKEN_DAYS * 86400,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _decode(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _extract_token(
    creds: Optional[HTTPAuthorizationCredentials],
    cookie_token: Optional[str],
) -> Optional[str]:
    """Accept token from Bearer header OR httpOnly cookie."""
    if creds and creds.credentials:
        return creds.credentials
    return cookie_token or None


async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    cookie_token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(creds, cookie_token)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non authentifié")
    email = _decode(token)
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide")
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur introuvable")
    return user


async def get_current_user_ws(
    token: str = Query(default=""),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """WebSocket auth — token passed as ?token= query param (headers not supported in WS)."""
    if not token:
        return None
    email = _decode(token)
    if not email:
        return None
    return get_user_by_email(db, email)
