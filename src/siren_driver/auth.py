from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass
from time import time

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthResult:
    timestamp: int


def _parse_signature(signature_header: str) -> str:
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        raise ValueError("invalid signature format")
    signature = signature_header[len(prefix) :]
    if len(signature) != 64:
        raise ValueError("invalid signature length")
    return signature


async def verify_hmac_request(request: Request, webhook_secret: str, skew_seconds: int) -> AuthResult:
    timestamp_header = request.headers.get("X-Siren-Timestamp")
    signature_header = request.headers.get("X-Siren-Signature")

    if not timestamp_header or not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authentication headers")

    try:
        timestamp = int(timestamp_header)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid timestamp") from exc

    if abs(int(time()) - timestamp) > skew_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="timestamp outside allowed skew")

    raw_body = await request.body()
    signing_input = f"{timestamp_header}.".encode("utf-8") + raw_body
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).hexdigest()

    try:
        provided_signature = _parse_signature(signature_header)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature") from exc

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="signature mismatch")

    return AuthResult(timestamp=timestamp)
