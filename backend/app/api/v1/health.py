from fastapi import APIRouter

from app.core.config import settings
from app.core.responses import ok

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Service health probe")
async def health() -> dict:
    return ok(
        {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION},
        message="Service healthy",
    )
