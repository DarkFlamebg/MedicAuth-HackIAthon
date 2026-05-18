"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from app.core.config import settings
from app.core.dependencies import rate_limiter_in_memory

router = APIRouter(
    dependencies=[Depends(rate_limiter_in_memory(times=7, seconds=1))]
)

@router.get("/health")
async def health_check():
    """
    Verifica el estado de la API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "services": {
            "notion": bool(settings.NOTION_TOKEN),
            "anthropic": bool(settings.ANTHROPIC_API_KEY)
        }
    }

@router.get("/ping")
async def ping():
    """Simple ping endpoint"""
    return {"ping": "pong"}
