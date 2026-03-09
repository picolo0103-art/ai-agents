"""JWT authentication helpers."""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database.database import get_db
from database.crud import get_user_by_email
from database.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-use-a-long-random-string-in-production")
ALGORITHM  = "HS256"
TOKEN_DAYS = 7

_bearer = HTTPBearer(auto_error=False)


def create_token(email: str) -> str:
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(days=TOKEN_DAYS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    token = creds.credentials if creds else None
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
    """For WebSocket connections — token passed as ?token= query param."""
    if not token:
        return None
    email = _decode(token)
    if not email:
        return None
    return get_user_by_email(db, email)
