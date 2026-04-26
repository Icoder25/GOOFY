from fastapi import APIRouter
from pydantic import BaseModel
import structlog
import time

from app.services.gemini import is_configured as gemini_configured

router = APIRouter()
logger = structlog.get_logger()


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: float
    services: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Returns service status and dependency health.
    """
    
    logger.debug("health_check_called")
    
    services = {
        "firebase": "not_configured",
        "gemini": "ready" if gemini_configured() else "not_configured",
        "speech_to_text": "not_configured",
    }
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=time.time(),
        services=services,
    )
