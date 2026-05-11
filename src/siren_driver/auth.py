from __future__ import annotations

import hmac

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials


def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    expected_token: str,
) -> None:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized
    if credentials.scheme.lower() != "bearer":
        raise unauthorized
    if not hmac.compare_digest(credentials.credentials, expected_token):
        raise unauthorized
