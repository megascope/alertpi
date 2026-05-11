from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
import math

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .auth import verify_bearer_token
from .config import Settings
from .gpio import SirenHardware


class TriggerRequest(BaseModel):
    duration_seconds: float | None = Field(default=None, gt=0, le=60, allow_inf_nan=False)


class TriggerResponse(BaseModel):
    accepted: bool
    duration_seconds: float
    message: str


@dataclass(frozen=True)
class AppState:
    settings: Settings
    hardware: SirenHardware


bearer_auth = HTTPBearer(auto_error=False)
logger = logging.getLogger("uvicorn.error")


def _sanitize_for_json(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_json(item) for item in value]
    return value


def _request_source_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_hop = forwarded_for.split(",", maxsplit=1)[0].strip()
        if first_hop:
            return first_hop

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = Settings.from_env()
        app.state.siren_state = AppState(
            settings=settings,
            hardware=SirenHardware(settings.gpio_pin),
        )
        try:
            yield
        finally:
            app.state.siren_state.hardware.shutdown()

    app = FastAPI(title="Siren Driver", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": _sanitize_for_json(exc.errors())},
        )

    def get_state(request: Request) -> AppState:
        return request.app.state.siren_state

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/trigger", response_model=TriggerResponse, status_code=status.HTTP_202_ACCEPTED)
    async def trigger_siren(
        request: Request,
        state: AppState = Depends(get_state),
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_auth),
        payload: TriggerRequest = Body(default_factory=TriggerRequest),
    ) -> TriggerResponse:
        verify_bearer_token(credentials, state.settings.bearer_token)

        source_ip = _request_source_ip(request)
        duration_seconds = payload.duration_seconds or state.settings.default_duration_seconds
        if duration_seconds > state.settings.max_duration_seconds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"duration_seconds cannot exceed {state.settings.max_duration_seconds}",
            )

        result = state.hardware.trigger(duration_seconds)
        if not result.accepted:
            logger.warning("Trigger rejected from %s for %.2fs: %s", source_ip, duration_seconds, result.message)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.message)

        logger.info("Trigger accepted from %s for %.2fs", source_ip, duration_seconds)

        return TriggerResponse(
            accepted=True,
            duration_seconds=duration_seconds,
            message=result.message,
        )

    return app


app = create_app()
