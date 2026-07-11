import platform

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    import anthropic
    import fastapi

    return HealthResponse(
        status="ok",
        versions={
            "app": "0.1.0",
            "python": platform.python_version(),
            "fastapi": fastapi.__version__,
            "anthropic": anthropic.__version__,
            "vlm_model": get_settings().vlm_model,
        },
    )
