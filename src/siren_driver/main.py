from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import verify_hmac_request
from .config import Settings
from .gpio import SirenHardware


class TriggerRequest(BaseModel):
    duration_seconds: float | None = Field(default=None, gt=0, le=60)


class TriggerResponse(BaseModel):
    accepted: bool
    duration_seconds: float
    message: str


@dataclass(frozen=True)
class AppState:
    settings: Settings
    hardware: SirenHardware


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

    def get_state(request: Request) -> AppState:
        return request.app.state.siren_state

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/trigger", response_model=TriggerResponse)
    async def trigger_siren(
        request: Request,
        state: AppState = Depends(get_state),
    ) -> JSONResponse:
        await verify_hmac_request(request, state.settings.webhook_secret, state.settings.auth_skew_seconds)

        try:
            payload = TriggerRequest.model_validate(await request.json())
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid request body") from exc

        duration_seconds = payload.duration_seconds or state.settings.default_duration_seconds
        if duration_seconds > state.settings.max_duration_seconds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"duration_seconds cannot exceed {state.settings.max_duration_seconds}",
            )

        result = state.hardware.trigger(duration_seconds)
        if not result.accepted:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.message)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=TriggerResponse(
                accepted=True,
                duration_seconds=duration_seconds,
                message=result.message,
            ).model_dump(),
        )

    return app


app = create_app()
