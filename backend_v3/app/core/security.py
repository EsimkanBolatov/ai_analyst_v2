from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str,
    role: str,
    expires_delta: timedelta,
    secret: str,
    token_type: str,
) -> str:
    expire_at = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "exp": expire_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        secret=settings.jwt_secret_key,
        token_type="access",
    )


def create_refresh_token(subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes),
        secret=settings.jwt_refresh_secret_key,
        token_type="refresh",
    )


def _decode_token(token: str, secret: str, expired_message: str, invalid_message: str) -> dict:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=expired_message,
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=invalid_message,
        ) from exc


def decode_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return _decode_token(
        token=credentials.credentials,
        secret=settings.jwt_secret_key,
        expired_message="Token expired.",
        invalid_message="Invalid token.",
    )


def decode_refresh_token(token: str) -> dict:
    return _decode_token(
        token=token,
        secret=settings.jwt_refresh_secret_key,
        expired_message="Refresh token expired.",
        invalid_message="Invalid refresh token.",
    )
